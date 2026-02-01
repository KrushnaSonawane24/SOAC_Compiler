"""
SOAC What-If Optimization Mode
==============================

Enables hypothetical policy and constraint exploration without rebuilding.

This module allows users to:
    - Simulate different optimization policies
    - Simulate relaxed/tightened constraints
    - Compare decisions without re-benchmarking

GUARANTEES:
    - Reuses existing benchmark data
    - No new artifacts generated
    - Deterministic: same input produces same output
    - Produces explainable comparison reports
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
import json
import hashlib
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# DATA STRUCTURES
# =============================================================================

class WhatIfScenarioType(str, Enum):
    """Types of what-if scenarios."""
    POLICY_CHANGE = "policy_change"
    CONSTRAINT_RELAXATION = "constraint_relaxation"
    CONSTRAINT_TIGHTENING = "constraint_tightening"
    HARDWARE_CHANGE = "hardware_change"
    CUSTOM = "custom"


@dataclass
class WhatIfScenario:
    """
    Definition of a what-if scenario.
    
    Describes the hypothetical changes to evaluate.
    """
    name: str
    scenario_type: WhatIfScenarioType
    description: str = ""
    
    # Policy changes
    policy_name: Optional[str] = None
    
    # Constraint changes (as deltas)
    latency_delta_ms: float = 0.0
    memory_delta_mb: float = 0.0
    size_delta_mb: float = 0.0
    accuracy_tolerance_delta: float = 0.0
    
    # Hardware changes
    target_hardware: Optional[str] = None
    
    # Custom parameters
    custom_params: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "scenario_type": self.scenario_type.value,
            "description": self.description,
            "policy_name": self.policy_name,
            "latency_delta_ms": self.latency_delta_ms,
            "memory_delta_mb": self.memory_delta_mb,
            "size_delta_mb": self.size_delta_mb,
            "accuracy_tolerance_delta": self.accuracy_tolerance_delta,
            "target_hardware": self.target_hardware,
            "custom_params": self.custom_params,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "WhatIfScenario":
        return cls(
            name=data["name"],
            scenario_type=WhatIfScenarioType(data["scenario_type"]),
            description=data.get("description", ""),
            policy_name=data.get("policy_name"),
            latency_delta_ms=data.get("latency_delta_ms", 0.0),
            memory_delta_mb=data.get("memory_delta_mb", 0.0),
            size_delta_mb=data.get("size_delta_mb", 0.0),
            accuracy_tolerance_delta=data.get("accuracy_tolerance_delta", 0.0),
            target_hardware=data.get("target_hardware"),
            custom_params=data.get("custom_params", {}),
        )


@dataclass
class WhatIfResult:
    """
    Result of a what-if scenario evaluation.
    
    Contains the hypothetical outcome without actually building.
    """
    scenario: WhatIfScenario
    
    # Would the selected variant change?
    would_selection_change: bool
    
    # Original selection
    original_variant_id: str
    original_variant_type: str
    
    # Hypothetical selection
    hypothetical_variant_id: str
    hypothetical_variant_type: str
    
    # Metrics comparison
    original_latency_ms: float = 0.0
    hypothetical_latency_ms: float = 0.0
    latency_change_percent: float = 0.0
    
    original_size_mb: float = 0.0
    hypothetical_size_mb: float = 0.0
    size_change_percent: float = 0.0
    
    original_accuracy_drop: float = 0.0
    hypothetical_accuracy_drop: float = 0.0
    
    # Constraint satisfaction
    original_constraints_met: bool = True
    hypothetical_constraints_met: bool = True
    
    # Decision reasoning
    reasoning: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenario": self.scenario.to_dict(),
            "would_selection_change": self.would_selection_change,
            "original_variant_id": self.original_variant_id,
            "original_variant_type": self.original_variant_type,
            "hypothetical_variant_id": self.hypothetical_variant_id,
            "hypothetical_variant_type": self.hypothetical_variant_type,
            "original_latency_ms": self.original_latency_ms,
            "hypothetical_latency_ms": self.hypothetical_latency_ms,
            "latency_change_percent": self.latency_change_percent,
            "original_size_mb": self.original_size_mb,
            "hypothetical_size_mb": self.hypothetical_size_mb,
            "size_change_percent": self.size_change_percent,
            "original_accuracy_drop": self.original_accuracy_drop,
            "hypothetical_accuracy_drop": self.hypothetical_accuracy_drop,
            "original_constraints_met": self.original_constraints_met,
            "hypothetical_constraints_met": self.hypothetical_constraints_met,
            "reasoning": self.reasoning,
        }


@dataclass
class WhatIfComparisonReport:
    """
    Comparison report for multiple what-if scenarios.
    """
    baseline_job_id: str
    scenarios_evaluated: int
    generated_at: str
    results: List[WhatIfResult] = field(default_factory=list)
    summary: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "baseline_job_id": self.baseline_job_id,
            "scenarios_evaluated": self.scenarios_evaluated,
            "generated_at": self.generated_at,
            "results": [r.to_dict() for r in self.results],
            "summary": self.summary,
        }
    
    def to_markdown(self) -> str:
        """Generate a markdown report."""
        lines = [
            "# What-If Analysis Report",
            "",
            f"**Baseline Job:** {self.baseline_job_id}",
            f"**Scenarios Evaluated:** {self.scenarios_evaluated}",
            f"**Generated:** {self.generated_at}",
            "",
            "## Summary",
            "",
            self.summary,
            "",
            "## Scenarios",
            "",
        ]
        
        for i, result in enumerate(self.results, 1):
            lines.append(f"### {i}. {result.scenario.name}")
            lines.append("")
            lines.append(f"**Type:** {result.scenario.scenario_type.value}")
            lines.append(f"**Description:** {result.scenario.description}")
            lines.append("")
            
            if result.would_selection_change:
                lines.append(f"⚠️ **Selection would change:**")
                lines.append(f"- Original: `{result.original_variant_type}` ({result.original_variant_id})")
                lines.append(f"- Hypothetical: `{result.hypothetical_variant_type}` ({result.hypothetical_variant_id})")
            else:
                lines.append(f"✅ **Selection unchanged:** `{result.original_variant_type}`")
            
            lines.append("")
            lines.append("| Metric | Original | Hypothetical | Change |")
            lines.append("|--------|----------|--------------|--------|")
            lines.append(f"| Latency | {result.original_latency_ms:.2f}ms | {result.hypothetical_latency_ms:.2f}ms | {result.latency_change_percent:+.1f}% |")
            lines.append(f"| Size | {result.original_size_mb:.2f}MB | {result.hypothetical_size_mb:.2f}MB | {result.size_change_percent:+.1f}% |")
            lines.append(f"| Accuracy Drop | {result.original_accuracy_drop:.2%} | {result.hypothetical_accuracy_drop:.2%} | - |")
            lines.append("")
            lines.append(f"**Reasoning:** {result.reasoning}")
            lines.append("")
        
        return "\n".join(lines)


# =============================================================================
# WHAT-IF ENGINE
# =============================================================================

class WhatIfEngine:
    """
    Engine for what-if optimization analysis.
    
    Enables exploration of alternative optimization decisions
    without regenerating artifacts.
    
    Key Features:
        - Reuses existing benchmark data
        - Simulates policy changes
        - Simulates constraint adjustments
        - Produces explainable comparisons
    
    Properties:
        - Deterministic: Same inputs produce same outputs
        - Read-only: Does not modify any state
        - No I/O: Works with in-memory data only
    
    Example:
        >>> engine = WhatIfEngine(original_result)
        >>> scenario = WhatIfScenario(
        ...     name="Relaxed latency",
        ...     scenario_type=WhatIfScenarioType.CONSTRAINT_RELAXATION,
        ...     latency_delta_ms=10.0,
        ... )
        >>> result = engine.evaluate(scenario)
        >>> print(result.would_selection_change)
    """
    
    def __init__(
        self,
        variants: List[Dict[str, Any]],
        original_selection: Dict[str, Any],
        original_constraints: Dict[str, Any],
        original_policy: str,
    ):
        """
        Initialize what-if engine.
        
        Args:
            variants: List of variant data with metrics
            original_selection: The originally selected variant
            original_constraints: Original constraint configuration
            original_policy: Name of the original policy used
        """
        self.variants = variants
        self.original_selection = original_selection
        self.original_constraints = original_constraints
        self.original_policy = original_policy
        
        # Pre-sort variants by different criteria for quick lookup
        self._variants_by_latency = sorted(
            variants, 
            key=lambda v: v.get("latency_ms", float('inf'))
        )
        self._variants_by_size = sorted(
            variants, 
            key=lambda v: v.get("size_bytes", float('inf'))
        )
        self._variants_by_accuracy = sorted(
            variants, 
            key=lambda v: v.get("accuracy_drop", 0.0)
        )
    
    def evaluate(self, scenario: WhatIfScenario) -> WhatIfResult:
        """
        Evaluate a what-if scenario.
        
        Args:
            scenario: The scenario to evaluate
        
        Returns:
            Result of the hypothetical evaluation
        """
        logger.info(f"Evaluating what-if scenario: {scenario.name}")
        
        # Get original metrics
        orig_latency = self.original_selection.get("latency_ms", 0.0)
        orig_size_bytes = self.original_selection.get("size_bytes", 0)
        orig_size_mb = orig_size_bytes / (1024 * 1024)
        orig_accuracy_drop = self.original_selection.get("accuracy_drop", 0.0)
        
        # Apply scenario to find hypothetical selection
        hypothetical_selection = self._apply_scenario(scenario)
        
        hyp_latency = hypothetical_selection.get("latency_ms", 0.0)
        hyp_size_bytes = hypothetical_selection.get("size_bytes", 0)
        hyp_size_mb = hyp_size_bytes / (1024 * 1024)
        hyp_accuracy_drop = hypothetical_selection.get("accuracy_drop", 0.0)
        
        # Check if selection would change
        would_change = (
            self.original_selection.get("variant_id") != 
            hypothetical_selection.get("variant_id")
        )
        
        # Calculate changes
        latency_change = 0.0
        if orig_latency > 0:
            latency_change = ((hyp_latency - orig_latency) / orig_latency) * 100
        
        size_change = 0.0
        if orig_size_mb > 0:
            size_change = ((hyp_size_mb - orig_size_mb) / orig_size_mb) * 100
        
        # Check constraint satisfaction
        adjusted_constraints = self._adjust_constraints(scenario)
        orig_met = self._check_constraints(self.original_selection, self.original_constraints)
        hyp_met = self._check_constraints(hypothetical_selection, adjusted_constraints)
        
        # Generate reasoning
        reasoning = self._generate_reasoning(scenario, would_change, hypothetical_selection)
        
        return WhatIfResult(
            scenario=scenario,
            would_selection_change=would_change,
            original_variant_id=self.original_selection.get("variant_id", "unknown"),
            original_variant_type=self.original_selection.get("variant_type", "unknown"),
            hypothetical_variant_id=hypothetical_selection.get("variant_id", "unknown"),
            hypothetical_variant_type=hypothetical_selection.get("variant_type", "unknown"),
            original_latency_ms=orig_latency,
            hypothetical_latency_ms=hyp_latency,
            latency_change_percent=latency_change,
            original_size_mb=orig_size_mb,
            hypothetical_size_mb=hyp_size_mb,
            size_change_percent=size_change,
            original_accuracy_drop=orig_accuracy_drop,
            hypothetical_accuracy_drop=hyp_accuracy_drop,
            original_constraints_met=orig_met,
            hypothetical_constraints_met=hyp_met,
            reasoning=reasoning,
        )
    
    def evaluate_multiple(self, scenarios: List[WhatIfScenario]) -> WhatIfComparisonReport:
        """
        Evaluate multiple what-if scenarios.
        
        Args:
            scenarios: List of scenarios to evaluate
        
        Returns:
            Comparison report with all results
        """
        results = [self.evaluate(s) for s in scenarios]
        
        # Generate summary
        changes_count = sum(1 for r in results if r.would_selection_change)
        summary = (
            f"Evaluated {len(scenarios)} scenarios. "
            f"{changes_count} would result in a different selection."
        )
        
        return WhatIfComparisonReport(
            baseline_job_id=self.original_selection.get("job_id", "unknown"),
            scenarios_evaluated=len(scenarios),
            generated_at=datetime.now(timezone.utc).isoformat(),
            results=results,
            summary=summary,
        )
    
    def _apply_scenario(self, scenario: WhatIfScenario) -> Dict[str, Any]:
        """Apply scenario to find hypothetical selection."""
        
        if scenario.scenario_type == WhatIfScenarioType.POLICY_CHANGE:
            return self._apply_policy(scenario.policy_name or self.original_policy)
        
        elif scenario.scenario_type == WhatIfScenarioType.CONSTRAINT_RELAXATION:
            adjusted = self._adjust_constraints(scenario)
            return self._select_with_constraints(adjusted)
        
        elif scenario.scenario_type == WhatIfScenarioType.CONSTRAINT_TIGHTENING:
            adjusted = self._adjust_constraints(scenario)
            return self._select_with_constraints(adjusted)
        
        else:
            # Default: return original
            return self.original_selection
    
    def _apply_policy(self, policy_name: str) -> Dict[str, Any]:
        """Select variant based on policy name."""
        policy_name = policy_name.lower()
        
        if policy_name in ("latency_first", "latency"):
            # Select fastest variant
            valid = [v for v in self._variants_by_latency if self._is_valid_variant(v)]
            return valid[0] if valid else self.original_selection
        
        elif policy_name in ("accuracy_first", "accuracy"):
            # Select most accurate variant
            valid = [v for v in self._variants_by_accuracy if self._is_valid_variant(v)]
            return valid[0] if valid else self.original_selection
        
        elif policy_name in ("size_first", "mobile_first", "mobile"):
            # Select smallest variant
            valid = [v for v in self._variants_by_size if self._is_valid_variant(v)]
            return valid[0] if valid else self.original_selection
        
        elif policy_name in ("balanced", "default"):
            # Return original selection
            return self.original_selection
        
        else:
            logger.warning(f"Unknown policy: {policy_name}, using original")
            return self.original_selection
    
    def _adjust_constraints(self, scenario: WhatIfScenario) -> Dict[str, Any]:
        """Create adjusted constraints based on scenario."""
        adjusted = dict(self.original_constraints)
        
        if "max_latency_ms" in adjusted and scenario.latency_delta_ms != 0:
            adjusted["max_latency_ms"] = adjusted["max_latency_ms"] + scenario.latency_delta_ms
        
        if "max_memory_mb" in adjusted and scenario.memory_delta_mb != 0:
            adjusted["max_memory_mb"] = adjusted["max_memory_mb"] + scenario.memory_delta_mb
        
        if "max_size_mb" in adjusted and scenario.size_delta_mb != 0:
            adjusted["max_size_mb"] = adjusted["max_size_mb"] + scenario.size_delta_mb
        
        if "max_accuracy_drop" in adjusted and scenario.accuracy_tolerance_delta != 0:
            adjusted["max_accuracy_drop"] = adjusted["max_accuracy_drop"] + scenario.accuracy_tolerance_delta
        
        return adjusted
    
    def _select_with_constraints(self, constraints: Dict[str, Any]) -> Dict[str, Any]:
        """Select best variant that meets constraints."""
        valid_variants = []
        
        for variant in self.variants:
            if self._check_constraints(variant, constraints):
                valid_variants.append(variant)
        
        if not valid_variants:
            # No variants meet constraints, return original
            return self.original_selection
        
        # Select best based on original policy
        return self._apply_policy_to_list(valid_variants, self.original_policy)
    
    def _apply_policy_to_list(self, variants: List[Dict], policy: str) -> Dict[str, Any]:
        """Apply policy to select from a list of variants."""
        if not variants:
            return self.original_selection
        
        policy = policy.lower()
        
        if policy in ("latency_first", "latency"):
            return min(variants, key=lambda v: v.get("latency_ms", float('inf')))
        elif policy in ("accuracy_first", "accuracy"):
            return min(variants, key=lambda v: v.get("accuracy_drop", 0.0))
        elif policy in ("size_first", "mobile_first", "mobile"):
            return min(variants, key=lambda v: v.get("size_bytes", float('inf')))
        else:
            return variants[0]
    
    def _check_constraints(self, variant: Dict[str, Any], constraints: Dict[str, Any]) -> bool:
        """Check if variant meets all constraints."""
        latency = variant.get("latency_ms", 0.0)
        size_mb = variant.get("size_bytes", 0) / (1024 * 1024)
        memory_mb = variant.get("memory_mb", 0)
        accuracy_drop = variant.get("accuracy_drop", 0.0)
        
        if "max_latency_ms" in constraints:
            if latency > constraints["max_latency_ms"]:
                return False
        
        if "max_size_mb" in constraints:
            if size_mb > constraints["max_size_mb"]:
                return False
        
        if "max_memory_mb" in constraints:
            if memory_mb > constraints["max_memory_mb"]:
                return False
        
        if "max_accuracy_drop" in constraints:
            if accuracy_drop > constraints["max_accuracy_drop"]:
                return False
        
        return True
    
    def _is_valid_variant(self, variant: Dict[str, Any]) -> bool:
        """Check if variant has valid metrics."""
        return (
            variant.get("latency_ms", 0) > 0 and
            variant.get("size_bytes", 0) > 0
        )
    
    def _generate_reasoning(
        self, 
        scenario: WhatIfScenario, 
        would_change: bool,
        hypothetical: Dict[str, Any]
    ) -> str:
        """Generate human-readable reasoning."""
        if not would_change:
            return f"The original selection remains optimal under {scenario.scenario_type.value}."
        
        if scenario.scenario_type == WhatIfScenarioType.POLICY_CHANGE:
            return (
                f"With {scenario.policy_name} policy, "
                f"{hypothetical.get('variant_type', 'unknown')} becomes preferred "
                f"due to better optimization for the policy's priority metric."
            )
        
        elif scenario.scenario_type == WhatIfScenarioType.CONSTRAINT_RELAXATION:
            return (
                f"Relaxing constraints allows selection of "
                f"{hypothetical.get('variant_type', 'unknown')}, "
                f"which offers better performance at the cost of constraints."
            )
        
        elif scenario.scenario_type == WhatIfScenarioType.CONSTRAINT_TIGHTENING:
            return (
                f"Tightening constraints forces selection of "
                f"{hypothetical.get('variant_type', 'unknown')}, "
                f"which better satisfies the stricter requirements."
            )
        
        else:
            return f"Selection changed to {hypothetical.get('variant_type', 'unknown')}."


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_policy_scenario(name: str, policy: str) -> WhatIfScenario:
    """Create a policy change scenario."""
    return WhatIfScenario(
        name=name,
        scenario_type=WhatIfScenarioType.POLICY_CHANGE,
        description=f"Evaluate using {policy} policy",
        policy_name=policy,
    )


def create_latency_relaxation(delta_ms: float) -> WhatIfScenario:
    """Create a latency relaxation scenario."""
    return WhatIfScenario(
        name=f"Relax latency by {delta_ms}ms",
        scenario_type=WhatIfScenarioType.CONSTRAINT_RELAXATION,
        description=f"Allow {delta_ms}ms additional latency",
        latency_delta_ms=delta_ms,
    )


def create_size_tightening(delta_mb: float) -> WhatIfScenario:
    """Create a size tightening scenario."""
    return WhatIfScenario(
        name=f"Reduce size limit by {abs(delta_mb)}MB",
        scenario_type=WhatIfScenarioType.CONSTRAINT_TIGHTENING,
        description=f"Require {abs(delta_mb)}MB smaller model",
        size_delta_mb=-abs(delta_mb),
    )
