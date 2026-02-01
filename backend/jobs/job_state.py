"""
SOAC Job State Machine
======================

Strict state transitions for job lifecycle.
"""

from typing import Set, Dict
from .models import JobState


# Valid state transitions
VALID_TRANSITIONS: Dict[JobState, Set[JobState]] = {
    JobState.CREATED: {JobState.NORMALIZING, JobState.FAILED},
    JobState.NORMALIZING: {JobState.VALIDATING, JobState.FAILED},
    JobState.VALIDATING: {JobState.CANONICALIZING, JobState.FAILED},
    JobState.CANONICALIZING: {JobState.OPTIMIZING, JobState.FAILED},
    JobState.OPTIMIZING: {JobState.BENCHMARKING, JobState.FAILED},
    JobState.BENCHMARKING: {JobState.SELECTING, JobState.FAILED},
    JobState.SELECTING: {JobState.DEPLOYING, JobState.FAILED},
    JobState.DEPLOYING: {JobState.COMPLETED, JobState.FAILED},
    JobState.COMPLETED: set(),  # Terminal
    JobState.FAILED: set(),     # Terminal
}


def can_transition(from_state: JobState, to_state: JobState) -> bool:
    """Check if state transition is valid."""
    return to_state in VALID_TRANSITIONS.get(from_state, set())


def is_terminal(state: JobState) -> bool:
    """Check if state is terminal (no further transitions)."""
    return state in {JobState.COMPLETED, JobState.FAILED}


def get_next_state(current: JobState) -> JobState:
    """Get next state in normal flow."""
    flow = [
        JobState.CREATED,
        JobState.NORMALIZING,
        JobState.VALIDATING,
        JobState.CANONICALIZING,
        JobState.OPTIMIZING,
        JobState.BENCHMARKING,
        JobState.SELECTING,
        JobState.DEPLOYING,
        JobState.COMPLETED,
    ]
    
    try:
        idx = flow.index(current)
        if idx < len(flow) - 1:
            return flow[idx + 1]
    except ValueError:
        pass
    
    return current


def get_all_states() -> list[JobState]:
    """Get all states in order."""
    return [
        JobState.CREATED,
        JobState.NORMALIZING,
        JobState.VALIDATING,
        JobState.CANONICALIZING,
        JobState.OPTIMIZING,
        JobState.BENCHMARKING,
        JobState.SELECTING,
        JobState.DEPLOYING,
        JobState.COMPLETED,
    ]
