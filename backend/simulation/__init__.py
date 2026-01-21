"""
SOAC Simulation Package
=======================

Failure simulation for testing.
"""

from .failure_injector import (
    SimulationConfig,
    InjectedMetrics,
    inject_failures,
    create_simulation_config,
)

__all__ = [
    "SimulationConfig",
    "InjectedMetrics",
    "inject_failures",
    "create_simulation_config",
]
