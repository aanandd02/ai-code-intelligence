"""
Application configuration using Pydantic Settings.
All values can be overridden via environment variables or .env file.
"""

from pathlib import Path
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
    OLLAMA_TIMEOUT: int = 120  # seconds

    # ── Embeddings ───────────────────────────────────────────────────────
    EMBEDDING_PROVIDER: str = "ollama"  # "ollama" or "sentence-transformers"
    EMBEDDING_MODEL: str = "nomic-embed-text"
    EMBEDDING_DIMENSION: int = 768

    # ── Qdrant Vector DB ─────────────────────────────────────────────────
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_GRPC_PORT: int = 6334

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
