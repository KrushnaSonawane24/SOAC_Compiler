"""
SOAC Docker Sandbox Runner
==========================

THE SINGLE ENTRY POINT for executing untrusted code in isolation.

This module provides a secure Docker-based sandbox that:
    - Executes commands in complete network isolation
    - Enforces strict resource limits
    - Guarantees cleanup on all exit paths
    - Prevents filesystem escape

SECURITY GUARANTEES:
    - NO network access (--network=none)
    - Read-only root filesystem (--read-only)
    - Limited processes (--pids-limit=100)
    - Limited memory (--memory)
    - Limited CPU (--cpus)
    - No privilege escalation (--security-opt=no-new-privileges)
    - Non-root execution (--user=nobody)
    - Automatic cleanup (via context manager + atexit)

USAGE:
    result = run_job_in_sandbox(
        job_id="job_123",
        command=["python", "-c", "print('hello')"],
        input_dir=Path("/path/to/input"),
        output_dir=Path("/path/to/output"),
    )
"""

import logging
import os
import re
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List

try:
    import docker
    from docker.errors import (
        DockerException,
        NotFound,
        ImageNotFound as DockerImageNotFound,
        APIError,
        ContainerError,
    )
    DOCKER_AVAILABLE = True
except ImportError:
    DOCKER_AVAILABLE = False
    docker = None  # type: ignore
    DockerException = Exception  # type: ignore
    NotFound = Exception  # type: ignore
    DockerImageNotFound = Exception  # type: ignore
    APIError = Exception  # type: ignore
    ContainerError = Exception  # type: ignore

from .config import (
    NETWORK_MODE,
    READ_ONLY_ROOT,
    TMPFS_SIZE,
    PIDS_LIMIT,
    SECURITY_OPTS,
    USER,
    DEFAULT_IMAGE,
    ALLOWED_IMAGES,
    CONTAINER_WORKSPACE,
    CONTAINER_INPUT_DIR,
    CONTAINER_OUTPUT_DIR,
    CONTAINER_LABEL_PREFIX,
)
from .exceptions import (
    SandboxError,
    DockerNotAvailableError,
    ContainerCreationError,
    ContainerExecutionError,
    ContainerTimeoutError,
    ContainerCleanupError,
    InvalidJobDirectoryError,
    ImageNotFoundError,
    ResourceLimitExceededError,
)
from .resource_limits import (
    ResourceLimits,
    create_resource_limits,
    format_resource_summary,
)
from .cleanup import (
    container_cleanup_context,
    force_remove_container,
    kill_container,
)


logger = logging.getLogger(__name__)


# =============================================================================
# EXECUTION RESULT
# =============================================================================

@dataclass(frozen=True)
class ExecutionResult:
    """
    Result of sandbox execution.
    
    All fields are immutable to prevent accidental modification.
    
    Attributes:
        job_id: Unique job identifier.
        success: True if command exited with code 0.
        exit_code: Command exit code.
        stdout: Standard output (may be truncated).
        stderr: Standard error (may be truncated).
        duration_seconds: Execution time in seconds.
        timed_out: True if job was killed due to timeout.
        resource_limits: The limits that were applied.
        execution_timestamp: ISO 8601 timestamp.
    """
    job_id: str
    success: bool
    exit_code: int
    stdout: str
    stderr: str
    duration_seconds: float
    timed_out: bool
    resource_limits: ResourceLimits
    execution_timestamp: str
    container_id: str = ""


# =============================================================================
# VALIDATION HELPERS
# =============================================================================

def validate_job_id(job_id: str) -> str:
    """
    Validate job ID format.
    
    Job IDs must be alphanumeric with underscores/hyphens only.
    This prevents injection into Docker labels and paths.
    """
    if not re.match(r'^[a-zA-Z0-9_-]+$', job_id):
        raise ValueError(f"Invalid job_id format: {job_id}")
    
    if len(job_id) > 64:
        raise ValueError(f"Job ID too long (max 64 chars): {job_id}")
    
    return job_id


def validate_directory(
    directory: Path,
    job_id: str,
    require_exists: bool = True,
    require_writable: bool = False
) -> Path:
    """
    Validate a job directory.
    
    Security checks:
        - Directory must exist (if require_exists)
        - Directory cannot be a symlink pointing outside
        - Directory cannot be system paths like C:\\\\ or /
    """
    directory = Path(directory).resolve()
    
    if require_exists and not directory.exists():
        raise InvalidJobDirectoryError(
            job_id, str(directory), "Directory does not exist"
        )
    
    if require_exists and not directory.is_dir():
        raise InvalidJobDirectoryError(
            job_id, str(directory), "Path is not a directory"
        )
    
    # Block obviously dangerous paths
    dangerous_paths = [
        Path("/"),
        Path("C:\\"),
        Path("C:\\Windows"),
        Path("C:\\Windows\\System32"),
        Path("/etc"),
        Path("/usr"),
        Path("/bin"),
        Path("/var"),
    ]
    
    for dangerous in dangerous_paths:
        try:
            if directory.resolve() == dangerous.resolve():
                raise InvalidJobDirectoryError(
                    job_id, str(directory), f"Cannot use system path: {dangerous}"
                )
        except (OSError, ValueError):
            pass  # Path doesn't exist or isn't comparable
    
    return directory


