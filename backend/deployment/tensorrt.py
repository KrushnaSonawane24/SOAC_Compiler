"""
SOAC TensorRT Deployment
========================

Build TensorRT engine for GPU deployment.

NOTE: Skips gracefully if TensorRT not available.
"""

import logging
from pathlib import Path
from typing import Optional

try:
    import tensorrt as trt
    TENSORRT_AVAILABLE = True
except ImportError:
    TENSORRT_AVAILABLE = False
    trt = None

from .exceptions import TensorRTConversionError
from .metadata import DeploymentArtifact, TargetPlatform, ArtifactStatus, create_skipped_artifact


logger = logging.getLogger(__name__)


def is_tensorrt_available() -> bool:
    """Check if TensorRT is available."""
    return TENSORRT_AVAILABLE


def build_tensorrt_engine(
    onnx_path: Path,
    output_path: Path,
    precision: str = "fp16",
    max_batch_size: int = 1,
) -> DeploymentArtifact:
    """
    Build TensorRT engine from ONNX model.
    
    Args:
        onnx_path: Path to source ONNX model.
        output_path: Path to save TensorRT engine.
        precision: Precision mode (fp32, fp16, int8).
        max_batch_size: Maximum batch size.
    
    Returns:
        DeploymentArtifact with result.
    
    NOTE: Skips gracefully if TensorRT not available.
    """
    if not TENSORRT_AVAILABLE:
        logger.info("TensorRT not available, skipping GPU deployment")
        return create_skipped_artifact(
            TargetPlatform.GPU,
            "plan",
            "TensorRT not available"
        )
    
    onnx_path = Path(onnx_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Building TensorRT engine: {onnx_path}")
    
    try:
        # Create builder
        TRT_LOGGER = trt.Logger(trt.Logger.WARNING)
        builder = trt.Builder(TRT_LOGGER)
        
        # Create network
        network_flags = 1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH)
        network = builder.create_network(network_flags)
        
        # Parse ONNX
        parser = trt.OnnxParser(network, TRT_LOGGER)
        
        with open(onnx_path, 'rb') as f:
            if not parser.parse(f.read()):
                errors = []
                for i in range(parser.num_errors):
                    errors.append(parser.get_error(i).desc())
                raise TensorRTConversionError(f"ONNX parsing failed: {errors}")
        
        # Configure builder
        config = builder.create_builder_config()
        config.max_workspace_size = 1 << 30  # 1GB
        
        if precision == "fp16":
            if builder.platform_has_fast_fp16:
                config.set_flag(trt.BuilderFlag.FP16)
        elif precision == "int8":
            if builder.platform_has_fast_int8:
                config.set_flag(trt.BuilderFlag.INT8)
        
        # Build engine
        engine = builder.build_engine(network, config)
        
        if engine is None:
            raise TensorRTConversionError("Engine build failed")
        
        # Serialize
        serialized = engine.serialize()
        output_path.write_bytes(serialized)
        
        size_bytes = output_path.stat().st_size
        
        logger.info(f"TensorRT engine created: {output_path} ({size_bytes} bytes)")
        
        return DeploymentArtifact(
            platform=TargetPlatform.GPU,
            format="plan",
            path=output_path,
            size_bytes=size_bytes,
            status=ArtifactStatus.SUCCESS,
            metadata={
                "precision": precision,
                "max_batch_size": max_batch_size,
            },
        )
        
    except TensorRTConversionError:
        raise
    except Exception as e:
        logger.error(f"TensorRT build failed: {e}")
        return DeploymentArtifact(
            platform=TargetPlatform.GPU,
            format="plan",
            path=None,
            size_bytes=0,
            status=ArtifactStatus.FAILED,
            error_message=str(e),
        )
