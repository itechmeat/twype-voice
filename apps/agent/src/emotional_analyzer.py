from __future__ import annotations

import json
import logging
import re
from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

import httpx

logger = logging.getLogger("twype-agent")

QuadrantName = Literal["distress", "melancholy", "serenity", "excitement", "neutral"]
TrendDirection = Literal["rising", "falling", "stable"]

DEFAULT_QUADRANT_THRESHOLD = 0.15
DEFAULT_TREND_THRESHOLD = 0.1
DEFAULT_WINDOW_SIZE = 10

_TONE_GUIDANCE: dict[QuadrantName, str] = {
    "distress": ("Calm, grounding, empathetic. Use short sentences. Acknowledge the difficulty."),
    "melancholy": "Warm, gentle, encouraging. Offer structure and small steps.",
    "serenity": "Supportive, steady, deepening. Match the calm pace.",
    "excitement": "Enthusiastic, validating, channeling energy constructively.",
    "neutral": "Balanced, attentive, responsive.",
}

_EXCLAMATION_RE = re.compile(r"[!?]+")
_CAPS_WORD_RE = re.compile(r"\b[A-Z\u0410-\u042F\u0401]{2,}\b")
_ELLIPSIS_RE = re.compile(r"\.{2,}|…")

_REFINEMENT_SYSTEM_PROMPT = (
    "You are an emotion analysis engine. Given a user utterance, conversation context, "
    "and a preliminary estimate, output ONLY a JSON object with two float fields: "
    '"valence" (-1.0 to 1.0, negative=unpleasant, positive=pleasant) and '
    '"arousal" (-1.0 to 1.0, negative=calm/low-energy, positive=excited/high-energy). '
    "Consider sarcasm, implicit emotions, and conversational context. "
    "Do not include any text outside the JSON object."
)


@dataclass(frozen=True, slots=True)
class EmotionalState:
    valence: float
    arousal: float
    quadrant: QuadrantName
    trend_valence: TrendDirection
    trend_arousal: TrendDirection
    sentiment_raw: float | None
    is_refined: bool


@dataclass(frozen=True, slots=True)
class EmotionalSnapshot:
    valence: float
    arousal: float
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


def estimate_circumplex(
    sentiment_raw: float | None,
    text: str,
) -> tuple[float, float]:
    valence = float(sentiment_raw) if sentiment_raw is not None else 0.0
    valence = max(-1.0, min(1.0, valence))

    arousal = _estimate_arousal_from_text(text)

    return valence, arousal


def _estimate_arousal_from_text(text: str) -> float:
    if not text or not text.strip():
        return 0.0

    words = text.split()
    word_count = len(words) or 1

    exclamation_count = len(_EXCLAMATION_RE.findall(text))
    caps_count = len(_CAPS_WORD_RE.findall(text))
    ellipsis_count = len(_ELLIPSIS_RE.findall(text))

    exclamation_score = min(exclamation_count / word_count, 1.0) * 0.6
    caps_score = min(caps_count / word_count, 1.0) * 0.3
    ellipsis_penalty = min(ellipsis_count / word_count, 1.0) * 0.2

    arousal = exclamation_score + caps_score - ellipsis_penalty
    return max(-1.0, min(1.0, arousal))


def classify_quadrant(
    valence: float,
    arousal: float,
    *,
    threshold: float = DEFAULT_QUADRANT_THRESHOLD,
) -> QuadrantName:
    if abs(valence) < threshold and abs(arousal) < threshold:
        return "neutral"

    if valence < -threshold:
        return "distress" if arousal >= threshold else "melancholy"

    if valence >= threshold:
        return "excitement" if arousal >= threshold else "serenity"

    if arousal >= threshold:
        return "distress" if valence < 0 else "excitement"

    return "melancholy" if valence < 0 else "serenity"


def get_tone_guidance(quadrant: QuadrantName) -> str:
    return _TONE_GUIDANCE.get(quadrant, _TONE_GUIDANCE["neutral"])


