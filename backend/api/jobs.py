"""
SOAC Jobs API
=============

Job management endpoints.
"""

from fastapi import APIRouter, Depends, UploadFile, File, Query, Form
from fastapi.responses import FileResponse
from typing import Optional, List, Dict
import uuid
from pathlib import Path

from .schemas import (
    JobResponse,
    JobCreatedResponse,
    JobListResponse,
    JobStateEnum,
    LogEntryResponse,
)
from .errors import NotFoundError, ForbiddenError
from .dependencies import get_current_user, get_manager

from backend.jobs import JobManager, JobNotFoundError, ArtifactNotFoundError, UnauthorizedAccessError
from backend.security import secure_save_and_validate


router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobCreatedResponse, status_code=201)
async def create_job(
    file: UploadFile = File(...),
    targets: List[str] = Form(["android", "gpu"]),
    policy: str = Form("balanced"),
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

    # Save + validate uploaded file securely
    file_id = uuid.uuid4().hex[:12]

    upload_meta = await secure_save_and_validate(upload_file=file, job_id=file_id)
    file_path = Path(upload_meta.file_path)
    file_size = upload_meta.file_size
    
    # Parse targets if they come as a single comma-separated string (common in FormData)
    if len(targets) == 1 and "," in targets[0]:
        targets = [t.strip() for t in targets[0].split(",")]
    
    # Create job
    job = await manager.create_job(
        user_id=user_id,
        original_filename=file.filename,
        file_size_bytes=file_size,
        input_path=file_path,
        config={
            "targets": targets,
            "policy": policy,
            "upload": {
                "sha256": upload_meta.file_hash,
                "detected_format": upload_meta.model_format,
                "mime_type": upload_meta.mime_type,
                "validated_at": upload_meta.validation_timestamp,
            },
        }
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


@router.get("/{job_id}/logs", response_model=Dict[str, List[LogEntryResponse]])
async def get_job_logs(
    job_id: str,
    user_id: str = Depends(get_current_user),
    manager: JobManager = Depends(get_manager),
):
    """
    Get job logs.
    """
    try:
        job = manager.get_job(job_id, user_id)
        return {"logs": [l.to_dict() for l in job.logs]}
    except JobNotFoundError:
        raise NotFoundError("Job", job_id)
    except UnauthorizedAccessError:
        raise ForbiddenError("Not authorized to access this job")


@router.get("/{job_id}/artifacts/{artifact_id}")
async def download_artifact(
    job_id: str,
    artifact_id: str,
    user_id: str = Depends(get_current_user),
    manager: JobManager = Depends(get_manager),
):
    """Download job artifact."""
    try:
        path = manager.get_artifact_path(job_id, artifact_id, user_id)
        path = Path(path)
        
        if not path.exists():
            raise NotFoundError("Artifact file", artifact_id)
            
        if path.is_dir():
            # Create zip archive of the directory
            shutil.make_archive(str(path), 'zip', str(path))
            return FileResponse(
                path=f"{path}.zip", 
                filename=f"{path.name}.zip",
                media_type="application/zip"
            )
            
        return FileResponse(
            path=str(path), 
            filename=path.name,
            media_type="application/octet-stream"
        )
    except JobNotFoundError:
        raise NotFoundError("Job", job_id)
    except ArtifactNotFoundError:
        raise NotFoundError("Artifact", artifact_id)
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
        metadata=job.metadata,
    )
