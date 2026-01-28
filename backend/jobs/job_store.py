"""
SOAC Job Store
==============

In-memory job storage (production: replace with database).
"""

from typing import Dict, List, Optional, Any
from threading import Lock
from datetime import datetime, timezone

from .models import Job, JobState, LogEntry, StageInfo, ArtifactInfo, STATE_PROGRESS
from .exceptions import JobNotFoundError, JobAlreadyExists, InvalidStateTransition
from .job_state import can_transition, is_terminal


class JobStore:
    """
    In-memory job store.
    
    Thread-safe for concurrent access.
    Production: Replace with database backend.
    """
    
    def __init__(self):
        self._jobs: Dict[str, Job] = {}
        self._lock = Lock()
    
    def add(self, job: Job) -> None:
        """Add a new job."""
        with self._lock:
            if job.job_id in self._jobs:
                raise JobAlreadyExists(job.job_id)
            self._jobs[job.job_id] = job
    
    def get(self, job_id: str) -> Job:
        """Get job by ID."""
        with self._lock:
            if job_id not in self._jobs:
                raise JobNotFoundError(job_id)
            return self._jobs[job_id]
    
    def exists(self, job_id: str) -> bool:
        """Check if job exists."""
        with self._lock:
            return job_id in self._jobs
    
    def update_state(
        self,
        job_id: str,
        new_state: JobState,
        error_code: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> Job:
        """Update job state with validation."""
        with self._lock:
            if job_id not in self._jobs:
                raise JobNotFoundError(job_id)
            
            job = self._jobs[job_id]

            if job.state == new_state:
                job.updated_at = datetime.now(timezone.utc).isoformat()
                if new_state == JobState.FAILED:
                    job.error_code = error_code
                    job.error_message = error_message
                    job.failed_stage = job.current_stage
                return job
            
            if not can_transition(job.state, new_state):
                raise InvalidStateTransition(job_id, job.state.value, new_state.value)
            
            job.state = new_state
            job.current_stage = new_state.value
            job.progress = STATE_PROGRESS.get(new_state, 0)
            job.updated_at = datetime.now(timezone.utc).isoformat()
            
            if new_state == JobState.FAILED:
                job.error_code = error_code
                job.error_message = error_message
                job.failed_stage = job.current_stage
            
            return job
    
    def add_log(self, job_id: str, stage: str, message: str, level: str = "info") -> None:
        """Add log entry to job."""
        with self._lock:
            if job_id not in self._jobs:
                raise JobNotFoundError(job_id)
            
            entry = LogEntry(
                timestamp=datetime.now(timezone.utc).isoformat(),
                stage=stage,
                message=message,
                level=level,
            )
            self._jobs[job_id].logs.append(entry)
    
    def add_stage(self, job_id: str, stage_info: StageInfo) -> None:
        """Add stage info to job."""
        with self._lock:
            if job_id not in self._jobs:
                raise JobNotFoundError(job_id)
            self._jobs[job_id].stages.append(stage_info)
    
    def set_artifact(self, job_id: str, artifact_id: str, info: ArtifactInfo, path: str) -> None:
        """Register artifact."""
        with self._lock:
            if job_id not in self._jobs:
                raise JobNotFoundError(job_id)
            self._jobs[job_id].artifact_metadata.append(info)
            self._jobs[job_id].artifacts[artifact_id] = path
    
    def set_result(
        self,
        job_id: str,
        selected_variant: str,
        selection_reason: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Set job result."""
        with self._lock:
            if job_id not in self._jobs:
                raise JobNotFoundError(job_id)
            self._jobs[job_id].selected_variant = selected_variant
            self._jobs[job_id].selection_reason = selection_reason
            if metadata:
                self._jobs[job_id].metadata.update(metadata)
    
    def list_jobs(
        self,
        user_id: Optional[str] = None,
        state: Optional[JobState] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[Job]:
        """List jobs with filtering."""
        with self._lock:
            jobs = list(self._jobs.values())
            
            if user_id:
                jobs = [j for j in jobs if j.user_id == user_id]
            
            if state:
                jobs = [j for j in jobs if j.state == state]
            
            # Sort by created_at descending
            jobs.sort(key=lambda j: j.created_at, reverse=True)
            
            return jobs[offset:offset + limit]
    
    def count(self, user_id: Optional[str] = None) -> int:
        """Count jobs."""
        with self._lock:
            if user_id:
                return sum(1 for j in self._jobs.values() if j.user_id == user_id)
            return len(self._jobs)
    
    def delete(self, job_id: str) -> None:
        """Delete job (admin only)."""
        with self._lock:
            if job_id in self._jobs:
                del self._jobs[job_id]


# Global singleton
_store: Optional[JobStore] = None


def get_job_store() -> JobStore:
    """Get global job store instance."""
    global _store
    if _store is None:
        _store = JobStore()
    return _store
