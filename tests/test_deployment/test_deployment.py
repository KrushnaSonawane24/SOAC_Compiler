"""
Tests for Deployment Engine
============================

Tests for deployment artifact generation.
"""

import pytest
from pathlib import Path

from backend.deployment import (
    generate_deployment_artifacts,
    get_available_targets,
    DeploymentBundle,
    TargetPlatform,
    ArtifactStatus,
    is_tflite_available,
    is_onnxruntime_available,
    is_tensorrt_available,
    is_coreml_available,
    create_onnxruntime_package,
)


class TestAvailableTargets:
    """Tests for target availability detection."""
    
    def test_get_available_targets_returns_dict(self):
        """Available targets returns dict with all platforms."""
        targets = get_available_targets()
        
        assert isinstance(targets, dict)
        assert "android" in targets
        assert "ios" in targets
        assert "cpu" in targets
        assert "gpu" in targets
    
    def test_availability_functions_return_bool(self):
        """Each availability function returns boolean."""
        assert isinstance(is_tflite_available(), bool)
        assert isinstance(is_onnxruntime_available(), bool)
        assert isinstance(is_tensorrt_available(), bool)
        assert isinstance(is_coreml_available(), bool)


class TestDeploymentBundle:
    """Tests for DeploymentBundle structure."""
    
    def test_bundle_creation(self, simple_onnx_model, temp_dir):
        """Bundle is created successfully."""
        bundle = generate_deployment_artifacts(
            simple_onnx_model,
            variant_id="test_variant",
            source_hash="abc123",
            output_dir=temp_dir,
        )
        
        assert isinstance(bundle, DeploymentBundle)
        assert bundle.source_variant_id == "test_variant"
        assert bundle.source_hash == "abc123"
    
    def test_bundle_has_artifacts(self, simple_onnx_model, temp_dir):
        """Bundle contains artifacts for all targets."""
        bundle = generate_deployment_artifacts(
            simple_onnx_model,
            variant_id="test",
            source_hash="hash",
            output_dir=temp_dir,
        )
        
        assert len(bundle.artifacts) > 0
    
    def test_bundle_serializable(self, simple_onnx_model, temp_dir):
        """Bundle can be serialized to dict."""
        bundle = generate_deployment_artifacts(
            simple_onnx_model,
            variant_id="test",
            source_hash="hash",
            output_dir=temp_dir,
        )
        
        bundle_dict = bundle.to_dict()
        
        assert "source_variant_id" in bundle_dict
        assert "artifacts" in bundle_dict
        assert "summary" in bundle_dict


class TestONNXRuntimePackage:
    """Tests for ONNX Runtime package creation."""
    
    def test_package_created(self, simple_onnx_model, temp_dir):
        """ONNX Runtime package is created."""
        artifact = create_onnxruntime_package(
            simple_onnx_model,
            temp_dir,
            model_name="test_model",
        )
        
        assert artifact.status == ArtifactStatus.SUCCESS
        assert artifact.path is not None
        assert artifact.path.exists()
    
    def test_package_contains_required_files(self, simple_onnx_model, temp_dir):
        """Package contains model, metadata, and inference script."""
        artifact = create_onnxruntime_package(
            simple_onnx_model,
            temp_dir,
            model_name="test_model",
        )
        
        if artifact.is_valid:
            package_dir = artifact.path
            assert (package_dir / "model.onnx").exists()
            assert (package_dir / "metadata.json").exists()
            assert (package_dir / "inference.py").exists()


class TestGracefulSkipping:
    """Tests for graceful handling of unavailable toolchains."""
    
    def test_tensorrt_skipped_when_unavailable(self, simple_onnx_model, temp_dir):
        """TensorRT is skipped gracefully when unavailable."""
        bundle = generate_deployment_artifacts(
            simple_onnx_model,
            variant_id="test",
            source_hash="hash",
            output_dir=temp_dir,
            targets=[TargetPlatform.GPU],
        )
        
        gpu_artifact = bundle.get_artifact(TargetPlatform.GPU)
        
        if not is_tensorrt_available():
            assert gpu_artifact.status == ArtifactStatus.SKIPPED
            assert "not available" in gpu_artifact.error_message.lower()
    
    def test_no_silent_failures(self, simple_onnx_model, temp_dir):
        """All artifacts have explicit status - no silent failures."""
        bundle = generate_deployment_artifacts(
            simple_onnx_model,
            variant_id="test",
            source_hash="hash",
            output_dir=temp_dir,
        )
        
        for platform, artifact in bundle.artifacts.items():
            assert artifact.status in [
                ArtifactStatus.SUCCESS,
                ArtifactStatus.FAILED,
                ArtifactStatus.SKIPPED,
            ]
            
            # Failed/skipped should have error message
            if artifact.status != ArtifactStatus.SUCCESS:
                assert artifact.error_message is not None


class TestManifest:
    """Tests for deployment manifest."""
    
    def test_manifest_created(self, simple_onnx_model, temp_dir):
        """Manifest file is created."""
        bundle = generate_deployment_artifacts(
            simple_onnx_model,
            variant_id="test",
            source_hash="hash",
            output_dir=temp_dir,
        )
        
        manifest_path = temp_dir / "manifest.json"
        assert manifest_path.exists()
    
    def test_manifest_contains_artifact_info(self, simple_onnx_model, temp_dir):
        """Manifest contains artifact information."""
        import json
        
        bundle = generate_deployment_artifacts(
            simple_onnx_model,
            variant_id="test",
            source_hash="hash",
            output_dir=temp_dir,
        )
        
        manifest_path = temp_dir / "manifest.json"
        with open(manifest_path) as f:
            manifest = json.load(f)
        
        assert "variant_id" in manifest
        assert "artifacts" in manifest
