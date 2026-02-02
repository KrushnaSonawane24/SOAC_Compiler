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
from dataclasses import replace

from .metadata import (
    DeploymentBundle,
    DeploymentArtifact,
    TargetPlatform,
    ArtifactStatus,
    create_timestamp,
    create_skipped_artifact,
    create_failed_artifact,
)
from .tflite import convert_onnx_to_tflite, convert_tf_to_tflite, is_tflite_available
from .onnxruntime_pkg import create_onnxruntime_package, is_onnxruntime_available
from .tensorrt import build_tensorrt_engine, is_tensorrt_available
from .coreml import convert_onnx_to_coreml, is_coreml_available
from .benchmarking import benchmark_tflite, benchmark_tensorrt
from .exceptions import PackagingError
import shutil


logger = logging.getLogger(__name__)


def _generate_android_artifact(
    source_path: Path,
    output_dir: Path,
    policy: str = "balanced",
    original_input_path: Optional[Path] = None,
) -> DeploymentArtifact:
    """Generate best Android TFLite model."""
    if not is_tflite_available():
        return create_skipped_artifact(
            TargetPlatform.ANDROID,
            "tflite",
            "TFLite not available"
        )
        
    output_dir = output_dir / "android"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    candidates = []
    
    quantization_order = ["int8", "fp16", "fp32"]
    if policy == "accuracy_first":
        quantization_order = ["fp32", "fp16", "int8"]
    elif policy == "mobile_first":
        quantization_order = ["int8", "fp16", "fp32"]
    elif policy == "latency_first":
        quantization_order = ["int8", "fp16", "fp32"]

    for q in quantization_order:
        try:
            out_path = output_dir / f"model_{q}.tflite"
            if original_input_path is not None and (original_input_path.is_dir() or original_input_path.suffix.lower() in [".h5", ".keras"]):
                artifact = convert_tf_to_tflite(original_input_path, out_path, quantization=q)
            else:
                artifact = convert_onnx_to_tflite(source_path, out_path, quantization=q)
            
            if artifact.status == ArtifactStatus.SUCCESS:
                # Benchmark
                lat, fps = benchmark_tflite(artifact.path)
                candidates.append((artifact, lat, fps, q))
                logger.info(f"Generated TFLite {q}: {lat:.2f}ms, {fps:.2f}fps")
            else:
                logger.warning(f"TFLite {q} generation failed: {artifact.error_message}")
                
        except Exception as e:
            logger.warning(f"Failed to generate TFLite {q}: {e}")
            
    if not candidates:
        return DeploymentArtifact(
            platform=TargetPlatform.ANDROID,
            format="tflite",
            path=None,
            size_bytes=0,
            status=ArtifactStatus.FAILED,
            error_message="All TFLite variants failed generation",
        )
        
    preference = {"fp32": 3, "fp16": 2, "int8": 1}
    if policy in ["balanced", "latency_first", "mobile_first"]:
        preference = {"int8": 3, "fp16": 2, "fp32": 1}

    def sort_key(c):
        _, lat, _, q = c
        pref = preference.get(q, 0)
        return (-pref, lat)
        
    candidates.sort(key=sort_key)
    best_artifact, best_lat, best_fps, best_q = candidates[0]
    
    # Rename best to standard 'model.tflite'
    final_path = output_dir / "model.tflite"
    if best_artifact.path != final_path:
        shutil.copy2(best_artifact.path, final_path)
        # We can delete the specific variant file to save space, or keep it.
        # Let's keep it for debugging but update artifact to point to final.
        best_artifact = replace(best_artifact, path=final_path)
        
    # Update metadata
    # Metadata is a dict, so it is mutable even if dataclass is frozen?
    # No, frozen dataclass fields are read-only. But if the field is a dict, the dict itself is mutable.
    # However, it's cleaner to use replace for metadata too if we want to be safe,
    # but since we are just updating the dict content, it *might* be allowed if the field is not frozen-recursive.
    # Let's check metadata definition. It's usually just Dict.
    if best_artifact.metadata is None: 
        # We need to replace it if it's None
        new_metadata = {}
    else:
        new_metadata = best_artifact.metadata.copy()
        
    new_metadata.update({
        "latency_ms": best_lat,
        "throughput_fps": best_fps,
        "selected_quantization": best_q,
        "all_variants": [c[3] for c in candidates]
    })
    
    best_artifact = replace(best_artifact, metadata=new_metadata)
    
    return best_artifact


