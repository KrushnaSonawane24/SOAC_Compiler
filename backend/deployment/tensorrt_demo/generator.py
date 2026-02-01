"""
SOAC TensorRT Demo Generator
============================

Generates TensorRT PC demo with conditional GPU support.

BEHAVIOR:
    GPU Available:    Generate engine + Python demo
    GPU Unavailable:  Generate stub + README explaining requirements

NO SILENT SKIPPING - unavailability is always explicit.
"""

import logging
import shutil
import zipfile
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional

from . import templates
from ..tensorrt import is_tensorrt_available, build_tensorrt_engine
from ..metadata import TargetPlatform, ArtifactStatus

logger = logging.getLogger(__name__)


def generate_tensorrt_demo(
    onnx_path: Path,
    output_dir: Path,
    model_name: str = "model",
    precision: str = "fp16",
    input_shape: Tuple[int, ...] = (1, 3, 224, 224),
    output_shape: Tuple[int, ...] = (1, 1000),
) -> Dict[str, Any]:
    """
    Generate TensorRT PC demo (conditionally).
    
    Args:
        onnx_path: Path to ONNX model file.
        output_dir: Directory to create demo in.
        model_name: Name of the model (for README).
        precision: Precision mode (fp16, int8).
        input_shape: Model input shape.
        output_shape: Model output shape.
    
    Returns:
        Dict with:
            - 'success': bool
            - 'available': bool (whether TensorRT was available)
            - 'path': str (demo directory path)
            - 'zip_path': str (zip archive path)
            - 'error': str or None
            - 'reason': str (explanation)
    """
    onnx_path = Path(onnx_path)
    output_dir = Path(output_dir)
    demo_dir = output_dir / "tensorrt_demo"
    
    # Check availability
    trt_available = is_tensorrt_available()
    
    if trt_available:
        return _generate_full_demo(
            onnx_path, demo_dir, output_dir,
            model_name, precision, input_shape, output_shape
        )
    else:
        return _generate_stub(demo_dir, output_dir)


def _generate_full_demo(
    onnx_path: Path,
    demo_dir: Path,
    output_dir: Path,
    model_name: str,
    precision: str,
    input_shape: Tuple[int, ...],
    output_shape: Tuple[int, ...],
) -> Dict[str, Any]:
    """Generate full demo when TensorRT is available."""
    try:
        demo_dir.mkdir(parents=True, exist_ok=True)
        
        # Build TensorRT engine
        engine_path = demo_dir / "model.plan"
        result = build_tensorrt_engine(
            onnx_path=onnx_path,
            output_path=engine_path,
            precision=precision,
        )
        
        if result.status != ArtifactStatus.SUCCESS:
            # Fall back to stub if engine build fails
            logger.warning(f"TensorRT engine build failed: {result.error_message}")
            shutil.rmtree(demo_dir, ignore_errors=True)
            return _generate_stub(demo_dir, output_dir, f"Engine build failed: {result.error_message}")
        
        # Generate inference script
        inference_script = templates.RUN_INFERENCE_PY.format(
            input_shape=input_shape,
            output_shape=output_shape,
        )
        (demo_dir / "run_inference.py").write_text(inference_script, encoding="utf-8")
        
        # Generate requirements
        (demo_dir / "requirements.txt").write_text(
            templates.REQUIREMENTS_TXT, encoding="utf-8"
        )
        
        # Generate README
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        model_size_mb = engine_path.stat().st_size / (1024 * 1024)
        readme = templates.README_AVAILABLE_MD.format(
            model_name=model_name,
            precision=precision,
            model_size_mb=model_size_mb,
            timestamp=timestamp,
        )
        (demo_dir / "README.md").write_text(readme, encoding="utf-8")
        
        # Create zip
        zip_path = _create_zip(demo_dir, output_dir)
        
        logger.info(f"TensorRT demo generated: {demo_dir}")
        
        return {
            "success": True,
            "available": True,
            "path": str(demo_dir),
            "zip_path": str(zip_path),
            "error": None,
            "reason": "TensorRT engine and demo generated successfully",
        }
        
    except Exception as e:
        logger.error(f"Failed to generate TensorRT demo: {e}")
        return {
            "success": False,
            "available": True,
            "path": None,
            "zip_path": None,
            "error": str(e),
            "reason": f"Generation failed: {e}",
        }


def _generate_stub(
    demo_dir: Path,
    output_dir: Path,
    additional_reason: Optional[str] = None,
) -> Dict[str, Any]:
    """Generate stub when TensorRT is not available."""
    try:
        demo_dir.mkdir(parents=True, exist_ok=True)
        
        # Write unavailable explanation
        (demo_dir / "UNAVAILABLE.md").write_text(
            templates.UNAVAILABLE_MD, encoding="utf-8"
        )
        
        # Write setup guide
        (demo_dir / "SETUP_GUIDE.md").write_text(
            templates.SETUP_GUIDE_MD, encoding="utf-8"
        )
        
        # Write requirements (for when they do set up GPU)
        (demo_dir / "requirements.txt").write_text(
            templates.REQUIREMENTS_TXT, encoding="utf-8"
        )
        
        # Create zip
        zip_path = _create_zip(demo_dir, output_dir, "tensorrt_demo_stub.zip")
        
        reason = "TensorRT/NVIDIA GPU not available on build machine"
        if additional_reason:
            reason = f"{reason}. {additional_reason}"
        
        logger.info(f"TensorRT stub generated: {demo_dir} (reason: {reason})")
        
        return {
            "success": True,  # Stub generation succeeded
            "available": False,  # But TensorRT wasn't available
            "path": str(demo_dir),
            "zip_path": str(zip_path),
            "error": None,
            "reason": reason,
        }
        
    except Exception as e:
        logger.error(f"Failed to generate TensorRT stub: {e}")
        return {
            "success": False,
            "available": False,
            "path": None,
            "zip_path": None,
            "error": str(e),
            "reason": f"Stub generation failed: {e}",
        }


def _create_zip(
    demo_dir: Path,
    output_dir: Path,
    zip_name: str = "tensorrt_demo.zip",
) -> Path:
    """Create zip archive."""
    zip_path = output_dir / zip_name
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        for file_path in demo_dir.rglob("*"):
            if file_path.is_file():
                arcname = file_path.relative_to(demo_dir.parent)
                zf.write(file_path, arcname)
    
    logger.info(f"Created zip: {zip_path} ({zip_path.stat().st_size / 1024:.1f} KB)")
    
    return zip_path
