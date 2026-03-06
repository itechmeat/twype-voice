from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal

import httpx

from src.knowledge_constants import (
    EMBEDDING_BATCH_SIZE,
    EMBEDDING_DIMENSION,
    EMBEDDING_MODEL,
)

logger = logging.getLogger(__name__)


class EmbeddingError(RuntimeError):
    pass


EmbeddingTaskType = Literal["RETRIEVAL_DOCUMENT", "RETRIEVAL_QUERY", "SEMANTIC_SIMILARITY"]


@dataclass(slots=True, frozen=True)
class EmbeddingInput:
    text: str
    title: str | None = None
    task_type: EmbeddingTaskType | None = None


@dataclass(slots=True, frozen=True)
class EmbeddingSettings:
    api_key: str
    base_url: str = "https://generativelanguage.googleapis.com/v1beta"
    model: str = EMBEDDING_MODEL
    batch_size: int = EMBEDDING_BATCH_SIZE
    timeout_seconds: float = 30.0
    output_dimensionality: int = EMBEDDING_DIMENSION
    default_task_type: EmbeddingTaskType = "RETRIEVAL_DOCUMENT"


class EmbeddingClient:
    def __init__(
        self,
        settings: EmbeddingSettings,
        *,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings
        self._client = client

    async def embed_inputs(self, inputs: list[EmbeddingInput]) -> list[list[float]]:
        if not inputs:
            return []

        results: list[list[float]] = []
        own_client = self._client is None
        client = self._client or httpx.AsyncClient(
            base_url=self._settings.base_url.rstrip("/"),
            headers={"x-goog-api-key": self._settings.api_key},
            timeout=self._settings.timeout_seconds,
        )

        try:
            for batch_start in range(0, len(inputs), self._settings.batch_size):
                batch = inputs[batch_start : batch_start + self._settings.batch_size]
                requests = []
                for item in batch:
                    request_payload: dict[str, object] = {
                        "model": self._model_name(),
                        "content": {"parts": [{"text": item.text}]},
                        "taskType": item.task_type or self._settings.default_task_type,
                        "outputDimensionality": self._settings.output_dimensionality,
                    }
                    if item.title:
                        request_payload["title"] = item.title
                    requests.append(request_payload)

                try:
                    response = await client.post(
                        f"/{self._model_name()}:batchEmbedContents",
                        json={"requests": requests},
                    )
                    response.raise_for_status()
                except httpx.HTTPError as exc:
                    logger.exception("Embedding request failed")
                    raise EmbeddingError(str(exc)) from exc

                payload = response.json()
                data = payload.get("embeddings")
                if not isinstance(data, list):
                    raise EmbeddingError("Embedding response missing 'embeddings' list")

                embeddings = [item.get("values") for item in data if isinstance(item, dict)]
                if len(embeddings) != len(batch):
                    raise EmbeddingError("Embedding response size does not match request batch")

                for embedding in embeddings:
                    if not isinstance(embedding, list):
                        raise EmbeddingError("Embedding vector must be a list")
                    if len(embedding) != self._settings.output_dimensionality:
                        raise EmbeddingError("Embedding vector dimension does not match settings")
                    results.append([float(value) for value in embedding])
        finally:
            if own_client:
                await client.aclose()

        return results

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return await self.embed_inputs([EmbeddingInput(text=text) for text in texts])

    def _model_name(self) -> str:
        if self._settings.model.startswith("models/"):
            return self._settings.model
        return f"models/{self._settings.model}"