def _generate_gpu_artifact(
    source_path: Path,
    output_dir: Path,
    policy: str = "balanced",
) -> DeploymentArtifact:
    """Generate best GPU TensorRT engine."""
    if not is_tensorrt_available():
        return create_skipped_artifact(
            TargetPlatform.GPU,
            "tensorrt_engine",
            "TensorRT not available"
        )
        
    output_dir = output_dir / "gpu"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    candidates = []
    
    precision_order = ["int8", "fp16"]
    if policy == "accuracy_first":
        precision_order = ["fp16", "int8"]

    for p in precision_order:
        try:
            out_path = output_dir / f"model_{p}.plan"
            artifact = build_tensorrt_engine(source_path, out_path, precision=p)
            
            if artifact.status == ArtifactStatus.SUCCESS:
                # Benchmark
                lat, fps = benchmark_tensorrt(artifact.path)
                candidates.append((artifact, lat, fps, p))
                logger.info(f"Generated TensorRT {p}: {lat:.2f}ms, {fps:.2f}fps")
            else:
                logger.warning(f"TensorRT {p} generation failed: {artifact.error_message}")
                
        except Exception as e:
            logger.warning(f"Failed to generate TensorRT {p}: {e}")
            
    if not candidates:
        return DeploymentArtifact(
            platform=TargetPlatform.GPU,
            format="tensorrt_engine",
            path=None,
            size_bytes=0,
            status=ArtifactStatus.FAILED,
            error_message="All TensorRT variants failed generation",
        )
        
    preference = {"fp16": 2, "int8": 1}
    if policy in ["balanced", "latency_first", "mobile_first"]:
        preference = {"int8": 2, "fp16": 1}

    def sort_key(c):
        _, lat, _, p = c
        pref = preference.get(p, 0)
        return (-pref, lat)
        
    candidates.sort(key=sort_key)
    best_artifact, best_lat, best_fps, best_p = candidates[0]
    
    # Rename best to standard 'model.plan'
    final_path = output_dir / "model.plan"
    if best_artifact.path != final_path:
        shutil.copy2(best_artifact.path, final_path)
        best_artifact = replace(best_artifact, path=final_path)
        
    # Update metadata
    if best_artifact.metadata is None: 
        new_metadata = {}
    else:
        new_metadata = best_artifact.metadata.copy()
        
    new_metadata.update({
        "latency_ms": best_lat,
        "throughput_fps": best_fps,
        "selected_precision": best_p,
        "all_variants": [c[3] for c in candidates]
    })
    
    best_artifact = replace(best_artifact, metadata=new_metadata)
    
    return best_artifact


def generate_deployment_artifacts(
    onnx_path: Path,
    variant_id: str,
    source_hash: str,
    output_dir: Optional[Path] = None,
    targets: Optional[list] = None,
    canonical_path: Optional[Path] = None,
    policy: str = "balanced",
    original_input_path: Optional[Path] = None,
) -> DeploymentBundle:
    """
    Generate all deployment artifacts from an ONNX model.
    
    Args:
        onnx_path: Path to source ONNX model (selected variant).
        variant_id: ID of the source variant.
        source_hash: Hash of the source model.
        output_dir: Directory for artifacts (defaults to temp).
        targets: List of target platforms (defaults to all).
        canonical_path: Path to canonical (unoptimized) ONNX model.
                       Used for generating fresh optimizations for TFLite/TRT.
    
    Returns:
        DeploymentBundle with all generated artifacts.
    
    NOTE: Missing toolchains are handled gracefully with SKIPPED status.
    """
    onnx_path = Path(onnx_path)
    # Use canonical path for fresh conversions if available, else use the selected variant path
    conversion_source = Path(canonical_path) if canonical_path and Path(canonical_path).exists() else onnx_path
    
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
            TargetPlatform.ONNX,
        ]
    
    logger.info(f"Generating deployment artifacts for: {variant_id}")
    logger.info(f"Source for conversion: {conversion_source}")
    logger.info(f"Output directory: {output_dir}")
    
    artifacts: Dict[TargetPlatform, DeploymentArtifact] = {}
    
    def _generate_onnx_artifact() -> DeploymentArtifact:
        onnx_dir = output_dir / "onnx"
        onnx_dir.mkdir(parents=True, exist_ok=True)
        out_path = onnx_dir / "model.onnx"
        shutil.copy2(onnx_path, out_path)
        return DeploymentArtifact(
            platform=TargetPlatform.ONNX,
            format="onnx",
            path=out_path,
            size_bytes=out_path.stat().st_size,
            status=ArtifactStatus.SUCCESS,
            metadata={"source_variant_id": variant_id},
        )

    # Generate each target
    for target in targets:
        try:
            if target == TargetPlatform.ANDROID:
                # Use our smart generator
                artifact = _generate_android_artifact(
                    conversion_source,
                    output_dir,
                    policy=policy,
                    original_input_path=original_input_path,
                )
            elif target == TargetPlatform.IOS:
                artifact = convert_onnx_to_coreml(
                    conversion_source,
                    output_dir / "ios" / "model.mlmodel",
                )
            elif target == TargetPlatform.CPU:
                # CPU usually just uses the ONNX Runtime package with the optimized ONNX
                # So we use onnx_path (the selected variant) here, not canonical
                artifact = create_onnxruntime_package(
                    onnx_path,
                    output_dir / "cpu",
                    model_name=variant_id.split("_")[0],
                )
            elif target == TargetPlatform.GPU:
                # Use our smart generator
                artifact = _generate_gpu_artifact(conversion_source, output_dir, policy=policy)
            elif target == TargetPlatform.ONNX:
                artifact = _generate_onnx_artifact()
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
                "metadata": a.metadata
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
        "onnx": True,
    }
