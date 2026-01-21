"""
SOAC Latency Measurement
========================

Inference latency benchmarking with warmup.

GUARANTEES:
    - Warmup runs before measurement
    - Median used for robustness
    - Deterministic conditions
"""

import logging
import time
from pathlib import Path
from typing import List, Optional
import numpy as np

try:
    import onnxruntime as ort
    ONNXRUNTIME_AVAILABLE = True
except ImportError:
    ONNXRUNTIME_AVAILABLE = False

from .exceptions import LatencyMeasurementError
from .result import LatencyResult
from .metrics import DEFAULT_WARMUP_RUNS, DEFAULT_MEASURED_RUNS, MIN_WARMUP_RUNS, MIN_MEASURED_RUNS


logger = logging.getLogger(__name__)


def measure_latency(
    model_path: Path,
    input_data: np.ndarray,
    warmup_runs: int = DEFAULT_WARMUP_RUNS,
    measured_runs: int = DEFAULT_MEASURED_RUNS,
) -> LatencyResult:
    """
    Measure inference latency.
    
    Args:
        model_path: Path to ONNX model.
        input_data: Sample input for inference.
        warmup_runs: Number of warmup runs (not measured).
        measured_runs: Number of runs for measurement.
    
    Returns:
        LatencyResult with latency statistics.
    
    METHODOLOGY:
        1. Create inference session
        2. Run warmup iterations (not timed)
        3. Run measured iterations (timed)
        4. Compute statistics
    """
    if not ONNXRUNTIME_AVAILABLE:
        raise LatencyMeasurementError("onnxruntime not available")
    
    if warmup_runs < MIN_WARMUP_RUNS:
        warmup_runs = MIN_WARMUP_RUNS
    
    if measured_runs < MIN_MEASURED_RUNS:
        measured_runs = MIN_MEASURED_RUNS
    
    model_path = Path(model_path)
    
    logger.info(f"Measuring latency: {model_path}")
    logger.debug(f"  Warmup: {warmup_runs}, Measured: {measured_runs}")
    
    try:
        # Create session (CPU for consistency)
        providers = ['CPUExecutionProvider']
        session = ort.InferenceSession(str(model_path), providers=providers)
        input_name = session.get_inputs()[0].name
    except Exception as e:
        raise LatencyMeasurementError(f"Failed to load model: {e}", e)
    
    # Warmup runs (not timed)
    for _ in range(warmup_runs):
        try:
            session.run(None, {input_name: input_data})
        except Exception as e:
            raise LatencyMeasurementError(f"Warmup failed: {e}", e)
    
    # Measured runs
    latencies: List[float] = []
    
    for _ in range(measured_runs):
        try:
            start = time.perf_counter()
            session.run(None, {input_name: input_data})
            end = time.perf_counter()
            
            latency_ms = (end - start) * 1000
            latencies.append(latency_ms)
        except Exception as e:
            raise LatencyMeasurementError(f"Measurement failed: {e}", e)
    
    # Compute statistics
    latencies_arr = np.array(latencies)
    
    result = LatencyResult(
        median_ms=float(np.median(latencies_arr)),
        mean_ms=float(np.mean(latencies_arr)),
        min_ms=float(np.min(latencies_arr)),
        max_ms=float(np.max(latencies_arr)),
        std_ms=float(np.std(latencies_arr)),
        warmup_runs=warmup_runs,
        measured_runs=measured_runs,
    )
    
    logger.info(f"  Median latency: {result.median_ms:.2f}ms")
    
    return result


def create_sample_input(
    model_path: Path,
    batch_size: int = 1,
) -> np.ndarray:
    """
    Create sample input for latency measurement.
    
    Infers input shape from model and creates random data.
    """
    if not ONNXRUNTIME_AVAILABLE:
        raise LatencyMeasurementError("onnxruntime not available")
    
    try:
        session = ort.InferenceSession(str(model_path), providers=['CPUExecutionProvider'])
        input_info = session.get_inputs()[0]
        
        # Get shape (replace dynamic dims with defaults)
        shape = []
        for dim in input_info.shape:
            if isinstance(dim, int):
                shape.append(dim)
            else:
                # Dynamic dimension - use default
                if len(shape) == 0:
                    shape.append(batch_size)  # Batch
                else:
                    shape.append(224)  # Default spatial
        
        # Create random input
        return np.random.randn(*shape).astype(np.float32)
        
    except Exception as e:
        raise LatencyMeasurementError(f"Failed to create input: {e}", e)
