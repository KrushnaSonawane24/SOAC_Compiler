"""
SOAC Sandbox Exceptions
=======================

Custom exception hierarchy for explicit, trackable sandbox failures.

WHY CUSTOM EXCEPTIONS?
    - Generic exceptions can be caught and silently ignored
    - Each exception maps to a specific failure mode, enabling precise handling
    - All exceptions inherit from SandboxError for catch-all handling
"""

from typing import Optional, Any


class SandboxError(Exception):
    """
    Base exception for ALL sandbox-related failures.
    
    This is the ONLY exception type that should escape the sandbox package.
    Downstream code should catch this to handle sandbox failures.
    
    Attributes:
        message: Human-readable error description
        context: Optional dict with forensic details
    """
    
    def __init__(self, message: str, context: Optional[dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.context = context or {}
    
    def __str__(self) -> str:
        if self.context:
            context_str = ", ".join(f"{k}={v!r}" for k, v in self.context.items())
            return f"{self.message} [{context_str}]"
        return self.message


class DockerNotAvailableError(SandboxError):
    """
    Raised when Docker daemon is not running or inaccessible.
    
    RESOLUTION:
        - Ensure Docker Desktop is running (Windows/macOS)
        - Ensure Docker daemon is started (Linux)
        - Check Docker socket permissions
    """
    
    def __init__(self, reason: str):
        super().__init__(
            f"Docker is not available: {reason}",
            context={"reason": reason}
        )
        self.reason = reason


class ContainerCreationError(SandboxError):
    """
    Raised when container cannot be created.
    
    POSSIBLE CAUSES:
        - Image not found
        - Invalid container configuration
        - Resource limits too restrictive
        - Docker daemon overloaded
    """
    
    def __init__(self, job_id: str, reason: str, original_exception: Optional[Exception] = None):
        super().__init__(
            f"Failed to create container for job {job_id}: {reason}",
            context={
                "job_id": job_id,
                "reason": reason,
                "original_error": str(original_exception) if original_exception else None
            }
        )
        self.job_id = job_id
        self.reason = reason
        self.original_exception = original_exception


class ContainerExecutionError(SandboxError):
    """
    Raised when container execution fails.
    
    This exception contains:
        - exit_code: Container's exit code
        - stdout: Standard output (if captured)
        - stderr: Standard error (if captured)
    """
    
    def __init__(
        self,
        job_id: str,
        exit_code: int,
        stdout: str = "",
        stderr: str = "",
        reason: str = ""
    ):
        super().__init__(
            f"Container execution failed for job {job_id} (exit code {exit_code})",
            context={
                "job_id": job_id,
                "exit_code": exit_code,
                "stderr_preview": stderr[:500] if stderr else ""
            }
        )
        self.job_id = job_id
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.reason = reason


class ContainerTimeoutError(SandboxError):
    """
    Raised when container exceeds its time limit.
    
    SECURITY NOTE:
        Timeout enforcement is critical to prevent:
        - Infinite loops consuming resources
        - Slow-loris style DoS attacks
        - Runaway compilation jobs
    """
    
    def __init__(self, job_id: str, timeout_seconds: int):
        super().__init__(
            f"Container for job {job_id} exceeded timeout of {timeout_seconds}s",
            context={
                "job_id": job_id,
                "timeout_seconds": timeout_seconds,
                "severity": "high"
            }
        )
        self.job_id = job_id
        self.timeout_seconds = timeout_seconds


class ContainerCleanupError(SandboxError):
    """
    Raised when container cleanup fails.
    
    SEVERITY: Warning (non-fatal for the job, but indicates resource leak)
    
    If cleanup fails, the container may remain and consume resources.
    This should trigger alerts for manual intervention.
    """
    
    def __init__(self, container_id: str, reason: str):
        super().__init__(
            f"Failed to cleanup container {container_id}: {reason}",
            context={
                "container_id": container_id,
                "reason": reason,
                "severity": "warning"
            }
        )
        self.container_id = container_id
        self.reason = reason


class InvalidJobDirectoryError(SandboxError):
    """
    Raised when job directories are invalid or unsafe.
    
    SECURITY CONSIDERATIONS:
        - Input directory must exist and be readable
        - Output directory must be writeable
        - Directories must not escape the allowed base path
        - Symlinks outside base path are rejected
    """
    
    def __init__(self, job_id: str, directory: str, reason: str):
        super().__init__(
            f"Invalid job directory for {job_id}: {reason}",
            context={
                "job_id": job_id,
                "directory": directory,
                "reason": reason
            }
        )
        self.job_id = job_id
        self.directory = directory
        self.reason = reason


class ImageNotFoundError(SandboxError):
    """
    Raised when the specified Docker image is not available.
    
    RESOLUTION:
        - Pull the image: docker pull <image>
        - Check image name spelling
        - Verify registry access
    """
    
    def __init__(self, image: str):
        super().__init__(
            f"Docker image not found: {image}",
            context={"image": image}
        )
        self.image = image


class ResourceLimitExceededError(SandboxError):
    """
    Raised when container hits resource limits.
    
    This can occur when:
        - Memory limit reached (OOM killed)
        - PID limit reached (fork bomb blocked)
        - CPU throttling too aggressive
    """
    
    def __init__(self, job_id: str, resource_type: str, limit: str):
        super().__init__(
            f"Job {job_id} exceeded {resource_type} limit of {limit}",
            context={
                "job_id": job_id,
                "resource_type": resource_type,
                "limit": limit
            }
        )
        self.job_id = job_id
        self.resource_type = resource_type
        self.limit = limit
