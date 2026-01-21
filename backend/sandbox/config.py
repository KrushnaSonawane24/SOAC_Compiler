"""
SOAC Sandbox Configuration
==========================

Centralized security constants for Docker sandbox execution.

MODIFICATION WARNING:
    Changes to this file directly impact sandbox security.
    Any modification should be reviewed by security team.

DESIGN PRINCIPLES:
    - All limits are explicit and documented
    - Defaults are secure (deny by default)
    - Configuration is immutable at runtime
"""

from typing import Final
from pathlib import Path


# =============================================================================
# NETWORK ISOLATION
# =============================================================================

NETWORK_MODE: Final[str] = "none"
"""
Docker network mode for sandbox containers.

'none' = Complete network isolation
    - No network interfaces except loopback
    - Cannot reach internet
    - Cannot reach other containers
    - Cannot reach host services

This is NON-NEGOTIABLE for security.
"""

# =============================================================================
# FILESYSTEM ISOLATION
# =============================================================================

READ_ONLY_ROOT: Final[bool] = True
"""
Whether container root filesystem is read-only.

When True:
    - Container cannot modify /usr, /bin, /etc, etc.
    - Malware cannot persist
    - Configuration cannot be tampered

/tmp is mounted as tmpfs for temporary files.
"""

TMPFS_SIZE: Final[str] = "64M"
"""
Size limit for /tmp tmpfs mount.

64MB is sufficient for:
    - Small temporary files during compilation
    - Intermediate outputs

Not enough for:
    - Dumping large datasets
    - Caching entire models
"""

# =============================================================================
# PROCESS LIMITS
# =============================================================================

PIDS_LIMIT: Final[int] = 100
"""
Maximum number of processes in container.

100 processes is enough for:
    - Python interpreter + workers
    - Compilation toolchain

Prevents:
    - Fork bombs
    - Excessive parallelism
    - Resource exhaustion
"""

# =============================================================================
# MEMORY LIMITS
# =============================================================================

DEFAULT_MEMORY_LIMIT: Final[str] = "512m"
"""
Default memory limit per container.

512MB is sufficient for:
    - Python runtime
    - Small to medium model processing

For larger models, callers can increase via parameter.
"""

MAX_MEMORY_LIMIT: Final[str] = "4g"
"""
Maximum allowed memory limit.

Even if callers request more, we cap at 4GB to prevent
any single job from consuming excessive host memory.
"""

# =============================================================================
# CPU LIMITS
# =============================================================================

DEFAULT_CPU_LIMIT: Final[float] = 1.0
"""
Default CPU limit (number of cores).

1.0 = One full CPU core
0.5 = Half a CPU core

This prevents CPU starvation of other processes.
"""

MAX_CPU_LIMIT: Final[float] = 4.0
"""
Maximum allowed CPU cores.

Even if callers request more, we cap to prevent
monopolizing host CPU.
"""

# =============================================================================
# TIMEOUT SETTINGS
# =============================================================================

DEFAULT_TIMEOUT_SECONDS: Final[int] = 300
"""
Default job timeout in seconds (5 minutes).

Most compilation jobs should complete much faster.
Long timeouts indicate potential issues.
"""

MAX_TIMEOUT_SECONDS: Final[int] = 3600
"""
Maximum allowed timeout (1 hour).

Jobs exceeding this are likely stuck or malicious.
"""

MIN_TIMEOUT_SECONDS: Final[int] = 10
"""
Minimum timeout to allow container startup.
"""

# =============================================================================
# SECURITY OPTIONS
# =============================================================================

SECURITY_OPTS: Final[list[str]] = [
    "no-new-privileges",
]
"""
Docker security options.

no-new-privileges:
    - Prevents gaining privileges via setuid/setgid binaries
    - Child processes cannot have more privileges than parent
"""

USER: Final[str] = "nobody"
"""
User to run container processes as.

'nobody' is a standard unprivileged user present in most images.
Running as non-root prevents privilege escalation attacks.
"""

# =============================================================================
# CONTAINER CONFIGURATION
# =============================================================================

DEFAULT_IMAGE: Final[str] = "python:3.11-slim"
"""
Default Docker image for sandbox execution.

python:3.11-slim is:
    - Small (~150MB)
    - Contains Python 3.11
    - Suitable for most compilation tasks
"""

ALLOWED_IMAGES: Final[frozenset[str]] = frozenset({
    "python:3.11-slim",
    "python:3.12-slim",
    "python:3.11-alpine",
    "python:3.12-alpine",
    "alpine:latest",
    "ubuntu:22.04",
})
"""
Whitelist of allowed Docker images.

Only images in this list can be used for sandbox execution.
This prevents running arbitrary images that may have vulnerabilities.
"""

# =============================================================================
# WORKSPACE CONFIGURATION
# =============================================================================

CONTAINER_WORKSPACE: Final[str] = "/workspace"
"""
Working directory inside container.
"""

CONTAINER_INPUT_DIR: Final[str] = "/workspace/input"
"""
Read-only input directory inside container.
"""

CONTAINER_OUTPUT_DIR: Final[str] = "/workspace/output"
"""
Writeable output directory inside container.
"""

# =============================================================================
# LABELS AND METADATA
# =============================================================================

CONTAINER_LABEL_PREFIX: Final[str] = "soac.sandbox"
"""
Prefix for container labels.

Labels are used for:
    - Identifying SOAC sandbox containers
    - Tracking job ownership
    - Facilitating cleanup
"""

# =============================================================================
# CLEANUP CONFIGURATION
# =============================================================================

CLEANUP_GRACE_PERIOD_SECONDS: Final[int] = 10
"""
Seconds to wait for graceful shutdown before force-kill.
"""

ORPHAN_CLEANUP_AGE_SECONDS: Final[int] = 3600
"""
Age after which unlabeled containers are considered orphaned.
Orphaned containers are cleaned up by periodic maintenance.
"""
