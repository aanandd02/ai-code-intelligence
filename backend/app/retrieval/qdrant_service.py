"""
Qdrant vector database service.
Handles collection creation, vector upsert, and similarity search.
Supports both remote Qdrant (Docker) and embedded local/in-memory fallback.
"""

from pathlib import Path
from typing import Any
import uuid

import qdrant_client
from qdrant_client.http.exceptions import UnexpectedResponse
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class QdrantService:
    """Service wrapping Qdrant client interactions."""

    def __init__(self):
        self._client: qdrant_client.QdrantClient | None = None
        self._is_local_fallback: bool = False

    def get_client(self) -> qdrant_client.QdrantClient:
        """
        Get or initialize the Qdrant client.
        Tries connecting to the remote Qdrant service first;
        if unavailable, falls back to embedded local storage.
        """
        if self._client is not None:
            return self._client

        try:
            # Try connecting to Qdrant HTTP service
            client = qdrant_client.QdrantClient(
                host=settings.QDRANT_HOST,
                port=settings.QDRANT_PORT,
                timeout=5.0,
                check_compatibility=False,
            )
            # Ping
            client.get_collections()
            self._client = client
            self._is_local_fallback = False
            logger.info(f"Connected to Qdrant server at {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")
            return self._client
        except Exception as e:
            logger.info(
                f"Qdrant server not reachable ({e}). Using embedded local vector storage."
            )
            data_dir = Path("./data/qdrant_storage").resolve()
            data_dir.mkdir(parents=True, exist_ok=True)
            self._client = qdrant_client.QdrantClient(path=str(data_dir))
            self._is_local_fallback = True
            return self._client

    @staticmethod
    def get_collection_name(repo_id: str) -> str:
        """Generate a valid Qdrant collection name for a repository."""
        # Clean collection name (alphanumeric and underscores only)
        clean_id = repo_id.replace("-", "_")
        return f"repo_{clean_id}"

    def ensure_collection(self, repo_id: str, dimension: int = 768) -> str:
        """Ensure the repository collection exists with proper vector configuration."""
        client = self.get_client()
        name = self.get_collection_name(repo_id)

        try:
            collections = [c.name for c in client.get_collections().collections]
            if name not in collections:
                client.create_collection(
                    collection_name=name,
                    vectors_config=VectorParams(
                        size=dimension,
                        distance=Distance.COSINE,
                    ),
                )
                logger.info(f"Created Qdrant collection: {name} (dim={dimension})")
        except Exception as e:
            logger.error(f"Failed to ensure collection {name}: {e}")
            raise

        return name

    def upsert_chunks(
        self,
        repo_id: str,
        vectors: list[list[float]],
        payloads: list[dict[str, Any]],
        dimension: int = 768,
    ) -> int:
        """
        Upsert chunk vectors and metadata into the repository collection.
        Returns the count of upserted points.
        """
        if not vectors or not payloads or len(vectors) != len(payloads):
            return 0

        client = self.get_client()
        col_name = self.ensure_collection(repo_id, dimension=dimension)

        points = []
        for vec, payload in zip(vectors, payloads):
            # Generate deterministic UUID from chunk hash or random UUID
            point_id = payload.get("id")
            if not point_id:
                point_id = str(uuid.uuid4())

            points.append(
                PointStruct(
                    id=point_id,
                    vector=vec,
                    payload=payload,
                )
            )

        # Batch upsert
        batch_size = 100
        total_upserted = 0
        for i in range(0, len(points), batch_size):
            batch = points[i : i + batch_size]
            client.upsert(collection_name=col_name, points=batch)
            total_upserted += len(batch)

        logger.info(f"Upserted {total_upserted} points into collection {col_name}")
        return total_upserted

    def search(
        self,
        repo_id: str,
        query_vector: list[float],
        top_k: int = 10,
        language: str | None = None,
        file_path_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Search for similar code chunks in the repository collection.
        """
        client = self.get_client()
        col_name = self.get_collection_name(repo_id)

        try:
            collections = [c.name for c in client.get_collections().collections]
            if col_name not in collections:
                logger.warning(f"Collection {col_name} does not exist yet")
                return []
        except Exception as e:
            logger.warning(f"Could not verify collection: {e}")
            return []

        filter_conditions = []
        if language:
            filter_conditions.append(
                FieldCondition(key="language", match=MatchValue(value=language))
            )
        if file_path_filter:
            filter_conditions.append(
                FieldCondition(key="file_path", match=MatchValue(value=file_path_filter))
            )

        query_filter = Filter(must=filter_conditions) if filter_conditions else None

        try:
            # Try modern query_points first
            res = client.query_points(
                collection_name=col_name,
                query=query_vector,
                query_filter=query_filter,
                limit=top_k,
            )
            points = res.points
        except Exception:
            # Fallback to search()
            points = client.search(
                collection_name=col_name,
                query_vector=query_vector,
                query_filter=query_filter,
                limit=top_k,
            )

        results = []
        for p in points:
            payload = p.payload or {}
            results.append({
                "chunk_id": payload.get("chunk_id", str(p.id)),
                "file_path": payload.get("file_path", ""),
                "symbol_name": payload.get("symbol_name"),
                "symbol_type": payload.get("symbol_type"),
                "language": payload.get("language"),
                "start_line": payload.get("start_line", 0),
                "end_line": payload.get("end_line", 0),
                "content": payload.get("content", ""),
                "score": float(p.score) if hasattr(p, "score") and p.score is not None else 0.0,
            })

        return results

    def delete_collection(self, repo_id: str) -> bool:
        """Delete collection when repository is removed."""
        client = self.get_client()
        col_name = self.get_collection_name(repo_id)
        try:
            client.delete_collection(collection_name=col_name)
            logger.info(f"Deleted Qdrant collection: {col_name}")
            return True
        except Exception as e:
            logger.warning(f"Error deleting collection {col_name}: {e}")
            return False


# Singleton instance
qdrant_service = QdrantService()
