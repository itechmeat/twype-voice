# ruff: noqa: E402, E501

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Protocol
from uuid import UUID

ROOT_DIR = Path(__file__).resolve().parents[1]
API_ROOT = ROOT_DIR / "apps" / "api"
for candidate in (ROOT_DIR, API_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

import sqlalchemy as sa
from passlib.context import CryptContext
from sqlalchemy.dialects.postgresql import insert
from src.database import session_scope
from src.knowledge_ingestion import EmbeddingClient, EmbeddingInput, EmbeddingSettings
from src.knowledge_ingestion.loader import DatabaseLoader, PreparedSource
from src.knowledge_ingestion.types import EmbeddedChunk, ManifestSource
from src.models import AgentConfig, CrisisContact, TTSConfig, User

logger = logging.getLogger(__name__)

TEST_USER_ID = UUID("00000000-0000-0000-0000-000000000001")

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

PROMPT_LAYER_TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        "system_prompt": (
            "You are Twype, an expert AI assistant for professional topics. "
            "Respond with care, stay structured, and state the limits of your confidence directly. "
            "Do not invent facts, hide uncertainty, or provide dangerous instructions."
        ),
        "voice_prompt": (
            "In voice mode, respond naturally, briefly, and conversationally, usually in 2-5 "
            "sentences. Start with the main point, then offer one useful next step or a short "
            "clarification."
        ),
        "dual_layer_prompt": (
            "Format every answer in two explicit sections using these delimiters exactly: "
            "---VOICE--- and ---TEXT---. "
            "In ---VOICE---, write 2-5 natural conversational sentences suitable for speech. "
            "In ---TEXT---, write bullet points starting with - or * for the data channel. "
            "When you use knowledge base context, cite the referenced chunk numbers with [N] "
            "markers that match the injected context order, for example [1] or [2][4]. "
            "Do not invent source numbers. If a point is your own reasoning or synthesis, leave "
            "it without [N] markers. Keep the meaning aligned between both sections.\n\n"
            "Example:\n"
            "---VOICE---\n"
            "The quickest way to reduce acute stress is to slow the breath "
            "and reorient to the room. "
            "Start with one simple exercise, then decide on the next safe action.\n"
            "---TEXT---\n"
            "- A longer exhale can reduce physiological arousal [2]\n"
            "- Sensory grounding helps bring attention back to the present moment [1]\n"
            "- After the stress wave drops, choose one concrete next step"
        ),
        "emotion_prompt": (
            "Adapt your response tone to the user's current emotional state.\n\n"
            "Circumplex emotional model — current reading:\n"
            "- Quadrant: {quadrant}\n"
            "- Valence (pleasant/unpleasant): {valence}\n"
            "- Arousal (high-energy/low-energy): {arousal}\n"
            "- Valence trend: {trend_valence}\n"
            "- Arousal trend: {trend_arousal}\n\n"
            "Tone guidance: {tone_guidance}\n\n"
            "Apply this guidance naturally without mentioning the model, "
            "scores, or quadrants to the user. "
            "If the emotional state is neutral or stable, "
            "respond in your default balanced tone."
        ),
        "crisis_prompt": (
            "Notice signs of crisis, self-harm, violence, or acute disorganization. "
            "In those cases, respond with empathy, avoid increasing risk, and gently recommend "
            "urgent help from qualified professionals and emergency services when the situation "
            "appears immediate."
        ),
        "rag_prompt": (
            "If knowledge base materials are available, rely on them first. "
            "Separate source-based facts from general reasoning and explicitly mention which "
            "materials you are relying on whenever possible."
        ),
        "language_prompt": (
            "Always adapt to the user's language and keep using it until the user switches. "
            "If the user mixes languages, choose the dominant language and avoid unnecessary "
            "code-switching."
        ),
        "proactive_prompt": (
            "The user has been silent. You are initiating a proactive follow-up.\n\n"
            "Proactive type: {proactive_type}\n"
            "Emotional context: {emotional_context}\n\n"
            "If proactive_type is 'follow_up', ask a brief clarifying question or suggest "
            "a concrete next step based on the recent conversation. Keep it to 1-2 sentences.\n"
            "If proactive_type is 'extended_silence', gently check in with the user. "
            "Adapt your tone to the emotional context. Be warm and non-intrusive. "
            "Offer to continue, change topic, or simply be available.\n\n"
            "Do not mention that you are following a timer or protocol. "
            "Sound natural, as if you genuinely noticed the pause."
        ),
        "mode_voice_guidance": (
            "Current input mode is voice. Reply briefly, naturally, and conversationally. "
            "Prefer a spoken rhythm over heavy structure."
        ),
        "mode_text_guidance": (
            "Current input mode is text. Reply with more detail and clearer structure. "
            "Use concise sections or bullets when that improves readability."
        ),
    },
    "ru": {
        "system_prompt": (
            "\u0412\u044b \u2014 Twype, \u044d\u043a\u0441\u043f\u0435\u0440\u0442\u043d\u044b\u0439 "
            "\u0418\u0418-\u043f\u043e\u043c\u043e\u0449\u043d\u0438\u043a \u043f\u043e "
            "\u043f\u0440\u043e\u0444\u0435\u0441\u0441\u0438\u043e\u043d\u0430\u043b\u044c\u043d"
            "\u044b\u043c \u0442\u0435\u043c\u0430\u043c. \u041e\u0442\u0432\u0435\u0447\u0430\u0439"
            "\u0442\u0435 \u0431\u0435\u0440\u0435\u0436\u043d\u043e, "
            "\u0441\u0442\u0440\u0443\u043a\u0442\u0443\u0440\u0438\u0440\u043e\u0432\u0430\u043d"
            "\u043d\u043e \u0438 \u043f\u0440\u044f\u043c\u043e \u043e\u0431\u043e\u0437\u043d\u0430"
            "\u0447\u0430\u0439\u0442\u0435 \u0433\u0440\u0430\u043d\u0438\u0446\u044b "
            "\u0441\u0432\u043e\u0435\u0439 \u0443\u0432\u0435\u0440\u0435\u043d\u043d\u043e\u0441"
            "\u0442\u0438. \u041d\u0435 \u043f\u0440\u0438\u0434\u0443\u043c\u044b\u0432\u0430\u0439"
            "\u0442\u0435 \u0444\u0430\u043a\u0442\u044b, \u043d\u0435 "
            "\u0441\u043a\u0440\u044b\u0432\u0430\u0439\u0442\u0435 "
            "\u043d\u0435\u043e\u043f\u0440\u0435\u0434\u0435\u043b\u0451\u043d\u043d\u043e\u0441"
            "\u0442\u044c \u0438 \u043d\u0435 \u0434\u0430\u0432\u0430\u0439\u0442\u0435 "
            "\u043e\u043f\u0430\u0441\u043d\u044b\u0445 \u0438\u043d\u0441\u0442\u0440\u0443\u043a"
            "\u0446\u0438\u0439."
        ),
        "voice_prompt": (
            "\u0412 \u0433\u043e\u043b\u043e\u0441\u043e\u0432\u043e\u043c \u0440\u0435\u0436\u0438"
            "\u043c\u0435 \u043e\u0442\u0432\u0435\u0447\u0430\u0439\u0442\u0435 "
            "\u0435\u0441\u0442\u0435\u0441\u0442\u0432\u0435\u043d\u043d\u043e, \u043a\u0440\u0430"
            "\u0442\u043a\u043e \u0438 \u0440\u0430\u0437\u0433\u043e\u0432\u043e\u0440\u043d\u043e, "
            "\u043e\u0431\u044b\u0447\u043d\u043e \u0432 2-5 "
            "\u043f\u0440\u0435\u0434\u043b\u043e\u0436\u0435\u043d\u0438\u044f\u0445. "
            "\u041d\u0430\u0447\u0438\u043d\u0430\u0439\u0442\u0435 \u0441 "
            "\u0433\u043b\u0430\u0432\u043d\u043e\u0439 \u043c\u044b\u0441\u043b\u0438, "
            "\u0437\u0430\u0442\u0435\u043c \u043f\u0440\u0435\u0434\u043b\u0430\u0433\u0430\u0439"
            "\u0442\u0435 \u043e\u0434\u0438\u043d \u043f\u043e\u043b\u0435\u0437\u043d\u044b\u0439 "
            "\u0441\u043b\u0435\u0434\u0443\u044e\u0449\u0438\u0439 \u0448\u0430\u0433 \u0438\u043b"
            "\u0438 \u043a\u043e\u0440\u043e\u0442\u043a\u043e\u0435 "
            "\u0443\u0442\u043e\u0447\u043d\u0435\u043d\u0438\u0435."
        ),
        "dual_layer_prompt": (
            "\u0424\u043e\u0440\u043c\u0430\u0442\u0438\u0440\u0443\u0439\u0442\u0435 "
            "\u043a\u0430\u0436\u0434\u044b\u0439 \u043e\u0442\u0432\u0435\u0442 \u0432 "
            "\u0434\u0432\u0443\u0445 \u044f\u0432\u043d\u044b\u0445 \u0441\u0435\u043a\u0446\u0438"
            "\u044f\u0445, \u0438\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u044f \u044d\u0442\u0438 "
            "\u0440\u0430\u0437\u0434\u0435\u043b\u0438\u0442\u0435\u043b\u0438 \u0431\u0435\u0437 "
            "\u0438\u0437\u043c\u0435\u043d\u0435\u043d\u0438\u0439: ---VOICE--- \u0438 "
            "---TEXT---. \u0412 \u0441\u0435\u043a\u0446\u0438\u0438 ---VOICE--- "
            "\u043f\u0438\u0448\u0438\u0442\u0435 2-5 \u0435\u0441\u0442\u0435\u0441\u0442\u0432"
            "\u0435\u043d\u043d\u044b\u0445 \u0440\u0430\u0437\u0433\u043e\u0432\u043e\u0440\u043d"
            "\u044b\u0445 \u043f\u0440\u0435\u0434\u043b\u043e\u0436\u0435\u043d\u0438\u0439, "
            "\u043f\u043e\u0434\u0445\u043e\u0434\u044f\u0449\u0438\u0445 \u0434\u043b\u044f "
            "\u043e\u0437\u0432\u0443\u0447\u0438\u0432\u0430\u043d\u0438\u044f. \u0412 "
            "\u0441\u0435\u043a\u0446\u0438\u0438 ---TEXT--- \u0438\u0441\u043f\u043e\u043b\u044c"
            "\u0437\u0443\u0439\u0442\u0435 \u043f\u0443\u043d\u043a\u0442\u044b, "
            "\u043d\u0430\u0447\u0438\u043d\u0430\u044e\u0449\u0438\u0435\u0441\u044f \u0441 - "
            "\u0438\u043b\u0438 *. \u0415\u0441\u043b\u0438 \u0432\u044b \u043e\u043f\u0438\u0440"
            "\u0430\u0435\u0442\u0435\u0441\u044c \u043d\u0430 \u043c\u0430\u0442\u0435\u0440\u0438"
            "\u0430\u043b\u044b \u0431\u0430\u0437\u044b \u0437\u043d\u0430\u043d\u0438\u0439, "
            "\u0443\u043a\u0430\u0437\u044b\u0432\u0430\u0439\u0442\u0435 \u043d\u043e\u043c\u0435"
            "\u0440\u0430 \u0444\u0440\u0430\u0433\u043c\u0435\u043d\u0442\u043e\u0432 \u0432 "
            "\u0432\u0438\u0434\u0435 [N], \u0441\u043e\u043e\u0442\u0432\u0435\u0442\u0441\u0442"
            "\u0432\u0443\u044e\u0449\u0438\u0435 \u043f\u043e\u0440\u044f\u0434\u043a\u0443 "
            "\u043f\u0435\u0440\u0435\u0434\u0430\u043d\u043d\u043e\u0433\u043e "
            "\u043a\u043e\u043d\u0442\u0435\u043a\u0441\u0442\u0430, \u043d\u0430\u043f\u0440\u0438"
            "\u043c\u0435\u0440 [1] \u0438\u043b\u0438 [2][4]. \u041d\u0435 \u043f\u0440\u0438\u0434"
            "\u0443\u043c\u044b\u0432\u0430\u0439\u0442\u0435 \u043d\u043e\u043c\u0435\u0440\u0430 "
            "\u0438\u0441\u0442\u043e\u0447\u043d\u0438\u043a\u043e\u0432. \u0415\u0441\u043b\u0438 "
            "\u043f\u0443\u043d\u043a\u0442 \u043e\u0441\u043d\u043e\u0432\u0430\u043d \u043d\u0430 "
            "\u0432\u0430\u0448\u0435\u043c \u0440\u0430\u0441\u0441\u0443\u0436\u0434\u0435\u043d"
            "\u0438\u0438 \u0438\u043b\u0438 \u0441\u0438\u043d\u0442\u0435\u0437\u0435, "
            "\u043e\u0441\u0442\u0430\u0432\u043b\u044f\u0439\u0442\u0435 \u0435\u0433\u043e "
            "\u0431\u0435\u0437 [N]. \u0421\u043c\u044b\u0441\u043b \u043e\u0431\u0435\u0438\u0445 "
            "\u0441\u0435\u043a\u0446\u0438\u0439 \u0434\u043e\u043b\u0436\u0435\u043d "
            "\u0441\u043e\u0432\u043f\u0430\u0434\u0430\u0442\u044c.\n\n\u041f\u0440\u0438\u043c"
            "\u0435\u0440:\n---VOICE---\n\u0421\u0430\u043c\u044b\u0439 "
            "\u0431\u044b\u0441\u0442\u0440\u044b\u0439 \u0441\u043f\u043e\u0441\u043e\u0431 "
            "\u0441\u043d\u0438\u0437\u0438\u0442\u044c \u043e\u0441\u0442\u0440\u044b\u0439 "
            "\u0441\u0442\u0440\u0435\u0441\u0441 \u2014 \u0437\u0430\u043c\u0435\u0434\u043b"
            "\u0438\u0442\u044c \u0434\u044b\u0445\u0430\u043d\u0438\u0435 \u0438 "
            "\u0441\u043d\u043e\u0432\u0430 \u0441\u043e\u0440\u0438\u0435\u043d\u0442\u0438\u0440"
            "\u043e\u0432\u0430\u0442\u044c\u0441\u044f \u0432 \u043e\u0431\u0441\u0442\u0430\u043d"
            "\u043e\u0432\u043a\u0435. \u041d\u0430\u0447\u043d\u0438\u0442\u0435 \u0441 "
            "\u043e\u0434\u043d\u043e\u0433\u043e \u043f\u0440\u043e\u0441\u0442\u043e\u0433\u043e "
            "\u0443\u043f\u0440\u0430\u0436\u043d\u0435\u043d\u0438\u044f, \u0430 \u0437\u0430"
            "\u0442\u0435\u043c \u0432\u044b\u0431\u0435\u0440\u0438\u0442\u0435 "
            "\u0441\u043b\u0435\u0434\u0443\u044e\u0449\u0438\u0439 \u0431\u0435\u0437\u043e"
            "\u043f\u0430\u0441\u043d\u044b\u0439 \u0448\u0430\u0433.\n---TEXT---\n- "
            "\u0411\u043e\u043b\u0435\u0435 \u0434\u043b\u0438\u043d\u043d\u044b\u0439 "
            "\u0432\u044b\u0434\u043e\u0445 \u043c\u043e\u0436\u0435\u0442 \u0441\u043d\u0438"
            "\u0437\u0438\u0442\u044c \u0444\u0438\u0437\u0438\u043e\u043b\u043e\u0433\u0438\u0447"
            "\u0435\u0441\u043a\u043e\u0435 \u043d\u0430\u043f\u0440\u044f\u0436\u0435\u043d\u0438"
            "\u0435 [2]\n- \u0421\u0435\u043d\u0441\u043e\u0440\u043d\u043e\u0435 "
            "\u0437\u0430\u0437\u0435\u043c\u043b\u0435\u043d\u0438\u0435 \u043f\u043e\u043c"
            "\u043e\u0433\u0430\u0435\u0442 \u0432\u0435\u0440\u043d\u0443\u0442\u044c "
            "\u0432\u043d\u0438\u043c\u0430\u043d\u0438\u0435 \u0432 "
            "\u043d\u0430\u0441\u0442\u043e\u044f\u0449\u0438\u0439 \u043c\u043e\u043c\u0435\u043d"
            "\u0442 [1]\n- \u041f\u043e\u0441\u043b\u0435 \u0441\u043f\u0430\u0434\u0430 "
            "\u0432\u043e\u043b\u043d\u044b \u0441\u0442\u0440\u0435\u0441\u0441\u0430 "
            "\u0432\u044b\u0431\u0435\u0440\u0438\u0442\u0435 \u043e\u0434\u043d\u043e "
            "\u043a\u043e\u043d\u043a\u0440\u0435\u0442\u043d\u043e\u0435 "
            "\u0441\u043b\u0435\u0434\u0443\u044e\u0449\u0435\u0435 \u0434\u0435\u0439\u0441\u0442"
            "\u0432\u0438\u0435"
        ),
        "emotion_prompt": (
            "\u0410\u0434\u0430\u043f\u0442\u0438\u0440\u0443\u0439\u0442\u0435 \u0442\u043e\u043d "
            "\u043e\u0442\u0432\u0435\u0442\u0430 \u043a \u0442\u0435\u043a\u0443\u0449\u0435\u043c"
            "\u0443 \u044d\u043c\u043e\u0446\u0438\u043e\u043d\u0430\u043b\u044c\u043d\u043e\u043c"
            "\u0443 \u0441\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u044e "
            "\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044f.\n\n"
            "\u0422\u0435\u043a\u0443\u0449\u0435\u0435 \u0441\u043e\u0441\u0442\u043e\u044f\u043d"
            "\u0438\u0435 \u043f\u043e \u0446\u0438\u0440\u043a\u0443\u043c\u043f\u043b\u0435\u043a"
            "\u0441\u043d\u043e\u0439 \u043c\u043e\u0434\u0435\u043b\u0438 \u044d\u043c\u043e\u0446"
            "\u0438\u0439:\n- \u041a\u0432\u0430\u0434\u0440\u0430\u043d\u0442: {quadrant}\n- "
            "\u0412\u0430\u043b\u0435\u043d\u0442\u043d\u043e\u0441\u0442\u044c "
            "(\u043f\u0440\u0438\u044f\u0442\u043d\u043e/\u043d\u0435\u043f\u0440\u0438\u044f"
            "\u0442\u043d\u043e): {valence}\n- \u0410\u043a\u0442\u0438\u0432\u0430\u0446\u0438"
            "\u044f (\u0432\u044b\u0441\u043e\u043a\u0430\u044f/\u043d\u0438\u0437\u043a\u0430\u044f "
            "\u044d\u043d\u0435\u0440\u0433\u0438\u044f): {arousal}\n- \u0422\u0440\u0435\u043d\u0434 "
            "\u0432\u0430\u043b\u0435\u043d\u0442\u043d\u043e\u0441\u0442\u0438: "
            "{trend_valence}\n- \u0422\u0440\u0435\u043d\u0434 \u0430\u043a\u0442\u0438\u0432"
            "\u0430\u0446\u0438\u0438: {trend_arousal}\n\n\u0420\u0435\u043a\u043e\u043c\u0435"
            "\u043d\u0434\u0430\u0446\u0438\u0438 \u043f\u043e \u0442\u043e\u043d\u0443: "
            "{tone_guidance}\n\n\u041f\u0440\u0438\u043c\u0435\u043d\u044f\u0439\u0442\u0435 "
            "\u044d\u0442\u0438 \u0440\u0435\u043a\u043e\u043c\u0435\u043d\u0434\u0430\u0446"
            "\u0438\u0438 \u0435\u0441\u0442\u0435\u0441\u0442\u0432\u0435\u043d\u043d\u043e, "
            "\u043d\u0435 \u0443\u043f\u043e\u043c\u0438\u043d\u0430\u044f \u043c\u043e\u0434\u0435"
            "\u043b\u044c, \u043e\u0446\u0435\u043d\u043a\u0438 \u0438\u043b\u0438 "
            "\u043a\u0432\u0430\u0434\u0440\u0430\u043d\u0442\u044b "
            "\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044e. \u0415\u0441"
            "\u043b\u0438 \u044d\u043c\u043e\u0446\u0438\u043e\u043d\u0430\u043b\u044c\u043d\u043e"
            "\u0435 \u0441\u043e\u0441\u0442\u043e\u044f\u043d\u0438\u0435 "
            "\u043d\u0435\u0439\u0442\u0440\u0430\u043b\u044c\u043d\u043e\u0435 \u0438\u043b\u0438 "
            "\u0441\u0442\u0430\u0431\u0438\u043b\u044c\u043d\u043e\u0435, "
            "\u043e\u0442\u0432\u0435\u0447\u0430\u0439\u0442\u0435 \u0441\u0432\u043e\u0438\u043c "
            "\u043e\u0431\u044b\u0447\u043d\u044b\u043c \u0441\u0431\u0430\u043b\u0430\u043d\u0441"
            "\u0438\u0440\u043e\u0432\u0430\u043d\u043d\u044b\u043c \u0442\u043e\u043d\u043e\u043c."
        ),
        "crisis_prompt": (
            "\u0417\u0430\u043c\u0435\u0447\u0430\u0439\u0442\u0435 \u043f\u0440\u0438\u0437\u043d"
            "\u0430\u043a\u0438 \u043a\u0440\u0438\u0437\u0438\u0441\u0430, "
            "\u0441\u0430\u043c\u043e\u043f\u043e\u0432\u0440\u0435\u0436\u0434\u0435\u043d\u0438"
            "\u044f, \u043d\u0430\u0441\u0438\u043b\u0438\u044f \u0438\u043b\u0438 "
            "\u043e\u0441\u0442\u0440\u043e\u0439 \u0434\u0435\u0437\u043e\u0440\u0433\u0430\u043d"
            "\u0438\u0437\u0430\u0446\u0438\u0438. \u0412 \u0442\u0430\u043a\u0438\u0445 "
            "\u0441\u043b\u0443\u0447\u0430\u044f\u0445 \u043e\u0442\u0432\u0435\u0447\u0430\u0439"
            "\u0442\u0435 \u0441 \u0441\u043e\u0447\u0443\u0432\u0441\u0442\u0432\u0438\u0435\u043c, "
            "\u043d\u0435 \u0443\u0441\u0438\u043b\u0438\u0432\u0430\u0439\u0442\u0435 "
            "\u0440\u0438\u0441\u043a \u0438 \u043c\u044f\u0433\u043a\u043e \u0440\u0435\u043a\u043e"
            "\u043c\u0435\u043d\u0434\u0443\u0439\u0442\u0435 \u0441\u0440\u043e\u0447\u043d\u0443"
            "\u044e \u043f\u043e\u043c\u043e\u0449\u044c "
            "\u043a\u0432\u0430\u043b\u0438\u0444\u0438\u0446\u0438\u0440\u043e\u0432\u0430\u043d"
            "\u043d\u044b\u0445 \u0441\u043f\u0435\u0446\u0438\u0430\u043b\u0438\u0441\u0442\u043e"
            "\u0432 \u0438 \u044d\u043a\u0441\u0442\u0440\u0435\u043d\u043d\u044b\u0445 "
            "\u0441\u043b\u0443\u0436\u0431, \u0435\u0441\u043b\u0438 "
            "\u0441\u0438\u0442\u0443\u0430\u0446\u0438\u044f \u0432\u044b\u0433\u043b\u044f\u0434"
            "\u0438\u0442 \u043d\u0435\u043e\u0442\u043b\u043e\u0436\u043d\u043e\u0439."
        ),
        "rag_prompt": (
            "\u0415\u0441\u043b\u0438 \u0434\u043e\u0441\u0442\u0443\u043f\u043d\u044b "
            "\u043c\u0430\u0442\u0435\u0440\u0438\u0430\u043b\u044b \u0431\u0430\u0437\u044b "
            "\u0437\u043d\u0430\u043d\u0438\u0439, \u043e\u043f\u0438\u0440\u0430\u0439\u0442\u0435"
            "\u0441\u044c \u043d\u0430 \u043d\u0438\u0445 \u0432 \u043f\u0435\u0440\u0432\u0443\u044e "
            "\u043e\u0447\u0435\u0440\u0435\u0434\u044c. \u041e\u0442\u0434\u0435\u043b\u044f\u0439"
            "\u0442\u0435 \u0444\u0430\u043a\u0442\u044b \u0438\u0437 \u0438\u0441\u0442\u043e\u0447"
            "\u043d\u0438\u043a\u043e\u0432 \u043e\u0442 \u043e\u0431\u0449\u0435\u0433\u043e "
            "\u0440\u0430\u0441\u0441\u0443\u0436\u0434\u0435\u043d\u0438\u044f \u0438 \u043f\u043e "
            "\u0432\u043e\u0437\u043c\u043e\u0436\u043d\u043e\u0441\u0442\u0438 \u044f\u0432\u043d\u043e "
            "\u043e\u0431\u043e\u0437\u043d\u0430\u0447\u0430\u0439\u0442\u0435, \u043d\u0430 "
            "\u043a\u0430\u043a\u0438\u0435 \u043c\u0430\u0442\u0435\u0440\u0438\u0430\u043b\u044b "
            "\u0432\u044b \u043e\u043f\u0438\u0440\u0430\u0435\u0442\u0435\u0441\u044c."
        ),
        "language_prompt": (
            "\u0412\u0441\u0435\u0433\u0434\u0430 \u043f\u043e\u0434\u0441\u0442\u0440\u0430\u0438"
            "\u0432\u0430\u0439\u0442\u0435\u0441\u044c \u043f\u043e\u0434 \u044f\u0437\u044b\u043a "
            "\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044f \u0438 "
            "\u043f\u0440\u043e\u0434\u043e\u043b\u0436\u0430\u0439\u0442\u0435 \u043d\u0430 \u043d"
            "\u0451\u043c, \u043f\u043e\u043a\u0430 \u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430"
            "\u0442\u0435\u043b\u044c \u0441\u0430\u043c \u043d\u0435 \u043f\u0435\u0440\u0435\u043a"
            "\u043b\u044e\u0447\u0438\u0442\u0441\u044f. \u0415\u0441\u043b\u0438 "
            "\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c "
            "\u0441\u043c\u0435\u0448\u0438\u0432\u0430\u0435\u0442 \u044f\u0437\u044b\u043a\u0438, "
            "\u0432\u044b\u0431\u0438\u0440\u0430\u0439\u0442\u0435 \u0434\u043e\u043c\u0438\u043d"
            "\u0438\u0440\u0443\u044e\u0449\u0438\u0439 \u044f\u0437\u044b\u043a \u0438 "
            "\u0438\u0437\u0431\u0435\u0433\u0430\u0439\u0442\u0435 \u043b\u0438\u0448\u043d\u0435"
            "\u0433\u043e \u043f\u0435\u0440\u0435\u043a\u043b\u044e\u0447\u0435\u043d\u0438\u044f "
            "\u043a\u043e\u0434\u043e\u0432."
        ),
        "proactive_prompt": (
            "\u041f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c "
            "\u043c\u043e\u043b\u0447\u0438\u0442, \u0438 \u0432\u044b \u043d\u0430\u0447\u0438"
            "\u043d\u0430\u0435\u0442\u0435 \u0431\u0435\u0440\u0435\u0436\u043d\u043e\u0435 "
            "\u043f\u0440\u043e\u0430\u043a\u0442\u0438\u0432\u043d\u043e\u0435 "
            "\u043f\u0440\u043e\u0434\u043e\u043b\u0436\u0435\u043d\u0438\u0435.\n\n\u0422\u0438"
            "\u043f \u043f\u0440\u043e\u0430\u043a\u0442\u0438\u0432\u043d\u043e\u0433\u043e "
            "\u0441\u043e\u043e\u0431\u0449\u0435\u043d\u0438\u044f: {proactive_type}\n\u042d"
            "\u043c\u043e\u0446\u0438\u043e\u043d\u0430\u043b\u044c\u043d\u044b\u0439 "
            "\u043a\u043e\u043d\u0442\u0435\u043a\u0441\u0442: {emotional_context}\n\n\u0415\u0441"
            "\u043b\u0438 proactive_type \u0440\u0430\u0432\u0435\u043d 'follow_up', "
            "\u0437\u0430\u0434\u0430\u0439\u0442\u0435 \u043a\u043e\u0440\u043e\u0442\u043a\u0438"
            "\u0439 \u0443\u0442\u043e\u0447\u043d\u044f\u044e\u0449\u0438\u0439 \u0432\u043e\u043f"
            "\u0440\u043e\u0441 \u0438\u043b\u0438 \u043f\u0440\u0435\u0434\u043b\u043e\u0436\u0438"
            "\u0442\u0435 \u043e\u0434\u0438\u043d \u043a\u043e\u043d\u043a\u0440\u0435\u0442"
            "\u043d\u044b\u0439 \u0441\u043b\u0435\u0434\u0443\u044e\u0449\u0438\u0439 \u0448\u0430"
            "\u0433 \u043f\u043e \u043d\u0435\u0434\u0430\u0432\u043d\u0435\u043c\u0443 "
            "\u0440\u0430\u0437\u0433\u043e\u0432\u043e\u0440\u0443. \u0423\u043b\u043e\u0436\u0438"
            "\u0442\u0435\u0441\u044c \u0432 1-2 \u043f\u0440\u0435\u0434\u043b\u043e\u0436\u0435"
            "\u043d\u0438\u044f. \u0415\u0441\u043b\u0438 proactive_type \u0440\u0430\u0432\u0435"
            "\u043d 'extended_silence', \u043c\u044f\u0433\u043a\u043e "
            "\u043f\u0440\u043e\u0432\u0435\u0440\u044c\u0442\u0435, \u043a\u0430\u043a "
            "\u043f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c. "
            "\u041f\u043e\u0434\u0441\u0442\u0440\u043e\u0439\u0442\u0435 \u0442\u043e\u043d "
            "\u043f\u043e\u0434 \u044d\u043c\u043e\u0446\u0438\u043e\u043d\u0430\u043b\u044c\u043d"
            "\u044b\u0439 \u043a\u043e\u043d\u0442\u0435\u043a\u0441\u0442. "
            "\u0411\u0443\u0434\u044c\u0442\u0435 \u0442\u0451\u043f\u043b\u044b\u043c \u0438 "
            "\u043d\u0435\u043d\u0430\u0432\u044f\u0437\u0447\u0438\u0432\u044b\u043c. "
            "\u041f\u0440\u0435\u0434\u043b\u043e\u0436\u0438\u0442\u0435 "
            "\u043f\u0440\u043e\u0434\u043e\u043b\u0436\u0438\u0442\u044c \u0440\u0430\u0437"
            "\u0433\u043e\u0432\u043e\u0440, \u0441\u043c\u0435\u043d\u0438\u0442\u044c \u0442\u0435"
            "\u043c\u0443 \u0438\u043b\u0438 \u043f\u0440\u043e\u0441\u0442\u043e \u043d\u0430\u043f"
            "\u043e\u043c\u043d\u0438\u0442\u0435, \u0447\u0442\u043e \u0432\u044b "
            "\u0440\u044f\u0434\u043e\u043c.\n\n\u041d\u0435 \u0433\u043e\u0432\u043e\u0440\u0438"
            "\u0442\u0435 \u043e \u0442\u0430\u0439\u043c\u0435\u0440\u0435 \u0438\u043b\u0438 "
            "\u043f\u0440\u043e\u0442\u043e\u043a\u043e\u043b\u0435. \u0424\u043e\u0440\u043c"
            "\u0443\u043b\u0438\u0440\u0443\u0439\u0442\u0435 \u0442\u0430\u043a, \u0431\u0443"
            "\u0434\u0442\u043e \u0432\u044b \u0435\u0441\u0442\u0435\u0441\u0442\u0432\u0435\u043d"
            "\u043d\u043e \u0437\u0430\u043c\u0435\u0442\u0438\u043b\u0438 \u043f\u0430\u0443\u0437"
            "\u0443."
        ),
        "mode_voice_guidance": (
            "\u0422\u0435\u043a\u0443\u0449\u0438\u0439 \u0440\u0435\u0436\u0438\u043c "
            "\u0432\u0432\u043e\u0434\u0430 \u2014 \u0433\u043e\u043b\u043e\u0441. "
            "\u041e\u0442\u0432\u0435\u0447\u0430\u0439\u0442\u0435 \u043a\u0440\u0430\u0442\u043a"
            "\u043e, \u0435\u0441\u0442\u0435\u0441\u0442\u0432\u0435\u043d\u043d\u043e \u0438 "
            "\u0440\u0430\u0437\u0433\u043e\u0432\u043e\u0440\u043d\u043e. "
            "\u041e\u0442\u0434\u0430\u0432\u0430\u0439\u0442\u0435 \u043f\u0440\u0438\u043e\u0440"
            "\u0438\u0442\u0435\u0442 \u0440\u0438\u0442\u043c\u0443, \u0443\u0434\u043e\u0431"
            "\u043d\u043e\u043c\u0443 \u0434\u043b\u044f \u0432\u043e\u0441\u043f\u0440\u0438\u044f"
            "\u0442\u0438\u044f \u043d\u0430 \u0441\u043b\u0443\u0445."
        ),
        "mode_text_guidance": (
            "\u0422\u0435\u043a\u0443\u0449\u0438\u0439 \u0440\u0435\u0436\u0438\u043c "
            "\u0432\u0432\u043e\u0434\u0430 \u2014 \u0442\u0435\u043a\u0441\u0442. "
            "\u041e\u0442\u0432\u0435\u0447\u0430\u0439\u0442\u0435 \u043f\u043e\u0434\u0440\u043e"
            "\u0431\u043d\u0435\u0435 \u0438 \u0441 \u0431\u043e\u043b\u0435\u0435 \u044f\u0432"
            "\u043d\u043e\u0439 \u0441\u0442\u0440\u0443\u043a\u0442\u0443\u0440\u043e\u0439. "
            "\u0418\u0441\u043f\u043e\u043b\u044c\u0437\u0443\u0439\u0442\u0435 "
            "\u043a\u043e\u0440\u043e\u0442\u043a\u0438\u0435 \u0441\u0435\u043a\u0446\u0438\u0438 "
            "\u0438\u043b\u0438 \u0441\u043f\u0438\u0441\u043a\u0438, \u043a\u043e\u0433\u0434\u0430 "
            "\u044d\u0442\u043e \u043f\u043e\u0432\u044b\u0448\u0430\u0435\u0442 "
            "\u0447\u0438\u0442\u0430\u0435\u043c\u043e\u0441\u0442\u044c."
        ),
    },
}

