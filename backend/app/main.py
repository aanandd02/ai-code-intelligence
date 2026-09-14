"""
AI Code Intelligence & Review Agent — FastAPI Application

A 100% local, zero-cost, repository-aware AI coding assistant.
No paid APIs. No cloud billing. Runs entirely on your machine.
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.db.database import close_db, init_db

# Set up logging before anything else
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Ollama: {settings.OLLAMA_BASE_URL} (model: {settings.OLLAMA_MODEL})")
    logger.info(f"Qdrant: {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")
    logger.info(f"Database: {settings.DATABASE_URL}")

    # Initialize database
    await init_db()

    yield

    # Cleanup
    await close_db()
    logger.info("Application shutdown complete")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "A repository-aware AI coding assistant that analyzes local repositories, "
        "performs semantic code search, reviews code, generates tests, and provides "
        "structured patch recommendations. 100% local — no API keys required."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Register routers ────────────────────────────────────────────────────

from app.api.health import router as health_router
from app.api.repositories import router as repositories_router

app.include_router(health_router, prefix="/api")
app.include_router(repositories_router, prefix="/api")


@app.get("/api/models", tags=["models"])
async def get_models():
    """List locally installed Ollama models."""
    from app.llm.provider import get_llm_provider

    llm = get_llm_provider()
    models = await llm.list_models()
    return {
        "models": [{"name": m} for m in models],
        "current_model": settings.OLLAMA_MODEL,
        "embedding_model": settings.EMBEDDING_MODEL,
    }


@app.get("/", tags=["root"])
async def root():
    """Root endpoint with application info."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/api/health",
        "cost": "$0 — fully local, no API keys required",
    }
