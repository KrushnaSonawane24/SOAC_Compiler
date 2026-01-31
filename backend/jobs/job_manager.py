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
from .exceptions import JobNotFoundError, ArtifactNotFoundError, UnauthorizedAccessError, InvalidStateTransition

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
        config: Optional[dict] = None,
    ) -> Job:
        """
        Create a new job and start execution.
        
        Args:
            user_id: User who owns the job.
            original_filename: Original uploaded filename.
            file_size_bytes: Size of uploaded file.
            input_path: Path to uploaded model.
            config: Job configuration (targets, policy).
        
        Returns:
            Created job.
        """
        job = create_job(
            user_id=user_id,
            original_filename=original_filename,
            file_size_bytes=file_size_bytes,
            input_path=input_path,
            metadata={"user_config": config or {}},
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
            user_config = job.metadata.get("user_config", {})
            
            config = JobConfig(
                accuracy_threshold=float(user_config.get("accuracy_threshold", 0.01)),
                max_model_size_mb=int(user_config.get("max_model_size_mb", 200)),
                max_stage_attempts=int(user_config.get("max_stage_attempts", 2)),
                retry_backoff_ms=int(user_config.get("retry_backoff_ms", 600)),
                warmup_runs=int(user_config.get("warmup_runs", 3)),
                measured_runs=int(user_config.get("measured_runs", 10)),
                cleanup_on_complete=False,
                deployment_targets=user_config.get("targets", ["android", "gpu"]),
                compilation_policy=user_config.get("policy", "balanced"),
            )
            
            def log_callback(job_id, stage, message):
                """Real-time log callback."""
                self.store.add_log(job_id, stage, message)
                
                # Attempt to update job state based on stage
                try:
                    # Map pipeline stages to job states if needed
                    # "pending" -> "created" is not really a transition we expect during run
                    if stage == "pending":
                        return

                    new_state = JobState(stage)
                    current_job = self.store.get(job_id)
                    
                    if current_job.state != new_state:
                        self.store.update_state(job_id, new_state)
                except (ValueError, Exception):
                    # Ignore invalid states or transitions
                    pass
            
            result = run_soac_job(
                uploaded_model_path=job.input_path,
                config=config,
                job_id=job_id,
                work_dir=work_dir,
                log_callback=log_callback,
            )
            
            # Update job from result
            if result.success:
                self._handle_success(job_id, result)
            else:
                self._handle_failure(job_id, result)
                
        except Exception as e:
            logger.exception(f"Job {job_id} failed with exception")
            try:
                self.store.update_state(
                    job_id,
                    JobState.FAILED,
                    error_code="INTERNAL_ERROR",
                    error_message=str(e),
                )
            except InvalidStateTransition:
                pass
    
    def _handle_success(self, job_id: str, result) -> None:
        """Handle successful job completion."""
        # Update state to completed
        self.store.update_state(job_id, JobState.COMPLETED)
        
        # Set result
        self.store.set_result(
            job_id,
            selected_variant=result.selected_variant or "unknown",
            selection_reason=result.metadata.get("selection_reason", ""),
            metadata=result.metadata,
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
        # 1. Deployment Bundle
        if result.deployment_bundle:
            path = Path(result.deployment_bundle)
            if path.exists():
                artifact_id = f"art_{uuid.uuid4().hex[:8]}"
                fmt = "zip" if path.is_dir() else path.suffix.lstrip(".")
                
                self.store.set_artifact(
                    job_id, 
                    artifact_id, 
                    ArtifactInfo(
                        artifact_id=artifact_id,
                        name="Deployment Bundle",
                        platform="all",
                        format=fmt,
                        size_bytes=0, # calculated on download if dir
                        status="available",
                    ),
                    path=str(path)
                )

        # 2. General Artifacts (from pipeline context)
        if hasattr(result, 'artifacts') and result.artifacts:
            for name, path_str in result.artifacts.items():
                # Skip deployment bundle as it's already handled
                if name == "deployment":
                    continue
                    
                path = Path(path_str)
                if path.exists():
                    # Check if already added (avoid duplicates)
                    # This is a simple check; ideally check by path equality
                    existing = [a for a in self.store.get(job_id).artifact_metadata if a.name == name]
                    if existing:
                        continue
                        
                    artifact_id = f"art_{uuid.uuid4().hex[:8]}"
                    fmt = "zip" if path.is_dir() else path.suffix.lstrip(".")
                    
                    self.store.set_artifact(
                        job_id,
                        artifact_id,
                        ArtifactInfo(
                            artifact_id=artifact_id,
                            name=name,
                            platform="unknown",
                            format=fmt,
                            size_bytes=path.stat().st_size if path.is_file() else 0,
                            status="available",
                        ),
                        path=str(path)
                    )

        # 3. Stage Artifacts (legacy fallback)
        for sr in result.stage_results:
            if sr.artifacts:
                for name, path_str in sr.artifacts.items():
                    path = Path(path_str)
                    if path.exists():
                        artifact_id = f"art_{uuid.uuid4().hex[:8]}"
                        self.store.set_artifact(
                            job_id,
                            artifact_id,
                            ArtifactInfo(
                                artifact_id=artifact_id,
                                name=name,
                                platform="unknown",
                                format=path.suffix.lstrip("."),
                                size_bytes=path.stat().st_size if path.is_file() else 0,
                                status="available",
                            ),
                            path=str(path)
                        )
        
        # Logs are handled in real-time via log_callback, so we don't need to add them here.
        # This prevents duplicate logs.
        
        logger.info(f"Job {job_id} completed successfully")
    
    def _handle_failure(self, job_id: str, result) -> None:
        """Handle job failure."""
        error = result.error or {}
        # PipelineError.to_dict() returns "error" for the message, not "message"
        error_msg = error.get("error") or error.get("message") or "Unknown error"
        
        try:
            self.store.update_state(
                job_id,
                JobState.FAILED,
                error_code=error.get("error_code", "UNKNOWN"),
                error_message=error_msg,
            )
        except InvalidStateTransition:
            pass
        
        logger.error(f"Job {job_id} failed: {error_msg}")
    
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