class EmotionalTrendTracker:
    __slots__ = ("_max_size", "_trend_threshold", "_window")

    def __init__(
        self,
        *,
        max_size: int = DEFAULT_WINDOW_SIZE,
        trend_threshold: float = DEFAULT_TREND_THRESHOLD,
    ) -> None:
        self._window: deque[EmotionalSnapshot] = deque(maxlen=max_size)
        self._max_size = max_size
        self._trend_threshold = trend_threshold

    @property
    def snapshots(self) -> list[EmotionalSnapshot]:
        return list(self._window)

    def add_snapshot(self, valence: float, arousal: float) -> None:
        self._window.append(EmotionalSnapshot(valence=valence, arousal=arousal))

    def replace_latest_snapshot(self, valence: float, arousal: float) -> None:
        if not self._window:
            self.add_snapshot(valence, arousal)
            return

        latest = self._window.pop()
        self._window.append(
            EmotionalSnapshot(
                valence=valence,
                arousal=arousal,
                timestamp=latest.timestamp,
            )
        )

    def get_trends(self) -> tuple[TrendDirection, TrendDirection]:
        if len(self._window) < 3:
            return "stable", "stable"

        items = list(self._window)
        mid = len(items) // 2
        older = items[:mid]
        recent = items[mid:]

        older_valence = sum(s.valence for s in older) / len(older)
        recent_valence = sum(s.valence for s in recent) / len(recent)
        older_arousal = sum(s.arousal for s in older) / len(older)
        recent_arousal = sum(s.arousal for s in recent) / len(recent)

        valence_trend = _direction(recent_valence - older_valence, self._trend_threshold)
        arousal_trend = _direction(recent_arousal - older_arousal, self._trend_threshold)

        return valence_trend, arousal_trend


def _direction(delta: float, threshold: float) -> TrendDirection:
    if delta > threshold:
        return "rising"
    if delta < -threshold:
        return "falling"
    return "stable"


def build_emotional_state(
    valence: float,
    arousal: float,
    sentiment_raw: float | None,
    trend_tracker: EmotionalTrendTracker,
    *,
    is_refined: bool = False,
    threshold: float = DEFAULT_QUADRANT_THRESHOLD,
) -> EmotionalState:
    quadrant = classify_quadrant(valence, arousal, threshold=threshold)
    trend_valence, trend_arousal = trend_tracker.get_trends()

    return EmotionalState(
        valence=round(valence, 3),
        arousal=round(arousal, 3),
        quadrant=quadrant,
        trend_valence=trend_valence,
        trend_arousal=trend_arousal,
        sentiment_raw=sentiment_raw,
        is_refined=is_refined,
    )


async def refine_with_llm(
    text: str,
    fast_estimate: tuple[float, float],
    context_messages: list[dict[str, str]],
    trend: tuple[TrendDirection, TrendDirection],
    *,
    base_url: str,
    api_key: str,
    model: str,
    timeout: float = 5.0,  # noqa: ASYNC109
) -> tuple[float, float] | None:
    user_content = (
        f"User utterance: {text}\n"
        f"Preliminary estimate: valence={fast_estimate[0]:.2f}, arousal={fast_estimate[1]:.2f}\n"
        f"Trend: valence={trend[0]}, arousal={trend[1]}\n"
    )

    if context_messages:
        recent = context_messages[-5:]
        context_lines = [f"  {msg['role']}: {msg['content']}" for msg in recent]
        user_content += "Recent conversation:\n" + "\n".join(context_lines)

    messages: list[dict[str, Any]] = [
        {"role": "system", "content": _REFINEMENT_SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
            response = await client.post(
                f"{base_url.rstrip('/')}/v1/chat/completions",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": 0.1,
                    "max_tokens": 60,
                },
            )
            response.raise_for_status()

        data = response.json()
        content = data["choices"][0]["message"]["content"].strip()

        cleaned = content
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```\w*\n?", "", cleaned)
            cleaned = re.sub(r"\n?```$", "", cleaned)
            cleaned = cleaned.strip()

        parsed = json.loads(cleaned)
        valence = float(parsed["valence"])
        arousal = float(parsed["arousal"])

        return (
            max(-1.0, min(1.0, valence)),
            max(-1.0, min(1.0, arousal)),
        )
    except (httpx.HTTPError, httpx.TimeoutException) as exc:
        logger.warning("emotional refinement LLM request failed: %s", exc)
        return None
    except (json.JSONDecodeError, KeyError, IndexError, ValueError, TypeError) as exc:
        logger.warning("emotional refinement LLM response parsing failed: %s", exc)
        return None