SAMPLE_KNOWLEDGE_SOURCE = ManifestSource(
    file="seed-sample",
    source_type="article",
    title="Grounding Techniques for Acute Stress",
    language="en",
    author="Twype Editorial",
    url=None,
    tags=["psychology", "stress", "grounding"],
)

SAMPLE_KNOWLEDGE_CHUNKS: list[dict[str, str | int | None]] = [
    {
        "content": (
            "Grounding techniques help people return attention to the present moment when acute "
            "stress, panic, or intrusive thoughts narrow their focus. A simple first step is to "
            "name five things you can see, four you can touch, three you can hear, two you can "
            "smell, and one you can taste."
        ),
        "section": "Sensory orientation",
        "page_range": None,
        "token_count": 58,
    },
    {
        "content": (
            "Breathing exercises work best when the pace is slightly slower than the person's "
            "usual rhythm. One practical pattern is inhale for four counts, pause for one, and "
            "exhale for six. The longer exhale can reduce physiological arousal without requiring "
            "special equipment or a quiet room."
        ),
        "section": "Breathing reset",
        "page_range": None,
        "token_count": 54,
    },
    {
        "content": (
            "After the immediate stress wave drops, it is useful to re-establish orientation: "
            "note where you are, what time it is, and what the next safe action will be. A short "
            "follow-up plan such as drinking water, texting a trusted person, or stepping outside "
            "can prevent the person from sliding back into confusion."
        ),
        "section": "Next safe action",
        "page_range": None,
        "token_count": 57,
    },
]

