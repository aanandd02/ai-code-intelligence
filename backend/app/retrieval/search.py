"""
Semantic code search service.
Translates natural language queries into vector embeddings and queries Qdrant.
"""

from app.core.logging import get_logger
from app.llm.embedding_provider import get_embedding_provider
from app.retrieval.qdrant_service import qdrant_service
from app.schemas.schemas import SearchResponse, SearchResult

logger = get_logger(__name__)


async def semantic_search(
    repo_id: str,
    query: str,
    top_k: int = 10,
    language: str | None = None,
    file_path_filter: str | None = None,
) -> SearchResponse:
    """
    Search repository codebase using semantic query vector against Qdrant.
    """
    embedder = get_embedding_provider()
    query_vector = await embedder.embed_query(query)

    raw_results = qdrant_service.search(
        repo_id=repo_id,
        query_vector=query_vector,
        top_k=top_k,
        language=language,
        file_path_filter=file_path_filter,
    )

    results = []
    for item in raw_results:
        results.append(
            SearchResult(
                file_path=item.get("file_path", ""),
                symbol_name=item.get("symbol_name"),
                symbol_type=item.get("symbol_type"),
                language=item.get("language"),
                start_line=item.get("start_line", 0),
                end_line=item.get("end_line", 0),
                content=item.get("content", ""),
                score=round(item.get("score", 0.0), 4),
            )
        )

    return SearchResponse(
        query=query,
        results=results,
        total=len(results),
    )
