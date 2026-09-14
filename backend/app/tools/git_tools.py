"""
Git inspection tools for the AI agent.
"""

from pathlib import Path
from typing import Any

import git

from app.agents.tool_registry import tool_registry


def _get_git_repo(repo_path: Path) -> git.Repo | None:
    try:
        return git.Repo(repo_path)
    except Exception:
        return None


@tool_registry.register(
    name="git_status",
    description="Get current Git status: branch, untracked files, modified files, and staged changes.",
    parameters={"type": "object", "properties": {}},
)
async def git_status_tool(repo_path: Path) -> dict[str, Any]:
    repo = _get_git_repo(repo_path)
    if not repo:
        return {"is_git": False, "message": "Not a git repository"}

    try:
        branch = repo.active_branch.name if not repo.head.is_detached else "DETACHED_HEAD"
    except Exception:
        branch = "unknown"

    untracked = repo.untracked_files
    modified = [item.a_path for item in repo.index.diff(None)]
    staged = [item.a_path for item in repo.index.diff("HEAD")] if repo.heads else []

    return {
        "is_git": True,
        "branch": branch,
        "is_dirty": repo.is_dirty(untracked_files=True),
        "untracked_files": untracked[:20],
        "modified_files": modified[:20],
        "staged_files": staged[:20],
    }


@tool_registry.register(
    name="git_diff",
    description="View git diff of uncommitted changes.",
    parameters={
        "type": "object",
        "properties": {
            "cached": {
                "type": "boolean",
                "description": "Whether to view staged changes (default false)",
            },
        },
    },
)
async def git_diff_tool(repo_path: Path, cached: bool = False) -> str:
    repo = _get_git_repo(repo_path)
    if not repo:
        return "Not a git repository"

    try:
        if cached:
            diff = repo.git.diff("--cached")
        else:
            diff = repo.git.diff()
        return diff if diff else "No uncommitted changes."
    except Exception as e:
        return f"Error running git diff: {e}"


@tool_registry.register(
    name="git_log",
    description="View recent git commit history.",
    parameters={
        "type": "object",
        "properties": {
            "max_commits": {
                "type": "integer",
                "description": "Maximum number of commits to retrieve (default 5)",
            },
        },
    },
)
async def git_log_tool(repo_path: Path, max_commits: int = 5) -> list[dict[str, str]]:
    repo = _get_git_repo(repo_path)
    if not repo:
        return [{"error": "Not a git repository"}]

    try:
        commits = list(repo.iter_commits(max_count=max_commits))
        return [
            {
                "hash": c.hexsha[:8],
                "author": f"{c.author.name} <{c.author.email}>",
                "date": c.committed_datetime.isoformat(),
                "message": c.message.strip(),
            }
            for c in commits
        ]
    except Exception as e:
        return [{"error": str(e)}]