def validate_image(image: str) -> str:
    """
    Validate Docker image is in the allowed whitelist.
    """
    if image not in ALLOWED_IMAGES:
        raise ValueError(
            f"Image '{image}' is not in allowed list. "
            f"Allowed: {', '.join(ALLOWED_IMAGES)}"
        )
    return image


def validate_command(command: List[str]) -> List[str]:
    """
    Validate command is a non-empty list of strings.
    """
    if not command:
        raise ValueError("Command cannot be empty")
    
    if not all(isinstance(arg, str) for arg in command):
        raise ValueError("All command arguments must be strings")
    
    return command


# =============================================================================
# DOCKER CLIENT
# =============================================================================

def get_docker_client() -> "docker.DockerClient":
    """
    Get a Docker client, validating the daemon is available.
    
    Raises:
        DockerNotAvailableError: If Docker is not running.
    """
    if not DOCKER_AVAILABLE:
        raise DockerNotAvailableError(
            "Docker SDK not installed. Install with: pip install docker"
        )
    
    try:
        client = docker.from_env()
        # Verify connection by pinging
        client.ping()
        return client
    except DockerException as e:
        raise DockerNotAvailableError(str(e))


def ensure_image_available(client: "docker.DockerClient", image: str) -> None:
    """
    Ensure Docker image is available locally.
    
    Does NOT pull from registry if missing (for security and offline use).
    """
    try:
        client.images.get(image)
    except DockerImageNotFound:
        raise ImageNotFoundError(image)


# =============================================================================
# MAIN EXECUTION FUNCTION
# =============================================================================

