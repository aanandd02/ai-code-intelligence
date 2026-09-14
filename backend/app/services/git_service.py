"""
Git integration service using GitPython.
Provides status, diffs, commit logs, and blame analysis.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException
import git

from app.core.logging import get_logger
from app.core.security import validate_path_containment
from app.schemas.schemas import GitDiffResponse, GitLogEntry, GitStatusResponse

logger = get_logger(__name__)


def _get_git_repo(repo_path: Path) -> git.Repo | None:
    """Load git repository or return None if not a git repository."""
    try:
        return git.Repo(repo_path)
    except (git.InvalidGitRepositoryError, git.NoSuchPathError):
        return None
    except Exception as e:
        logger.warning(f"Git inspection error on {repo_path}: {e}")
        return None


class GitService:
    """Service for interacting with local Git repositories."""

    def get_status(self, repo_path: Path) -> GitStatusResponse:
        repo = _get_git_repo(repo_path)
        if not repo:
            return GitStatusResponse(
                branch="non-git",
                is_dirty=False,
                changed_files=[],
                untracked_files=[],
                commit_message="Not a git repository",
            )

        try:
            branch = repo.active_branch.name if not repo.head.is_detached else "DETACHED_HEAD"
        except Exception:
            branch = None

        commit_hash = None
        commit_message = None
        if repo.heads:
            try:
                commit = repo.head.commit
                commit_hash = commit.hexsha
                commit_message = commit.message.strip()
            except Exception:
                pass

        # Changed files in working tree vs index
        changed_files = []
        for diff_item in repo.index.diff(None):
            changed_files.append({
                "path": diff_item.a_path or diff_item.b_path,
                "change_type": diff_item.change_type,
            })

        # Staged files vs HEAD
        if repo.heads:
            for diff_item in repo.index.diff("HEAD"):
                changed_files.append({
                    "path": diff_item.a_path or diff_item.b_path,
                    "change_type": f"staged_{diff_item.change_type}",
                })

        untracked = repo.untracked_files

        return GitStatusResponse(
            branch=branch,
            is_dirty=repo.is_dirty(untracked_files=True),
            changed_files=changed_files,
            untracked_files=untracked,
            commit_hash=commit_hash,
            commit_message=commit_message,
        )

    def get_diff(self, repo_path: Path, cached: bool = False) -> GitDiffResponse:
        repo = _get_git_repo(repo_path)
        if not repo:
            return GitDiffResponse(
                diff="Directory is not a Git repository. Initialize git to view diffs.",
                files_changed=0,
                insertions=0,
                deletions=0,
            )

        try:
            if cached:
                diff_text = repo.git.diff("--cached")
            else:
                diff_text = repo.git.diff()

            insertions = 0
            deletions = 0
            for line in diff_text.splitlines():
                if line.startswith("+") and not line.startswith("+++"):
                    insertions += 1
                elif line.startswith("-") and not line.startswith("---"):
                    deletions += 1

            files_changed = diff_text.count("diff --git")

            return GitDiffResponse(
                diff=diff_text if diff_text else "Working directory clean. No uncommitted changes.",
                files_changed=files_changed,
                insertions=insertions,
                deletions=deletions,
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to generate git diff: {e}")

    def get_log(self, repo_path: Path, max_commits: int = 20) -> list[GitLogEntry]:
        repo = _get_git_repo(repo_path)
        if not repo:
            return []

        try:
            commits = list(repo.iter_commits(max_count=max_commits))
            entries = []
            for c in commits:
                entries.append(
                    GitLogEntry(
                        hash=c.hexsha,
                        short_hash=c.hexsha[:8],
                        author=f"{c.author.name} <{c.author.email}>",
                        date=c.committed_datetime,
                        message=c.message.strip(),
                        files_changed=len(c.stats.files) if hasattr(c, "stats") else 0,
                    )
                )
            return entries
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to read git log: {e}")

    def get_blame(self, repo_path: Path, file_path: str) -> list[dict[str, Any]]:
        repo = _get_git_repo(repo_path)
        if not repo:
            return []
        target = validate_path_containment(repo_path, file_path)
        rel_path = str(target.relative_to(repo_path))

        try:
            blame_data = repo.blame("HEAD", rel_path)
            results = []
            line_counter = 1
            for commit, lines in blame_data:
                for line in lines:
                    results.append({
                        "line": line_counter,
                        "commit": commit.hexsha[:8],
                        "author": commit.author.name,
                        "date": commit.committed_datetime.isoformat(),
                        "content": line,
                    })
                    line_counter += 1
            return results
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get git blame: {e}")


git_service = GitService()
