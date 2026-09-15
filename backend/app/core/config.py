"""
Application configuration using Pydantic Settings.
All values can be overridden via environment variables or .env file.
"""

from pathlib import Path
from typing import Any
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings — all configurable via environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Application ──────────────────────────────────────────────────────
    APP_NAME: str = "AI Code Intelligence"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # ── Server ───────────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ── Database (SQLite) ────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/code_intelligence.db"

    # ── LLM Provider ("ollama" or "groq") ───────────────────────────────
    LLM_PROVIDER: str = "ollama"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    GROQ_BASE_URL: str = "https://api.groq.com/openai/v1"

    # ── Ollama LLM ───────────────────────────────────────────────────────
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "qwen2.5-coder:7b"
    OLLAMA_TIMEOUT: int = 300  # seconds (ample headroom for local LLM inference)

    # ── Embeddings ───────────────────────────────────────────────────────
    EMBEDDING_PROVIDER: str = "ollama"  # "ollama" or "sentence-transformers"
    EMBEDDING_MODEL: str = "nomic-embed-text"
    EMBEDDING_DIMENSION: int = 768

    # ── Qdrant Vector DB ─────────────────────────────────────────────────
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_GRPC_PORT: int = 6334

    # ── Host Filesystem Mapping (Docker on macOS) ───────────────────────
    # On macOS Docker Desktop the host root is mounted at /host_fs/host_mnt
    # On Linux Docker it is typically /host_fs directly.
    HOST_FS_PREFIX: str = "/host_fs/host_mnt"  # override to "" for Linux

    # ── Repository Settings ──────────────────────────────────────────────
    MAX_FILE_SIZE_MB: int = 10
    MAX_REPO_FILES: int = 50000
    CHUNK_OVERLAP_LINES: int = 2
    MAX_CHUNK_SIZE: int = 4000  # characters

    # ── Agent / LLM Context ─────────────────────────────────────────────
    MAX_CONTEXT_TOKENS: int = 4096
    SEARCH_TOP_K: int = 10
    AGENT_MAX_ITERATIONS: int = 10

    # ── Security ─────────────────────────────────────────────────────────
    ALLOWED_REPO_BASE_PATHS: list[str] = []  # empty = allow any valid path
    MAX_REQUEST_SIZE_MB: int = 50

    # ── CORS ─────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ]

    @property
    def data_dir(self) -> Path:
        """Directory for persistent data (SQLite DB, caches, etc.)."""
        p = Path("./data")
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()


def resolve_host_path(path: str | Path | None) -> Path | None:
    """
    Convert a host-machine absolute path to the corresponding in-container path.
    When running inside Docker on macOS, /Users/... is accessible as
    /host_fs/host_mnt/Users/...
    Returns None if path is None.
    """
    if not path:
        return None
    p = Path(path)
    if p.exists():
        return p
    # Try prepending the host_fs prefix
    if settings.HOST_FS_PREFIX:
        try:
            rel = p.relative_to("/") if p.is_absolute() else p
            candidate = Path(settings.HOST_FS_PREFIX) / rel
            if candidate.exists():
                return candidate
        except Exception:
            pass
    return p  # return as-is; caller handles non-existent gracefully


def resolve_repo_path(repo_or_path: Any) -> Path:
    """Safely resolve a repository model, string path, or Path to an existing filesystem Path."""
    if not repo_or_path:
        return Path(".")
    if hasattr(repo_or_path, "path"):
        raw = repo_or_path.path
    else:
        raw = repo_or_path
    resolved = resolve_host_path(raw)
    return resolved if resolved is not None else Path(raw)


