"""
Tests for Pipeline Orchestrator
================================

E2E tests for SOAC pipeline.
"""

import pytest
from pathlib import Path

try:
    import onnxruntime
    ONNXRUNTIME_AVAILABLE = True
except ImportError:
    ONNXRUNTIME_AVAILABLE = False

from backend.orchestrator import (
    run_soac_job,
    JobConfig,
    JobResult,
    PipelineStage,
    create_job_context,
)
from backend.orchestrator.state_machine import (
    can_transition,
    is_terminal_stage,
    get_stage_order,
)


class TestStateMachine:
    """Tests for pipeline state machine."""
    
    def test_valid_transitions(self):
        """Valid transitions are allowed."""
        assert can_transition(PipelineStage.PENDING, PipelineStage.VALIDATING)
        assert can_transition(PipelineStage.VALIDATING, PipelineStage.CANONICALIZING)
        assert can_transition(PipelineStage.DEPLOYING, PipelineStage.COMPLETED)
    
    def test_invalid_transitions(self):
        """Invalid transitions are blocked."""
        assert not can_transition(PipelineStage.PENDING, PipelineStage.COMPLETED)
        assert not can_transition(PipelineStage.VALIDATING, PipelineStage.DEPLOYING)
    
    def test_failure_always_allowed(self):
        """Transition to FAILED is always allowed."""
        for stage in get_stage_order():
            if not is_terminal_stage(stage):
                assert can_transition(stage, PipelineStage.FAILED)
    
    def test_terminal_stages(self):
        """Terminal stages have no outgoing transitions."""
        assert is_terminal_stage(PipelineStage.COMPLETED)
        assert is_terminal_stage(PipelineStage.FAILED)
        assert is_terminal_stage(PipelineStage.CANCELLED)


class TestJobContext:
    """Tests for job context."""
    
    def test_context_creation(self, simple_onnx_model, temp_dir):
        """Job context is created correctly."""
        ctx = create_job_context(
            input_path=simple_onnx_model,
            work_dir=temp_dir,
        )
        
        assert ctx.job_id.startswith("job_")
        assert ctx.current_stage == PipelineStage.PENDING
    
    def test_context_directories(self, simple_onnx_model, temp_dir):
        """Context creates required directories."""
        ctx = create_job_context(
            input_path=simple_onnx_model,
            work_dir=temp_dir,
        )
        
        assert ctx.canonical_dir.exists()
        assert ctx.variants_dir.exists()
        assert ctx.deployment_dir.exists()


class TestJobConfig:
    """Tests for job configuration."""
    
    def test_default_config(self):
        """Default config has correct values."""
        config = JobConfig()
        
        assert config.accuracy_threshold == 0.02
        assert config.cleanup_on_complete == True
    
    def test_config_serializable(self, test_config):
        """Config can be serialized."""
        config_dict = test_config.to_dict()
        
        assert "accuracy_threshold" in config_dict
        assert "warmup_runs" in config_dict


class TestJobResult:
    """Tests for job results."""
    
    def test_result_serializable(self, simple_onnx_model, temp_dir, test_config):
        """Job result can be serialized."""
        if not ONNXRUNTIME_AVAILABLE:
            pytest.skip("onnxruntime not available")
        
        result = run_soac_job(
            simple_onnx_model,
            config=test_config,
            work_dir=temp_dir,
        )
        
        result_dict = result.to_dict()
        
        assert "job_id" in result_dict
        assert "success" in result_dict
        assert "final_stage" in result_dict


@pytest.mark.skipif(not ONNXRUNTIME_AVAILABLE, reason="onnxruntime not available")
class TestE2EPipeline:
    """End-to-end pipeline tests."""
    
    def test_full_pipeline_success(self, simple_onnx_model, temp_dir, test_config):
        """Full pipeline runs successfully."""
        result = run_soac_job(
            simple_onnx_model,
            config=test_config,
            work_dir=temp_dir,
        )
        
        assert result.success
        assert result.final_stage == PipelineStage.COMPLETED
        assert result.selected_variant is not None
    
    def test_deployment_artifacts_created(self, simple_onnx_model, temp_dir, test_config):
        """Deployment artifacts are created."""
        result = run_soac_job(
            simple_onnx_model,
            config=test_config,
            work_dir=temp_dir,
        )
        
        if result.success:
            assert result.deployment_bundle is not None
            bundle_path = Path(result.deployment_bundle)
            assert bundle_path.exists()
    
    def test_stage_results_recorded(self, simple_onnx_model, temp_dir, test_config):
        """All stage results are recorded."""
        result = run_soac_job(
            simple_onnx_model,
            config=test_config,
            work_dir=temp_dir,
        )
        
        # Should have results for all stages
        assert len(result.stage_results) > 0
        
        for stage_result in result.stage_results:
            assert stage_result.duration_ms > 0
    
    def test_logs_captured(self, simple_onnx_model, temp_dir, test_config):
        """Execution logs are captured."""
        result = run_soac_job(
            simple_onnx_model,
            config=test_config,
            work_dir=temp_dir,
        )
        
        assert len(result.logs) > 0


class TestFailureHandling:
    """Tests for failure scenarios."""
    
    def test_invalid_model_fails_validation(self, temp_dir, test_config):
        """Invalid model fails at validation."""
        invalid_path = temp_dir / "invalid.onnx"
        invalid_path.write_bytes(b"not a valid onnx model")
        
        result = run_soac_job(
            invalid_path,
            config=test_config,
            work_dir=temp_dir,
        )
        
        assert not result.success
        assert result.error is not None
    
    def test_nonexistent_file_fails(self, temp_dir, test_config):
        """Nonexistent file fails gracefully or raises error."""
        nonexistent_path = temp_dir / "nonexistent.onnx"
        
        # Either raises exception or returns failure result
        try:
            result = run_soac_job(
                nonexistent_path,
                config=test_config,
                work_dir=temp_dir,
            )
            # If no exception, should be marked as failed
            assert not result.success
        except (FileNotFoundError, OSError):
            # Raising is also acceptable
            pass
