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
import os
from pathlib import Path
from typing import Optional, Tuple
from enum import Enum
import subprocess
import sys

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
    ".hdf5": InputFormat.KERAS_H5,
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


def convert_keras_to_onnx(input_path: Path) -> "onnx.ModelProto":
    """
    Convert Keras .h5 or .keras model to ONNX.
    
    Uses tf2onnx for conversion.
    
    Args:
        input_path: Path to Keras model file.
    
    Returns:
        Converted ONNX model.
    """
    os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "2")
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
        def run_tf2onnx_cli(args: list[str]) -> Path:
            wrapper_path = Path(__file__).parent / "tf2onnx_wrapper.py"
            out_path = Path(tempfile.mkdtemp(prefix="soac_tf2onnx_out_")) / "model.onnx"
            cmd = [sys.executable, str(wrapper_path), *args, "--output", str(out_path)]
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if result.returncode != 0 or not out_path.exists():
                err = (result.stderr or result.stdout or "").strip()
                raise ConversionError("keras", "onnx", err[:1200] if err else "tf2onnx CLI failed")
            return out_path

        def normalize_model_for_export(m):
            try:
                inputs = []
                for inp in m.inputs:
                    ts = tf.TensorShape(inp.shape)
                    if ts.rank is None:
                        shape = ()
                    else:
                        shape = tuple(None if d is None else int(d) for d in ts.as_list()[1:])
                    name = (inp.name or "input").split(":")[0]
                    inputs.append(tf.keras.Input(shape=shape, dtype=inp.dtype, name=name))
                outputs = m(inputs, training=False) if len(inputs) > 1 else m(inputs[0], training=False)
                rebuilt = tf.keras.Model(inputs=inputs, outputs=outputs)
                rebuilt.set_weights(m.get_weights())
                return rebuilt
            except Exception:
                return m

        def build_input_signature(m):
            sig = []
            for inp in m.inputs:
                dims = []
                for i, d in enumerate(tf.TensorShape(inp.shape).as_list()):
                    if d is None:
                        dims.append(None if i == 0 else 1)
                    else:
                        dims.append(int(d))
                sig.append(tf.TensorSpec(dims, inp.dtype, name=inp.name))
            return sig
        
        def convert_via_frozen_graph_def(m):
            input_signature = build_input_signature(m)

            @tf.function(input_signature=input_signature)
            def serving_fn(*args):
                if len(args) == 1:
                    return m(args[0], training=False)
                return m(list(args), training=False)

            concrete = serving_fn.get_concrete_function()
            from tensorflow.python.framework.convert_to_constants import convert_variables_to_constants_v2

            frozen = convert_variables_to_constants_v2(concrete)
            graph_def = frozen.graph.as_graph_def(add_shapes=True)
            input_names = [t.name for t in frozen.inputs if t.dtype != tf.dtypes.resource]
            output_names = [t.name for t in frozen.outputs if t.dtype != tf.dtypes.resource]

            onnx_model, _ = tf2onnx.convert.from_graph_def(
                graph_def,
                input_names=input_names,
                output_names=output_names,
                opset=13,
                output_path=None,
            )
            return onnx_model

        def convert_via_tf_function(m, input_signature):
            def call(*args):
                if len(args) == 1:
                    return m(args[0], training=False)
                return m(list(args), training=False)

            fn = tf.function(call)
            onnx_model, _ = tf2onnx.convert.from_function(
                fn,
                input_signature=input_signature,
                opset=13,
                output_path=None,
            )
            return onnx_model

        def has_rnn_layers(m) -> bool:
            try:
                stack = [m]
                seen = set()
                while stack:
                    cur = stack.pop()
                    cur_id = id(cur)
                    if cur_id in seen:
                        continue
                    seen.add(cur_id)
                    layers = getattr(cur, "layers", []) or []
                    for layer in layers:
                        name = layer.__class__.__name__.lower()
                        if "lstm" in name or "gru" in name or "rnn" in name:
                            return True
                        if hasattr(layer, "layers"):
                            stack.append(layer)
                return False
            except Exception:
                return False

        def can_unroll_rnn(m) -> bool:
            try:
                for inp in m.inputs:
                    ts = tf.TensorShape(inp.shape)
                    dims = ts.as_list()
                    if not dims or len(dims) < 3:
                        continue
                    if dims[1] is None:
                        return False
                return True
            except Exception:
                return False

        def try_make_unrolled_model(m):
            try:
                try:
                    import keras as _keras
                    clone_model = _keras.models.clone_model
                    base_layer = _keras.layers.Layer
                except Exception:
                    clone_model = tf.keras.models.clone_model
                    base_layer = tf.keras.layers.Layer

                def clone_fn(layer: base_layer):
                    cfg = layer.get_config()
                    lname = layer.__class__.__name__.lower()
                    if "lstm" in lname or "gru" in lname or lname == "simplernn":
                        cfg["unroll"] = True
                        return layer.__class__.from_config(cfg)
                    if lname == "bidirectional":
                        for k in ("layer", "forward_layer", "backward_layer"):
                            sub = cfg.get(k)
                            if isinstance(sub, dict) and isinstance(sub.get("config"), dict):
                                if "unroll" in sub["config"]:
                                    sub["config"]["unroll"] = True
                        return layer.__class__.from_config(cfg)
                    if "unroll" in cfg:
                        cfg["unroll"] = True
                        return layer.__class__.from_config(cfg)
                    return layer.__class__.from_config(cfg)

                cloned = clone_model(m, clone_function=clone_fn)
                try:
                    cloned.set_weights(m.get_weights())
                except Exception:
                    return None
                return cloned
            except Exception:
                return None

        try:
            try:
                import keras
                if hasattr(keras, "saving") and hasattr(keras.saving, "load_model"):
                    model = keras.saving.load_model(str(input_path), compile=False, safe_mode=False)
                else:
                    model = keras.models.load_model(str(input_path), compile=False)
            except Exception:
                model = tf.keras.models.load_model(str(input_path), compile=False)

            model = normalize_model_for_export(model)
            prefer_frozen = has_rnn_layers(model)
            if prefer_frozen and can_unroll_rnn(model):
                unrolled = try_make_unrolled_model(model)
                if unrolled is not None:
                    try:
                        return convert_via_frozen_graph_def(unrolled)
                    except Exception:
                        pass
            if prefer_frozen:
                try:
                    return convert_via_frozen_graph_def(model)
                except Exception:
                    pass
            input_signature = build_input_signature(model)
            onnx_model, _ = tf2onnx.convert.from_keras(
                model,
                input_signature=input_signature,
                opset=13,
                output_path=None,
            )
            return onnx_model
        except Exception:
            try:
                if model is not None and has_rnn_layers(model) and can_unroll_rnn(model):
                    unrolled = try_make_unrolled_model(model)
                    if unrolled is not None:
                        return convert_via_frozen_graph_def(unrolled)
            except Exception:
                pass
            try:
                return convert_via_frozen_graph_def(model)
            except Exception:
                pass
            try:
                out_path = run_tf2onnx_cli(["--keras", str(input_path), "--opset", "13"])
                return onnx.load(str(out_path), load_external_data=False)
            except Exception:
                pass
            try:
                try:
                    import keras
                    if hasattr(keras, "saving") and hasattr(keras.saving, "load_model"):
                        sm_model = keras.saving.load_model(str(input_path), compile=False, safe_mode=False)
                    else:
                        sm_model = keras.models.load_model(str(input_path), compile=False)
                except Exception:
                    sm_model = tf.keras.models.load_model(str(input_path), compile=False)

                savedmodel_dir = Path(tempfile.mkdtemp(prefix="soac_savedmodel_export_"))
                try:
                    if hasattr(sm_model, "export"):
                        sm_model.export(str(savedmodel_dir))
                    else:
                        input_signature = build_input_signature(sm_model)

                        @tf.function(input_signature=input_signature)
                        def serving_fn(*args):
                            if len(args) == 1:
                                return sm_model(args[0], training=False)
                            return sm_model(list(args), training=False)

                        tf.saved_model.save(
                            sm_model,
                            str(savedmodel_dir),
                            signatures={"serving_default": serving_fn.get_concrete_function()},
                        )

                    out_path = run_tf2onnx_cli(["--saved-model", str(savedmodel_dir), "--opset", "13"])
                    return onnx.load(str(out_path), load_external_data=False)
                finally:
                    shutil.rmtree(savedmodel_dir, ignore_errors=True)
            except Exception:
                pass
            try:
                import keras

                if hasattr(keras, "saving") and hasattr(keras.saving, "load_model"):
                    kmodel = keras.saving.load_model(str(input_path), compile=False, safe_mode=False)
                else:
                    kmodel = keras.models.load_model(str(input_path), compile=False)
                try:
                    kmodel = normalize_model_for_export(kmodel)
                    input_signature = build_input_signature(kmodel)
                except Exception:
                    raise
                return convert_via_tf_function(kmodel, input_signature)
            except Exception:
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
        wrapper_path = Path(__file__).parent / "tf2onnx_wrapper.py"
        out_path = Path(tempfile.mkdtemp(prefix="soac_tf2onnx_out_")) / "model.onnx"
        cmd = [sys.executable, str(wrapper_path), "--saved-model", str(input_path), "--opset", "13", "--output", str(out_path)]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0 or not out_path.exists():
            err = (result.stderr or result.stdout or "").strip()
            raise ConversionError("savedmodel", "onnx", err[:1200] if err else "tf2onnx CLI failed")
        return onnx.load(str(out_path), load_external_data=False)
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
        from tf2onnx.convert import _convert_common
    except ImportError as e:
        raise ConversionError(
            "tflite", "onnx",
            f"tf2onnx not installed: {e}"
        )
    
    logger.info(f"Converting TFLite model: {input_path}")
    
    try:
        wrapper_path = Path(__file__).parent / "tf2onnx_wrapper.py"
        out_path = Path(tempfile.mkdtemp(prefix="soac_tf2onnx_out_")) / "model.onnx"
        cmd = [sys.executable, str(wrapper_path), "--tflite", str(input_path), "--opset", "13", "--output", str(out_path)]
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0 or not out_path.exists():
            err = (result.stderr or result.stdout or "").strip()
            raise ConversionError("tflite", "onnx", err[:1200] if err else "tf2onnx CLI failed")
        return onnx.load(str(out_path), load_external_data=False)
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
    else:
        raise UnsupportedFormatError(str(input_path), format.value)
    
    return model, format


def get_supported_formats() -> list[str]:
    """Get list of supported file extensions."""
    return list(EXTENSION_FORMAT_MAP.keys()) + ["directory (SavedModel)"]
