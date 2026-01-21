"""
SOAC Jobs API
=============

Job management endpoints.
"""

from fastapi import APIRouter, Depends, UploadFile, File, Query
from typing import Optional
import shutil
import uuid
from pathlib import Path

from .schemas import (
    JobResponse,
    JobCreatedResponse,
    JobListResponse,
    JobStateEnum,
)
from .errors import NotFoundError, ForbiddenError
from .dependencies import get_current_user, get_manager, get_upload_dir

from backend.jobs import JobManager, JobNotFoundError, UnauthorizedAccessError


router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobCreatedResponse, status_code=201)
async def create_job(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
    manager: JobManager = Depends(get_manager),
):
    """
    Create a new optimization job.
    
    Accepts an ONNX model file and starts processing.
    """
    # Validate file
    if not file.filename:
        raise ForbiddenError("No filename provided")
    
    # Supported file formats (ONNX, TensorFlow, PyTorch)
    SUPPORTED_EXTENSIONS = ('.onnx', '.h5', '.keras', '.pb', '.tflite', '.mlmodel', '.pt', '.pth')
    if not file.filename.endswith(SUPPORTED_EXTENSIONS):
        raise ForbiddenError(f"Unsupported file format. Supported: {', '.join(SUPPORTED_EXTENSIONS)}")
    
    # Save uploaded file
    upload_dir = get_upload_dir()
    file_id = uuid.uuid4().hex[:12]
    file_path = upload_dir / f"{file_id}_{file.filename}"
    
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    file_size = file_path.stat().st_size
    
    # Create job
    job = await manager.create_job(
        user_id=user_id,
        original_filename=file.filename,
        file_size_bytes=file_size,
        input_path=file_path,
    )
    
    return JobCreatedResponse(
        job_id=job.job_id,
        state=JobStateEnum(job.state.value),
    )


@router.get("", response_model=JobListResponse)
async def list_jobs(
    state: Optional[JobStateEnum] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user),
    manager: JobManager = Depends(get_manager),
):
    """
    List jobs for the current user.
    
    Supports filtering by state and pagination.
    """
    jobs, total = manager.list_jobs(
        user_id=user_id,
        state=state.value if state else None,
        limit=limit,
        offset=offset,
    )
    
    return JobListResponse(
        jobs=[_job_to_response(j) for j in jobs],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    user_id: str = Depends(get_current_user),
    manager: JobManager = Depends(get_manager),
):
    """
    Get job status and details.
    
    Returns current state, progress, stages, and artifacts.
    """
    try:
        job = manager.get_job(job_id, user_id)
        return _job_to_response(job)
    except JobNotFoundError:
        raise NotFoundError("Job", job_id)
    except UnauthorizedAccessError:
        raise ForbiddenError("Not authorized to access this job")


def _job_to_response(job) -> JobResponse:
    """Convert Job to JobResponse."""
    error = None
    if job.error_code:
        error = {
            "code": job.error_code,
            "message": job.error_message,
            "stage": job.failed_stage,
        }
    
    return JobResponse(
        job_id=job.job_id,
        state=JobStateEnum(job.state.value),
        created_at=job.created_at,
        updated_at=job.updated_at,
        original_filename=job.original_filename,
        file_size_bytes=job.file_size_bytes,
        progress=job.progress,
        current_stage=job.current_stage,
        selected_variant=job.selected_variant,
        selection_reason=job.selection_reason,
        stages=[s.to_dict() for s in job.stages],
        artifacts=[a.to_dict() for a in job.artifact_metadata],
        error=error,
    )
