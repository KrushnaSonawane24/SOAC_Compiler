"""
SOAC Uploads API
================

File upload handling.
"""

from fastapi import APIRouter, UploadFile, File, Depends
from pydantic import BaseModel
from typing import Optional
import uuid

from .dependencies import get_current_user
from backend.security import secure_save_and_validate


router = APIRouter(prefix="/uploads", tags=["uploads"])


class UploadResponse(BaseModel):
    """Upload response."""
    file_id: str
    filename: str
    size_bytes: int
    sha256: Optional[str] = None
    detected_format: Optional[str] = None
    message: str = "File uploaded successfully"


@router.post("", response_model=UploadResponse, status_code=201)
async def upload_file(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
):
    """
    Upload a model file.
    
    Alternative to using POST /jobs directly.
    Returns a file_id that can be used with job creation.
    """
    file_id = uuid.uuid4().hex[:12]

    upload_meta = await secure_save_and_validate(upload_file=file, job_id=file_id)

    return UploadResponse(
        file_id=file_id,
        filename=file.filename or "unknown",
        size_bytes=upload_meta.file_size,
        sha256=upload_meta.file_hash,
        detected_format=upload_meta.model_format,
    )
