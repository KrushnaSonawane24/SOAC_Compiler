"""
SOAC Job Exceptions
===================

Custom exceptions for job management.
"""

from typing import Optional, Any


class JobError(Exception):
    """Base exception for job errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str,
        job_id: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.job_id = job_id
    
    def __str__(self) -> str:
        if self.job_id:
            return f"[{self.error_code}] Job {self.job_id}: {self.message}"
        return f"[{self.error_code}] {self.message}"


class JobNotFoundError(JobError):
    """Job does not exist."""
    
    def __init__(self, job_id: str):
        super().__init__(
            f"Job not found: {job_id}",
            error_code="JOB_NOT_FOUND",
            job_id=job_id,
        )


class InvalidStateTransition(JobError):
    """Invalid state transition attempted."""
    
    def __init__(self, job_id: str, from_state: str, to_state: str):
        super().__init__(
            f"Cannot transition from {from_state} to {to_state}",
            error_code="INVALID_STATE_TRANSITION",
            job_id=job_id,
        )


class JobAlreadyExists(JobError):
    """Job with ID already exists."""
    
    def __init__(self, job_id: str):
        super().__init__(
            f"Job already exists: {job_id}",
            error_code="JOB_ALREADY_EXISTS",
            job_id=job_id,
        )


class ArtifactNotFoundError(JobError):
    """Artifact does not exist."""
    
    def __init__(self, job_id: str, artifact_id: str):
        super().__init__(
            f"Artifact not found: {artifact_id}",
            error_code="ARTIFACT_NOT_FOUND",
            job_id=job_id,
        )


class JobNotCompletedError(JobError):
    """Job not yet completed."""
    
    def __init__(self, job_id: str, current_state: str):
        super().__init__(
            f"Job not completed yet (current: {current_state})",
            error_code="JOB_NOT_COMPLETED",
            job_id=job_id,
        )


class UnauthorizedAccessError(JobError):
    """User not authorized to access job."""
    
    def __init__(self, job_id: str, user_id: str):
        super().__init__(
            f"Unauthorized access to job",
            error_code="UNAUTHORIZED",
            job_id=job_id,
        )