CRISIS_CONTACTS: list[dict[str, str | int | bool | UUID | None]] = [
    {
        "id": UUID("10000000-0000-0000-0000-000000000001"),
        "language": "en",
        "locale": "US",
        "contact_type": "emergency_services",
        "name": "Emergency Services",
        "phone": "911",
        "url": None,
        "description": "Call emergency services immediately if there is an immediate risk of harm.",
        "priority": 1,
        "is_active": True,
    },
    {
        "id": UUID("10000000-0000-0000-0000-000000000002"),
        "language": "en",
        "locale": "US",
        "contact_type": "suicide_hotline",
        "name": "988 Suicide & Crisis Lifeline",
        "phone": "988",
        "url": "https://988lifeline.org/",
        "description": "Call or text 988 for immediate crisis support in the United States.",
        "priority": 2,
        "is_active": True,
    },
    {
        "id": UUID("10000000-0000-0000-0000-000000000003"),
        "language": "en",
        "locale": "US",
        "contact_type": "crisis_helpline",
        "name": "Crisis Text Line",
        "phone": "741741",
        "url": "https://www.crisistextline.org/",
        "description": "Text HOME to 741741 to connect with a trained crisis counselor.",
        "priority": 3,
        "is_active": True,
    },
    {
        "id": UUID("20000000-0000-0000-0000-000000000001"),
        "language": "ru",
        "locale": "RU",
        "contact_type": "emergency_services",
        "name": "\u042d\u043a\u0441\u0442\u0440\u0435\u043d\u043d\u044b\u0435 \u0441\u043b\u0443\u0436\u0431\u044b",
        "phone": "112",
        "url": None,
        "description": (
            "\u041d\u0435\u043c\u0435\u0434\u043b\u0435\u043d\u043d\u043e \u0437\u0432\u043e\u043d\u0438\u0442\u0435 112, "
            "\u0435\u0441\u043b\u0438 \u0435\u0441\u0442\u044c "
            "\u043d\u0435\u043f\u043e\u0441\u0440\u0435\u0434\u0441\u0442\u0432\u0435\u043d\u043d\u0430\u044f "
            "\u0443\u0433\u0440\u043e\u0437\u0430 \u0436\u0438\u0437\u043d\u0438 \u0438\u043b\u0438 "
            "\u0440\u0438\u0441\u043a \u043f\u0440\u0438\u0447\u0438\u043d\u0435\u043d\u0438\u044f "
            "\u0432\u0440\u0435\u0434\u0430."
        ),
        "priority": 1,
        "is_active": True,
    },
    {
        "id": UUID("20000000-0000-0000-0000-000000000002"),
        "language": "ru",
        "locale": "RU",
        "contact_type": "crisis_helpline",
        "name": "\u0414\u0435\u0442\u0441\u043a\u0438\u0439 \u0442\u0435\u043b\u0435\u0444\u043e\u043d \u0434\u043e\u0432\u0435\u0440\u0438\u044f",
        "phone": "8-800-2000-122",
        "url": "https://telefon-doveria.ru/",
        "description": (
            "\u041a\u0440\u0443\u0433\u043b\u043e\u0441\u0443\u0442\u043e\u0447\u043d\u0430\u044f "
            "\u0444\u0435\u0434\u0435\u0440\u0430\u043b\u044c\u043d\u0430\u044f \u043b\u0438\u043d\u0438\u044f "
            "\u043f\u043e\u043c\u043e\u0449\u0438 \u0434\u043b\u044f \u0434\u0435\u0442\u0435\u0439, "
            "\u043f\u043e\u0434\u0440\u043e\u0441\u0442\u043a\u043e\u0432 \u0438 \u0438\u0445 "
            "\u0431\u043b\u0438\u0437\u043a\u0438\u0445 \u0432 \u043a\u0440\u0438\u0437\u0438\u0441\u043d\u043e\u0439 "
            "\u0441\u0438\u0442\u0443\u0430\u0446\u0438\u0438."
        ),
        "priority": 2,
        "is_active": True,
    },
    {
        "id": UUID("20000000-0000-0000-0000-000000000003"),
        "language": "ru",
        "locale": "RU",
        "contact_type": "mental_health_support",
        "name": (
            "\u042d\u043a\u0441\u0442\u0440\u0435\u043d\u043d\u0430\u044f "
            "\u043f\u0441\u0438\u0445\u043e\u043b\u043e\u0433\u0438\u0447\u0435\u0441\u043a\u0430\u044f "
            "\u043f\u043e\u043c\u043e\u0449\u044c \u041c\u0427\u0421 \u0420\u043e\u0441\u0441\u0438\u0438"
        ),
        "phone": "8-800-200-47-03",
        "url": "https://psi.mchs.gov.ru/",
        "description": (
            "\u041a\u0440\u0443\u0433\u043b\u043e\u0441\u0443\u0442\u043e\u0447\u043d\u0430\u044f "
            "\u043f\u0441\u0438\u0445\u043e\u043b\u043e\u0433\u0438\u0447\u0435\u0441\u043a\u0430\u044f "
            "\u043f\u043e\u043c\u043e\u0449\u044c \u041c\u0427\u0421 \u0420\u043e\u0441\u0441\u0438\u0438 "
            "\u0434\u043b\u044f \u043e\u0441\u0442\u0440\u044b\u0445 \u043a\u0440\u0438\u0437\u0438\u0441\u043d\u044b\u0445 "
            "\u0441\u0438\u0442\u0443\u0430\u0446\u0438\u0439 \u0438 \u044d\u043c\u043e\u0446\u0438\u043e\u043d\u0430\u043b\u044c\u043d\u043e\u0439 "
            "\u0434\u0435\u0437\u043e\u0440\u0433\u0430\u043d\u0438\u0437\u0430\u0446\u0438\u0438."
        ),
        "priority": 3,
        "is_active": True,
    },
]

