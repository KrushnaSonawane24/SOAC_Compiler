"""
SOAC Logs API
=============

Job logs endpoint.
"""

from fastapi import APIRouter, Depends

from .schemas import LogsResponse, LogEntryResponse
from .errors import NotFoundError, ForbiddenError
from .dependencies import get_current_user, get_manager

from backend.jobs import JobManager, JobNotFoundError, UnauthorizedAccessError


router = APIRouter(prefix="/jobs", tags=["logs"])


@router.get("/{job_id}/logs", response_model=LogsResponse)
async def get_job_logs(
    job_id: str,
    user_id: str = Depends(get_current_user),
    manager: JobManager = Depends(get_manager),
):
    """
    Get job execution logs.
    
    Returns ordered log entries with timestamps and stages.
    """
    try:
        logs = manager.get_job_logs(job_id, user_id)
        
        return LogsResponse(
            job_id=job_id,
            logs=[LogEntryResponse(**l) for l in logs],
            total=len(logs),
        )
    except JobNotFoundError:
        raise NotFoundError("Job", job_id)
    except UnauthorizedAccessError:
        raise ForbiddenError("Not authorized to access this job")
