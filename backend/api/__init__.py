"""
SOAC API Package
================

FastAPI backend for SOAC.
"""

import os
from pathlib import Path
from fastapi import FastAPI

from .jobs import router as jobs_router
from .logs import router as logs_router
from .artifacts import router as artifacts_router
from .uploads import router as uploads_router
from .audit import router as audit_router
from backend.auth import auth_router
from backend.audit import AuditLogger
from backend.db import create_mongo_client, close_mongo_client
from backend.auth.mongo_user_store import ensure_auth_indexes


def _load_dotenv_if_present() -> None:
    env_path = Path(__file__).resolve().parents[2] / ".env"
    if not env_path.exists():
        return
    try:
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[len("export ") :].lstrip()
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if not key:
                continue
            if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
                value = value[1:-1]
            existing = os.environ.get(key)
            if existing is None or existing == "":
                os.environ[key] = value
    except OSError:
        return


_load_dotenv_if_present()


def create_app() -> FastAPI:
    """Create FastAPI application."""
    _load_dotenv_if_present()
    app = FastAPI(
        title="SOAC API",
        description="Self-Optimizing AI Compiler API",
        version="1.0.0",
    )
    
    @app.on_event("startup")
    async def _startup() -> None:
        try:
            client, db = await create_mongo_client()
        except Exception:
            client, db = None, None
        app.state.mongo_client = client
        app.state.mongo_db = db
        app.state.audit_logger = AuditLogger(db)
        await app.state.audit_logger.ensure_indexes()
        await ensure_auth_indexes(db)

    @app.on_event("shutdown")
    async def _shutdown() -> None:
        await close_mongo_client(getattr(app.state, "mongo_client", None))

    # Include routers
    app.include_router(auth_router)  # Auth endpoints
    app.include_router(jobs_router)
    app.include_router(logs_router)
    app.include_router(artifacts_router)
    app.include_router(uploads_router)
    app.include_router(audit_router)
    
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
    "audit_router",
]
