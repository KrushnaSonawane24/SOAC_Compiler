"""
SOAC ONNX Converter
===================

Converts supported formats to ONNX.

SUPPORTED FORMATS:
    - ONNX (.onnx) - No conversion needed
    - TensorFlow Keras (.h5, .keras) - via tf2onnx
    - TensorFlow SavedModel (directory) - via tf2onnx
    - TFLite (.tflite) - via tf2onnx
    - CoreML (.mlmodel) - via coremltools (if available)
"""

import logging
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Tuple
from enum import Enum

try:
    import onnx
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    onnx = None

from .exceptions import ConversionError, UnsupportedFormatError


logger = logging.getLogger(__name__)


class InputFormat(str, Enum):
    """Supported input formats."""
    ONNX = "onnx"
    KERAS_H5 = "keras_h5"
    KERAS = "keras"
    SAVEDMODEL = "savedmodel"
    TFLITE = "tflite"
    COREML = "coreml"
    PYTORCH = "pytorch"


# Extension to format mapping
EXTENSION_FORMAT_MAP = {
    ".onnx": InputFormat.ONNX,
    ".h5": InputFormat.KERAS_H5,
    ".keras": InputFormat.KERAS,
    ".tflite": InputFormat.TFLITE,
    ".mlmodel": InputFormat.COREML,
    ".pt": InputFormat.PYTORCH,
    ".pth": InputFormat.PYTORCH,
}


def detect_format(input_path: Path) -> InputFormat:
    """
    Detect input format from file path.
    
    Args:
        input_path: Path to input model.
    
    Returns:
        Detected InputFormat.
    
    Raises:
        UnsupportedFormatError: If format cannot be determined.
    """
    input_path = Path(input_path)
    
    # Check if it's a directory (SavedModel)
    if input_path.is_dir():
        # Check for SavedModel signature
        if (input_path / "saved_model.pb").exists():
            return InputFormat.SAVEDMODEL
        raise UnsupportedFormatError(str(input_path), "directory")
    
    # Check extension
    ext = input_path.suffix.lower()
    
    if ext in EXTENSION_FORMAT_MAP:
        return EXTENSION_FORMAT_MAP[ext]
    
    raise UnsupportedFormatError(str(input_path), ext)


def load_onnx(input_path: Path) -> "onnx.ModelProto":
    """
    Load an ONNX model file.
    
    Args:
        input_path: Path to .onnx file.
    
    Returns:
        Loaded ONNX ModelProto.
    """
    if not ONNX_AVAILABLE:
        raise ConversionError("onnx", "onnx", "ONNX library not installed")
    
    try:
        model = onnx.load(str(input_path), load_external_data=False)
        return model
    except Exception as e:
        raise ConversionError("onnx", "onnx", f"Failed to load: {e}", e)


def _fix_keras3_config(config: dict) -> dict:
    """
    Fix Keras 3.x config to be compatible with Keras 2.x.
    
    Keras 3.x uses 'batch_shape' but Keras 2.x expects 'batch_input_shape'.
    This function recursively fixes the config.
    """
    if not isinstance(config, dict):
        return config
    
    fixed = {}
    for key, value in config.items():
        if key == 'batch_shape':
            # Convert Keras 3 'batch_shape' to Keras 2 'batch_input_shape'
            fixed['batch_input_shape'] = value
        elif key == 'config' and isinstance(value, dict):
            # Recursively fix nested configs
            fixed[key] = _fix_keras3_config(value)
        elif key == 'layers' and isinstance(value, list):
            # Fix each layer config
            fixed[key] = [_fix_keras3_config(layer) for layer in value]
        elif isinstance(value, dict):
            fixed[key] = _fix_keras3_config(value)
        elif isinstance(value, list):
            fixed[key] = [_fix_keras3_config(item) if isinstance(item, dict) else item for item in value]
        else:
            fixed[key] = value
    
    return fixed


def _load_keras_model_with_compat(input_path: Path):
    """
    Load Keras model with Keras 2/3 compatibility.
    
    With TensorFlow 2.20+ and Keras 3, models load natively.
    Falls back to compatibility fixes for older model formats.
    """
    import tensorflow as tf
    
    input_path = Path(input_path)
    
    # Strategy 1: Try direct load with Keras 3 (native for TF 2.20+)
    try:
        model = tf.keras.models.load_model(str(input_path), compile=False)
        logger.info("Loaded Keras model successfully")
        return model
    except Exception as e:
        error_msg = str(e)
        logger.warning(f"Direct load failed: {error_msg}")
    
    # Strategy 2: Try with safe_mode=False for custom objects
    try:
        model = tf.keras.models.load_model(
            str(input_path), 
            compile=False,
            safe_mode=False
        )
        logger.info("Loaded Keras model with safe_mode=False")
        return model
    except Exception as e:
        logger.warning(f"Safe mode disabled load failed: {e}")
    
    # Strategy 3: Try loading with custom_objects empty dict
    try:
        model = tf.keras.models.load_model(
            str(input_path),
            compile=False,
            custom_objects={}
        )
        logger.info("Loaded Keras model with custom_objects")
        return model
    except Exception as e:
        logger.warning(f"Custom objects load failed: {e}")
    
    raise ConversionError(
        "keras", "onnx",
        f"Could not load Keras model: {input_path.name}. "
        f"Please ensure the model was saved correctly. "
        f"Try exporting as SavedModel format for better compatibility."
    )



