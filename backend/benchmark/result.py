"""
SOAC Benchmark Results
======================

Structured result types for benchmarking.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone


@dataclass(frozen=True)
class AccuracyResult:
    """
    Accuracy measurement result.
    
    Attributes:
        accuracy: Top-1 accuracy (0.0 to 1.0)
        correct: Number of correct predictions
        total: Total number of samples
        accuracy_drop: Drop from baseline (0.0 if this is baseline)
        is_baseline: Whether this is the baseline measurement
        model_path: Path to the model evaluated
    """
    accuracy: float
    correct: int
    total: int
    accuracy_drop: float = 0.0
    is_baseline: bool = False
    model_path: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "accuracy": self.accuracy,
            "correct": self.correct,
            "total": self.total,
            "accuracy_drop": self.accuracy_drop,
            "is_baseline": self.is_baseline,
            "model_path": self.model_path,
        }


@dataclass(frozen=True)
class LatencyResult:
    """
    Latency measurement result.
    
    Attributes:
        median_ms: Median latency in milliseconds
        mean_ms: Mean latency in milliseconds
        min_ms: Minimum latency
        max_ms: Maximum latency
        std_ms: Standard deviation
        warmup_runs: Number of warmup runs
        measured_runs: Number of measured runs
    """
    median_ms: float
    mean_ms: float
    min_ms: float
    max_ms: float
    std_ms: float
    warmup_runs: int
    measured_runs: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "median_ms": self.median_ms,
            "mean_ms": self.mean_ms,
            "min_ms": self.min_ms,
            "max_ms": self.max_ms,
            "std_ms": self.std_ms,
            "warmup_runs": self.warmup_runs,
            "measured_runs": self.measured_runs,
        }


@dataclass(frozen=True)
class MemoryResult:
    """
    Memory usage result.
    
    Attributes:
        peak_mb: Peak memory usage in MB
        before_mb: Memory before inference
        after_mb: Memory after inference
        delta_mb: Memory increase during inference
    """
    peak_mb: float
    before_mb: float
    after_mb: float
    delta_mb: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "peak_mb": self.peak_mb,
            "before_mb": self.before_mb,
            "after_mb": self.after_mb,
            "delta_mb": self.delta_mb,
        }


@dataclass(frozen=True)
class SizeResult:
    """
    Model size result.
    
    Attributes:
        file_size_bytes: Size on disk in bytes
        file_size_mb: Size in megabytes
        parameter_count: Number of parameters (if available)
    """
    file_size_bytes: int
    file_size_mb: float
    parameter_count: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_size_bytes": self.file_size_bytes,
            "file_size_mb": self.file_size_mb,
            "parameter_count": self.parameter_count,
        }


@dataclass(frozen=True)
class BenchmarkResult:
    """
    Complete benchmark result.
    
    Contains all metrics for a single model variant.
    """
    model_path: str
    accuracy: AccuracyResult
    latency: LatencyResult
    memory: MemoryResult
    size: SizeResult
    timestamp: str
    is_valid: bool = True
    rejection_reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_path": self.model_path,
            "accuracy": self.accuracy.to_dict(),
            "latency": self.latency.to_dict(),
            "memory": self.memory.to_dict(),
            "size": self.size.to_dict(),
            "timestamp": self.timestamp,
            "is_valid": self.is_valid,
            "rejection_reason": self.rejection_reason,
            "metadata": self.metadata,
        }


def create_timestamp() -> str:
    """Create ISO format timestamp."""
    return datetime.now(timezone.utc).isoformat()
