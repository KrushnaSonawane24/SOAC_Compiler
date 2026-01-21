"""
SOAC Compilation Policies
=========================

Policy-based compilation for variant selection.
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from enum import Enum


class CompilationPolicy(str, Enum):
    """Compilation policy types."""
    BALANCED = "balanced"          # Default balanced approach
    ACCURACY_FIRST = "accuracy_first"  # Prioritize accuracy
    LATENCY_FIRST = "latency_first"    # Prioritize speed
    MOBILE_FIRST = "mobile_first"      # Prioritize size/memory


@dataclass
class PolicyWeights:
    """
    Weighting factors for variant scoring.
    
    All weights normalized to sum to 1.0.
    """
    accuracy: float
    latency: float
    memory: float
    size: float
    
    def to_dict(self) -> Dict[str, float]:
        return {
            "accuracy": self.accuracy,
            "latency": self.latency,
            "memory": self.memory,
            "size": self.size,
        }


# Policy weight configurations
POLICY_WEIGHTS: Dict[CompilationPolicy, PolicyWeights] = {
    CompilationPolicy.BALANCED: PolicyWeights(
        accuracy=0.30,
        latency=0.35,
        memory=0.20,
        size=0.15,
    ),
    CompilationPolicy.ACCURACY_FIRST: PolicyWeights(
        accuracy=0.60,
        latency=0.20,
        memory=0.10,
        size=0.10,
    ),
    CompilationPolicy.LATENCY_FIRST: PolicyWeights(
        accuracy=0.20,
        latency=0.55,
        memory=0.15,
        size=0.10,
    ),
    CompilationPolicy.MOBILE_FIRST: PolicyWeights(
        accuracy=0.25,
        latency=0.20,
        memory=0.30,
        size=0.25,
    ),
}


def get_policy_weights(policy: CompilationPolicy) -> PolicyWeights:
    """Get weights for a policy."""
    return POLICY_WEIGHTS.get(policy, POLICY_WEIGHTS[CompilationPolicy.BALANCED])


def compute_policy_score(
    accuracy_score: float,
    latency_score: float,
    memory_score: float,
    size_score: float,
    policy: CompilationPolicy,
) -> float:
    """
    Compute weighted score based on policy.
    
    All input scores should be normalized (0-1, higher is better).
    """
    weights = get_policy_weights(policy)
    
    return (
        accuracy_score * weights.accuracy +
        latency_score * weights.latency +
        memory_score * weights.memory +
        size_score * weights.size
    )


def get_variant_preference(policy: CompilationPolicy) -> list[str]:
    """
    Get preferred variant types for a policy.
    
    Returns ordered list of variant type preferences.
    """
    preferences = {
        CompilationPolicy.BALANCED: ["fp16", "baseline", "int8"],
        CompilationPolicy.ACCURACY_FIRST: ["baseline", "fp16", "int8"],
        CompilationPolicy.LATENCY_FIRST: ["int8", "fp16", "baseline"],
        CompilationPolicy.MOBILE_FIRST: ["int8", "fp16", "baseline"],
    }
    return preferences.get(policy, preferences[CompilationPolicy.BALANCED])


def get_deployment_priority(policy: CompilationPolicy) -> list[str]:
    """
    Get deployment target priority for a policy.
    
    Returns ordered list of deployment targets.
    """
    priorities = {
        CompilationPolicy.BALANCED: ["onnx_runtime", "tflite", "tensorrt", "coreml"],
        CompilationPolicy.ACCURACY_FIRST: ["onnx_runtime", "tensorrt", "tflite", "coreml"],
        CompilationPolicy.LATENCY_FIRST: ["tensorrt", "onnx_runtime", "tflite", "coreml"],
        CompilationPolicy.MOBILE_FIRST: ["tflite", "coreml", "onnx_runtime", "tensorrt"],
    }
    return priorities.get(policy, priorities[CompilationPolicy.BALANCED])


@dataclass
class PolicyExplanation:
    """Explanation of policy influence."""
    policy: CompilationPolicy
    weights: PolicyWeights
    variant_preference: list[str]
    deployment_priority: list[str]
    selection_rationale: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "policy": self.policy.value,
            "weights": self.weights.to_dict(),
            "variant_preference": self.variant_preference,
            "deployment_priority": self.deployment_priority,
            "selection_rationale": self.selection_rationale,
        }


def explain_policy(
    policy: CompilationPolicy,
    selected_variant_id: str,
    accuracy_drop: float,
) -> PolicyExplanation:
    """Generate policy explanation."""
    weights = get_policy_weights(policy)
    
    rationales = {
        CompilationPolicy.ACCURACY_FIRST: (
            f"Accuracy-first policy prioritized {selected_variant_id} for minimal accuracy loss"
        ),
        CompilationPolicy.LATENCY_FIRST: (
            f"Latency-first policy selected {selected_variant_id} for optimal speed "
            f"(accuracy drop: {accuracy_drop*100:.2f}%)"
        ),
        CompilationPolicy.MOBILE_FIRST: (
            f"Mobile-first policy chose {selected_variant_id} for optimal size/memory"
        ),
        CompilationPolicy.BALANCED: (
            f"Balanced policy selected {selected_variant_id} as best overall"
        ),
    }
    
    return PolicyExplanation(
        policy=policy,
        weights=weights,
        variant_preference=get_variant_preference(policy),
        deployment_priority=get_deployment_priority(policy),
        selection_rationale=rationales.get(policy, ""),
    )