CRISIS_KEYWORD_PATTERNS: dict[str, dict[str, list[dict[str, str | bool]]]] = {
    "en": {
        "suicide": [
            {"pattern": "kill myself", "regex": False},
            {"pattern": "want to die", "regex": False},
            {"pattern": r"\bend my life\b", "regex": True},
        ],
        "self_harm": [
            {"pattern": "cut myself", "regex": False},
            {"pattern": "overdose", "regex": False},
            {"pattern": r"\bhurt myself\b", "regex": True},
        ],
        "acute_symptoms": [
            {"pattern": "hearing voices", "regex": False},
            {"pattern": "can't tell what is real", "regex": False},
            {"pattern": r"\bpanic attack\b", "regex": True},
        ],
        "violence": [
            {"pattern": "want to hurt someone", "regex": False},
            {"pattern": "going to kill him", "regex": False},
            {"pattern": r"\bviolent thoughts\b", "regex": True},
        ],
    },
    "ru": {
        "suicide": [
            {
                "pattern": ("\u0445\u043e\u0447\u0443 \u0443\u043c\u0435\u0440\u0435\u0442\u044c"),
                "regex": False,
            },
            {
                "pattern": (
                    "\u043f\u043e\u043a\u043e\u043d\u0447\u0438\u0442\u044c "
                    "\u0441 \u0441\u043e\u0431\u043e\u0439"
                ),
                "regex": False,
            },
            {
                "pattern": ("\\b\u0443\u0431\u0438\u0442\u044c \u0441\u0435\u0431\u044f\\b"),
                "regex": True,
            },
        ],
        "self_harm": [
            {
                "pattern": (
                    "\u043f\u043e\u0440\u0435\u0437\u0430\u0442\u044c \u0441\u0435\u0431\u044f"
                ),
                "regex": False,
            },
            {
                "pattern": (
                    "\u043f\u0435\u0440\u0435\u0434\u043e\u0437\u0438\u0440\u043e\u0432\u043a\u0430"
                ),
                "regex": False,
            },
            {
                "pattern": (
                    "\\b\u043d\u0430\u0432\u0440\u0435\u0434\u0438\u0442\u044c "
                    "\u0441\u0435\u0431\u0435\\b"
                ),
                "regex": True,
            },
        ],
        "acute_symptoms": [
            {
                "pattern": ("\u0441\u043b\u044b\u0448\u0443 \u0433\u043e\u043b\u043e\u0441\u0430"),
                "regex": False,
            },
            {
                "pattern": (
                    "\u043d\u0435 \u043f\u043e\u043d\u0438\u043c\u0430\u044e "
                    "\u0447\u0442\u043e \u0440\u0435\u0430\u043b\u044c\u043d\u043e"
                ),
                "regex": False,
            },
            {
                "pattern": (
                    "\\b\u0441\u0438\u043b\u044c\u043d\u0430\u044f "
                    "\u043f\u0430\u043d\u0438\u043a\u0430\\b"
                ),
                "regex": True,
            },
        ],
        "violence": [
            {
                "pattern": (
                    "\u0445\u043e\u0447\u0443 \u043a\u043e\u0433\u043e-\u0442\u043e "
                    "\u0443\u0431\u0438\u0442\u044c"
                ),
                "regex": False,
            },
            {
                "pattern": (
                    "\u043c\u043e\u0433\u0443 \u0443\u0434\u0430\u0440\u0438\u0442\u044c "
                    "\u0435\u0433\u043e"
                ),
                "regex": False,
            },
            {
                "pattern": (
                    "\\b\u043f\u0440\u0438\u0447\u0438\u043d\u0438\u0442\u044c "
                    "\u0432\u0440\u0435\u0434 \u0434\u0440\u0443\u0433\u0438\u043c\\b"
                ),
                "regex": True,
            },
        ],
    },
}


