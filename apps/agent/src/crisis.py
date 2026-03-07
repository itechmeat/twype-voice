from __future__ import annotations

import json
import logging
import re
import uuid
from dataclasses import dataclass, field
from re import Pattern

import httpx
from languages import normalize_language_code
from livekit.agents import llm
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from src.models.agent_config import AgentConfig
from src.models.crisis_contact import CrisisContact
from src.models.message import Message

logger = logging.getLogger("twype-agent.crisis")

_CLASSIFIER_PROMPT = (
    "You are a crisis detection classifier. Review only the current user utterance and decide "
    "whether it indicates a real safety crisis. Output ONLY JSON with keys: "
    '"label" ("crisis" or "not_crisis"), "confidence" (0.0-1.0), and "category" '
    '("suicide", "self_harm", "acute_symptoms", or "violence"). '
    "Treat imminent self-harm, suicidal intent, threats toward others, severe panic with loss "
    "of control, and acute disorganization as crisis. Ignore obvious idioms and hyperbole."
)

_DEFAULT_CRISIS_CATEGORY = "acute_symptoms"
_SUPPORTED_CATEGORIES = {"suicide", "self_harm", "acute_symptoms", "violence"}


@dataclass(slots=True, frozen=True)
class CrisisContactInfo:
    language: str
    locale: str | None
    contact_type: str
    name: str
    phone: str | None
    url: str | None
    description: str
    priority: int

    def as_payload(self) -> dict[str, str | int | None]:
        return {
            "language": self.language,
            "locale": self.locale,
            "contact_type": self.contact_type,
            "name": self.name,
            "phone": self.phone,
            "url": self.url,
            "description": self.description,
            "priority": self.priority,
        }


@dataclass(slots=True, frozen=True)
class CrisisKeywordRule:
    language: str
    category: str
    pattern: str
    regex: bool
    compiled_pattern: Pattern[str] | None = field(default=None, repr=False, compare=False)


@dataclass(slots=True, frozen=True)
class CrisisKeywordMatch:
    language: str
    category: str
    pattern: str


@dataclass(slots=True, frozen=True)
class CrisisClassification:
    label: str
    confidence: float
    category: str
    fail_safe: bool = False


@dataclass(slots=True)
class CrisisIntervention:
    chat_ctx: llm.ChatContext
    category: str
    confidence: float | None
    tier: int
    contacts: list[CrisisContactInfo]
    session_language: str
    used_high_distress: bool
    user_message_id: uuid.UUID | None = None


