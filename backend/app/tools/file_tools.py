"""
File inspection tools for the AI agent.
"""

from pathlib import Path
from typing import Any

from app.agents.tool_registry import tool_registry
from app.indexing.file_discovery import discover_files
from app.services.repository import safe_resolve_relative_path


@tool_registry.register(
    name="list_files",
    description="List files in the repository, optionally filtering by directory or file extension.",
    parameters={
        "type": "object",
        "properties": {
            "directory": {
                "type": "string",
                "description": "Optional subdirectory to list within (repo-relative, e.g. 'src' or 'backend')",
            },
            "extension": {
                "type": "string",
                "description": "Optional extension filter (e.g. '.py', '.ts')",
            },
        },
    },
)
async def list_files_tool(
    repo_path: Path,
    directory: str | None = None,
    extension: str | None = None,
) -> list[str]:
    search_dir = (repo_path / directory).resolve() if directory else repo_path
    if not search_dir.exists() or not search_dir.is_dir():
        return [f"Directory not found: {directory}"]

    files = []
    for f in discover_files(repo_path, max_files=200):
        p = f["path"]
        if directory and not p.startswith(directory.strip("/") + "/"):
            continue
        if extension and not p.endswith(extension):
            continue
        files.append(p)
        if len(files) >= 100:
            break
    return files


@tool_registry.register(
    name="read_file",
    description="Read lines from a specific source code file in the repository with line numbers.",
    parameters={
        "type": "object",
        "required": ["file_path"],
        "properties": {
            "file_path": {
                "type": "string",
                "description": "Repository-relative file path (e.g. 'backend/app/main.py')",
            },
            "start_line": {
                "type": "integer",
                "description": "1-indexed starting line number (default 1)",
            },
            "end_line": {
                "type": "integer",
                "description": "1-indexed ending line number (default start_line + 100)",
            },
        },
    },
)
async def read_file_tool(
    repo_path: Path,
    file_path: str,
    start_line: int = 1,
    end_line: int | None = None,
) -> str:
    resolved = safe_resolve_relative_path(repo_path, file_path)
    try:
        content = resolved.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return f"Error reading file: {e}"

    lines = content.splitlines()
    total_lines = len(lines)

    start_idx = max(1, start_line)
    end_idx = min(total_lines, end_line or (start_idx + 100))

    numbered_lines = [
        f"{idx:4d}: {lines[idx - 1]}"
        for idx in range(start_idx, end_idx + 1)
    ]
    return f"File: {file_path} (lines {start_idx}-{end_idx} of {total_lines}):\n" + "\n".join(numbered_lines)
