"""
SOAC Orchestrator Package
=========================

Pipeline Orchestration Layer.

PUBLIC API:
    - run_soac_job(model_path, config) -> JobResult
"""

from .pipeline import run_soac_job, SOACPipeline
from .job_context import JobContext, JobConfig, create_job_context
from .results import JobResult, StageResult, create_success_result, create_failure_result
from .state_machine import (
    can_transition,
    validate_transition,
    is_terminal_stage,
    get_stage_order,
)
from .exceptions import (
    PipelineStage,
    PipelineError,
    ValidationFailedError,
    CanonicalizationFailedError,
    OptimizationFailedError,
    BenchmarkingFailedError,
    SelectionFailedError,
    DeploymentFailedError,
    AccuracyConstraintError,
)

__version__ = "1.0.0"

__all__ = [
    # Main API
    "run_soac_job",
    "SOACPipeline",
    
    # Context
    "JobContext",
    "JobConfig",
    "create_job_context",
    
    # Results
    "JobResult",
    "StageResult",
    
    # State
    "PipelineStage",
    "can_transition",
    "get_stage_order",
    
    # Exceptions
    "PipelineError",
    "ValidationFailedError",
    "CanonicalizationFailedError",
    "OptimizationFailedError",
    "BenchmarkingFailedError",
    "SelectionFailedError",
    "DeploymentFailedError",
    "AccuracyConstraintError",
]
