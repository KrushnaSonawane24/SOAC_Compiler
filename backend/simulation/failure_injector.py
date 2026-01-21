"""
SOAC Failure Injector
=====================

Injects controlled failures for testing.
"""

from dataclasses import dataclass
from typing import Optional
import logging


logger = logging.getLogger(__name__)


@dataclass
class SimulationConfig:
    """Configuration for failure simulation."""
    accuracy_drop: Optional[float] = None  # Additional accuracy drop to inject
    latency_multiplier: Optional[float] = None  # Multiply latency by this
    memory_override: Optional[float] = None  # Override memory MB


@dataclass
class InjectedMetrics:
    """Metrics after injection."""
    latency_ms: float
    memory_mb: float
    accuracy: float
    accuracy_drop: float
    was_injected: bool = False
    injection_details: Optional[str] = None


def inject_failures(
    original_latency_ms: float,
    original_memory_mb: float,
    original_accuracy: float,
    baseline_accuracy: float,
    config: SimulationConfig,
) -> InjectedMetrics:
    """
    Inject controlled failures into metrics.
    
    Args:
        original_latency_ms: Real latency measurement.
        original_memory_mb: Real memory measurement.
        original_accuracy: Real accuracy.
        baseline_accuracy: Baseline accuracy for drop calculation.
        config: Simulation configuration.
    
    Returns:
        InjectedMetrics with potentially modified values.
    """
    latency = original_latency_ms
    memory = original_memory_mb
    accuracy = original_accuracy
    was_injected = False
    details = []
    
    # Inject latency spike
    if config.latency_multiplier is not None:
        latency = original_latency_ms * config.latency_multiplier
        details.append(f"latency*{config.latency_multiplier}")
        was_injected = True
        logger.warning(f"[SIMULATION] Latency spike: {original_latency_ms:.2f}ms -> {latency:.2f}ms")
    
    # Inject memory override
    if config.memory_override is not None:
        memory = config.memory_override
        details.append(f"memory={config.memory_override}MB")
        was_injected = True
        logger.warning(f"[SIMULATION] Memory override: {original_memory_mb:.2f}MB -> {memory:.2f}MB")
    
    # Inject accuracy drop
    if config.accuracy_drop is not None:
        accuracy = original_accuracy - config.accuracy_drop
        details.append(f"accuracy-{config.accuracy_drop}")
        was_injected = True
        logger.warning(f"[SIMULATION] Accuracy drop: {original_accuracy:.4f} -> {accuracy:.4f}")
    
    # Calculate accuracy drop from baseline
    accuracy_drop = (baseline_accuracy - accuracy) / baseline_accuracy if baseline_accuracy > 0 else 0.0
    
    return InjectedMetrics(
        latency_ms=latency,
        memory_mb=memory,
        accuracy=accuracy,
        accuracy_drop=accuracy_drop,
        was_injected=was_injected,
        injection_details=", ".join(details) if details else None,
    )


def create_simulation_config(
    simulate_accuracy_drop: Optional[float] = None,
    simulate_latency_spike: Optional[float] = None,
    simulate_memory_exceed: Optional[float] = None,
) -> SimulationConfig:
    """Create simulation config from job config values."""
    return SimulationConfig(
        accuracy_drop=simulate_accuracy_drop,
        latency_multiplier=simulate_latency_spike,
        memory_override=simulate_memory_exceed,
    )
