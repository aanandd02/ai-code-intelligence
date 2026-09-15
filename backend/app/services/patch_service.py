"""
Safe patch management and application service.
Generates unified diffs, verifies path containment, creates backups before applying,
and allows safe revert.
"""

from datetime import datetime, timezone
import difflib
import json
from pathlib import Path
import shutil
from typing import Any
import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import resolve_repo_path, settings
from app.core.logging import get_logger
from app.core.security import validate_path_containment
from app.db.models import GeneratedPatch, Repository
from app.schemas.schemas import (
    PatchApplyRequest,
    PatchApplyResponse,
    PatchFile,
    PatchPreviewRequest,
    PatchPreviewResponse,
)

logger = get_logger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PatchService:
    """Service for safely staging, previewing, and applying patches."""

    async def preview_patch(
        self,
        repo_id: str,
        req: PatchPreviewRequest,
        session: AsyncSession,
    ) -> PatchPreviewResponse:
        res = await session.execute(select(Repository).where(Repository.id == repo_id))
        repo = res.scalar_one_or_none()
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")

        repo_path = resolve_repo_path(repo)
        processed_files: list[PatchFile] = []
        warnings: list[str] = []

        for pf in req.files:
            target = validate_path_containment(repo_path, pf.file_path)
            before_content = ""
            if target.exists():
                before_content = target.read_text(encoding="utf-8", errors="replace")
            else:
                warnings.append(f"File `{pf.file_path}` does not exist; applying this patch will create a new file.")

            after_content = pf.after or ""

            # Compute unified diff
            diff_lines = list(
                difflib.unified_diff(
                    before_content.splitlines(keepends=True),
                    after_content.splitlines(keepends=True),
                    fromfile=f"a/{pf.file_path}",
                    tofile=f"b/{pf.file_path}",
                )
            )
            diff_text = "".join(diff_lines)

            processed_files.append(
                PatchFile(
                    file_path=pf.file_path,
                    before=before_content,
                    after=after_content,
                    diff=diff_text,
                )
            )

        # Check if git repo is clean
        is_clean = True
        try:
            import git
            git_repo = git.Repo(repo_path)
            is_clean = not git_repo.is_dirty(untracked_files=False)
            if not is_clean:
                warnings.append("Repository has uncommitted changes in working tree.")
        except Exception:
            pass

        # Save staged patch record
        patch_id = uuid.uuid4().hex
        patch_record = GeneratedPatch(
            id=patch_id,
            repository_id=repo.id,
            description=req.description,
            diff_content="\n".join(f.diff or "" for f in processed_files),
            files_json=json.dumps([f.model_dump() for f in processed_files]),
            status="pending",
        )
        session.add(patch_record)
        await session.commit()

        return PatchPreviewResponse(
            id=patch_id,
            description=req.description,
            files=processed_files,
            is_repo_clean=is_clean,
            warnings=warnings,
        )

    async def apply_patch(
        self,
        repo_id: str,
        req: PatchApplyRequest,
        session: AsyncSession,
    ) -> PatchApplyResponse:
        res = await session.execute(
            select(GeneratedPatch).where(
                GeneratedPatch.id == req.patch_id,
                GeneratedPatch.repository_id == repo_id,
            )
        )
        patch = res.scalar_one_or_none()
        if not patch:
            raise HTTPException(status_code=404, detail="Patch not found")

        if patch.status == "applied":
            raise HTTPException(status_code=400, detail="Patch has already been applied")

        repo_res = await session.execute(select(Repository).where(Repository.id == repo_id))
        repo = repo_res.scalar_one_or_none()
        if not repo:
            raise HTTPException(status_code=404, detail="Repository not found")

        repo_path = resolve_repo_path(repo)
        files_data = json.loads(patch.files_json or "[]")

        # Create backup directory
        backup_id = f"backup_{patch.id[:8]}_{int(datetime.now().timestamp())}"
        backup_dir = settings.data_dir / "backups" / repo.id / backup_id
        if req.create_backup:
            backup_dir.mkdir(parents=True, exist_ok=True)

        applied_files: list[str] = []

        try:
            for item in files_data:
                rel_path = item["file_path"]
                target_path = validate_path_containment(repo_path, rel_path)
                after_content = item.get("after", "")

                # Backup existing file
                if req.create_backup and target_path.exists():
                    backup_file = backup_dir / rel_path
                    backup_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(target_path, backup_file)

                # Write new content
                target_path.parent.mkdir(parents=True, exist_ok=True)
                target_path.write_text(after_content, encoding="utf-8")
                applied_files.append(rel_path)

            patch.status = "applied"
            patch.applied_at = _utcnow()
            await session.commit()

            return PatchApplyResponse(
                success=True,
                message=f"Successfully applied patch to {len(applied_files)} files.",
                applied_files=applied_files,
                backup_ref=str(backup_dir) if req.create_backup else None,
            )

        except Exception as e:
            logger.error(f"Error applying patch {patch.id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to apply patch: {e}")


patch_service = PatchService()
