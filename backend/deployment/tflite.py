"""
SOAC TFLite Deployment
======================

Convert ONNX to TensorFlow Lite for Android deployment.
"""

import logging
import shutil
from pathlib import Path
from typing import Optional

try:
    import tensorflow as tf
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    tf = None

try:
    import onnx
    from onnx_tf.backend import prepare as onnx_tf_prepare
    ONNX_TF_AVAILABLE = True
except ImportError:
    ONNX_TF_AVAILABLE = False

from .exceptions import TFLiteConversionError, ToolchainNotAvailable
from .metadata import DeploymentArtifact, TargetPlatform, ArtifactStatus, create_skipped_artifact


logger = logging.getLogger(__name__)


def is_tflite_available() -> bool:
    """Check if TFLite conversion is available."""
    return TF_AVAILABLE


def convert_onnx_to_tflite(
    onnx_path: Path,
    output_path: Path,
    quantization: str = "fp32",
) -> DeploymentArtifact:
    """
    Convert ONNX model to TFLite.
    
    Args:
        onnx_path: Path to source ONNX model.
        output_path: Path to save TFLite model.
        quantization: Quantization type (fp32, fp16, int8).
    
    Returns:
        DeploymentArtifact with result.
    """
    if not TF_AVAILABLE:
        return create_skipped_artifact(
            TargetPlatform.ANDROID,
            "tflite",
            "TensorFlow not available"
        )
    
    onnx_path = Path(onnx_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Converting to TFLite: {onnx_path}")
    
    try:
        # Method 1: Direct tf2onnx reverse (preferred)
        try:
            import tf2onnx
            from tf2onnx.tfonnx import process_tf_graph
            
            # Load ONNX and convert via TF
            import onnx
            onnx_model = onnx.load(str(onnx_path))
            
            # Use onnx-tf to convert to TF SavedModel
            if ONNX_TF_AVAILABLE:
                tf_rep = onnx_tf_prepare(onnx_model)
                savedmodel_dir = output_path.parent / "temp_savedmodel"
                tf_rep.export_graph(str(savedmodel_dir))
                
                # Convert SavedModel to TFLite
                converter = tf.lite.TFLiteConverter.from_saved_model(str(savedmodel_dir))
                
                # Apply quantization
                if quantization == "fp16":
                    converter.optimizations = [tf.lite.Optimize.DEFAULT]
                    converter.target_spec.supported_types = [tf.float16]
                elif quantization == "int8":
                    converter.optimizations = [tf.lite.Optimize.DEFAULT]
                
                tflite_model = converter.convert()
                
                # Save
                output_path.write_bytes(tflite_model)
                
                # Cleanup
                if savedmodel_dir.exists():
                    shutil.rmtree(savedmodel_dir)
            else:
                raise ImportError("onnx-tf not available")
            
        except Exception as e:
            logger.warning(f"Primary conversion failed: {e}, trying fallback")
            
            # Fallback: Create a placeholder valid TFLite
            # In production, this would use alternative conversion paths
            raise TFLiteConversionError(f"Conversion not supported: {e}")
        
        # Verify output
        if not output_path.exists():
            raise TFLiteConversionError("Output file not created")
        
        size_bytes = output_path.stat().st_size
        
        logger.info(f"TFLite created: {output_path} ({size_bytes} bytes)")
        
        return DeploymentArtifact(
            platform=TargetPlatform.ANDROID,
            format="tflite",
            path=output_path,
            size_bytes=size_bytes,
            status=ArtifactStatus.SUCCESS,
            metadata={"quantization": quantization},
        )
        
    except TFLiteConversionError:
        raise
    except Exception as e:
        logger.error(f"TFLite conversion failed: {e}")
        return DeploymentArtifact(
            platform=TargetPlatform.ANDROID,
            format="tflite",
            path=None,
            size_bytes=0,
            status=ArtifactStatus.FAILED,
            error_message=str(e),
        )


def validate_tflite(tflite_path: Path) -> bool:
    """Validate TFLite file is loadable."""
    if not TF_AVAILABLE:
        return False
    
    try:
        interpreter = tf.lite.Interpreter(model_path=str(tflite_path))
        interpreter.allocate_tensors()
        return True
    except Exception:
        return False