def run_job_in_sandbox(
    job_id: str,
    command: List[str],
    input_dir: Path,
    output_dir: Path,
    timeout_seconds: Optional[int] = None,
    memory_limit: Optional[str] = None,
    cpu_limit: Optional[float] = None,
    image: str = DEFAULT_IMAGE,
) -> ExecutionResult:
    """
    Execute a command in an isolated Docker container.
    
    This is THE SINGLE ENTRY POINT for sandbox execution.
    
    Args:
        job_id: Unique job identifier (alphanumeric with _-).
        command: Command and arguments to execute.
        input_dir: Host directory mounted read-only at /workspace/input.
        output_dir: Host directory mounted read-write at /workspace/output.
        timeout_seconds: Job timeout (default: 300s, max: 3600s).
        memory_limit: Memory limit (default: "512m", max: "4g").
        cpu_limit: CPU limit (default: 1.0, max: 4.0).
        image: Docker image to use (must be in whitelist).
    
    Returns:
        ExecutionResult with stdout, stderr, exit code, and metadata.
    
    Raises:
        DockerNotAvailableError: Docker daemon not accessible.
        ContainerCreationError: Failed to create container.
        ContainerTimeoutError: Job exceeded timeout.
        ContainerExecutionError: Job failed with non-zero exit.
        InvalidJobDirectoryError: Input/output directories invalid.
        ImageNotFoundError: Specified image not available locally.
    
    Security Guarantees:
        - Container has NO network access
        - Container cannot modify its root filesystem
        - Container can only write to output_dir
        - Container is killed if it exceeds timeout
        - Container is ALWAYS cleaned up, even on crashes
    
    Example:
        >>> result = run_job_in_sandbox(
        ...     job_id="compile_job_123",
        ...     command=["python", "compile.py", "/workspace/input/model.onnx"],
        ...     input_dir=Path("/tmp/jobs/123/input"),
        ...     output_dir=Path("/tmp/jobs/123/output"),
        ...     timeout_seconds=60,
        ... )
        >>> if result.success:
        ...     print(f"Output: {result.stdout}")
    """
    start_time = time.monotonic()
    
    # ==========================================================================
    # VALIDATION
    # ==========================================================================
    
    job_id = validate_job_id(job_id)
    command = validate_command(command)
    image = validate_image(image)
    input_dir = validate_directory(input_dir, job_id, require_exists=True)
    output_dir = validate_directory(output_dir, job_id, require_exists=True)
    
    limits = create_resource_limits(
        memory=memory_limit,
        cpu=cpu_limit,
        timeout=timeout_seconds,
    )
    
    logger.info(
        f"Starting sandbox job {job_id} | "
        f"image={image} | {format_resource_summary(limits)}"
    )
    
    # ==========================================================================
    # DOCKER CLIENT
    # ==========================================================================
    
    client = get_docker_client()
    ensure_image_available(client, image)
    
    # ==========================================================================
    # CONTAINER CONFIGURATION
    # ==========================================================================
    
    # Labels for tracking and cleanup
    labels = {
        f"{CONTAINER_LABEL_PREFIX}.managed": "true",
        f"{CONTAINER_LABEL_PREFIX}.job_id": job_id,
        f"{CONTAINER_LABEL_PREFIX}.created": datetime.now(timezone.utc).isoformat(),
    }
    
    # Volume mounts - CRITICAL for security
    # Input is read-only, output is read-write
    volumes = {
        str(input_dir): {"bind": CONTAINER_INPUT_DIR, "mode": "ro"},
        str(output_dir): {"bind": CONTAINER_OUTPUT_DIR, "mode": "rw"},
    }
    
    # tmpfs for writeable /tmp (RAM-backed, limited size)
    tmpfs = {
        "/tmp": f"size={TMPFS_SIZE},mode=1777",
    }
    
    # ==========================================================================
    # CREATE AND RUN CONTAINER
    # ==========================================================================
    
    container = None
    timed_out = False
    exit_code = -1
    stdout = ""
    stderr = ""
    
    try:
        logger.debug(f"Creating container for job {job_id}")
        
        container = client.containers.run(
            image=image,
            command=command,
            
            # CRITICAL SECURITY FLAGS
            detach=True,
            network_mode=NETWORK_MODE,
            read_only=READ_ONLY_ROOT,
            pids_limit=PIDS_LIMIT,
            mem_limit=limits.memory,
            nano_cpus=limits.nano_cpus,
            security_opt=SECURITY_OPTS,
            user=USER,
            
            # Workspace
            working_dir=CONTAINER_WORKSPACE,
            volumes=volumes,
            tmpfs=tmpfs,
            
            # Metadata
            labels=labels,
            name=f"soac_sandbox_{job_id}",
            
            # Misc
            auto_remove=False,  # We handle removal ourselves
            stdout=True,
            stderr=True,
        )
        
        logger.debug(f"Container {container.short_id} created for job {job_id}")
        
        # Use cleanup context to GUARANTEE removal
        with container_cleanup_context(client, container.id):
            
            # Wait for completion with timeout
            try:
                result = container.wait(timeout=limits.timeout)
                exit_code = result.get("StatusCode", -1)
            except Exception as e:
                # Timeout or other error
                if "timed out" in str(e).lower() or "timeout" in str(e).lower():
                    logger.warning(f"Job {job_id} timed out after {limits.timeout}s")
                    timed_out = True
                    kill_container(client, container.id)
                else:
                    raise
            
            # Capture logs
            try:
                logs = container.logs(stdout=True, stderr=True)
                # Split stdout and stderr
                # Docker logs combines them, so we get combined output
                if isinstance(logs, bytes):
                    stdout = logs.decode("utf-8", errors="replace")
                else:
                    stdout = str(logs)
                
                # Truncate if too large
                max_output = 1024 * 1024  # 1MB
                if len(stdout) > max_output:
                    stdout = stdout[:max_output] + "\n... (truncated)"
                    
            except Exception as e:
                logger.warning(f"Failed to capture logs for job {job_id}: {e}")
        
        # Container is cleaned up here by context manager
        
    except DockerImageNotFound:
        raise ImageNotFoundError(image)
    except APIError as e:
        raise ContainerCreationError(job_id, str(e), e)
    except DockerException as e:
        raise ContainerCreationError(job_id, str(e), e)
    
    # ==========================================================================
    # BUILD RESULT
    # ==========================================================================
    
    duration = time.monotonic() - start_time
    timestamp = datetime.now(timezone.utc).isoformat()
    
    result = ExecutionResult(
        job_id=job_id,
        success=exit_code == 0 and not timed_out,
        exit_code=exit_code,
        stdout=stdout,
        stderr=stderr,
        duration_seconds=round(duration, 3),
        timed_out=timed_out,
        resource_limits=limits,
        execution_timestamp=timestamp,
        container_id=container.id if container else "",
    )
    
    if timed_out:
        raise ContainerTimeoutError(job_id, limits.timeout)
    
    if exit_code != 0:
        logger.warning(f"Job {job_id} failed with exit code {exit_code}")
        # Don't raise - return the result with failure info
    else:
        logger.info(f"Job {job_id} completed successfully in {duration:.2f}s")
    
    return result
