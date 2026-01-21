"""
Tests for Failure Simulation
============================

Tests for controlled failure injection.
"""

import pytest

from backend.simulation import (
    SimulationConfig,
    InjectedMetrics,
    inject_failures,
    create_simulation_config,
)
from backend.orchestrator.job_context import JobConfig


class TestSimulationConfig:
    """Tests for simulation config."""
    
    def test_job_config_has_simulation_flags(self):
        """JobConfig has simulation flags."""
        config = JobConfig(
            simulate_accuracy_drop=0.05,
            simulate_latency_spike=2.0,
            simulate_memory_exceed=10000.0,
        )
        
        assert config.simulate_accuracy_drop == 0.05
        assert config.simulate_latency_spike == 2.0
        assert config.simulate_memory_exceed == 10000.0
    
    def test_has_simulated_failures_detects_flags(self):
        """has_simulated_failures property works."""
        normal_config = JobConfig()
        assert not normal_config.has_simulated_failures
        
        sim_config = JobConfig(simulate_accuracy_drop=0.05)
        assert sim_config.has_simulated_failures
    
    def test_create_simulation_config(self):
        """Simulation config can be created from values."""
        config = create_simulation_config(
            simulate_accuracy_drop=0.03,
            simulate_latency_spike=1.5,
        )
        
        assert config.accuracy_drop == 0.03
        assert config.latency_multiplier == 1.5
        assert config.memory_override is None


class TestFailureInjection:
    """Tests for failure injection."""
    
    def test_accuracy_drop_injection(self):
        """Accuracy drop is injected correctly."""
        config = SimulationConfig(accuracy_drop=0.05)
        
        result = inject_failures(
            original_latency_ms=10.0,
            original_memory_mb=100.0,
            original_accuracy=0.95,
            baseline_accuracy=0.95,
            config=config,
        )
        
        assert result.accuracy == pytest.approx(0.90)  # 0.95 - 0.05
        assert result.was_injected
        assert "accuracy" in (result.injection_details or "")
    
    def test_latency_spike_injection(self):
        """Latency spike is injected correctly."""
        config = SimulationConfig(latency_multiplier=2.0)
        
        result = inject_failures(
            original_latency_ms=10.0,
            original_memory_mb=100.0,
            original_accuracy=0.95,
            baseline_accuracy=0.95,
            config=config,
        )
        
        assert result.latency_ms == 20.0  # 10 * 2
        assert result.was_injected
    
    def test_memory_exceed_injection(self):
        """Memory override is injected correctly."""
        config = SimulationConfig(memory_override=10000.0)  # 10GB
        
        result = inject_failures(
            original_latency_ms=10.0,
            original_memory_mb=100.0,
            original_accuracy=0.95,
            baseline_accuracy=0.95,
            config=config,
        )
        
        assert result.memory_mb == 10000.0
        assert result.was_injected
    
    def test_no_injection_without_config(self):
        """No injection without simulation config."""
        config = SimulationConfig()
        
        result = inject_failures(
            original_latency_ms=10.0,
            original_memory_mb=100.0,
            original_accuracy=0.95,
            baseline_accuracy=0.95,
            config=config,
        )
        
        assert result.latency_ms == 10.0
        assert result.memory_mb == 100.0
        assert result.accuracy == 0.95
        assert not result.was_injected


class TestAccuracyDropRejection:
    """Tests for accuracy drop causing rejection."""
    
    def test_simulated_accuracy_drop_exceeds_threshold(self):
        """Simulated accuracy drop >2% causes high accuracy_drop value."""
        config = SimulationConfig(accuracy_drop=0.05)  # 5% drop
        
        result = inject_failures(
            original_latency_ms=10.0,
            original_memory_mb=100.0,
            original_accuracy=0.95,
            baseline_accuracy=0.95,
            config=config,
        )
        
        # accuracy_drop = (baseline - new) / baseline
        # = (0.95 - 0.90) / 0.95 = 0.0526 = 5.26%
        assert result.accuracy_drop > 0.02  # Exceeds 2% threshold
        
        # This would cause ALO to reject the variant
        accuracy_threshold = 0.02
        would_be_rejected = result.accuracy_drop > accuracy_threshold
        assert would_be_rejected
    
    def test_simulated_accuracy_drop_within_threshold(self):
        """Simulated accuracy drop within threshold is accepted."""
        config = SimulationConfig(accuracy_drop=0.01)  # 1% drop
        
        result = inject_failures(
            original_latency_ms=10.0,
            original_memory_mb=100.0,
            original_accuracy=0.95,
            baseline_accuracy=0.95,
            config=config,
        )
        
        # accuracy_drop = (0.95 - 0.94) / 0.95 = 0.0105 = 1.05%
        accuracy_threshold = 0.02
        would_be_rejected = result.accuracy_drop > accuracy_threshold
        assert not would_be_rejected


class TestNormalModeUnaffected:
    """Tests that normal mode is unaffected."""
    
    def test_normal_config_no_simulation(self):
        """Normal config has no simulation flags."""
        config = JobConfig()  # Default config
        
        assert config.simulate_accuracy_drop is None
        assert config.simulate_latency_spike is None
        assert config.simulate_memory_exceed is None
        assert not config.has_simulated_failures
    
    def test_normal_mode_metrics_unchanged(self):
        """Normal mode keeps original metrics."""
        config = SimulationConfig()  # No simulation
        
        original = {
            "latency": 10.0,
            "memory": 100.0,
            "accuracy": 0.95,
        }
        
        result = inject_failures(
            original_latency_ms=original["latency"],
            original_memory_mb=original["memory"],
            original_accuracy=original["accuracy"],
            baseline_accuracy=0.95,
            config=config,
        )
        
        assert result.latency_ms == original["latency"]
        assert result.memory_mb == original["memory"]
        assert result.accuracy == original["accuracy"]
