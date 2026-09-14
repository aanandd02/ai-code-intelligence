"""
Embedding provider abstraction and implementations.
100% free, local embedding using Ollama (e.g. nomic-embed-text).
Includes deterministic fallback for local offline testing when Ollama is not active.
"""

from abc import ABC, abstractmethod
import hashlib
import math
from typing import Sequence

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class EmbeddingProvider(ABC):
    """Abstract base class for text embedding generation."""

    @abstractmethod
    async def embed_query(self, text: str) -> list[float]:
        """Embed a single search query text."""
        ...

    @abstractmethod
    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        """Embed a batch of document texts."""
        ...

    @property
    @abstractmethod
    def dimension(self) -> int:
        """Return the vector dimensionality."""
        ...


def _normalize(vec: list[float]) -> list[float]:
    """L2 normalize a vector."""
    norm = math.sqrt(sum(x * x for x in vec))
    if norm < 1e-9:
        return vec
    return [x / norm for x in vec]


def _deterministic_hash_vector(text: str, dim: int = 768) -> list[float]:
    """
    Generate a deterministic pseudo-semantic dense vector from text tokens.
    Used as an offline fallback when Ollama is unavailable.
    """
    vec = [0.0] * dim
    words = text.lower().split()
    if not words:
        words = ["empty"]

    for word in words:
        h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
        # Distribute word influence across multiple dimensions
        idx1 = h % dim
        idx2 = (h >> 16) % dim
        idx3 = (h >> 32) % dim
        sign = 1.0 if (h & 1) else -1.0
        vec[idx1] += sign * 1.0
        vec[idx2] += sign * 0.5
        vec[idx3] += sign * 0.25

    return _normalize(vec)


class OllamaEmbeddingProvider(EmbeddingProvider):
    """
    Local embedding provider using Ollama's nomic-embed-text or any local model.
    Zero-cost, private, GPU/CPU accelerated.
    """

    def __init__(
        self,
        base_url: str | None = None,
        model: str | None = None,
        dimension: int = 768,
        batch_size: int = 32,
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.EMBEDDING_MODEL
        self._dim = dimension or settings.EMBEDDING_DIMENSION
        self.batch_size = batch_size

    @property
    def dimension(self) -> int:
        return self._dim

    async def embed_query(self, text: str) -> list[float]:
        results = await self.embed_documents([text])
        return results[0] if results else [0.0] * self._dim

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []

        all_embeddings: list[list[float]] = []

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                for i in range(0, len(texts), self.batch_size):
                    batch = list(texts[i : i + self.batch_size])

                    # Try modern Ollama /api/embed endpoint first
                    embed_url = f"{self.base_url}/api/embed"
                    resp = await client.post(
                        embed_url,
                        json={"model": self.model, "input": batch},
                    )

                    if resp.status_code == 200:
                        data = resp.json()
                        embeddings = data.get("embeddings", [])
                        if embeddings:
                            all_embeddings.extend(embeddings)
                            continue

                    # Fallback to legacy /api/embeddings endpoint (one by one)
                    legacy_url = f"{self.base_url}/api/embeddings"
                    for item in batch:
                        resp = await client.post(
                            legacy_url,
                            json={"model": self.model, "prompt": item},
                        )
                        if resp.status_code == 200:
                            data = resp.json()
                            all_embeddings.append(data.get("embedding", []))
                        else:
                            raise RuntimeError(f"Ollama embedding error: {resp.text}")

            return all_embeddings

        except Exception as e:
            logger.warning(
                f"Ollama embedding failed ({e}), falling back to deterministic local embeddings. "
                f"To use Ollama, ensure 'ollama serve' is running and '{self.model}' is pulled."
            )
            return [_deterministic_hash_vector(t, self._dim) for t in texts]


class FallbackEmbeddingProvider(EmbeddingProvider):
    """Deterministic offline embedding provider with no dependencies."""

    def __init__(self, dimension: int = 768):
        self._dim = dimension

    @property
    def dimension(self) -> int:
        return self._dim

    async def embed_query(self, text: str) -> list[float]:
        return _deterministic_hash_vector(text, self._dim)

    async def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [_deterministic_hash_vector(t, self._dim) for t in texts]


def get_embedding_provider() -> EmbeddingProvider:
    """Factory function for the active embedding provider."""
    return OllamaEmbeddingProvider()
