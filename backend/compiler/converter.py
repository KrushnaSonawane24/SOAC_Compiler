"""
SOAC Model Converter
====================

Converts various model formats to ONNX for unified processing.
Supports: TensorFlow (.h5, .pb), PyTorch (.pt, .pth)
"""

import logging
import tempfile
import shutil
from pathlib import Path
from typing import Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ModelFormat(str, Enum):
    """Supported model formats."""
    ONNX = "onnx"
    KERAS_H5 = "h5"
    TF_SAVEDMODEL = "savedmodel"
    TF_PB = "pb"
    PYTORCH = "pt"
    PYTORCH_PTH = "pth"


@dataclass
class ConversionResult:
    """Result of model conversion."""
    success: bool
    output_path: Optional[Path]
    original_format: ModelFormat
    error: Optional[str] = None
    

def detect_format(file_path: Path) -> ModelFormat:
    """Detect model format from file extension."""
    suffix = file_path.suffix.lower()
    
    format_map = {
        ".onnx": ModelFormat.ONNX,
        ".h5": ModelFormat.KERAS_H5,
        ".keras": ModelFormat.KERAS_H5,
        ".pb": ModelFormat.TF_PB,
        ".pt": ModelFormat.PYTORCH,
        ".pth": ModelFormat.PYTORCH_PTH,
    }
    
    return format_map.get(suffix)


def convert_keras_to_onnx(input_path: Path, output_path: Path, opset: int = 13) -> ConversionResult:
    """Convert Keras .h5 model to ONNX."""
    try:
        import tf2onnx
        import tensorflow as tf
        
        logger.info(f"Converting Keras model: {input_path}")
        
        # Load Keras model
        model = tf.keras.models.load_model(str(input_path), compile=False)
        
        # Get input spec
        input_signature = [tf.TensorSpec(model.input_shape, tf.float32, name='input')]
        
        # Convert to ONNX
        onnx_model, _ = tf2onnx.convert.from_keras(
            model,
            input_signature=input_signature,
            opset=opset,
        )
        
        # Save
        import onnx
        onnx.save(onnx_model, str(output_path))
        
        logger.info(f"Keras → ONNX conversion successful: {output_path}")
        return ConversionResult(
            success=True,
            output_path=output_path,
            original_format=ModelFormat.KERAS_H5,
        )
        
    except ImportError as e:
        return ConversionResult(
            success=False,
            output_path=None,
            original_format=ModelFormat.KERAS_H5,
            error=f"TensorFlow or tf2onnx not installed: {e}",
        )
    except Exception as e:
        logger.error(f"Keras conversion failed: {e}")
        return ConversionResult(
            success=False,
            output_path=None,
            original_format=ModelFormat.KERAS_H5,
            error=str(e),
        )


def convert_tf_pb_to_onnx(input_path: Path, output_path: Path, opset: int = 13) -> ConversionResult:
    """Convert TensorFlow frozen graph (.pb) to ONNX."""
    try:
        import subprocess
        
        logger.info(f"Converting TF frozen graph: {input_path}")
        
        # Use tf2onnx CLI
        result = subprocess.run([
            "python", "-m", "tf2onnx.convert",
            "--graphdef", str(input_path),
            "--output", str(output_path),
            "--opset", str(opset),
            "--inputs", "input:0",
            "--outputs", "output:0",
        ], capture_output=True, text=True, timeout=300)
        
        if result.returncode == 0 and output_path.exists():
            logger.info(f"TF PB → ONNX conversion successful: {output_path}")
            return ConversionResult(
                success=True,
                output_path=output_path,
                original_format=ModelFormat.TF_PB,
            )
        else:
            return ConversionResult(
                success=False,
                output_path=None,
                original_format=ModelFormat.TF_PB,
                error=result.stderr or "Conversion failed",
            )
            
    except Exception as e:
        logger.error(f"TF PB conversion failed: {e}")
        return ConversionResult(
            success=False,
            output_path=None,
            original_format=ModelFormat.TF_PB,
            error=str(e),
        )


