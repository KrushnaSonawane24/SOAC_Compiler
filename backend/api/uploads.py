"""
SOAC Uploads API
================

File upload handling.
"""

from fastapi import APIRouter, UploadFile, File, Depends
from pydantic import BaseModel
from pathlib import Path
import shutil
import uuid

from .dependencies import get_current_user, get_upload_dir


router = APIRouter(prefix="/uploads", tags=["uploads"])


class UploadResponse(BaseModel):
    """Upload response."""
    file_id: str
    filename: str
    size_bytes: int
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
    upload_dir = get_upload_dir()
    file_id = uuid.uuid4().hex[:12]
    
    # Preserve original extension
    ext = Path(file.filename).suffix if file.filename else ".onnx"
    file_path = upload_dir / f"{file_id}{ext}"
    
    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    
    return UploadResponse(
        file_id=file_id,
        filename=file.filename or "unknown",
        size_bytes=file_path.stat().st_size,
    )
