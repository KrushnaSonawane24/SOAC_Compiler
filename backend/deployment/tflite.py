"""
SOAC TFLite Deployment
======================

Convert ONNX to TensorFlow Lite for Android deployment.
Uses onnx2tf for robust conversion.
"""

import logging
import shutil
import subprocess
import sys
import numpy as np
from pathlib import Path
from typing import Optional, List, Dict, Any

try:
    import tensorflow as tf
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    tf = None

try:
    import onnx
    import onnx2tf
    ONNX2TF_AVAILABLE = True
except ImportError as e:
    logging.getLogger(__name__).warning(f"onnx2tf import failed: {e}")
    ONNX2TF_AVAILABLE = False
except Exception as e:
    logging.getLogger(__name__).warning(f"onnx2tf import error: {e}")
    ONNX2TF_AVAILABLE = False

from .exceptions import TFLiteConversionError, ToolchainNotAvailable
from .metadata import DeploymentArtifact, TargetPlatform, ArtifactStatus, create_skipped_artifact


logger = logging.getLogger(__name__)


def is_tflite_available() -> bool:
    """Check if TFLite conversion is available."""
    return TF_AVAILABLE and ONNX2TF_AVAILABLE


def _generate_calibration_data(onnx_path: Path, output_dir: Path, num_samples: int = 20) -> Optional[Dict[str, Path]]:
    """
    Generate dummy calibration data for INT8 quantization.
    
    Args:
        onnx_path: Path to ONNX model.
        output_dir: Directory to save .npy files.
        num_samples: Number of calibration samples.
        
    Returns:
        Dictionary mapping input name to calibration file path, or None if failed.
    """
    try:
        model = onnx.load(str(onnx_path))
        
        calib_dir = output_dir / "calibration_data"
        calib_dir.mkdir(parents=True, exist_ok=True)
        
        results = {}
        
        for input_tensor in model.graph.input:
            name = input_tensor.name
            
            # Get shape
            shape = []
            for dim in input_tensor.type.tensor_type.shape.dim:
                if dim.dim_value > 0:
                    shape.append(dim.dim_value)
                else:
                    shape.append(1) # Assume batch size 1 for dynamic dims
            
            # Heuristic for NCHW -> NHWC conversion (typical for ONNX -> TF)
            # ONNX is typically NCHW [N, C, H, W]
            # TF is typically NHWC [N, H, W, C]
            tf_shape = list(shape)
            if len(shape) == 4:
                # Assume NCHW -> NHWC: [0, 2, 3, 1]
                # But we are generating random data, so we just need target shape
                n, c, h, w = shape
                tf_shape = [n, h, w, c]
                
            # Generate data
            data_shape = [num_samples] + tf_shape[1:] # Use tf_shape (assuming batch 1)
            
            # Random uniform data 0.0 to 1.0 (assuming image-like or normalized)
            data = np.random.uniform(0.0, 1.0, data_shape).astype(np.float32)
            
            # Save as name.npy (sanitize name)
            safe_name = name.replace("/", "_").replace(":", "_")
            npy_path = calib_dir / f"{safe_name}.npy"
            np.save(npy_path, data)
            
            results[name] = npy_path
            
        return results

    except Exception as e:
        logger.warning(f"Failed to generate calibration data: {e}")
        return None


def convert_onnx_to_tflite(
    onnx_path: Path,
    output_path: Path,
    quantization: str = "fp32",
) -> DeploymentArtifact:
    """
    Convert ONNX model to TFLite using onnx2tf.
    
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
            "TensorFlow or onnx2tf not available"
        )
    
    onnx_path = Path(onnx_path)
    output_path = Path(output_path)
    output_dir = output_path.parent
    output_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Converting to TFLite: {onnx_path} (Quantization: {quantization})")
    
    try:
        # Prepare arguments for onnx2tf
        # We use subprocess to isolate it and capture output
        # Use our wrapper to patch onnx compatibility issues
        wrapper_path = Path(__file__).parent / "onnx2tf_wrapper.py"
        cmd = [
            sys.executable, str(wrapper_path),
            "-i", str(onnx_path),
            "-o", str(output_dir / "onnx2tf_temp"),
            "-osd" # Output simplified
        ]
        
        # Quantization flags
        if quantization == "fp16":
            cmd.extend(["-ois", "fp16"]) # Output float16
        elif quantization == "int8":
            # Generate calibration data
            calib_data = _generate_calibration_data(onnx_path, output_dir)
            if calib_data:
                cmd.extend(["-oiqt", "-qt", "per-tensor"]) # Quantize per-tensor (safer)
                
                # Add -cind arguments for each input
                # -cind {name} {path} {mean} {std}
                for name, path in calib_data.items():
                    cmd.extend(["-cind", name, str(path), "[0]", "[1]"])
            else:
                 logger.warning("Skipping INT8 quantization due to calibration data failure, falling back to FP32")
        
        # Run conversion
        logger.info(f"Running command: {cmd}") # Debug print
        print(f"DEBUG COMMAND: {cmd}") # Force print to stdout for tool capture

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False # We handle return code
        )
        
        if result.returncode != 0:
            logger.error(f"onnx2tf failed:\n{result.stderr}")
            raise TFLiteConversionError(f"onnx2tf conversion failed: {result.stderr[:500]}...")
            
        # Find the output file
        # onnx2tf outputs to output_folder / model_name.tflite
        # Or specified output?
        temp_out = output_dir / "onnx2tf_temp"
        # Search for .tflite files
        tflite_files = list(temp_out.glob("*.tflite"))
        if not tflite_files:
             raise TFLiteConversionError("onnx2tf did not produce a .tflite file")
             
        src_tflite = tflite_files[0]
        
        # Check size constraint (< 200MB)
        size_mb = src_tflite.stat().st_size / (1024 * 1024)
        if size_mb > 200:
             raise TFLiteConversionError(f"Model size {size_mb:.2f}MB exceeds 200MB limit")
        
        # Move to final location
        shutil.move(str(src_tflite), str(output_path))
        
        # Cleanup
        shutil.rmtree(temp_out, ignore_errors=True)
        if quantization == "int8" and 'calib_data' in locals() and calib_data:
            # Clean up calibration files
            first_path = next(iter(calib_data.values()))
            shutil.rmtree(first_path.parent, ignore_errors=True)
            
        return DeploymentArtifact(
            platform=TargetPlatform.ANDROID,
            format="tflite",
            path=output_path,
            status=ArtifactStatus.SUCCESS,
            size_bytes=output_path.stat().st_size,
            metadata={
                "quantization": quantization,
                "converter": "onnx2tf"
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