class EmbeddingClientProtocol(Protocol):
    async def embed_inputs(self, inputs: list[EmbeddingInput]) -> list[list[float]]: ...


def _require_database_url() -> None:
    if not os.environ.get("DATABASE_URL"):
        raise RuntimeError("DATABASE_URL is not set")


def _require_google_api_key() -> str:
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_API_KEY is not set")
    return api_key


def _should_seed_test_user() -> bool:
    raw_value = os.environ.get("TWYPE_SEED_INCLUDE_TEST_USER", "false").strip().lower()
    return raw_value in {"1", "true", "yes", "on"}


def _password_hash(plaintext: str) -> str:
    return pwd_context.hash(plaintext)


async def seed_user() -> None:
    plaintext = os.environ.get("TWYPE_SEED_TEST_USER_PLAINTEXT", "twype-test-user")
    password_hash = _password_hash(plaintext)

    stmt = insert(User).values(
        id=TEST_USER_ID,
        email="test@twype.local",
        password_hash=password_hash,
        is_verified=True,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[User.email],
        set_={
            "password_hash": stmt.excluded.password_hash,
            "is_verified": stmt.excluded.is_verified,
            "updated_at": sa.text("now()"),
        },
    )

    async with session_scope() as session:
        await session.execute(stmt)


async def seed_agent_config() -> None:
    async with session_scope() as session:
        for locale, prompt_layers in PROMPT_LAYER_TRANSLATIONS.items():
            for key, value in prompt_layers.items():
                stmt = insert(AgentConfig).values(
                    key=key,
                    locale=locale,
                    value=value,
                    version=1,
                    is_active=True,
                )
                stmt = stmt.on_conflict_do_update(
                    index_elements=[AgentConfig.key, AgentConfig.locale],
                    set_={
                        "value": stmt.excluded.value,
                        "is_active": stmt.excluded.is_active,
                        "updated_at": sa.text("now()"),
                    },
                )
                await session.execute(stmt)


