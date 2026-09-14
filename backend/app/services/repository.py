"""
Repository service — business logic for repository management,
file scanning, path safety, and file content retrieval.
"""

import json
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.db.models import Repository
from app.indexing.file_discovery import build_file_tree, discover_files
from app.indexing.language_detector import detect_language, get_language_stats

logger = get_logger(__name__)


def validate_repo_path(path: str) -> Path:
    """Validate and resolve repository path with path traversal protection."""
    resolved = Path(path).resolve()

    if not resolved.exists():
        raise HTTPException(status_code=400, detail=f"Path does not exist: {path}")

    if not resolved.is_dir():
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {path}")

    if settings.ALLOWED_REPO_BASE_PATHS:
        allowed = any(
            str(resolved).startswith(str(Path(base).resolve()))
            for base in settings.ALLOWED_REPO_BASE_PATHS
        )
        if not allowed:
            raise HTTPException(
                status_code=403,
                detail="Repository path is not within allowed base paths",
            )

    return resolved


def safe_resolve_relative_path(repo_path: Path, rel_path: str) -> Path:
    """Safely resolve a relative file path inside a repository."""
    resolved = (repo_path / rel_path).resolve()
    try:
        resolved.relative_to(repo_path)
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied: path traversal attempt")

    if not resolved.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {rel_path}")

    if not resolved.is_file():
        raise HTTPException(status_code=400, detail=f"Path is not a file: {rel_path}")

    return resolved


async def scan_repository_files(repo: Repository, session: AsyncSession) -> dict[str, Any]:
    """
    Scan files in a repository, update total_files and language stats in DB.
    """
    repo_path = Path(repo.path)
    discovered = list(discover_files(repo_path))
    lang_stats = get_language_stats(discovered)

    repo.total_files = len(discovered)
    repo.languages = json.dumps(list(lang_stats.keys()))
    await session.commit()
    await session.refresh(repo)

    return {
        "total_files": len(discovered),
        "languages": lang_stats,
        "files": discovered[:500],
    }


def get_repo_file_content(repo_path: Path, rel_path: str) -> dict[str, Any]:
    """Safely read and return the content of a file within a repo."""
    file_path = safe_resolve_relative_path(repo_path, rel_path)

    # Check file size (max 5MB)
    size = file_path.stat().st_size
    if size > 5 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large to view directly (>5MB)")

    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read file: {e}")

    language = detect_language(rel_path)
    lines = content.splitlines()

    return {
        "path": rel_path,
        "language": language,
        "content": content,
        "size_bytes": size,
        "line_count": len(lines),
    }
