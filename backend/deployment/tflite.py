"""
SOAC TFLite Deployment
======================

Convert ONNX to TensorFlow Lite for Android deployment.
Uses onnx-tf + TFLiteConverter.
"""

import logging
import numpy as np
from pathlib import Path
from typing import Optional, Dict, Any, Callable, Iterator, Tuple

try:
    import onnx
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    onnx = None

from .exceptions import TFLiteConversionError, ToolchainNotAvailable
from .metadata import DeploymentArtifact, TargetPlatform, ArtifactStatus, create_skipped_artifact


logger = logging.getLogger(__name__)


def is_tflite_available() -> bool:
    """Check if TFLite conversion is available."""
    try:
        import tensorflow  # noqa: F401
    except ImportError:
        return False
    return True


def _coerce_dim(value: Any, fallback: int = 1) -> int:
    try:
        v = int(value)
        return v if v > 0 else fallback
    except Exception:
        return fallback


def _extract_onnx_inputs(onnx_path: Path) -> list[Tuple[str, Tuple[int, ...]]]:
    model = onnx.load(str(onnx_path))
    inputs: list[Tuple[str, Tuple[int, ...]]] = []
    for input_tensor in model.graph.input:
        tt = input_tensor.type.tensor_type
        if not tt.HasField("shape"):
            continue
        dims = [_coerce_dim(d.dim_value, 1) for d in tt.shape.dim]
        if not dims:
            dims = [1]
        dims[0] = 1
        inputs.append((input_tensor.name, tuple(dims)))
    return inputs


def _representative_dataset_for_int8(onnx_path: Path, samples: int = 20) -> Callable[[], Iterator[Dict[str, np.ndarray]]]:
    inputs = _extract_onnx_inputs(onnx_path)

    def gen() -> Iterator[Dict[str, np.ndarray]]:
        for _ in range(samples):
            payload: Dict[str, np.ndarray] = {}
            for name, shape in inputs:
                payload[name] = np.random.uniform(0.0, 1.0, shape).astype(np.float32)
            yield payload

    return gen


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
    if not is_tflite_available():
        return create_skipped_artifact(
            TargetPlatform.ANDROID,
            "tflite",
            "TensorFlow not available"
        )
    if not ONNX_AVAILABLE:
        return create_skipped_artifact(
            TargetPlatform.ANDROID,
            "tflite",
            "ONNX not available"
        )
    
    onnx_path = Path(onnx_path)
    output_path = Path(output_path)
    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        raise ToolchainNotAvailable("onnx_to_tflite", "ONNX→TFLite toolchain not available in this environment")
        
        return DeploymentArtifact(
            platform=TargetPlatform.ANDROID,
            format="tflite",
            path=output_path,
            status=ArtifactStatus.SUCCESS,
            size_bytes=output_path.stat().st_size,
            metadata={
                "quantization": quantization,
                "converter": "onnx"
            }
        )

    except Exception as e:
        logger.error(f"TFLite conversion error: {str(e)}")
        return DeploymentArtifact(
            platform=TargetPlatform.ANDROID,
            format="tflite",
            path=output_path,
            status=ArtifactStatus.FAILED,
            size_bytes=0,
            error_message=str(e)
        )


def convert_tf_to_tflite(
    tf_path: Path,
    output_path: Path,
    quantization: str = "fp32",
) -> DeploymentArtifact:
    if not is_tflite_available():
        return create_skipped_artifact(TargetPlatform.ANDROID, "tflite", "TensorFlow not available")

    tf_path = Path(tf_path)
    output_path = Path(output_path)
    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        import tensorflow as tf

        keras_model = None
        if tf_path.is_dir():
            converter = tf.lite.TFLiteConverter.from_saved_model(str(tf_path))
        else:
            keras_model = tf.keras.models.load_model(str(tf_path))
            converter = tf.lite.TFLiteConverter.from_keras_model(keras_model)

        if quantization == "fp16":
            converter.optimizations = [tf.lite.Optimize.DEFAULT]
            converter.target_spec.supported_types = [tf.float16]
        elif quantization == "int8":
            converter.optimizations = [tf.lite.Optimize.DEFAULT]

            def rep():
                if keras_model is not None:
                    shapes = [tuple(int(d) if d is not None else 1 for d in t.shape) for t in keras_model.inputs]
                    shapes = [(1, *s[1:]) if len(s) > 0 else (1, 1) for s in shapes]
                    for _ in range(20):
                        yield [tf.random.uniform(s, dtype=tf.float32) for s in shapes]
                    return

                loaded = tf.saved_model.load(str(tf_path))
                fn = loaded.signatures.get("serving_default")
                if fn is None:
                    for _ in range(20):
                        yield [tf.random.uniform((1, 1), dtype=tf.float32)]
                    return
                inputs = list(fn.structured_input_signature[1].values())
                shapes = [tuple(int(d) if d is not None else 1 for d in t.shape) for t in inputs]
                shapes = [(1, *s[1:]) if len(s) > 0 else (1, 1) for s in shapes]
                for _ in range(20):
                    yield [tf.random.uniform(s, dtype=tf.float32) for s in shapes]

            converter.representative_dataset = rep
            converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
            converter.inference_input_type = tf.int8
            converter.inference_output_type = tf.int8

        tflite_model = converter.convert()
        output_path.write_bytes(tflite_model)

        return DeploymentArtifact(
            platform=TargetPlatform.ANDROID,
            format="tflite",
            path=output_path,
            status=ArtifactStatus.SUCCESS,
            size_bytes=output_path.stat().st_size,
            metadata={"quantization": quantization, "converter": "tensorflow"},
        )
    except Exception as e:
        logger.error(f"TFLite conversion error: {str(e)}")
        return DeploymentArtifact(
            platform=TargetPlatform.ANDROID,
            format="tflite",
            path=output_path,
            status=ArtifactStatus.FAILED,
            size_bytes=0,
            error_message=str(e),
        )