async def seed_crisis_contacts() -> None:
    async with session_scope() as session:
        for contact in CRISIS_CONTACTS:
            stmt = insert(CrisisContact).values(**contact)
            stmt = stmt.on_conflict_do_update(
                index_elements=[CrisisContact.id],
                set_={
                    "language": stmt.excluded.language,
                    "locale": stmt.excluded.locale,
                    "contact_type": stmt.excluded.contact_type,
                    "name": stmt.excluded.name,
                    "phone": stmt.excluded.phone,
                    "url": stmt.excluded.url,
                    "description": stmt.excluded.description,
                    "priority": stmt.excluded.priority,
                    "is_active": stmt.excluded.is_active,
                    "updated_at": sa.text("now()"),
                },
            )
            await session.execute(stmt)


async def seed_crisis_keywords() -> None:
    async with session_scope() as session:
        for language, payload in CRISIS_KEYWORD_PATTERNS.items():
            stmt = insert(AgentConfig).values(
                key=f"crisis_keywords_{language}",
                locale=language,
                value=json.dumps(payload, ensure_ascii=False),
                version=1,
                is_active=True,
            )
            stmt = stmt.on_conflict_do_update(
                index_elements=[AgentConfig.key, AgentConfig.locale],
                set_={
                    "value": stmt.excluded.value,
                    "is_active": stmt.excluded.is_active,
                    "updated_at": sa.text("now()"),
                },
            )
            await session.execute(stmt)