def convert_pytorch_to_onnx(input_path: Path, output_path: Path, opset: int = 13) -> ConversionResult:
    """Convert PyTorch model (.pt/.pth) to ONNX."""
    try:
        import torch
        
        logger.info(f"Converting PyTorch model: {input_path}")
        
        # Load model
        model = torch.load(str(input_path), map_location='cpu', weights_only=False)
        
        # Handle different save formats
        if isinstance(model, dict):
            # State dict - need model architecture
            return ConversionResult(
                success=False,
                output_path=None,
                original_format=ModelFormat.PYTORCH,
                error="PyTorch state_dict requires model architecture. Please save with torch.save(model, path) instead of torch.save(model.state_dict(), path)",
            )
        
        model.eval()
        
        # Try to infer input shape from model
        # Default to common shapes
        dummy_input = torch.randn(1, 3, 224, 224)  # Default image input
        
        # Try common input shapes
        input_shapes = [
            (1, 3, 224, 224),  # ImageNet
            (1, 3, 256, 256),
            (1, 1, 28, 28),   # MNIST
            (1, 10),          # Simple FC
            (1, 100),
        ]
        
        for shape in input_shapes:
            try:
                dummy_input = torch.randn(*shape)
                with torch.no_grad():
                    model(dummy_input)
                break
            except:
                continue
        
        # Export to ONNX
        torch.onnx.export(
            model,
            dummy_input,
            str(output_path),
            export_params=True,
            opset_version=opset,
            do_constant_folding=True,
            input_names=['input'],
            output_names=['output'],
            dynamic_axes={
                'input': {0: 'batch_size'},
                'output': {0: 'batch_size'},
            },
        )
        
        logger.info(f"PyTorch → ONNX conversion successful: {output_path}")
        return ConversionResult(
            success=True,
            output_path=output_path,
            original_format=ModelFormat.PYTORCH,
        )
        
    except ImportError as e:
        return ConversionResult(
            success=False,
            output_path=None,
            original_format=ModelFormat.PYTORCH,
            error=f"PyTorch not installed: {e}",
        )
    except Exception as e:
        logger.error(f"PyTorch conversion failed: {e}")
        return ConversionResult(
            success=False,
            output_path=None,
            original_format=ModelFormat.PYTORCH,
            error=str(e),
        )


def convert_to_onnx(input_path: Path, output_dir: Path, opset: int = 13) -> ConversionResult:
    """
    Convert any supported model format to ONNX.
    
    Args:
        input_path: Path to input model
        output_dir: Directory to save converted ONNX model
        opset: ONNX opset version
    
    Returns:
        ConversionResult with success status and output path
    """
    input_path = Path(input_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    format = detect_format(input_path)
    
    if format is None:
        return ConversionResult(
            success=False,
            output_path=None,
            original_format=None,
            error=f"Unsupported file format: {input_path.suffix}",
        )
    
    # Already ONNX - just copy
    if format == ModelFormat.ONNX:
        output_path = output_dir / input_path.name
        if input_path != output_path:
            shutil.copy(input_path, output_path)
        return ConversionResult(
            success=True,
            output_path=output_path,
            original_format=ModelFormat.ONNX,
        )
    
    # Output path
    output_path = output_dir / f"{input_path.stem}.onnx"
    
    # Convert based on format
    if format == ModelFormat.KERAS_H5:
        return convert_keras_to_onnx(input_path, output_path, opset)
    
    elif format == ModelFormat.TF_PB:
        return convert_tf_pb_to_onnx(input_path, output_path, opset)
    
    elif format in (ModelFormat.PYTORCH, ModelFormat.PYTORCH_PTH):
        return convert_pytorch_to_onnx(input_path, output_path, opset)
    
    else:
        return ConversionResult(
            success=False,
            output_path=None,
            original_format=format,
            error=f"No converter implemented for {format}",
        )


# Supported extensions
SUPPORTED_EXTENSIONS = {'.onnx', '.h5', '.keras', '.pb', '.pt', '.pth'}

def is_supported_format(file_path: Path) -> bool:
    """Check if file format is supported."""
    return file_path.suffix.lower() in SUPPORTED_EXTENSIONS
