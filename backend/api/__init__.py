"""
SOAC API Package
================

FastAPI backend for SOAC.
"""

from fastapi import FastAPI

from .jobs import router as jobs_router
from .logs import router as logs_router
from .artifacts import router as artifacts_router
from .uploads import router as uploads_router
from backend.auth import auth_router


def create_app() -> FastAPI:
    """Create FastAPI application."""
    app = FastAPI(
        title="SOAC API",
        description="Self-Optimizing AI Compiler API",
        version="1.0.0",
    )
    
    # Include routers
    app.include_router(auth_router)  # Auth endpoints
    app.include_router(jobs_router)
    app.include_router(logs_router)
    app.include_router(artifacts_router)
    app.include_router(uploads_router)
    
    @app.get("/health")
    async def health():
        return {"status": "healthy"}
    
    return app


# Create default app instance
app = create_app()


__all__ = [
    "create_app",
    "app",
    "auth_router",
    "jobs_router",
    "logs_router",
    "artifacts_router",
    "uploads_router",
]