async def seed_tts_config() -> None:
    stmt = insert(TTSConfig).values(
        voice_id="Olivia",
        model_id="inworld-tts-1.5-max",
        expressiveness=1.0,
        speed=1.0,
        language="ru",
        is_active=True,
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[TTSConfig.voice_id],
        set_={
            "voice_id": stmt.excluded.voice_id,
            "model_id": stmt.excluded.model_id,
            "expressiveness": stmt.excluded.expressiveness,
            "speed": stmt.excluded.speed,
            "language": stmt.excluded.language,
            "is_active": stmt.excluded.is_active,
        },
    )

    async with session_scope() as session:
        await session.execute(stmt)


async def _build_sample_knowledge_chunks(
    *,
    embedding_client: EmbeddingClientProtocol | None = None,
) -> list[EmbeddedChunk]:
    resolved_embedding_client = embedding_client or EmbeddingClient(
        EmbeddingSettings(api_key=_require_google_api_key())
    )
    embedding_inputs = [
        EmbeddingInput(
            text=str(chunk["content"]),
            title=SAMPLE_KNOWLEDGE_SOURCE.title,
            task_type="RETRIEVAL_DOCUMENT",
        )
        for chunk in SAMPLE_KNOWLEDGE_CHUNKS
    ]
    embeddings = await resolved_embedding_client.embed_inputs(embedding_inputs)
    if len(embeddings) != len(SAMPLE_KNOWLEDGE_CHUNKS):
        raise RuntimeError("sample knowledge embedding count does not match seeded chunks")

    return [
        EmbeddedChunk(
            content=str(chunk["content"]),
            section=str(chunk["section"]) if chunk["section"] is not None else None,
            page_range=str(chunk["page_range"]) if chunk["page_range"] is not None else None,
            language=SAMPLE_KNOWLEDGE_SOURCE.language,
            token_count=int(chunk["token_count"]),
            embedding=embedding,
        )
        for chunk, embedding in zip(SAMPLE_KNOWLEDGE_CHUNKS, embeddings, strict=True)
    ]


async def seed_knowledge_data(
    *,
    embedding_client: EmbeddingClientProtocol | None = None,
) -> None:
    loader = DatabaseLoader()
    prepared_source = PreparedSource(
        source=SAMPLE_KNOWLEDGE_SOURCE,
        chunks=await _build_sample_knowledge_chunks(embedding_client=embedding_client),
    )

    async with session_scope() as session:
        await loader.load(session, [prepared_source])


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    _require_database_url()

    logger.info("Seeding database")
    if _should_seed_test_user():
        await seed_user()
    else:
        logger.info("Skipping test user seed; set TWYPE_SEED_INCLUDE_TEST_USER=true to enable it")
    await seed_agent_config()
    await seed_crisis_contacts()
    await seed_crisis_keywords()
    await seed_tts_config()
    await seed_knowledge_data()
    logger.info("Seed complete")


if __name__ == "__main__":
    asyncio.run(main())
