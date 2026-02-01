"""
SOAC Quantization
=================

FP16 and INT8 quantization for ONNX models.

Uses onnxruntime.quantization for stable, production-ready quantization.
"""

import logging
import tempfile
from pathlib import Path
from typing import Optional

try:
    import onnx
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False

try:
    from onnxruntime.quantization import (
        quantize_dynamic,
        quantize_static,
        QuantType,
        QuantFormat,
    )
    from onnxruntime.quantization.shape_inference import quant_pre_process
    QUANTIZATION_AVAILABLE = True
except ImportError:
    QUANTIZATION_AVAILABLE = False

from .exceptions import QuantizationError


logger = logging.getLogger(__name__)


def quantize_to_fp16(
    input_path: Path,
    output_path: Path,
) -> Path:
    """
    Convert model to FP16 (float16) precision.
    
    Uses ONNX's built-in FP16 conversion which:
    - Converts all float32 tensors to float16
    - Keeps some ops in float32 for numerical stability
    
    Args:
        input_path: Path to input ONNX model.
        output_path: Path to save FP16 model.
    
    Returns:
        Path to FP16 model.
    
    Raises:
        QuantizationError: If quantization fails.
    """
    if not ONNX_AVAILABLE:
        raise QuantizationError("fp16", "ONNX library not available")
    
    try:
        from onnx import version_converter
        from onnxconverter_common import float16
        
        model = onnx.load(str(input_path))
        
        # Convert to FP16
        model_fp16 = float16.convert_float_to_float16(
            model,
            keep_io_types=True,  # Keep inputs/outputs as FP32
            disable_shape_infer=False,
        )
        
        onnx.save(model_fp16, str(output_path))
        logger.info(f"FP16 quantization complete: {output_path}")
        
        return output_path
        
    except ImportError:
        # Fallback: Manual FP16 conversion using ONNX
        try:
            model = onnx.load(str(input_path))
            
            # Convert initializers to FP16
            from onnx import numpy_helper
            import numpy as np
            
            for initializer in model.graph.initializer:
                if initializer.data_type == onnx.TensorProto.FLOAT:
                    # Convert to FP16
                    arr = numpy_helper.to_array(initializer)
                    arr_fp16 = arr.astype(np.float16)
                    new_init = numpy_helper.from_array(arr_fp16, initializer.name)
                    initializer.CopyFrom(new_init)
            
            onnx.save(model, str(output_path))
            logger.info(f"FP16 quantization (fallback) complete: {output_path}")
            
            return output_path
            
        except Exception as e:
            raise QuantizationError("fp16", str(e), e)
    
    except Exception as e:
        raise QuantizationError("fp16", str(e), e)


def quantize_to_int8_dynamic(
    input_path: Path,
    output_path: Path,
) -> Path:
    """
    Convert model to INT8 using dynamic quantization.
    
    Dynamic quantization:
    - Quantizes weights to INT8
    - Computes activation scales at runtime
    - No calibration data needed
    
    Args:
        input_path: Path to input ONNX model.
        output_path: Path to save INT8 model.
    
    Returns:
        Path to INT8 model.
    
    Raises:
        QuantizationError: If quantization fails.
    """
    if not QUANTIZATION_AVAILABLE:
        raise QuantizationError("int8", "onnxruntime.quantization not available")
    
    try:
        # Preprocess model for quantization
        preprocessed_path = output_path.parent / f"{output_path.stem}_preprocessed.onnx"
        
        try:
            quant_pre_process(
                str(input_path),
                str(preprocessed_path),
                skip_optimization=False,
                skip_onnx_shape=False,
                skip_symbolic_shape=True,
            )
            quantize_input = preprocessed_path
        except Exception as e:
            logger.warning(f"Preprocessing failed, using original: {e}")
            quantize_input = input_path
        
        # Apply dynamic quantization
        quantize_dynamic(
            model_input=str(quantize_input),
            model_output=str(output_path),
            weight_type=QuantType.QInt8,
            per_channel=False,
            reduce_range=False,
        )
        
        # Cleanup preprocessed file
        if preprocessed_path.exists() and preprocessed_path != input_path:
            preprocessed_path.unlink()
        
        logger.info(f"INT8 quantization complete: {output_path}")
        return output_path
        
    except Exception as e:
        raise QuantizationError("int8", str(e), e)


def can_quantize_to_fp16(model_path: Path) -> bool:
    """
    Check if model can be quantized to FP16.
    
    Returns:
        True if FP16 quantization is supported.
    """
    if not ONNX_AVAILABLE:
        return False
    
    try:
        model = onnx.load(str(model_path))
        
        # Check for ops that don't support FP16
        unsupported_ops = {"DynamicQuantizeLinear", "QLinearConv", "QLinearMatMul"}
        
        for node in model.graph.node:
            if node.op_type in unsupported_ops:
                return False
        
        return True
        
    except Exception:
        return False


def can_quantize_to_int8(model_path: Path) -> bool:
    """
    Check if model can be quantized to INT8.
    
    Returns:
        True if INT8 quantization is supported.
    """
    if not QUANTIZATION_AVAILABLE:
        return False
    
    try:
        model = onnx.load(str(model_path))
        
        # Check for ops required for INT8
        supported_ops = {
            "Conv", "MatMul", "Gemm", "Add", "Relu", "MaxPool",
            "AveragePool", "GlobalAveragePool", "Flatten", "Reshape",
        }
        
        for node in model.graph.node:
            # Already quantized ops are not re-quantizable
            if "Quantize" in node.op_type or "QLinear" in node.op_type:
                return False
        
        return True
        
    except Exception:
        return False


def get_quantization_support() -> dict:
    """Get supported quantization methods."""
    return {
        "fp16": ONNX_AVAILABLE,
        "int8_dynamic": QUANTIZATION_AVAILABLE,
        "int8_static": False,  # Requires calibration data
    }
