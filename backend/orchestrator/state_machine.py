"""
SOAC Pipeline State Machine
===========================

Manages pipeline state transitions.
"""

from typing import Set
from .exceptions import PipelineStage, PipelineError


# Valid state transitions
VALID_TRANSITIONS: dict[PipelineStage, Set[PipelineStage]] = {
    PipelineStage.PENDING: {PipelineStage.VALIDATING, PipelineStage.FAILED, PipelineStage.CANCELLED},
    PipelineStage.VALIDATING: {PipelineStage.CANONICALIZING, PipelineStage.FAILED, PipelineStage.CANCELLED},
    PipelineStage.CANONICALIZING: {PipelineStage.OPTIMIZING, PipelineStage.FAILED, PipelineStage.CANCELLED},
    PipelineStage.OPTIMIZING: {PipelineStage.BENCHMARKING, PipelineStage.FAILED, PipelineStage.CANCELLED},
    PipelineStage.BENCHMARKING: {PipelineStage.SELECTING, PipelineStage.FAILED, PipelineStage.CANCELLED},
    PipelineStage.SELECTING: {PipelineStage.DEPLOYING, PipelineStage.FAILED, PipelineStage.CANCELLED},
    PipelineStage.DEPLOYING: {PipelineStage.COMPLETED, PipelineStage.FAILED, PipelineStage.CANCELLED},
    PipelineStage.COMPLETED: set(),  # Terminal
    PipelineStage.FAILED: set(),     # Terminal
    PipelineStage.CANCELLED: set(),  # Terminal
}


def can_transition(from_stage: PipelineStage, to_stage: PipelineStage) -> bool:
    """Check if transition is valid."""
    return to_stage in VALID_TRANSITIONS.get(from_stage, set())


def validate_transition(
    from_stage: PipelineStage,
    to_stage: PipelineStage,
    job_id: str,
) -> bool:
    """
    Validate and return True if transition is valid.
    
    Raises:
        PipelineError: If transition is invalid.
    """
    if not can_transition(from_stage, to_stage):
        raise PipelineError(
            message=f"Invalid transition from {from_stage.value} to {to_stage.value}",
            stage=from_stage,
            job_id=job_id,
            error_code="INVALID_STATE_TRANSITION",
        )
    return True


def is_terminal_stage(stage: PipelineStage) -> bool:
    """Check if stage is terminal (no further transitions)."""
    return stage in {PipelineStage.COMPLETED, PipelineStage.FAILED, PipelineStage.CANCELLED}


def get_next_stage(current: PipelineStage) -> PipelineStage:
    """Get the next stage in normal flow."""
    normal_flow = [
        PipelineStage.PENDING,
        PipelineStage.VALIDATING,
        PipelineStage.CANONICALIZING,
        PipelineStage.OPTIMIZING,
        PipelineStage.BENCHMARKING,
        PipelineStage.SELECTING,
        PipelineStage.DEPLOYING,
        PipelineStage.COMPLETED,
    ]
    
    try:
        idx = normal_flow.index(current)
        if idx < len(normal_flow) - 1:
            return normal_flow[idx + 1]
    except ValueError:
        pass
    
    return current


def get_stage_order() -> list[PipelineStage]:
    """Get ordered list of pipeline stages."""
    return [
        PipelineStage.PENDING,
        PipelineStage.VALIDATING,
        PipelineStage.CANONICALIZING,
        PipelineStage.OPTIMIZING,
        PipelineStage.BENCHMARKING,
        PipelineStage.SELECTING,
        PipelineStage.DEPLOYING,
        PipelineStage.COMPLETED,
    ]
