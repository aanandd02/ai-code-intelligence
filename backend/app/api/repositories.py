"""
Repository management API endpoints.
Provides repository CRUD, file discovery, tree view, and file content viewing.
"""

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.db.database import get_session
from app.db.models import Repository
from app.indexing.file_discovery import build_file_tree, discover_files
from app.indexing.language_detector import detect_language
from app.schemas.schemas import (
    ChatRequest,
    ChatResponse,
    FileContentResponse,
    FileInfo,
    GenerateTestsRequest,
    GenerateTestsResponse,
    GitDiffResponse,
    GitLogEntry,
    GitStatusResponse,
    IndexingJobResponse,
    InvestigateRequest,
    InvestigationResponse,
    PatchApplyRequest,
    PatchApplyResponse,
    PatchPreviewRequest,
    PatchPreviewResponse,
    RepositoryCreate,
    RepositoryListResponse,
    RepositoryResponse,
    ReviewRequest,
    ReviewResponse,
    RunTestsRequest,
    SearchResponse,
    SemanticSearchRequest,
    TestRunResponse,
)
from app.services.repository import (
    get_repo_file_content,
    scan_repository_files,
    validate_repo_path,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/repositories", tags=["repositories"])


@router.post("", response_model=RepositoryResponse, status_code=201)
async def create_repository(
    req: RepositoryCreate,
    session: AsyncSession = Depends(get_session),
) -> RepositoryResponse:
    """Register a local repository for analysis."""
    resolved_path = validate_repo_path(req.path)

    # Check for duplicate
    existing = await session.execute(
        select(Repository).where(Repository.path == str(resolved_path))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"Repository already registered: {resolved_path}",
        )

    # Auto-detect name from directory
    name = req.name or resolved_path.name

    # Detect if it's a Git repo
    is_git = (resolved_path / ".git").exists()
    default_branch = None
    if is_git:
        try:
            head_file = resolved_path / ".git" / "HEAD"
            if head_file.exists():
                ref = head_file.read_text().strip()
                if ref.startswith("ref: refs/heads/"):
                    default_branch = ref.replace("ref: refs/heads/", "")
        except Exception:
            pass

    repo = Repository(
        name=name,
        path=str(resolved_path),
        default_branch=default_branch,
    )
    session.add(repo)
    await session.flush()
    await session.refresh(repo)

    logger.info(f"Repository registered: {name} at {resolved_path}")

    # Initial scan to populate file counts and languages
    try:
        await scan_repository_files(repo, session)
    except Exception as e:
        logger.warning(f"Initial scan failed for {name}: {e}")

    languages = None
    if repo.languages:
        try:
            languages = json.loads(repo.languages)
        except Exception:
            languages = None

    return RepositoryResponse(
        id=repo.id,
        name=repo.name,
        path=repo.path,
        default_branch=repo.default_branch,
        languages=languages,
        total_files=repo.total_files,
        total_chunks=repo.total_chunks,
        created_at=repo.created_at,
        updated_at=repo.updated_at,
    )


@router.get("", response_model=RepositoryListResponse)
async def list_repositories(
    session: AsyncSession = Depends(get_session),
) -> RepositoryListResponse:
    """List all registered repositories."""
    result = await session.execute(select(Repository).order_by(Repository.created_at.desc()))
    repos = result.scalars().all()

    items = []
    for r in repos:
        languages = None
        if r.languages:
            try:
                languages = json.loads(r.languages)
            except Exception:
                languages = None

        items.append(
            RepositoryResponse(
                id=r.id,
                name=r.name,
                path=r.path,
                description=r.description,
                default_branch=r.default_branch,
                languages=languages,
                total_files=r.total_files,
                total_chunks=r.total_chunks,
                indexed_at=r.indexed_at,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
        )

    return RepositoryListResponse(repositories=items, total=len(items))


@router.get("/{repo_id}", response_model=RepositoryResponse)
async def get_repository(
    repo_id: str,
    session: AsyncSession = Depends(get_session),
) -> RepositoryResponse:
    """Get repository details."""
    result = await session.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    languages = None
    if repo.languages:
        try:
            languages = json.loads(repo.languages)
        except Exception:
            languages = None

    return RepositoryResponse(
        id=repo.id,
        name=repo.name,
        path=repo.path,
        description=repo.description,
        default_branch=repo.default_branch,
        languages=languages,
        total_files=repo.total_files,
        total_chunks=repo.total_chunks,
        indexed_at=repo.indexed_at,
        created_at=repo.created_at,
        updated_at=repo.updated_at,
    )


@router.post("/{repo_id}/scan")
async def scan_repository(
    repo_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Scan or rescan repository files and recalculate language breakdown."""
    result = await session.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    return await scan_repository_files(repo, session)


@router.get("/{repo_id}/files", response_model=list[FileInfo])
async def list_repo_files(
    repo_id: str,
    session: AsyncSession = Depends(get_session),
) -> list[FileInfo]:
    """Get flat list of files in the repository."""
    result = await session.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    repo_path = Path(repo.path)
    if not repo_path.is_dir():
        raise HTTPException(status_code=400, detail="Repository directory no longer exists on disk")

    files = []
    for f in discover_files(repo_path):
        lang = detect_language(f["path"])
        files.append(
            FileInfo(
                path=f["path"],
                language=lang,
                size_bytes=f["size_bytes"],
                is_directory=False,
            )
        )

    return files


@router.get("/{repo_id}/tree")
async def get_repo_file_tree(
    repo_id: str,
    session: AsyncSession = Depends(get_session),
) -> list[dict]:
    """Get hierarchical file tree for the repository."""
    result = await session.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    repo_path = Path(repo.path)
    if not repo_path.is_dir():
        raise HTTPException(status_code=400, detail="Repository directory no longer exists on disk")

    return build_file_tree(repo_path)


@router.get("/{repo_id}/file", response_model=FileContentResponse)
async def get_file_content(
    repo_id: str,
    path: str = Query(..., description="Repository-relative file path"),
    session: AsyncSession = Depends(get_session),
) -> FileContentResponse:
    """Safely get the content of a specific file in the repository."""
    result = await session.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    file_data = get_repo_file_content(Path(repo.path), path)
    return FileContentResponse(**file_data)


@router.post("/{repo_id}/index", response_model=IndexingJobResponse)
async def trigger_indexing(
    repo_id: str,
    force: bool = Query(False, description="Force re-indexing all files"),
    session: AsyncSession = Depends(get_session),
) -> IndexingJobResponse:
    """Trigger indexing for a repository (AST parsing + embeddings + vector storage)."""
    result = await session.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    from app.indexing.pipeline import run_indexing_pipeline

    job = await run_indexing_pipeline(repo_id, session, force_reindex=force)
    return IndexingJobResponse.model_validate(job)


@router.get("/{repo_id}/indexing-status", response_model=IndexingJobResponse)
async def get_indexing_status(
    repo_id: str,
    session: AsyncSession = Depends(get_session),
) -> IndexingJobResponse:
    """Get the latest indexing job status for a repository."""
    from app.db.models import IndexingJob

    result = await session.execute(
        select(IndexingJob)
        .where(IndexingJob.repository_id == repo_id)
        .order_by(IndexingJob.created_at.desc())
    )
    job = result.scalars().first()
    if not job:
        raise HTTPException(status_code=404, detail="No indexing jobs found for this repository")

    return IndexingJobResponse.model_validate(job)


@router.post("/{repo_id}/semantic-search", response_model=SearchResponse)
async def search_repository_code(
    repo_id: str,
    req: SemanticSearchRequest,
    session: AsyncSession = Depends(get_session),
) -> SearchResponse:
    """Semantic vector search across repository code chunks."""
    result = await session.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    from app.retrieval.search import semantic_search

    return await semantic_search(
        repo_id=repo_id,
        query=req.query,
        top_k=req.top_k,
        language=req.language,
        file_path_filter=req.file_path_filter,
    )


@router.post("/{repo_id}/chat", response_model=ChatResponse)
async def chat_with_repository(
    repo_id: str,
    req: ChatRequest,
    session: AsyncSession = Depends(get_session),
) -> ChatResponse:
    """Chat with the repository using semantic context and Ollama."""
    from app.services.chat import chat_service

    return await chat_service.send_message(
        repo_id=repo_id,
        user_content=req.message,
        session_id=req.session_id,
        model=req.model,
        provider=req.provider,
        session=session,
    )


@router.get("/{repo_id}/chat/sessions")
async def list_repo_chat_sessions(
    repo_id: str,
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    """List chat sessions for a repository."""
    from app.services.chat import chat_service

    return await chat_service.list_sessions(repo_id, session)


@router.delete("/{repo_id}/chat/sessions")
async def clear_all_chat_sessions(
    repo_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Clear all chat sessions and messages for a repository."""
    from app.services.chat import chat_service

    count = await chat_service.clear_all_sessions(repo_id, session)
    return {"success": True, "deleted_count": count}


@router.get("/{repo_id}/chat/sessions/{session_id}/messages")
async def get_chat_session_messages(
    repo_id: str,
    session_id: str,
    session: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    """Get message history for a specific chat session."""
    from app.services.chat import chat_service

    return await chat_service.get_messages(session_id, session)


@router.delete("/{repo_id}/chat/sessions/{session_id}")
async def delete_chat_session(
    repo_id: str,
    session_id: str,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Delete a chat session and its messages."""
    from app.services.chat import chat_service

    success = await chat_service.delete_session(session_id, session)
    return {"success": success, "session_id": session_id}


@router.get("/{repo_id}/models")
async def list_available_models(
    repo_id: str,
) -> dict[str, Any]:
    """List locally installed Ollama models."""
    from app.llm.provider import get_llm_provider

    llm = get_llm_provider()
    models = await llm.list_models()
    return {
        "models": models,
        "default_model": settings.OLLAMA_MODEL,
        "embedding_model": settings.EMBEDDING_MODEL,
    }


@router.post("/{repo_id}/review", response_model=ReviewResponse)
async def review_repository_code(
    repo_id: str,
    req: ReviewRequest,
    session: AsyncSession = Depends(get_session),
) -> ReviewResponse:
    """Review repository code, file, or diff for bugs, vulnerabilities, and code quality."""
    from app.services.review import review_service

    return await review_service.review_code(
        repo_id=repo_id,
        file_path=req.file_path,
        code_input=req.code,
        diff_input=req.diff,
        review_type=req.review_type,
        session=session,
    )


@router.post("/{repo_id}/investigate", response_model=InvestigationResponse)
async def investigate_repository_issue(
    repo_id: str,
    req: InvestigateRequest,
    session: AsyncSession = Depends(get_session),
) -> InvestigationResponse:
    """Autonomously investigate a bug or issue description across the repository."""
    from app.services.investigation import investigation_service

    return await investigation_service.investigate_issue(
        repo_id=repo_id,
        issue_text=req.issue,
        session=session,
    )


@router.post("/{repo_id}/generate-tests", response_model=GenerateTestsResponse)
async def generate_repository_tests(
    repo_id: str,
    req: GenerateTestsRequest,
    session: AsyncSession = Depends(get_session),
) -> GenerateTestsResponse:
    """Generate comprehensive unit tests for a file or function using repo conventions."""
    from app.services.test_generator import test_generator_service

    return await test_generator_service.generate_tests(
        repo_id=repo_id,
        file_path=req.file_path,
        function_name=req.function_name,
        framework=req.framework,
        session=session,
    )


@router.post("/{repo_id}/run-tests", response_model=TestRunResponse)
async def run_repository_tests(
    repo_id: str,
    req: RunTestsRequest,
    session: AsyncSession = Depends(get_session),
) -> TestRunResponse:
    """Safely execute test suite within the repository and capture execution outputs."""
    from app.services.test_runner import test_runner_service

    return await test_runner_service.run_tests(
        repo_id=repo_id,
        custom_command=req.command,
        file_path=req.file_path,
        session=session,
    )


@router.get("/{repo_id}/git/status", response_model=GitStatusResponse)
async def get_repository_git_status(
    repo_id: str,
    session: AsyncSession = Depends(get_session),
) -> GitStatusResponse:
    """Get current Git status: branch, untracked, modified, and staged files."""
    result = await session.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    from app.services.git_service import git_service

    return git_service.get_status(Path(repo.path))


@router.get("/{repo_id}/git/diff", response_model=GitDiffResponse)
async def get_repository_git_diff(
    repo_id: str,
    cached: bool = Query(False, description="Whether to view staged changes"),
    session: AsyncSession = Depends(get_session),
) -> GitDiffResponse:
    """Get git diff for uncommitted or staged changes."""
    result = await session.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    from app.services.git_service import git_service

    return git_service.get_diff(Path(repo.path), cached=cached)


@router.get("/{repo_id}/git/log", response_model=list[GitLogEntry])
async def get_repository_git_log(
    repo_id: str,
    max_commits: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_session),
) -> list[GitLogEntry]:
    """Get recent Git commit history."""
    result = await session.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    from app.services.git_service import git_service

    return git_service.get_log(Path(repo.path), max_commits=max_commits)


@router.post("/{repo_id}/patch/preview", response_model=PatchPreviewResponse)
async def preview_code_patch(
    repo_id: str,
    req: PatchPreviewRequest,
    session: AsyncSession = Depends(get_session),
) -> PatchPreviewResponse:
    """Generate a unified diff preview for proposed file changes before applying."""
    from app.services.patch_service import patch_service

    return await patch_service.preview_patch(repo_id, req, session)


@router.post("/{repo_id}/patch/apply", response_model=PatchApplyResponse)
async def apply_code_patch(
    repo_id: str,
    req: PatchApplyRequest,
    session: AsyncSession = Depends(get_session),
) -> PatchApplyResponse:
    """Safely apply a staged patch to repository files with automated pre-modification backups."""
    from app.services.patch_service import patch_service

    return await patch_service.apply_patch(repo_id, req, session)


@router.delete("/{repo_id}", status_code=204)
async def delete_repository(
    repo_id: str,
    session: AsyncSession = Depends(get_session),
) -> None:
    """Remove a repository registration and its vector collection (does not delete actual files)."""
    result = await session.execute(select(Repository).where(Repository.id == repo_id))
    repo = result.scalar_one_or_none()
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    from app.retrieval.qdrant_service import qdrant_service

    try:
        qdrant_service.delete_collection(repo_id)
    except Exception as e:
        logger.warning(f"Could not delete vector collection for {repo_id}: {e}")

    await session.delete(repo)
    logger.info(f"Repository removed: {repo.name}")


