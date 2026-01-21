"""
SOAC Memory Measurement
=======================

Memory usage tracking during inference.
"""

import logging
from pathlib import Path
from typing import Optional
import gc
import numpy as np

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

try:
    import onnxruntime as ort
    ONNXRUNTIME_AVAILABLE = True
except ImportError:
    ONNXRUNTIME_AVAILABLE = False

from .exceptions import MemoryMeasurementError
from .result import MemoryResult


logger = logging.getLogger(__name__)


def get_current_memory_mb() -> float:
    """Get current process memory usage in MB."""
    if not PSUTIL_AVAILABLE:
        return 0.0
    
    process = psutil.Process()
    return process.memory_info().rss / (1024 * 1024)


def measure_memory(
    model_path: Path,
    input_data: np.ndarray,
    num_runs: int = 5,
) -> MemoryResult:
    """
    Measure memory usage during inference.
    
    Args:
        model_path: Path to ONNX model.
        input_data: Sample input for inference.
        num_runs: Number of inference runs.
    
    Returns:
        MemoryResult with memory statistics.
    """
    if not ONNXRUNTIME_AVAILABLE:
        raise MemoryMeasurementError("onnxruntime not available")
    
    model_path = Path(model_path)
    
    logger.info(f"Measuring memory: {model_path}")
    
    # Clean up before measurement
    gc.collect()
    
    before_mb = get_current_memory_mb()
    peak_mb = before_mb
    
    try:
        # Create session
        providers = ['CPUExecutionProvider']
        session = ort.InferenceSession(str(model_path), providers=providers)
        input_name = session.get_inputs()[0].name
        
        # Track peak during inference
        for _ in range(num_runs):
            session.run(None, {input_name: input_data})
            current_mb = get_current_memory_mb()
            peak_mb = max(peak_mb, current_mb)
        
        after_mb = get_current_memory_mb()
        
    except Exception as e:
        raise MemoryMeasurementError(f"Measurement failed: {e}", e)
    
    result = MemoryResult(
        peak_mb=peak_mb,
        before_mb=before_mb,
        after_mb=after_mb,
        delta_mb=after_mb - before_mb,
    )
    
    logger.info(f"  Peak memory: {result.peak_mb:.2f}MB")
    
    return result
