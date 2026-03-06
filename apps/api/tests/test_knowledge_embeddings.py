from __future__ import annotations

import httpx
import pytest
from src.knowledge_constants import EMBEDDING_DIMENSION
from src.knowledge_ingestion.embeddings import (
    EmbeddingClient,
    EmbeddingError,
    EmbeddingInput,
    EmbeddingSettings,
)


@pytest.mark.asyncio
async def test_embedding_client_batches_requests() -> None:
    requests: list[list[dict[str, object]]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        payload = __import__("json").loads(request.content.decode("utf-8"))
        requests.append(payload["requests"])
        data = [{"values": [0.001] * EMBEDDING_DIMENSION} for _ in payload["requests"]]
        return httpx.Response(200, json={"embeddings": data})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://gemini.test") as client:
        embedding_client = EmbeddingClient(
            EmbeddingSettings(api_key="test-key"),
            client=client,
        )
        embeddings = await embedding_client.embed_inputs(
            [EmbeddingInput(text="chunk", title="Fixture", task_type="RETRIEVAL_DOCUMENT")] * 250
        )

    assert len(requests) == 3
    assert [len(batch) for batch in requests] == [100, 100, 50]
    assert requests[0][0]["taskType"] == "RETRIEVAL_DOCUMENT"
    assert requests[0][0]["outputDimensionality"] == EMBEDDING_DIMENSION
    assert requests[0][0]["title"] == "Fixture"
    assert len(embeddings) == 250


@pytest.mark.asyncio
async def test_embedding_client_raises_on_http_error() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"error": "temporary failure"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="https://gemini.test") as client:
        embedding_client = EmbeddingClient(
            EmbeddingSettings(api_key="test-key"),
            client=client,
        )
        with pytest.raises(EmbeddingError):
            await embedding_client.embed_texts(["chunk"])
