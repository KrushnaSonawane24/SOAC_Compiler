"""
SOAC API Schemas
================

Pydantic schemas for request/response validation.
"""

from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field
from enum import Enum


class JobStateEnum(str, Enum):
    """Job states for API."""
    created = "created"
    normalizing = "normalizing"
    validating = "validating"
    canonicalizing = "canonicalizing"
    optimizing = "optimizing"
    benchmarking = "benchmarking"
    selecting = "selecting"
    deploying = "deploying"
    completed = "completed"
    failed = "failed"


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class CreateJobRequest(BaseModel):
    """Request to create a new job."""
    # File is sent via form-data, not JSON
    pass


class ListJobsParams(BaseModel):
    """Query params for listing jobs."""
    state: Optional[JobStateEnum] = None
    limit: int = Field(default=50, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================

class ErrorDetail(BaseModel):
    """Error details."""
    code: str
    message: str
    stage: Optional[str] = None


class StageResponse(BaseModel):
    """Stage info response."""
    name: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[float] = None
    success: bool
    message: Optional[str] = None


class ArtifactResponse(BaseModel):
    """Artifact info response."""
    artifact_id: str
    name: str
    platform: str
    format: str
    size_bytes: int
    status: str


class LogEntryResponse(BaseModel):
    """Log entry response."""
    timestamp: str
    stage: str
    message: str
    level: str = "info"


class JobResponse(BaseModel):
    """Job response."""
    job_id: str
    state: JobStateEnum
    created_at: str
    updated_at: str
    original_filename: str
    file_size_bytes: int
    progress: int
    current_stage: Optional[str] = None
    selected_variant: Optional[str] = None
    selection_reason: Optional[str] = None
    stages: List[StageResponse] = []
    artifacts: List[ArtifactResponse] = []
    error: Optional[ErrorDetail] = None
    metadata: Dict[str, Any] = {}


class JobCreatedResponse(BaseModel):
    """Response after job creation."""
    job_id: str
    state: JobStateEnum
    message: str = "Job created successfully"


class JobListResponse(BaseModel):
    """Response for job list."""
    jobs: List[JobResponse]
    total: int
    limit: int
    offset: int


class LogsResponse(BaseModel):
    """Response for job logs."""
    job_id: str
    logs: List[LogEntryResponse]
    total: int


class ArtifactsResponse(BaseModel):
    """Response for artifacts list."""
    job_id: str
    artifacts: List[ArtifactResponse]
    total: int


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    error_code: str
    details: Optional[Dict[str, Any]] = None
