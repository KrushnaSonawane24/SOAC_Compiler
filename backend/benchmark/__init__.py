"""
SOAC Benchmark Package
======================

Accuracy Verification and Benchmarking Engine.

PUBLIC API:
    - evaluate_accuracy(model_path, dataset) -> AccuracyResult
    - benchmark_model(model_path, dataset) -> BenchmarkResult

METRICS:
    - Accuracy: Top-1 accuracy
    - Latency: Median inference time
    - Memory: Peak RSS
    - Size: File size
"""

from pathlib import Path
from typing import Optional
import numpy as np

from .result import (
    AccuracyResult,
    LatencyResult,
    MemoryResult,
    SizeResult,
    BenchmarkResult,
    create_timestamp,
)

from .metrics import (
    MAX_ACCURACY_DROP,
    DEFAULT_WARMUP_RUNS,
    DEFAULT_MEASURED_RUNS,
    calculate_accuracy_drop,
    is_accuracy_acceptable,
)

from .dataset import (
    ReferenceDataset,
    DatasetSample,
    create_synthetic_dataset,
    load_dataset_from_numpy,
)

from .accuracy import (
    evaluate_accuracy,
    verify_accuracy_constraint,
    compare_accuracy,
)

from .latency import (
    measure_latency,
    create_sample_input,
)

from .memory import (
    measure_memory,
    get_current_memory_mb,
)

from .size import (
    measure_size,
    count_parameters,
    compare_sizes,
)

from .exceptions import (
    BenchmarkError,
    AccuracyMeasurementError,
    AccuracyConstraintViolation,
    LatencyMeasurementError,
    MemoryMeasurementError,
    DatasetError,
    InferenceError,
    InvalidBenchmarkConfig,
)


def benchmark_model(
    model_path: Path,
    dataset: Optional[ReferenceDataset] = None,
    baseline_accuracy: Optional[float] = None,
    warmup_runs: int = DEFAULT_WARMUP_RUNS,
    measured_runs: int = DEFAULT_MEASURED_RUNS,
) -> BenchmarkResult:
    """
    Run complete benchmark on a model.
    
    Args:
        model_path: Path to ONNX model.
        dataset: Reference dataset for accuracy (if None, skips accuracy).
        baseline_accuracy: Baseline accuracy for comparison.
        warmup_runs: Number of warmup runs for latency.
        measured_runs: Number of measured runs for latency.
    
    Returns:
        BenchmarkResult with all metrics.
    """
    model_path = Path(model_path)
    
    # Measure size
    size_result = measure_size(model_path)
    
    # Create sample input for latency/memory
    sample_input = create_sample_input(model_path)
    
    # Measure latency
    latency_result = measure_latency(
        model_path,
        sample_input,
        warmup_runs=warmup_runs,
        measured_runs=measured_runs,
    )
    
    # Measure memory
    memory_result = measure_memory(model_path, sample_input)
    
    # Measure accuracy if dataset provided
    if dataset is not None:
        accuracy_result = evaluate_accuracy(
            model_path,
            dataset,
            baseline_accuracy=baseline_accuracy,
        )
        is_valid = accuracy_result.accuracy_drop <= MAX_ACCURACY_DROP
        rejection_reason = None if is_valid else f"Accuracy drop {accuracy_result.accuracy_drop:.2%} > {MAX_ACCURACY_DROP:.2%}"
    else:
        # No accuracy check - create placeholder
        accuracy_result = AccuracyResult(
            accuracy=1.0,
            correct=0,
            total=0,
            accuracy_drop=0.0,
            is_baseline=True,
            model_path=str(model_path),
        )
        is_valid = True
        rejection_reason = None
    
    return BenchmarkResult(
        model_path=str(model_path),
        accuracy=accuracy_result,
        latency=latency_result,
        memory=memory_result,
        size=size_result,
        timestamp=create_timestamp(),
        is_valid=is_valid,
        rejection_reason=rejection_reason,
    )


__version__ = "1.0.0"

__all__ = [
    # Main API
    "benchmark_model",
    "evaluate_accuracy",
    
    # Result types
    "AccuracyResult",
    "LatencyResult",
    "MemoryResult",
    "SizeResult",
    "BenchmarkResult",
    
    # Dataset
    "ReferenceDataset",
    "DatasetSample",
    "create_synthetic_dataset",
    "load_dataset_from_numpy",
    
    # Metrics
    "measure_latency",
    "measure_memory",
    "measure_size",
    "verify_accuracy_constraint",
    "compare_accuracy",
    
    # Constants
    "MAX_ACCURACY_DROP",
    
    # Exceptions
    "BenchmarkError",
    "AccuracyMeasurementError",
    "AccuracyConstraintViolation",
    "LatencyMeasurementError",
    "MemoryMeasurementError",
    "DatasetError",
    "InferenceError",
]
