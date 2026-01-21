"""
SOAC Artifacts API
==================

Artifact listing and download.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from pathlib import Path
import zipfile
import tempfile

from .schemas import ArtifactsResponse, ArtifactResponse
from .errors import NotFoundError, ForbiddenError, BadRequestError
from .dependencies import get_current_user, get_manager

from backend.jobs import (
    JobManager,
    JobNotFoundError,
    UnauthorizedAccessError,
    ArtifactNotFoundError,
    JobNotCompletedError,
    JobState,
)


router = APIRouter(prefix="/jobs", tags=["artifacts"])


@router.get("/{job_id}/artifacts", response_model=ArtifactsResponse)
async def list_artifacts(
    job_id: str,
    user_id: str = Depends(get_current_user),
    manager: JobManager = Depends(get_manager),
):
    """
    List available artifacts for a job.
    
    Only available after job completion.
    """
    try:
        job = manager.get_job(job_id, user_id)
        
        if job.state not in [JobState.COMPLETED, JobState.FAILED]:
            return ArtifactsResponse(
                job_id=job_id,
                artifacts=[],
                total=0,
            )
        
        artifacts = manager.get_artifacts(job_id, user_id)
        
        return ArtifactsResponse(
            job_id=job_id,
            artifacts=[ArtifactResponse(**a) for a in artifacts],
            total=len(artifacts),
        )
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
    """
    Download an artifact.
    
    Returns the artifact file or a zip of the artifact directory.
    """
    try:
        job = manager.get_job(job_id, user_id)
        
        if job.state != JobState.COMPLETED:
            raise BadRequestError("Job not completed yet")
        
        artifact_path = manager.get_artifact_path(job_id, artifact_id, user_id)
        
        if artifact_path.is_dir():
            # Create zip of directory
            zip_path = Path(tempfile.mktemp(suffix=".zip"))
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file in artifact_path.rglob("*"):
                    if file.is_file():
                        zf.write(file, file.relative_to(artifact_path))
            
            return FileResponse(
                zip_path,
                media_type="application/zip",
                filename=f"{job_id}_{artifact_id}.zip",
            )
        else:
            return FileResponse(
                artifact_path,
                filename=artifact_path.name,
            )
        
    except JobNotFoundError:
        raise NotFoundError("Job", job_id)
    except ArtifactNotFoundError:
        raise NotFoundError("Artifact", artifact_id)
    except UnauthorizedAccessError:
        raise ForbiddenError("Not authorized to access this job")
