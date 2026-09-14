"""
Health check endpoint.
Checks connectivity to all services: backend, SQLite, Qdrant, Ollama.
"""

from datetime import datetime, timezone

import httpx
from fastapi import APIRouter

from app.core.config import settings
from app.core.logging import get_logger
from app.schemas.schemas import HealthResponse, ServiceStatus

logger = get_logger(__name__)

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check the health of all services."""
    services: dict[str, ServiceStatus] = {}

    # Backend is always OK if we reach this point
    services["backend"] = ServiceStatus(
        status="ok",
        message="Running",
        version=settings.APP_VERSION,
    )

    # SQLite check
    try:
        from app.db.database import engine
        from sqlalchemy import text

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        services["database"] = ServiceStatus(status="ok", message="SQLite connected")
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        services["database"] = ServiceStatus(status="error", message=str(e))

    # Qdrant check
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"http://{settings.QDRANT_HOST}:{settings.QDRANT_PORT}/healthz")
            if resp.status_code == 200:
                services["qdrant"] = ServiceStatus(status="ok", message="Qdrant connected")
            else:
                services["qdrant"] = ServiceStatus(
                    status="error", message=f"HTTP {resp.status_code}"
                )
    except Exception as e:
        logger.warning(f"Qdrant health check failed: {e}")
        services["qdrant"] = ServiceStatus(
            status="unavailable",
            message="Qdrant is not running. Start it with: docker compose up qdrant",
        )

    # Ollama check
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL}/api/version")
            if resp.status_code == 200:
                data = resp.json()
                services["ollama"] = ServiceStatus(
                    status="ok",
                    message="Ollama connected",
                    version=data.get("version"),
                )
            else:
                services["ollama"] = ServiceStatus(
                    status="error", message=f"HTTP {resp.status_code}"
                )
    except Exception as e:
        logger.warning(f"Ollama health check failed: {e}")
        services["ollama"] = ServiceStatus(
            status="unavailable",
            message=(
                "Ollama is not running. Install from https://ollama.ai and run: "
                f"ollama serve. Then pull a model: ollama pull {settings.OLLAMA_MODEL}"
            ),
        )

    # Overall status
    statuses = [s.status for s in services.values()]
    if all(s == "ok" for s in statuses):
        overall = "healthy"
    elif services["backend"].status == "ok":
        overall = "degraded"
    else:
        overall = "unhealthy"

    return HealthResponse(
        status=overall,
        services=services,
        timestamp=datetime.now(timezone.utc),
    )
