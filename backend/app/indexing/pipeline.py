"""
Repository indexing pipeline.
Performs incremental discovery, AST chunking, embedding generation,
and Qdrant vector storage with content-hash deduplication.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any
import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import resolve_repo_path, settings
from app.core.logging import get_logger
from app.db.database import get_session
from app.db.models import Chunk, File, IndexingJob, Repository
from app.indexing.chunker import chunk_with_tree_sitter
from app.indexing.file_discovery import discover_files
from app.indexing.language_detector import detect_language, get_language_stats
from app.llm.embedding_provider import get_embedding_provider
from app.retrieval.qdrant_service import qdrant_service

logger = get_logger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def run_indexing_pipeline(
    repo_id: str,
    session: AsyncSession,
    force_reindex: bool = False,
) -> IndexingJob:
    """
    Run full or incremental indexing for a repository.
    """
    # 1. Load repository
    result = await session.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise ValueError(f"Repository {repo_id} not found")

    repo_path = resolve_repo_path(repo)
    if not repo_path.is_dir():
        raise ValueError(f"Repository directory does not exist: {repo.path}")

    # 2. Create indexing job
    job = IndexingJob(
        repository_id=repo.id,
        status="running",
        started_at=_utcnow(),
    )
    session.add(job)
    await session.commit()
    await session.refresh(job)

    try:
        embedder = get_embedding_provider()
        dim = embedder.dimension
        qdrant_service.ensure_collection(repo.id, dimension=dim)

        # 3. Discover files
        discovered_files = list(discover_files(repo_path))
        job.total_files = len(discovered_files)
        await session.commit()

        # Update language stats on repo
        lang_stats = get_language_stats(discovered_files)
        repo.languages = json.dumps(list(lang_stats.keys()))

        # 4. Fetch existing files from DB
        existing_files_result = await session.execute(
            select(File).where(File.repository_id == repo.id)
        )
        existing_files_map = {f.path: f for f in existing_files_result.scalars().all()}

        chunks_to_embed: list[dict[str, Any]] = []
        new_file_models: list[File] = []
        skipped_chunks_count = 0
        processed_files_count = 0

        for file_info in discovered_files:
            rel_path = file_info["path"]
            abs_path = Path(file_info["abs_path"])
            lang = detect_language(rel_path)

            try:
                content = abs_path.read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                logger.warning(f"Could not read file {abs_path}: {e}")
                continue

            file_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
            existing_file = existing_files_map.get(rel_path)

            # Check if unchanged (incremental indexing)
            if not force_reindex and existing_file and existing_file.content_hash == file_hash:
                skipped_chunks_count += 1
                processed_files_count += 1
                continue

            # If existing file changed, delete old chunks from DB
            if existing_file:
                await session.execute(delete(Chunk).where(Chunk.file_id == existing_file.id))
                existing_file.content_hash = file_hash
                existing_file.last_indexed_at = _utcnow()
                existing_file.size_bytes = file_info["size_bytes"]
                file_record = existing_file
            else:
                file_record = File(
                    repository_id=repo.id,
                    path=rel_path,
                    language=lang,
                    size_bytes=file_info["size_bytes"],
                    content_hash=file_hash,
                    last_indexed_at=_utcnow(),
                )
                session.add(file_record)
                await session.flush()
                existing_files_map[rel_path] = file_record

            # Chunk file content using AST-aware tree-sitter or line fallback
            code_chunks = chunk_with_tree_sitter(
                content=content,
                file_path=rel_path,
                language=lang or "text",
            )

            for c in code_chunks:
                chunk_id = uuid.uuid4().hex
                chunk_record = Chunk(
                    id=chunk_id,
                    file_id=file_record.id,
                    repository_id=repo.id,
                    content=c.content,
                    content_hash=c.content_hash,
                    symbol_name=c.symbol_name,
                    symbol_type=c.symbol_type,
                    language=c.language,
                    start_line=c.start_line,
                    end_line=c.end_line,
                    parent_symbol=c.parent_symbol,
                )
                session.add(chunk_record)

                # Prepare payload for Qdrant
                chunks_to_embed.append({
                    "chunk_id": chunk_id,
                    "text": c.content,
                    "payload": {
                        "chunk_id": chunk_id,
                        "file_path": rel_path,
                        "symbol_name": c.symbol_name,
                        "symbol_type": c.symbol_type,
                        "language": c.language,
                        "start_line": c.start_line,
                        "end_line": c.end_line,
                        "content": c.content,
                        "content_hash": c.content_hash,
                    },
                })

            processed_files_count += 1
            if processed_files_count % 20 == 0:
                job.processed_files = processed_files_count
                await session.commit()

        # 5. Embed chunks in batches and upsert to Qdrant
        if chunks_to_embed:
            texts = [item["text"] for item in chunks_to_embed]
            vectors = await embedder.embed_documents(texts)
            payloads = [item["payload"] for item in chunks_to_embed]

            qdrant_service.upsert_chunks(
                repo_id=repo.id,
                vectors=vectors,
                payloads=payloads,
                dimension=dim,
            )

        # 6. Count total chunks in DB for this repo
        total_chunks_res = await session.execute(
            select(Chunk).where(Chunk.repository_id == repo.id)
        )
        total_chunks = len(total_chunks_res.scalars().all())

        repo.total_files = len(discovered_files)
        repo.total_chunks = total_chunks
        repo.indexed_at = _utcnow()

        job.status = "completed"
        job.processed_files = len(discovered_files)
        job.total_chunks = len(chunks_to_embed)
        job.skipped_chunks = skipped_chunks_count
        job.completed_at = _utcnow()

        await session.commit()
        await session.refresh(job)
        logger.info(
            f"Indexing completed for {repo.name}: {len(chunks_to_embed)} new chunks embedded, "
            f"{skipped_chunks_count} skipped, total {total_chunks} chunks."
        )
        return job

    except Exception as e:
        logger.error(f"Indexing failed for repository {repo_id}: {e}", exc_info=True)
        job.status = "failed"
        job.error_message = str(e)
        job.completed_at = _utcnow()
        await session.commit()
        await session.refresh(job)
        return job
