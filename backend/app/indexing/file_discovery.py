"""
File discovery service — recursively finds source files in a repository,
respecting ignore patterns and .gitignore.
"""

import os
from pathlib import Path
from typing import Generator

import pathspec

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Directories to always ignore
IGNORE_DIRS = {
    ".git",
    "node_modules",
    "venv",
    ".venv",
    "__pycache__",
    "dist",
    "build",
    "coverage",
    ".next",
    "target",
    "vendor",
    ".cache",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "eggs",
    ".eggs",
    "*.egg-info",
    ".gradle",
    ".idea",
    ".vscode",
    ".DS_Store",
}

# File patterns to always ignore
IGNORE_PATTERNS = {
    "*.pyc",
    "*.pyo",
    "*.so",
    "*.dylib",
    "*.dll",
    "*.class",
    "*.o",
    "*.a",
    "*.exe",
    "*.bin",
    "*.lock",
    "package-lock.json",
    "yarn.lock",
    "*.min.js",
    "*.min.css",
    "*.map",
    "*.wasm",
    "*.ico",
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.svg",
    "*.bmp",
    "*.tiff",
    "*.webp",
    "*.mp3",
    "*.mp4",
    "*.avi",
    "*.mov",
    "*.zip",
    "*.tar",
    "*.gz",
    "*.bz2",
    "*.rar",
    "*.7z",
    "*.pdf",
    "*.doc",
    "*.docx",
    "*.xls",
    "*.xlsx",
    "*.ppt",
    "*.pptx",
    "*.db",
    "*.sqlite",
    "*.sqlite3",
}


def _load_gitignore(repo_path: Path) -> pathspec.PathSpec | None:
    """Load .gitignore patterns from the repository root."""
    gitignore_path = repo_path / ".gitignore"
    if not gitignore_path.exists():
        return None

    try:
        with open(gitignore_path, "r") as f:
            return pathspec.PathSpec.from_lines("gitignore", f)
    except Exception as e:
        logger.warning(f"Failed to load .gitignore: {e}")
        return None


def _should_ignore_dir(dirname: str) -> bool:
    """Check if a directory name should be ignored."""
    return dirname in IGNORE_DIRS or dirname.startswith(".")


def _should_ignore_file(filename: str) -> bool:
    """Check if a file should be ignored by its name/extension."""
    for pattern in IGNORE_PATTERNS:
        if pattern.startswith("*."):
            ext = pattern[1:]
            if filename.endswith(ext):
                return True
        elif filename == pattern:
            return True
    return False


def discover_files(
    repo_path: str | Path,
    max_files: int | None = None,
    max_file_size_mb: int | None = None,
) -> Generator[dict, None, None]:
    """
    Recursively discover source files in a repository.

    Yields dicts with:
        - path: repo-relative file path
        - abs_path: absolute file path
        - size_bytes: file size
        - extension: file extension

    Respects .gitignore, built-in ignore lists, and size limits.
    """
    repo_path = Path(repo_path).resolve()
    if not repo_path.is_dir():
        raise ValueError(f"Not a valid directory: {repo_path}")

    max_files = max_files or settings.MAX_REPO_FILES
    max_size = (max_file_size_mb or settings.MAX_FILE_SIZE_MB) * 1024 * 1024

    gitignore = _load_gitignore(repo_path)
    file_count = 0

    for root, dirs, files in os.walk(repo_path, topdown=True):
        root_path = Path(root)
        rel_root = root_path.relative_to(repo_path)

        # Filter out ignored directories (modifying dirs in-place with topdown=True)
        dirs[:] = sorted(
            d for d in dirs
            if not _should_ignore_dir(d)
        )

        # Further filter using .gitignore
        if gitignore:
            dirs[:] = [
                d for d in dirs
                if not gitignore.match_file(str(rel_root / d) + "/")
            ]

        for filename in sorted(files):
            if file_count >= max_files:
                logger.warning(f"File limit reached ({max_files}), stopping discovery")
                return

            # Check ignore patterns
            if _should_ignore_file(filename):
                continue

            file_path = root_path / filename
            rel_path = str(file_path.relative_to(repo_path))

            # Check .gitignore
            if gitignore and gitignore.match_file(rel_path):
                continue

            # Check file size
            try:
                size = file_path.stat().st_size
            except OSError:
                continue

            if size > max_size:
                logger.debug(f"Skipping large file: {rel_path} ({size} bytes)")
                continue

            if size == 0:
                continue

            # Check if it's likely a text file (skip binary)
            extension = file_path.suffix.lower()

            file_count += 1
            yield {
                "path": rel_path,
                "abs_path": str(file_path),
                "size_bytes": size,
                "extension": extension,
            }

    logger.info(f"Discovered {file_count} files in {repo_path}")


def build_file_tree(repo_path: str | Path) -> list[dict]:
    """
    Build a hierarchical file tree for the repository.
    Returns nested dicts suitable for the frontend tree view.
    """
    repo_path = Path(repo_path).resolve()
    tree: dict = {}

    for file_info in discover_files(repo_path, max_files=5000):
        parts = Path(file_info["path"]).parts
        current = tree
        for i, part in enumerate(parts):
            if i == len(parts) - 1:
                # File
                if "_files" not in current:
                    current["_files"] = []
                current["_files"].append({
                    "path": file_info["path"],
                    "language": None,  # Will be set by language detector
                    "size_bytes": file_info["size_bytes"],
                    "is_directory": False,
                })
            else:
                # Directory
                if part not in current:
                    current[part] = {}
                current = current[part]

    def _dict_to_tree(d: dict, prefix: str = "") -> list[dict]:
        items = []
        # Directories first
        for key in sorted(k for k in d if k != "_files"):
            dir_path = f"{prefix}/{key}" if prefix else key
            children = _dict_to_tree(d[key], dir_path)
            items.append({
                "path": dir_path,
                "is_directory": True,
                "size_bytes": 0,
                "language": None,
                "children": children,
            })
        # Then files
        if "_files" in d:
            items.extend(sorted(d["_files"], key=lambda f: f["path"]))
        return items

    return _dict_to_tree(tree)
