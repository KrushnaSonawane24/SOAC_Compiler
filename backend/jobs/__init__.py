"""
SOAC Jobs Package
=================

Job management for SOAC.
"""

from .models import Job, JobState, LogEntry, StageInfo, ArtifactInfo, create_job, STATE_PROGRESS
from .exceptions import (
    JobError,
    JobNotFoundError,
    JobAlreadyExists,
    InvalidStateTransition,
    ArtifactNotFoundError,
    JobNotCompletedError,
    UnauthorizedAccessError,
)
from .job_state import can_transition, is_terminal, get_next_state, get_all_states
from .job_store import JobStore, get_job_store
from .job_manager import JobManager, get_job_manager

__all__ = [
    # Models
    "Job",
    "JobState",
    "LogEntry",
    "StageInfo",
    "ArtifactInfo",
    "create_job",
    "STATE_PROGRESS",
    
    # State machine
    "can_transition",
    "is_terminal",
    "get_next_state",
    "get_all_states",
    
    # Store
    "JobStore",
    "get_job_store",
    
    # Manager
    "JobManager",
    "get_job_manager",
    
    # Exceptions
    "JobError",
    "JobNotFoundError",
    "JobAlreadyExists",
    "InvalidStateTransition",
    "ArtifactNotFoundError",
    "JobNotCompletedError",
    "UnauthorizedAccessError",
]
