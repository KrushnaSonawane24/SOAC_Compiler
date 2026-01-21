"""
SOAC CoreML Deployment
======================

Convert ONNX to CoreML for iOS deployment.
"""

import logging
from pathlib import Path
from typing import Optional

try:
    import coremltools as ct
    COREML_AVAILABLE = True
except ImportError:
    COREML_AVAILABLE = False
    ct = None

try:
    import onnx
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False

from .exceptions import CoreMLConversionError
from .metadata import DeploymentArtifact, TargetPlatform, ArtifactStatus, create_skipped_artifact


logger = logging.getLogger(__name__)


def is_coreml_available() -> bool:
    """Check if CoreML conversion is available."""
    return COREML_AVAILABLE and ONNX_AVAILABLE


def convert_onnx_to_coreml(
    onnx_path: Path,
    output_path: Path,
    minimum_deployment_target: str = "iOS15",
) -> DeploymentArtifact:
    """
    Convert ONNX model to CoreML.
    
    Args:
        onnx_path: Path to source ONNX model.
        output_path: Path to save CoreML model.
        minimum_deployment_target: iOS version target.
    
    Returns:
        DeploymentArtifact with result.
    """
    if not COREML_AVAILABLE:
        logger.info("coremltools not available, skipping iOS deployment")
        return create_skipped_artifact(
            TargetPlatform.IOS,
            "mlmodel",
            "coremltools not available"
        )
    
    if not ONNX_AVAILABLE:
        return create_skipped_artifact(
            TargetPlatform.IOS,
            "mlmodel",
            "ONNX not available"
        )
    
    onnx_path = Path(onnx_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Converting to CoreML: {onnx_path}")
    
    try:
        # Load ONNX model
        onnx_model = onnx.load(str(onnx_path))
        
        # Convert to CoreML
        mlmodel = ct.convert(
            onnx_model,
            source="onnx",
            minimum_deployment_target=getattr(ct.target, minimum_deployment_target, ct.target.iOS15),
        )
        
        # Save
        mlmodel.save(str(output_path))
        
        # Verify output
        if not output_path.exists():
            raise CoreMLConversionError("Output file not created")
        
        # Get size (mlmodel can be package or file)
        if output_path.is_dir():
            size_bytes = sum(f.stat().st_size for f in output_path.rglob("*") if f.is_file())
        else:
            size_bytes = output_path.stat().st_size
        
        logger.info(f"CoreML model created: {output_path} ({size_bytes} bytes)")
        
        return DeploymentArtifact(
            platform=TargetPlatform.IOS,
            format="mlmodel",
            path=output_path,
            size_bytes=size_bytes,
            status=ArtifactStatus.SUCCESS,
            metadata={"deployment_target": minimum_deployment_target},
        )
        
    except CoreMLConversionError:
        raise
    except Exception as e:
        logger.error(f"CoreML conversion failed: {e}")
        return DeploymentArtifact(
            platform=TargetPlatform.IOS,
            format="mlmodel",
            path=None,
            size_bytes=0,
            status=ArtifactStatus.FAILED,
            error_message=str(e),
        )


def validate_coreml(mlmodel_path: Path) -> bool:
    """Validate CoreML model is loadable."""
    if not COREML_AVAILABLE:
        return False
    
    try:
        model = ct.models.MLModel(str(mlmodel_path))
        return model is not None
    except Exception:
        return False