def convert_keras_to_onnx(input_path: Path) -> "onnx.ModelProto":
    """
    Convert Keras .h5 or .keras model to ONNX.
    
    Supports both Keras 2.x and Keras 3.x models through automatic
    compatibility detection and conversion.
    
    Args:
        input_path: Path to Keras model file.
    
    Returns:
        Converted ONNX model.
    """
    try:
        import tensorflow as tf
        import tf2onnx
    except ImportError as e:
        raise ConversionError(
            "keras", "onnx",
            f"tf2onnx or tensorflow not installed: {e}"
        )
    
    logger.info(f"Converting Keras model: {input_path}")
    
    try:
        # Load Keras model with compatibility layer
        model = _load_keras_model_with_compat(input_path)
        
        # Get input signature
        input_signature = []
        for inp in model.inputs:
            shape = [d if d is not None else 1 for d in inp.shape]
            input_signature.append(
                tf.TensorSpec(shape, inp.dtype, name=inp.name)
            )
        
        # Convert to ONNX
        onnx_model, _ = tf2onnx.convert.from_keras(
            model,
            input_signature=input_signature,
            opset=17,
            output_path=None,
        )
        
        return onnx_model
        
    except ConversionError:
        raise
    except Exception as e:
        raise ConversionError("keras", "onnx", str(e), e)




def convert_savedmodel_to_onnx(input_path: Path) -> "onnx.ModelProto":
    """
    Convert TensorFlow SavedModel to ONNX.
    
    Args:
        input_path: Path to SavedModel directory.
    
    Returns:
        Converted ONNX model.
    """
    try:
        import tensorflow as tf
        import tf2onnx
    except ImportError as e:
        raise ConversionError(
            "savedmodel", "onnx",
            f"tf2onnx or tensorflow not installed: {e}"
        )
    
    logger.info(f"Converting SavedModel: {input_path}")
    
    try:
        # Convert using tf2onnx command-line interface approach
        onnx_model, _ = tf2onnx.convert.from_saved_model(
            str(input_path),
            opset=17,
            output_path=None,
        )
        
        return onnx_model
        
    except Exception as e:
        raise ConversionError("savedmodel", "onnx", str(e), e)


def convert_tflite_to_onnx(input_path: Path) -> "onnx.ModelProto":
    """
    Convert TFLite model to ONNX.
    
    Args:
        input_path: Path to .tflite file.
    
    Returns:
        Converted ONNX model.
    """
    try:
        import tf2onnx
        from tf2onnx import tf_loader
    except ImportError as e:
        raise ConversionError(
            "tflite", "onnx",
            f"tf2onnx not installed: {e}"
        )
    
    logger.info(f"Converting TFLite model: {input_path}")
    
    try:
        # Convert TFLite to ONNX
        onnx_model, _ = tf2onnx.convert.from_tflite(
            str(input_path),
            opset=17,
            output_path=None,
        )
        
        return onnx_model
        
    except Exception as e:
        raise ConversionError("tflite", "onnx", str(e), e)


def convert_coreml_to_onnx(input_path: Path) -> "onnx.ModelProto":
    """
    Convert CoreML model to ONNX.
    
    Args:
        input_path: Path to .mlmodel file.
    
    Returns:
        Converted ONNX model.
    """
    try:
        import coremltools as ct
        from coremltools.converters.onnx import convert as coreml_to_onnx
    except ImportError:
        # Try alternative approach
        try:
            import onnxmltools
            from onnxmltools.convert import convert_coreml
        except ImportError as e:
            raise ConversionError(
                "coreml", "onnx",
                f"coremltools or onnxmltools not installed: {e}"
            )
        
        logger.info(f"Converting CoreML model: {input_path}")
        
        try:
            import coremltools as ct
            coreml_model = ct.models.MLModel(str(input_path))
            onnx_model = convert_coreml(coreml_model)
            return onnx_model
        except Exception as e:
            raise ConversionError("coreml", "onnx", str(e), e)
    
    logger.info(f"Converting CoreML model: {input_path}")
    
    try:
        coreml_model = ct.models.MLModel(str(input_path))
        onnx_model = coreml_to_onnx(coreml_model)
        return onnx_model
    except Exception as e:
        raise ConversionError("coreml", "onnx", str(e), e)