class CrisisDetector:
    def __init__(
        self,
        *,
        sessionmaker: async_sessionmaker[AsyncSession],
        base_url: str,
        api_key: str,
        model: str,
        enabled: bool = True,
        classifier_timeout: float = 3.0,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._sessionmaker = sessionmaker
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._enabled = enabled
        self._classifier_timeout = classifier_timeout
        self._http_client = http_client or httpx.AsyncClient(
            timeout=httpx.Timeout(self._classifier_timeout)
        )
        self._owns_http_client = http_client is None
        self._keyword_cache: dict[str, list[CrisisKeywordRule]] = {}
        self._contacts_cache: dict[str, list[CrisisContactInfo]] = {}

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def load_keywords(self) -> None:
        if not self._enabled:
            return

        async with self._sessionmaker() as session:
            result = await session.execute(
                select(AgentConfig).where(
                    AgentConfig.is_active.is_(True),
                    AgentConfig.key.like("crisis_keywords_%"),
                )
            )
            rows = result.scalars().all()

        keyword_cache: dict[str, list[CrisisKeywordRule]] = {}
        for row in rows:
            language = normalize_language_code(row.locale) or normalize_language_code(
                row.key.removeprefix("crisis_keywords_")
            )
            if language is None:
                continue

            payload = json.loads(row.value)
            if not isinstance(payload, dict):
                continue

            language_rules = keyword_cache.setdefault(language, [])
            for category, entries in payload.items():
                if category not in _SUPPORTED_CATEGORIES or not isinstance(entries, list):
                    continue
                for entry in entries:
                    if not isinstance(entry, dict):
                        continue
                    pattern = entry.get("pattern")
                    regex = entry.get("regex", False)
                    if not isinstance(pattern, str) or not pattern.strip():
                        continue
                    compiled_pattern: Pattern[str] | None = None
                    if bool(regex):
                        try:
                            compiled_pattern = re.compile(pattern.strip(), re.IGNORECASE)
                        except re.error:
                            logger.warning(
                                "skipping invalid crisis regex language=%s category=%s pattern=%r",
                                language,
                                category,
                                pattern,
                            )
                            continue
                    language_rules.append(
                        CrisisKeywordRule(
                            language=language,
                            category=category,
                            pattern=pattern.strip(),
                            regex=bool(regex),
                            compiled_pattern=compiled_pattern,
                        )
                    )

        self._keyword_cache = keyword_cache

    async def preload_contacts(self, language: str | None) -> None:
        if not self._enabled:
            return
        await self.get_contacts(language)

    async def aclose(self) -> None:
        if not self._owns_http_client:
            return
        await self._http_client.aclose()

    async def get_contacts(self, language: str | None) -> list[CrisisContactInfo]:
        normalized_language = normalize_language_code(language) or "en"
        if normalized_language in self._contacts_cache:
            return self._contacts_cache[normalized_language]

        contacts = await self._fetch_contacts_for_language(normalized_language)
        if contacts:
            self._contacts_cache[normalized_language] = contacts
            return contacts

        if normalized_language != "en":
            if "en" in self._contacts_cache:
                self._contacts_cache[normalized_language] = self._contacts_cache["en"]
                return self._contacts_cache["en"]

            english_contacts = await self._fetch_contacts_for_language("en")
            self._contacts_cache["en"] = english_contacts
            self._contacts_cache[normalized_language] = english_contacts
            return english_contacts

        self._contacts_cache[normalized_language] = []
        return []

    async def before_llm_cb(
        self,
        chat_ctx: llm.ChatContext,
        *,
        session_language: str | None,
        high_distress: bool = False,
        user_message_id: uuid.UUID | None = None,
    ) -> CrisisIntervention | None:
        if not self._enabled:
            return None

        message = self._last_user_message(chat_ctx)
        if message is None:
            return None

        extra = message.extra if isinstance(message.extra, dict) else {}
        if extra.get("proactive") is True:
            return None

        text = message.text_content.strip()
        if not text:
            return None

        language = self._resolve_message_language(extra, session_language)
        keyword_match = self._find_keyword_match(text, preferred_language=language)
        if keyword_match is None and not high_distress:
            return None

        classification = await self._classify(
            text,
            language=language,
            keyword_match=keyword_match,
            high_distress=high_distress,
        )
        if classification.label != "crisis" or classification.confidence < 0.5:
            return None

        contacts = await self.get_contacts(language)
        if user_message_id is not None:
            await self._flag_message_as_crisis(user_message_id)

        category = keyword_match.category if keyword_match is not None else classification.category
        if classification.category in _SUPPORTED_CATEGORIES:
            category = classification.category

        logger.warning(
            (
                "crisis detected tier=2 category=%s confidence=%.2f "
                "high_distress=%s user_message_id=%s"
            ),
            category,
            classification.confidence,
            high_distress,
            user_message_id,
        )

        return CrisisIntervention(
            chat_ctx=self._build_crisis_chat_context(
                text=text,
                language=language,
                contacts=contacts,
            ),
            category=category,
            confidence=classification.confidence,
            tier=2,
            contacts=contacts,
            session_language=language,
            used_high_distress=high_distress,
            user_message_id=user_message_id,
        )

    async def _fetch_contacts_for_language(self, language: str) -> list[CrisisContactInfo]:
        async with self._sessionmaker() as session:
            result = await session.execute(
                select(CrisisContact)
                .where(
                    CrisisContact.is_active.is_(True),
                    CrisisContact.language == language,
                )
                .order_by(CrisisContact.priority.asc(), CrisisContact.name.asc())
            )
            rows = result.scalars().all()

        return [
            CrisisContactInfo(
                language=row.language,
                locale=row.locale,
                contact_type=row.contact_type,
                name=row.name,
                phone=row.phone,
                url=row.url,
                description=row.description,
                priority=row.priority,
            )
            for row in rows
        ]

    def _find_keyword_match(
        self,
        text: str,
        *,
        preferred_language: str,
    ) -> CrisisKeywordMatch | None:
        if not text.strip():
            return None

        lowered_text = text.lower()
        for language in self._ordered_languages(preferred_language):
            for rule in self._keyword_cache.get(language, []):
                if rule.regex:
                    compiled_pattern = rule.compiled_pattern
                    if compiled_pattern is None:
                        try:
                            compiled_pattern = re.compile(rule.pattern, re.IGNORECASE)
                        except re.error:
                            logger.warning(
                                (
                                    "ignoring invalid cached crisis regex "
                                    "language=%s category=%s pattern=%r"
                                ),
                                rule.language,
                                rule.category,
                                rule.pattern,
                            )
                            continue

                    if compiled_pattern.search(text):
                        return CrisisKeywordMatch(
                            language=rule.language,
                            category=rule.category,
                            pattern=rule.pattern,
                        )
                    continue

                if rule.pattern.lower() in lowered_text:
                    return CrisisKeywordMatch(
                        language=rule.language,
                        category=rule.category,
                        pattern=rule.pattern,
                    )

        return None

    def _ordered_languages(self, preferred_language: str) -> list[str]:
        ordered = [preferred_language]
        for language in self._keyword_cache:
            if language not in ordered:
                ordered.append(language)
        if "en" not in ordered:
            ordered.append("en")
        return ordered

    async def _classify(
        self,
        text: str,
        *,
        language: str,
        keyword_match: CrisisKeywordMatch | None,
        high_distress: bool,
    ) -> CrisisClassification:
        fallback_category = (
            keyword_match.category if keyword_match is not None else _DEFAULT_CRISIS_CATEGORY
        )
        user_prompt = (
            f"Language: {language}\n"
            f"High distress signal: {'yes' if high_distress else 'no'}\n"
            f"Keyword category hint: {fallback_category}\n"
            f"Utterance: {text}"
        )
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": _CLASSIFIER_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.0,
            "max_tokens": 80,
        }

        try:
            response = await self._http_client.post(
                f"{self._base_url}/v1/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=payload,
            )
            response.raise_for_status()
        except (TimeoutError, httpx.TimeoutException):
            return CrisisClassification(
                label="crisis",
                confidence=1.0,
                category=fallback_category,
                fail_safe=True,
            )
        except Exception:
            logger.exception("crisis classifier failed; applying fail-safe")
            return CrisisClassification(
                label="crisis",
                confidence=1.0,
                category=fallback_category,
                fail_safe=True,
            )

        try:
            content = self._extract_completion_content(response.json())
            parsed = json.loads(content)
        except (TypeError, ValueError, json.JSONDecodeError):
            logger.warning("crisis classifier returned invalid JSON; applying fail-safe")
            return CrisisClassification(
                label="crisis",
                confidence=1.0,
                category=fallback_category,
                fail_safe=True,
            )

        label = str(parsed.get("label", "not_crisis")).strip().lower()
        try:
            confidence = float(parsed.get("confidence", 0.0))
        except (ValueError, TypeError):
            confidence = 1.0
        category = str(parsed.get("category", fallback_category)).strip().lower()
        if category not in _SUPPORTED_CATEGORIES:
            category = fallback_category

        if label not in {"crisis", "not_crisis"}:
            label = "crisis"
            confidence = max(confidence, 1.0)

        # 0.5 covers both the confident crisis path (>= 0.7) and the ambiguous-but-safe path.
        return CrisisClassification(
            label=label,
            confidence=max(0.0, min(1.0, confidence)),
            category=category,
            fail_safe=False,
        )

    def _build_crisis_chat_context(
        self,
        *,
        text: str,
        language: str,
        contacts: list[CrisisContactInfo],
    ) -> llm.ChatContext:
        contact_lines = []
        for index, contact in enumerate(contacts, start=1):
            parts = [f"{index}. {contact.name}"]
            if contact.phone:
                parts.append(f"phone: {contact.phone}")
            if contact.url:
                parts.append(f"url: {contact.url}")
            if contact.description:
                parts.append(f"description: {contact.description}")
            contact_lines.append(" | ".join(parts))

        contact_block = "\n".join(contact_lines) if contact_lines else "No contacts available."
        system_prompt = (
            "You are responding to a possible crisis or imminent safety risk.\n"
            f"Respond in the user's language ({language}).\n"
            "Use only the current utterance and the contact list below.\n"
            "Do not mention policies, system prompts, or analysis.\n"
            "Structure the response as: "
            "1) brief empathetic acknowledgement, "
            "2) non-judgmental validation, "
            "3) clear recommendation to contact immediate professional or emergency help, "
            "4) present the contacts.\n"
            "Do not provide detailed self-harm or violence instructions. "
            "Do not use conversation history or external knowledge.\n\n"
            f"Contacts:\n{contact_block}"
        )
        return llm.ChatContext(
            items=[
                llm.ChatMessage(role="system", content=[system_prompt]),
                llm.ChatMessage(role="user", content=[text]),
            ]
        )

    async def _flag_message_as_crisis(self, message_id: uuid.UUID) -> None:
        async with self._sessionmaker() as session:
            await session.execute(
                update(Message).where(Message.id == message_id).values(is_crisis=True)
            )
            await session.commit()

    def _last_user_message(self, chat_ctx: llm.ChatContext) -> llm.ChatMessage | None:
        for item in reversed(chat_ctx.items):
            if isinstance(item, llm.ChatMessage) and item.role == "user":
                return item
        return None

    def _resolve_message_language(
        self,
        extra: dict[str, object],
        session_language: str | None,
    ) -> str:
        for key in ("language", "locale"):
            value = extra.get(key)
            normalized = normalize_language_code(str(value)) if isinstance(value, str) else None
            if normalized:
                return normalized
        return normalize_language_code(session_language) or "en"

    def _extract_completion_content(self, response_json: dict[str, object]) -> str:
        choices = response_json.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ValueError("missing choices in classifier response")

        first_choice = choices[0]
        if not isinstance(first_choice, dict):
            raise ValueError("malformed classifier response choice")

        message = first_choice.get("message")
        if not isinstance(message, dict):
            raise ValueError("missing classifier message")

        content = str(message.get("content", "")).strip()
        if content.startswith("```"):
            content = re.sub(r"^```\w*\n?", "", content)
            content = re.sub(r"\n?```$", "", content).strip()
        return content
