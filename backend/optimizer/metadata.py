"""
SOAC Optimizer Metadata
=======================

Data structures for optimization variants and metrics.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Tuple
from enum import Enum
from pathlib import Path


class VariantType(str, Enum):
    """Types of optimization variants."""
    BASELINE = "baseline"
    FP16 = "fp16"
    INT8 = "int8"
    PRUNED = "pruned"


class VariantStatus(str, Enum):
    """Validation status of a variant."""
    VALID = "valid"
    REJECTED = "rejected"
    GENERATION_FAILED = "generation_failed"
    BENCHMARK_FAILED = "benchmark_failed"


# Variant type preference order (higher is better for tie-breaking)
VARIANT_PREFERENCE_ORDER: Dict[VariantType, int] = {
    VariantType.INT8: 4,    # Most preferred
    VariantType.FP16: 3,
    VariantType.BASELINE: 2,
    VariantType.PRUNED: 1,  # Least preferred
}


@dataclass(frozen=True)
class BenchmarkMetrics:
    """
    Benchmark results for a variant.
    
    Attributes:
        latency_ms: Average inference latency in milliseconds
        throughput: Inferences per second
        memory_mb: Peak memory usage in MB
        accuracy: Accuracy score (0.0 to 1.0)
        accuracy_drop: Drop from baseline (0.0 to 1.0)
    """
    latency_ms: float
    throughput: float
    memory_mb: float
    accuracy: float
    accuracy_drop: float
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "latency_ms": self.latency_ms,
            "throughput": self.throughput,
            "memory_mb": self.memory_mb,
            "accuracy": self.accuracy,
            "accuracy_drop": self.accuracy_drop,
        }


@dataclass(frozen=True)
class OptimizedVariant:
    """
    A single optimized model variant.
    
    Attributes:
        variant_id: Unique identifier
        variant_type: Type of optimization applied
        onnx_path: Path to optimized ONNX file
        graph_hash: SHA-256 hash of the variant
        size_bytes: File size in bytes
        status: Validation status
        metrics: Benchmark results (if available)
        error_message: Error reason (if failed)
        metadata: Additional variant-specific info
    """
    variant_id: str
    variant_type: VariantType
    onnx_path: Path
    graph_hash: str
    size_bytes: int
    status: VariantStatus = VariantStatus.VALID
    metrics: Optional[BenchmarkMetrics] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_valid(self) -> bool:
        """Check if variant is valid for selection."""
        return self.status == VariantStatus.VALID
    
    @property
    def preference_score(self) -> int:
        """Get tie-breaking preference score."""
        return VARIANT_PREFERENCE_ORDER.get(self.variant_type, 0)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "variant_type": self.variant_type.value,
            "onnx_path": str(self.onnx_path),
            "graph_hash": self.graph_hash,
            "size_bytes": self.size_bytes,
            "status": self.status.value,
            "metrics": self.metrics.to_dict() if self.metrics else None,
            "error_message": self.error_message,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class RejectedVariant:
    """A variant that was rejected during selection."""
    variant_id: str
    variant_type: VariantType
    rejection_reason: str
    accuracy_drop: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "variant_type": self.variant_type.value,
            "rejection_reason": self.rejection_reason,
            "accuracy_drop": self.accuracy_drop,
        }


@dataclass(frozen=True)
class RankedVariant:
    """A variant with its ranking score."""
    variant_id: str
    variant_type: VariantType
    rank: int
    latency_ms: float
    size_bytes: int
    preference_score: int
    score_breakdown: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "variant_id": self.variant_id,
            "variant_type": self.variant_type.value,
            "rank": self.rank,
            "latency_ms": self.latency_ms,
            "size_bytes": self.size_bytes,
            "preference_score": self.preference_score,
            "score_breakdown": self.score_breakdown,
        }


# =============================================================================
# CONFIGURATION
# =============================================================================

MAX_ACCURACY_DROP: float = 0.01
"""Maximum allowed accuracy drop (1%)."""

DEFAULT_BASELINE_ACCURACY: float = 1.0
"""Default baseline accuracy when not measured."""
