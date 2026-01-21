"""
SOAC Sandbox Package
====================

Docker-based sandbox for secure execution of untrusted AI compiler jobs.

This package provides complete isolation for executing untrusted code:
    - No network access
    - Read-only filesystem
    - Strict resource limits
    - Guaranteed cleanup

PUBLIC API:
    - run_job_in_sandbox(job_id, command, input_dir, output_dir, ...) -> ExecutionResult
      THE ONLY function external code should call.

EXCEPTION HIERARCHY:
    - SandboxError (base)
        - DockerNotAvailableError
        - ContainerCreationError
        - ContainerExecutionError
        - ContainerTimeoutError
        - ContainerCleanupError
        - InvalidJobDirectoryError
        - ImageNotFoundError
        - ResourceLimitExceededError

USAGE:
    from backend.sandbox import run_job_in_sandbox, SandboxError
    
    try:
        result = run_job_in_sandbox(
            job_id="compile_123",
            command=["python", "compile.py"],
            input_dir=Path("/tmp/input"),
            output_dir=Path("/tmp/output"),
        )
        if result.success:
            print(result.stdout)
    except SandboxError as e:
        print(f"Sandbox error: {e}")

For more details, see: backend/sandbox/README.md
"""

# Public API - THE ONLY ENTRY POINT
from .docker_runner import (
    run_job_in_sandbox,
    ExecutionResult,
)

# Resource limit helpers
from .resource_limits import (
    ResourceLimits,
    create_resource_limits,
)

# Cleanup utilities
from .cleanup import (
    cleanup_orphaned_containers,
)

# Exceptions - for structured error handling
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

# Configuration - for inspection only
from .config import (
    DEFAULT_IMAGE,
    ALLOWED_IMAGES,
    DEFAULT_MEMORY_LIMIT,
    DEFAULT_CPU_LIMIT,
    DEFAULT_TIMEOUT_SECONDS,
)

# Version
__version__ = "1.0.0"

# Explicit public API
__all__ = [
    # Main function
    "run_job_in_sandbox",
    "ExecutionResult",
    
    # Resource limits
    "ResourceLimits",
    "create_resource_limits",
    
    # Cleanup
    "cleanup_orphaned_containers",
    
    # Base exception
    "SandboxError",
    
    # Specific exceptions
    "DockerNotAvailableError",
    "ContainerCreationError",
    "ContainerExecutionError",
    "ContainerTimeoutError",
    "ContainerCleanupError",
    "InvalidJobDirectoryError",
    "ImageNotFoundError",
    "ResourceLimitExceededError",
    
    # Configuration (read-only)
    "DEFAULT_IMAGE",
    "ALLOWED_IMAGES",
    "DEFAULT_MEMORY_LIMIT",
    "DEFAULT_CPU_LIMIT",
    "DEFAULT_TIMEOUT_SECONDS",
]
