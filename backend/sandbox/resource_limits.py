"""
SOAC Sandbox Resource Limits
============================

Helpers for configuring and validating container resource limits.

SECURITY PRINCIPLES:
    - All limits have both defaults AND maximums
    - Callers cannot exceed maximum limits
    - Invalid values are rejected, not silently corrected
"""

from dataclasses import dataclass
from typing import Optional

from .config import (
    DEFAULT_MEMORY_LIMIT,
    MAX_MEMORY_LIMIT,
    DEFAULT_CPU_LIMIT,
    MAX_CPU_LIMIT,
    DEFAULT_TIMEOUT_SECONDS,
    MAX_TIMEOUT_SECONDS,
    MIN_TIMEOUT_SECONDS,
    PIDS_LIMIT,
)


@dataclass(frozen=True)
class ResourceLimits:
    """
    Immutable container resource limits.
    
    All values are validated on construction.
    This dataclass is frozen to prevent modification after creation.
    
    Attributes:
        memory: Memory limit string (e.g., "512m", "1g")
        memory_bytes: Memory limit in bytes (calculated)
        cpu: CPU limit as float (e.g., 1.0 = 1 core)
        nano_cpus: CPU limit in nano-cpus for Docker API
        pids: Maximum number of processes
        timeout: Job timeout in seconds
    """
    memory: str
    memory_bytes: int
    cpu: float
    nano_cpus: int
    pids: int
    timeout: int


def parse_memory_string(memory_str: str) -> int:
    """
    Parse a memory string to bytes.
    
    Supported formats:
        - "512m" or "512M" -> 512 * 1024 * 1024
        - "1g" or "1G" -> 1 * 1024 * 1024 * 1024
        - "1024k" or "1024K" -> 1024 * 1024
        - "1073741824" -> 1073741824 (raw bytes)
    
    Args:
        memory_str: Memory limit string.
    
    Returns:
        Memory limit in bytes.
    
    Raises:
        ValueError: If format is invalid.
    """
    memory_str = memory_str.strip().lower()
    
    if memory_str.endswith('g'):
        return int(float(memory_str[:-1]) * 1024 * 1024 * 1024)
    elif memory_str.endswith('m'):
        return int(float(memory_str[:-1]) * 1024 * 1024)
    elif memory_str.endswith('k'):
        return int(float(memory_str[:-1]) * 1024)
    else:
        return int(memory_str)


def validate_memory_limit(memory: str) -> str:
    """
    Validate and normalize memory limit.
    
    Args:
        memory: Requested memory limit.
    
    Returns:
        Validated memory limit string.
    
    Raises:
        ValueError: If limit exceeds maximum or is invalid.
    """
    requested_bytes = parse_memory_string(memory)
    max_bytes = parse_memory_string(MAX_MEMORY_LIMIT)
    
    if requested_bytes > max_bytes:
        raise ValueError(
            f"Memory limit {memory} exceeds maximum allowed {MAX_MEMORY_LIMIT}"
        )
    
    if requested_bytes < 32 * 1024 * 1024:  # 32MB minimum
        raise ValueError(
            f"Memory limit {memory} is below minimum 32m"
        )
    
    return memory


def validate_cpu_limit(cpu: float) -> float:
    """
    Validate CPU limit.
    
    Args:
        cpu: Requested CPU limit.
    
    Returns:
        Validated CPU limit.
    
    Raises:
        ValueError: If limit exceeds maximum or is invalid.
    """
    if cpu > MAX_CPU_LIMIT:
        raise ValueError(
            f"CPU limit {cpu} exceeds maximum allowed {MAX_CPU_LIMIT}"
        )
    
    if cpu < 0.1:
        raise ValueError(
            f"CPU limit {cpu} is below minimum 0.1"
        )
    
    return cpu


def validate_timeout(timeout: int) -> int:
    """
    Validate timeout value.
    
    Args:
        timeout: Requested timeout in seconds.
    
    Returns:
        Validated timeout.
    
    Raises:
        ValueError: If timeout is outside allowed range.
    """
    if timeout > MAX_TIMEOUT_SECONDS:
        raise ValueError(
            f"Timeout {timeout}s exceeds maximum allowed {MAX_TIMEOUT_SECONDS}s"
        )
    
    if timeout < MIN_TIMEOUT_SECONDS:
        raise ValueError(
            f"Timeout {timeout}s is below minimum {MIN_TIMEOUT_SECONDS}s"
        )
    
    return timeout


def create_resource_limits(
    memory: Optional[str] = None,
    cpu: Optional[float] = None,
    timeout: Optional[int] = None,
) -> ResourceLimits:
    """
    Create validated resource limits.
    
    Uses defaults for any unspecified values.
    All values are validated against maximum limits.
    
    Args:
        memory: Memory limit (e.g., "512m", "1g"). Default: 512m
        cpu: CPU limit (e.g., 1.0 = 1 core). Default: 1.0
        timeout: Job timeout in seconds. Default: 300
    
    Returns:
        Validated ResourceLimits object.
    
    Raises:
        ValueError: If any value is invalid or exceeds maximum.
    
    Example:
        >>> limits = create_resource_limits(memory="1g", cpu=2.0, timeout=600)
        >>> print(limits.memory_bytes)
        1073741824
    """
    # Apply defaults
    memory = memory or DEFAULT_MEMORY_LIMIT
    cpu = cpu if cpu is not None else DEFAULT_CPU_LIMIT
    timeout = timeout if timeout is not None else DEFAULT_TIMEOUT_SECONDS
    
    # Validate all values
    validated_memory = validate_memory_limit(memory)
    validated_cpu = validate_cpu_limit(cpu)
    validated_timeout = validate_timeout(timeout)
    
    # Calculate derived values
    memory_bytes = parse_memory_string(validated_memory)
    nano_cpus = int(validated_cpu * 1e9)
    
    return ResourceLimits(
        memory=validated_memory,
        memory_bytes=memory_bytes,
        cpu=validated_cpu,
        nano_cpus=nano_cpus,
        pids=PIDS_LIMIT,
        timeout=validated_timeout,
    )


def format_resource_summary(limits: ResourceLimits) -> str:
    """
    Format resource limits for logging.
    
    Returns:
        Human-readable summary string.
    """
    return (
        f"memory={limits.memory}, "
        f"cpu={limits.cpu}, "
        f"pids={limits.pids}, "
        f"timeout={limits.timeout}s"
    )
