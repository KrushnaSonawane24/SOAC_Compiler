"""
SOAC Benchmark Metrics
======================

Configuration and constants for benchmarking.
"""

from typing import Final


# =============================================================================
# ACCURACY CONFIGURATION
# =============================================================================

MAX_ACCURACY_DROP: Final[float] = 0.02
"""Maximum allowed accuracy drop (2%)."""

MIN_EVAL_SAMPLES: Final[int] = 10
"""Minimum number of samples for evaluation."""


# =============================================================================
# LATENCY CONFIGURATION
# =============================================================================

DEFAULT_WARMUP_RUNS: Final[int] = 5
"""Number of warmup runs before measurement."""

DEFAULT_MEASURED_RUNS: Final[int] = 50
"""Number of runs for measurement."""

MIN_WARMUP_RUNS: Final[int] = 1
"""Minimum warmup runs."""

MIN_MEASURED_RUNS: Final[int] = 10
"""Minimum measured runs."""


# =============================================================================
# MEMORY CONFIGURATION
# =============================================================================

MEMORY_SAMPLE_INTERVAL_MS: Final[int] = 10
"""Memory sampling interval in milliseconds."""


# =============================================================================
# SIZE THRESHOLDS
# =============================================================================

MAX_MODEL_SIZE_MB: Final[float] = 500.0
"""Maximum model size for benchmarking (500 MB)."""


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def validate_accuracy_threshold(threshold: float) -> float:
    """Validate and return accuracy threshold."""
    if threshold < 0.0 or threshold > 1.0:
        raise ValueError(f"Threshold must be between 0 and 1, got {threshold}")
    return threshold


def calculate_accuracy_drop(baseline: float, measured: float) -> float:
    """
    Calculate accuracy drop from baseline.
    
    Returns:
        Positive value if accuracy decreased, negative if improved.
    """
    return max(0.0, baseline - measured)


def is_accuracy_acceptable(
    baseline: float,
    measured: float,
    threshold: float = MAX_ACCURACY_DROP
) -> bool:
    """
    Check if accuracy drop is within acceptable threshold.
    
    Args:
        baseline: Baseline model accuracy.
        measured: Optimized model accuracy.
        threshold: Maximum allowed drop (default 2%).
    
    Returns:
        True if drop is acceptable.
    """
    drop = calculate_accuracy_drop(baseline, measured)
    return drop <= threshold


def bytes_to_mb(bytes_val: int) -> float:
    """Convert bytes to megabytes."""
    return bytes_val / (1024 * 1024)


def mb_to_bytes(mb_val: float) -> int:
    """Convert megabytes to bytes."""
    return int(mb_val * 1024 * 1024)
