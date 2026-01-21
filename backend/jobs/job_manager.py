"""
SOAC Job Manager
================

High-level job operations with orchestrator integration.
"""

import logging
import asyncio
from pathlib import Path
from typing import Optional
from concurrent.futures import ThreadPoolExecutor
import uuid

from .models import Job, JobState, StageInfo, ArtifactInfo, create_job
from .job_store import JobStore, get_job_store
from .exceptions import JobNotFoundError, ArtifactNotFoundError, UnauthorizedAccessError

from backend.orchestrator import run_soac_job, JobConfig


logger = logging.getLogger(__name__)

# Thread pool for background job execution
_executor = ThreadPoolExecutor(max_workers=4)


class JobManager:
    """
    High-level job management operations.
    
    Integrates with orchestrator for actual execution.
    """
    
    def __init__(self, store: Optional[JobStore] = None):
        self.store = store or get_job_store()
    
    async def create_job(
        self,
        user_id: str,
        original_filename: str,
        file_size_bytes: int,
        input_path: Path,
    ) -> Job:
        """
        Create a new job and start execution.
        
        Args:
            user_id: User who owns the job.
            original_filename: Original uploaded filename.
            file_size_bytes: Size of uploaded file.
            input_path: Path to uploaded model.
        
        Returns:
            Created job.
        """
        job = create_job(
            user_id=user_id,
            original_filename=original_filename,
            file_size_bytes=file_size_bytes,
            input_path=input_path,
        )
        
        self.store.add(job)
        logger.info(f"Created job {job.job_id} for user {user_id}")
        
        # Start execution in background
        asyncio.get_event_loop().run_in_executor(
            _executor,
            self._run_job,
            job.job_id,
        )
        
        return job
    
    def _run_job(self, job_id: str) -> None:
        """Run job in background thread."""
        try:
            job = self.store.get(job_id)
            
            logger.info(f"Starting job execution: {job_id}")
            
            # Create work directory
            work_dir = job.input_path.parent / f"work_{job_id}"
            work_dir.mkdir(exist_ok=True)
            job.work_dir = work_dir
            
            # Configure and run
            config = JobConfig(
                accuracy_threshold=0.02,
                warmup_runs=3,
                measured_runs=10,
                cleanup_on_complete=False,
            )
            
            result = run_soac_job(
                uploaded_model_path=job.input_path,
                config=config,
                job_id=job_id,
                work_dir=work_dir,
            )
            
            # Update job from result
            if result.success:
                self._handle_success(job_id, result)
            else:
                self._handle_failure(job_id, result)
                
        except Exception as e:
            logger.exception(f"Job {job_id} failed with exception")
            self.store.update_state(
                job_id,
                JobState.FAILED,
                error_code="INTERNAL_ERROR",
                error_message=str(e),
            )
    
    def _handle_success(self, job_id: str, result) -> None:
        """Handle successful job completion."""
        # Update state to completed
        self.store.update_state(job_id, JobState.COMPLETED)
        
        # Set result
        self.store.set_result(
            job_id,
            selected_variant=result.selected_variant or "unknown",
            selection_reason=result.metadata.get("selection_reason", ""),
        )
        
        # Add stage info
        for sr in result.stage_results:
            self.store.add_stage(job_id, StageInfo(
                name=sr.stage.value,
                duration_ms=sr.duration_ms,
                success=sr.success,
                message=sr.message,
            ))
        
        # Add artifacts
        deployment = result.metadata.get("deployment_summary", {})
        if deployment.get("successful", 0) > 0:
            artifact_id = f"art_{uuid.uuid4().hex[:8]}"
            self.store.set_artifact(job_id, artifact_id, ArtifactInfo(
                artifact_id=artifact_id,
                name="ONNX Runtime Package",
                platform="cpu",
                format="onnx",
                size_bytes=0,
                status="available",
            ))
        
        # Add logs
        for log in result.logs:
            # Parse log format: [timestamp] [stage] message
            parts = log.split("] ")
            if len(parts) >= 3:
                stage = parts[1].strip("[")
                message = "] ".join(parts[2:])
                self.store.add_log(job_id, stage, message)
            else:
                self.store.add_log(job_id, "info", log)
        
        logger.info(f"Job {job_id} completed successfully")
    
    def _handle_failure(self, job_id: str, result) -> None:
        """Handle job failure."""
        error = result.error or {}
        self.store.update_state(
            job_id,
            JobState.FAILED,
            error_code=error.get("error_code", "UNKNOWN"),
            error_message=error.get("message", "Unknown error"),
        )
        
        logger.error(f"Job {job_id} failed: {error.get('message')}")
    
    def get_job(self, job_id: str, user_id: str) -> Job:
        """
        Get job with authorization check.
        
        Args:
            job_id: Job ID.
            user_id: Requesting user ID.
        
        Returns:
            Job if authorized.
        
        Raises:
            JobNotFoundError: If job doesn't exist.
            UnauthorizedAccessError: If user not authorized.
        """
        job = self.store.get(job_id)
        
        if job.user_id != user_id:
            raise UnauthorizedAccessError(job_id, user_id)
        
        return job
    
    def get_job_logs(self, job_id: str, user_id: str) -> list:
        """Get job logs with auth check."""
        job = self.get_job(job_id, user_id)
        return [l.to_dict() for l in job.logs]
    
    def get_artifacts(self, job_id: str, user_id: str) -> list:
        """Get job artifacts with auth check."""
        job = self.get_job(job_id, user_id)
        return [a.to_dict() for a in job.artifact_metadata]
    
    def get_artifact_path(self, job_id: str, artifact_id: str, user_id: str) -> Path:
        """
        Get artifact file path for download.
        
        Returns internal path (only for file streaming).
        """
        job = self.get_job(job_id, user_id)
        
        for artifact in job.artifact_metadata:
            if artifact.artifact_id == artifact_id:
                # Get actual path from artifacts dict
                if artifact_id in job.artifacts:
                    return job.artifacts[artifact_id]
                # Fallback to work_dir
                if job.work_dir:
                    cpu_dir = job.work_dir / "deployment" / "cpu"
                    if cpu_dir.exists():
                        return cpu_dir
        
        raise ArtifactNotFoundError(job_id, artifact_id)
    
    def list_jobs(
        self,
        user_id: str,
        state: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Job], int]:
        """List user's jobs."""
        state_filter = JobState(state) if state else None
        
        jobs = self.store.list_jobs(
            user_id=user_id,
            state=state_filter,
            limit=limit,
            offset=offset,
        )
        
        total = self.store.count(user_id=user_id)
        
        return jobs, total


# Global singleton
_manager: Optional[JobManager] = None


def get_job_manager() -> JobManager:
    """Get global job manager instance."""
    global _manager
    if _manager is None:
        _manager = JobManager()
    return _manager
