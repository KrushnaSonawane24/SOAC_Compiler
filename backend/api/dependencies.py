"""
SOAC API Dependencies
=====================

FastAPI dependency injection.
"""

from typing import Optional
from fastapi import Depends
from pathlib import Path
import tempfile

from backend.jobs import get_job_manager, JobManager
from backend.auth import get_current_user_id


# ============================================================================
# AUTHENTICATION
# ============================================================================

async def get_current_user(
    user_id: str = Depends(get_current_user_id),
) -> str:
    """
    Get current user ID from JWT token.
    
    This replaces the old header-based auth with JWT.
    """
    return user_id


# ============================================================================
# SERVICES
# ============================================================================

def get_manager() -> JobManager:
    """Get job manager instance."""
    return get_job_manager()


# ============================================================================
# FILE HANDLING
# ============================================================================

_upload_dir: Optional[Path] = None


def get_upload_dir() -> Path:
    """Get upload directory."""
    global _upload_dir
    if _upload_dir is None:
        _upload_dir = Path(tempfile.mkdtemp(prefix="soac_uploads_"))
    return _upload_dir


def set_upload_dir(path: Path) -> None:
    """Set upload directory (for testing)."""
    global _upload_dir
    _upload_dir = path
    _upload_dir.mkdir(parents=True, exist_ok=True)
