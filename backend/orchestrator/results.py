"""
SOAC Job Results
================

Final job result structures.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from pathlib import Path

from .exceptions import PipelineStage, PipelineError


@dataclass
class StageResult:
    """Result of a single pipeline stage."""
    stage: PipelineStage
    success: bool
    duration_ms: float
    message: str
    artifacts: Dict[str, str] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "stage": self.stage.value,
            "success": self.success,
            "duration_ms": self.duration_ms,
            "message": self.message,
            "artifacts": self.artifacts,
        }


@dataclass
class JobResult:
    """
    Complete result of a SOAC job.
    
    Attributes:
        job_id: Unique job identifier
        success: Whether job completed successfully
        final_stage: Last stage reached
        input_path: Original input model path
        selected_variant: ID of selected variant (if successful)
        deployment_bundle: Path to deployment artifacts
        stage_results: Results from each stage
        error: Error info if failed
        total_duration_ms: Total job duration
        logs: Job execution logs
    """
    job_id: str
    success: bool
    final_stage: PipelineStage
    input_path: str
    selected_variant: Optional[str] = None
    deployment_bundle: Optional[str] = None
    stage_results: List[StageResult] = field(default_factory=list)
    error: Optional[Dict[str, Any]] = None
    total_duration_ms: float = 0.0
    logs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "job_id": self.job_id,
            "success": self.success,
            "final_stage": self.final_stage.value,
            "input_path": self.input_path,
            "selected_variant": self.selected_variant,
            "deployment_bundle": self.deployment_bundle,
            "stage_results": [s.to_dict() for s in self.stage_results],
            "error": self.error,
            "total_duration_ms": self.total_duration_ms,
            "metadata": self.metadata,
        }
    
    def get_summary(self) -> str:
        """Get human-readable summary."""
        status = "✓ SUCCESS" if self.success else "✗ FAILED"
        return (
            f"Job {self.job_id}: {status}\n"
            f"  Stage: {self.final_stage.value}\n"
            f"  Duration: {self.total_duration_ms:.2f}ms\n"
            f"  Selected: {self.selected_variant or 'N/A'}"
        )


def create_success_result(
    job_id: str,
    input_path: str,
    selected_variant: str,
    deployment_bundle: str,
    stage_results: List[StageResult],
    total_duration_ms: float,
    logs: List[str],
    metadata: Optional[Dict[str, Any]] = None,
) -> JobResult:
    """Create successful job result."""
    return JobResult(
        job_id=job_id,
        success=True,
        final_stage=PipelineStage.COMPLETED,
        input_path=input_path,
        selected_variant=selected_variant,
        deployment_bundle=deployment_bundle,
        stage_results=stage_results,
        total_duration_ms=total_duration_ms,
        logs=logs,
        metadata=metadata or {},
    )


def create_failure_result(
    job_id: str,
    input_path: str,
    error: PipelineError,
    stage_results: List[StageResult],
    total_duration_ms: float,
    logs: List[str],
) -> JobResult:
    """Create failed job result."""
    return JobResult(
        job_id=job_id,
        success=False,
        final_stage=error.stage,
        input_path=input_path,
        stage_results=stage_results,
        error=error.to_dict(),
        total_duration_ms=total_duration_ms,
        logs=logs,
    )
