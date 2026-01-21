"""
SOAC Model Size
===============

Model file size measurement.
"""

import logging
from pathlib import Path
from typing import Optional

try:
    import onnx
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False

from .result import SizeResult
from .metrics import bytes_to_mb


logger = logging.getLogger(__name__)


def measure_size(model_path: Path) -> SizeResult:
    """
    Measure model file size.
    
    Args:
        model_path: Path to ONNX model.
    
    Returns:
        SizeResult with size metrics.
    """
    model_path = Path(model_path)
    
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")
    
    size_bytes = model_path.stat().st_size
    size_mb = bytes_to_mb(size_bytes)
    
    # Try to count parameters
    param_count = None
    if ONNX_AVAILABLE:
        try:
            param_count = count_parameters(model_path)
        except Exception:
            pass  # Parameter count is optional
    
    result = SizeResult(
        file_size_bytes=size_bytes,
        file_size_mb=size_mb,
        parameter_count=param_count,
    )
    
    logger.info(f"Model size: {size_mb:.2f}MB ({size_bytes} bytes)")
    
    return result


def count_parameters(model_path: Path) -> int:
    """
    Count number of parameters in ONNX model.
    
    Args:
        model_path: Path to ONNX model.
    
    Returns:
        Total parameter count.
    """
    if not ONNX_AVAILABLE:
        return 0
    
    model = onnx.load(str(model_path))
    
    total_params = 0
    for initializer in model.graph.initializer:
        # Calculate elements from dims
        dims = initializer.dims
        if dims:
            num_elements = 1
            for d in dims:
                num_elements *= d
            total_params += num_elements
    
    return total_params


def compare_sizes(
    baseline_path: Path,
    optimized_path: Path,
) -> dict:
    """
    Compare sizes between baseline and optimized model.
    
    Returns:
        Dict with comparison metrics.
    """
    baseline_size = measure_size(baseline_path)
    optimized_size = measure_size(optimized_path)
    
    reduction_bytes = baseline_size.file_size_bytes - optimized_size.file_size_bytes
    reduction_ratio = reduction_bytes / baseline_size.file_size_bytes if baseline_size.file_size_bytes > 0 else 0.0
    
    return {
        "baseline_mb": baseline_size.file_size_mb,
        "optimized_mb": optimized_size.file_size_mb,
        "reduction_mb": bytes_to_mb(reduction_bytes),
        "reduction_ratio": reduction_ratio,
    }
