"""
Security and input validation utilities.
Guards against path traversal, arbitrary command execution, and malicious input.
"""

from pathlib import Path
from typing import Sequence

from fastapi import HTTPException

from app.core.config import resolve_repo_path, settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def validate_path_containment(base_dir: Path, target_path: str | Path) -> Path:
    """
    Ensure target_path resolves strictly within base_dir.
    Raises HTTPException 403 on path traversal attempt.
    """
    base_resolved = resolve_repo_path(base_dir).resolve()
    target_resolved = (base_resolved / target_path).resolve()

    try:
        target_resolved.relative_to(base_resolved)
    except ValueError:
        logger.warning(f"Path traversal detected: {target_path} outside {base_dir}")
        raise HTTPException(
            status_code=403,
            detail="Access forbidden: Path traversal attempt detected",
        )

    return target_resolved


def check_file_size_limit(file_path: Path, max_mb: int | None = None) -> int:
    """Validate that a file does not exceed maximum allowable size."""
    limit_bytes = (max_mb or settings.MAX_FILE_SIZE_MB) * 1024 * 1024
    try:
        size = file_path.stat().st_size
        if size > limit_bytes:
            raise HTTPException(
                status_code=400,
                detail=f"File exceeds maximum allowed size ({size} > {limit_bytes} bytes)",
            )
        return size
    except OSError as e:
        raise HTTPException(status_code=400, detail=f"Cannot inspect file: {e}")