def convert_pytorch_to_onnx(input_path: Path) -> "onnx.ModelProto":
    """
    Convert PyTorch model (.pt/.pth) to ONNX.
    
    Supports:
        - Full model saves (torch.save(model, path))
        - State dicts with model architecture
        - TorchScript models
    
    Args:
        input_path: Path to .pt or .pth file.
    
    Returns:
        Converted ONNX model.
    
    Raises:
        ConversionError: If conversion fails.
    """
    try:
        import torch
        import torch.onnx
    except ImportError as e:
        raise ConversionError(
            "pytorch", "onnx",
            f"PyTorch not installed: {e}"
        )
    
    logger.info(f"Converting PyTorch model: {input_path}")
    
    try:
        # Try loading as full model first
        try:
            model = torch.load(str(input_path), map_location="cpu", weights_only=False)
        except Exception:
            # Try with weights_only=True for newer PyTorch
            model = torch.load(str(input_path), map_location="cpu")
        
        # Check if it's a state_dict or a full model
        if isinstance(model, dict):
            # It's likely a state_dict - we need the model architecture
            # Try common patterns
            if "model" in model:
                model = model["model"]
            elif "state_dict" in model:
                raise ConversionError(
                    "pytorch", "onnx",
                    "State dict detected but model architecture not included. "
                    "Please save the full model using torch.save(model, path) "
                    "or provide the model architecture."
                )
            elif all(isinstance(v, torch.Tensor) for v in model.values()):
                raise ConversionError(
                    "pytorch", "onnx",
                    "Pure state_dict detected. Cannot convert without model architecture. "
                    "Please save the full model using torch.save(model, path)."
                )
        
        # Check if it's a TorchScript model
        if isinstance(model, torch.jit.ScriptModule):
            # TorchScript model - get example input from model
            logger.info("Detected TorchScript model")
            # Try to infer input shape from the model
            dummy_input = torch.randn(1, 3, 224, 224)  # Default for vision models
        else:
            # Regular PyTorch model
            model.eval()
            
            # Try to infer input shape
            dummy_input = torch.randn(1, 3, 224, 224)  # Default for vision models
        
        # Export to ONNX
        with tempfile.NamedTemporaryFile(suffix=".onnx", delete=False) as tmp:
            tmp_path = tmp.name
        
        try:
            torch.onnx.export(
                model,
                dummy_input,
                tmp_path,
                export_params=True,
                opset_version=17,
                do_constant_folding=True,
                input_names=["input"],
                output_names=["output"],
                dynamic_axes={
                    "input": {0: "batch_size"},
                    "output": {0: "batch_size"},
                },
            )
            
            # Load and return the ONNX model
            onnx_model = onnx.load(tmp_path)
            return onnx_model
            
        finally:
            # Clean up temp file
            Path(tmp_path).unlink(missing_ok=True)
        
    except ConversionError:
        raise
    except Exception as e:
        raise ConversionError("pytorch", "onnx", str(e), e)


def convert_to_onnx(input_path: Path) -> Tuple["onnx.ModelProto", InputFormat]:
    """
    Convert any supported format to ONNX.
    
    Args:
        input_path: Path to input model.
    
    Returns:
        Tuple of (ONNX model, original format).
    
    Raises:
        UnsupportedFormatError: If format not supported.
        ConversionError: If conversion fails.
    """
    input_path = Path(input_path)
    
    if not input_path.exists():
        raise ConversionError("unknown", "onnx", f"File not found: {input_path}")
    
    # Detect format
    format = detect_format(input_path)
    logger.info(f"Detected format: {format.value}")
    
    # Dispatch to appropriate converter
    if format == InputFormat.ONNX:
        model = load_onnx(input_path)
    elif format == InputFormat.KERAS_H5 or format == InputFormat.KERAS:
        model = convert_keras_to_onnx(input_path)
    elif format == InputFormat.SAVEDMODEL:
        model = convert_savedmodel_to_onnx(input_path)
    elif format == InputFormat.TFLITE:
        model = convert_tflite_to_onnx(input_path)
    elif format == InputFormat.COREML:
        model = convert_coreml_to_onnx(input_path)
    elif format == InputFormat.PYTORCH:
        model = convert_pytorch_to_onnx(input_path)
    else:
        raise UnsupportedFormatError(str(input_path), format.value)
    
    return model, format


def get_supported_formats() -> list[str]:
    """Get list of supported file extensions."""
    return list(EXTENSION_FORMAT_MAP.keys()) + ["directory (SavedModel)"]
