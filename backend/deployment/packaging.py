"""
SOAC Deployment Packaging
=========================

Orchestrates deployment artifact generation.
"""

import logging
import json
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime, timezone
import tempfile

from .metadata import (
    DeploymentBundle,
    DeploymentArtifact,
    TargetPlatform,
    ArtifactStatus,
    create_timestamp,
)
from .tflite import convert_onnx_to_tflite, is_tflite_available
from .onnxruntime_pkg import create_onnxruntime_package, is_onnxruntime_available
from .tensorrt import build_tensorrt_engine, is_tensorrt_available
from .coreml import convert_onnx_to_coreml, is_coreml_available
from .exceptions import PackagingError


logger = logging.getLogger(__name__)


def generate_deployment_artifacts(
    onnx_path: Path,
    variant_id: str,
    source_hash: str,
    output_dir: Optional[Path] = None,
    targets: Optional[list] = None,
) -> DeploymentBundle:
    """
    Generate all deployment artifacts from an ONNX model.
    
    Args:
        onnx_path: Path to source ONNX model.
        variant_id: ID of the source variant.
        source_hash: Hash of the source model.
        output_dir: Directory for artifacts (defaults to temp).
        targets: List of target platforms (defaults to all).
    
    Returns:
        DeploymentBundle with all generated artifacts.
    
    NOTE: Missing toolchains are handled gracefully with SKIPPED status.
    """
    onnx_path = Path(onnx_path)
    
    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix="soac_deployment_"))
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    
    if targets is None:
        targets = [
            TargetPlatform.ANDROID,
            TargetPlatform.IOS,
            TargetPlatform.CPU,
            TargetPlatform.GPU,
        ]
    
    logger.info(f"Generating deployment artifacts for: {variant_id}")
    logger.info(f"Output directory: {output_dir}")
    
    artifacts: Dict[TargetPlatform, DeploymentArtifact] = {}
    
    # Generate each target
    for target in targets:
        try:
            if target == TargetPlatform.ANDROID:
                artifact = convert_onnx_to_tflite(
                    onnx_path,
                    output_dir / "android" / "model.tflite",
                )
            elif target == TargetPlatform.IOS:
                artifact = convert_onnx_to_coreml(
                    onnx_path,
                    output_dir / "ios" / "model.mlmodel",
                )
            elif target == TargetPlatform.CPU:
                artifact = create_onnxruntime_package(
                    onnx_path,
                    output_dir / "cpu",
                    model_name=variant_id.split("_")[0],
                )
            elif target == TargetPlatform.GPU:
                artifact = build_tensorrt_engine(
                    onnx_path,
                    output_dir / "gpu" / "model.plan",
                )
            else:
                continue
            
            artifacts[target] = artifact
            
            status_emoji = "✓" if artifact.is_valid else ("⊘" if artifact.status == ArtifactStatus.SKIPPED else "✗")
            logger.info(f"  {status_emoji} {target.value}: {artifact.status.value}")
            
        except Exception as e:
            logger.error(f"Failed to generate {target.value}: {e}")
            artifacts[target] = DeploymentArtifact(
                platform=target,
                format="unknown",
                path=None,
                size_bytes=0,
                status=ArtifactStatus.FAILED,
                error_message=str(e),
            )
    
    # Create manifest
    manifest = {
        "variant_id": variant_id,
        "source_hash": source_hash,
        "generated_at": create_timestamp(),
        "artifacts": {
            p.value: {
                "status": a.status.value,
                "path": str(a.path) if a.path else None,
                "format": a.format,
            }
            for p, a in artifacts.items()
        },
    }
    
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    bundle = DeploymentBundle(
        source_variant_id=variant_id,
        source_hash=source_hash,
        artifacts=artifacts,
        output_dir=output_dir,
        timestamp=create_timestamp(),
    )
    
    logger.info(f"Deployment complete: {bundle.successful_count} success, {bundle.skipped_count} skipped, {bundle.failed_count} failed")
    
    return bundle


def get_available_targets() -> Dict[str, bool]:
    """Get availability status of each deployment target."""
    return {
        "android": is_tflite_available(),
        "ios": is_coreml_available(),
        "cpu": is_onnxruntime_available(),
        "gpu": is_tensorrt_available(),
    }
