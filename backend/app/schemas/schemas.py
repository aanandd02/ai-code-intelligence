"""
Pydantic schemas for API request/response models.
"""

from datetime import datetime
from pydantic import BaseModel, Field


# ── Health ───────────────────────────────────────────────────────────────


class ServiceStatus(BaseModel):
    status: str  # "ok" | "error" | "unavailable"
    message: str | None = None
    version: str | None = None


class HealthResponse(BaseModel):
    status: str  # "healthy" | "degraded" | "unhealthy"
    services: dict[str, ServiceStatus]
    timestamp: datetime


# ── Repository ───────────────────────────────────────────────────────────


class RepositoryCreate(BaseModel):
    path: str = Field(..., description="Absolute path to local Git repository")
    name: str | None = Field(None, description="Optional display name (auto-detected if omitted)")


class RepositoryResponse(BaseModel):
    id: str
    name: str
    path: str
    description: str | None = None
    default_branch: str | None = None
    languages: list[str] | None = None
    total_files: int = 0
    total_chunks: int = 0
    indexed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RepositoryListResponse(BaseModel):
    repositories: list[RepositoryResponse]
    total: int


# ── File ─────────────────────────────────────────────────────────────────


class FileInfo(BaseModel):
    path: str
    language: str | None = None
    size_bytes: int = 0
    is_directory: bool = False
    children: list["FileInfo"] | None = None


class FileContentResponse(BaseModel):
    path: str
    language: str | None = None
    content: str
    size_bytes: int
    line_count: int


# ── Indexing ─────────────────────────────────────────────────────────────


class IndexingJobResponse(BaseModel):
    id: str
    repository_id: str
    status: str
    total_files: int
    processed_files: int
    total_chunks: int
    skipped_chunks: int
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    model_config = {"from_attributes": True}


# ── Search ───────────────────────────────────────────────────────────────


class SemanticSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language search query")
    top_k: int = Field(10, ge=1, le=50)
    language: str | None = None
    file_path_filter: str | None = None


class SearchResult(BaseModel):
    file_path: str
    symbol_name: str | None = None
    symbol_type: str | None = None
    language: str | None = None
    start_line: int = 0
    end_line: int = 0
    content: str
    score: float


class SearchResponse(BaseModel):
    query: str
    results: list[SearchResult]
    total: int


# ── Chat ─────────────────────────────────────────────────────────────────


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1)
    session_id: str | None = None
    model: str | None = None
    provider: str | None = None  # "ollama" (local) or "groq" (cloud)


class Citation(BaseModel):
    file_path: str
    start_line: int | None = None
    end_line: int | None = None
    symbol_name: str | None = None
    content: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    message: str
    citations: list[Citation] = []
    model: str | None = None
    provider: str | None = None
    tool_calls: list[dict] | None = None


# ── Code Review ──────────────────────────────────────────────────────────


class ReviewRequest(BaseModel):
    file_path: str | None = None
    code: str | None = None
    diff: str | None = None
    review_type: str = "full"  # full, security, performance, bugs


class ReviewFinding(BaseModel):
    severity: str  # critical, high, medium, low, info
    file: str | None = None
    line: int | None = None
    title: str
    description: str
    recommendation: str | None = None
    confidence: float = 0.0


class ReviewResponse(BaseModel):
    id: str
    findings: list[ReviewFinding]
    summary: str | None = None
    model: str | None = None


# ── Investigation ────────────────────────────────────────────────────────


class InvestigateRequest(BaseModel):
    issue: str = Field(..., min_length=1, description="Description of the issue to investigate")


class InvestigationDiagnosis(BaseModel):
    probable_root_cause: str
    confidence: float = 0.0
    supporting_evidence: list[str] = []
    affected_components: list[str] = []
    relevant_files: list[str] = []
    relevant_symbols: list[str] = []


class SuggestedFix(BaseModel):
    description: str
    affected_files: list[str] = []
    expected_impact: str | None = None
    code_changes: list[dict] | None = None


class InvestigationResponse(BaseModel):
    id: str
    diagnosis: InvestigationDiagnosis | None = None
    suggested_fix: SuggestedFix | None = None
    validation: dict | None = None
    tool_calls: list[dict] | None = None


# ── Test Generation ─────────────────────────────────────────────────────


class GenerateTestsRequest(BaseModel):
    file_path: str
    function_name: str | None = None
    framework: str | None = None  # auto-detect if not provided


class GenerateTestsResponse(BaseModel):
    file_path: str
    test_file_path: str
    test_code: str
    framework: str
    language: str


# ── Test Run ─────────────────────────────────────────────────────────────


class RunTestsRequest(BaseModel):
    command: str | None = None  # auto-detect if not provided
    file_path: str | None = None


class TestRunResponse(BaseModel):
    id: str
    command: str
    exit_code: int | None = None
    stdout: str | None = None
    stderr: str | None = None
    duration_seconds: float | None = None
    status: str  # running, passed, failed, error

    model_config = {"from_attributes": True}


# ── Git ──────────────────────────────────────────────────────────────────


class GitStatusResponse(BaseModel):
    branch: str | None = None
    is_dirty: bool = False
    changed_files: list[dict] = []
    untracked_files: list[str] = []
    commit_hash: str | None = None
    commit_message: str | None = None


class GitDiffResponse(BaseModel):
    diff: str
    files_changed: int = 0
    insertions: int = 0
    deletions: int = 0


class GitLogEntry(BaseModel):
    hash: str
    short_hash: str
    author: str
    date: datetime
    message: str
    files_changed: int = 0


class GitLogResponse(BaseModel):
    entries: list[GitLogEntry]
    total: int


# ── Patch ────────────────────────────────────────────────────────────────


class PatchFile(BaseModel):
    file_path: str
    before: str | None = None
    after: str | None = None
    diff: str | None = None


class PatchPreviewRequest(BaseModel):
    description: str
    files: list[PatchFile]


class PatchPreviewResponse(BaseModel):
    id: str
    description: str
    files: list[PatchFile]
    is_repo_clean: bool
    warnings: list[str] = []


class PatchApplyRequest(BaseModel):
    patch_id: str
    create_backup: bool = True


class PatchApplyResponse(BaseModel):
    success: bool
    message: str
    applied_files: list[str] = []
    backup_ref: str | None = None


# ── Models ───────────────────────────────────────────────────────────────


class OllamaModel(BaseModel):
    name: str
    size: str | None = None
    modified_at: str | None = None


class ModelsResponse(BaseModel):
    models: list[OllamaModel]
    current_model: str
