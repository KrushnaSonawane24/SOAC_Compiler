"""
SOAC Selection Policy Base
==========================

Abstract base class for variant selection policies.

CRITICAL RULE:
    Policies MUST NOT access raw metrics directly.
    They ONLY consume cost model outputs.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from backend.optimizer.metadata import OptimizedVariant
    from backend.compiler.cost import CostEstimate


@dataclass(frozen=True)
class PolicyScore:
    """
    Score assigned by a policy to a variant.
    
    Lower score = better candidate.
    
    Attributes:
        variant_id: ID of the scored variant
        score: Computed score (lower is better)
        breakdown: Score component breakdown
        explanation: Human-readable explanation
    """
    variant_id: str
    score: float
    breakdown: Dict[str, float] = field(default_factory=dict)
    explanation: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "variant_id": self.variant_id,
            "score": self.score,
            "breakdown": self.breakdown,
            "explanation": self.explanation,
        }


@dataclass
class SelectionResult:
    """
    Result of policy selection.
    
    Attributes:
        selected: The selected variant
        selected_score: Score of the selected variant
        all_scores: Scores for all candidates
        policy_name: Name of the policy used
        rationale: Human-readable selection rationale
    """
    selected: "OptimizedVariant"
    selected_score: PolicyScore
    all_scores: List[PolicyScore]
    policy_name: str
    rationale: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "selected_id": self.selected.variant_id,
            "selected_score": self.selected_score.to_dict(),
            "all_scores": [s.to_dict() for s in self.all_scores],
            "policy_name": self.policy_name,
            "rationale": self.rationale,
        }


class SelectionPolicy(ABC):
    """
    Abstract base class for selection policies.
    
    Policies determine HOW to select among valid variants.
    They operate ONLY on cost model outputs, not raw metrics.
    
    This separation ensures:
        - Policies are testable in isolation
        - Cost models can be swapped independently
        - Selection logic is explicit and auditable
    
    Example:
        >>> policy = LatencyFirstPolicy()
        >>> costs = [cost_model.estimate(v) for v in variants]
        >>> result = policy.select(variants, costs)
        >>> print(f"Selected: {result.selected.variant_id}")
    """
    
    # Policy name for identification
    name: str = "base_policy"
    
    # Policy description
    description: str = "Base selection policy"
    
    @abstractmethod
    def compute_score(
        self, 
        variant: "OptimizedVariant",
        cost: "CostEstimate"
    ) -> PolicyScore:
        """
        Compute score for a single variant.
        
        Args:
            variant: The variant.
            cost: Cost estimate from cost model.
        
        Returns:
            PolicyScore (lower is better).
        """
        pass
    
    def select(
        self, 
        variants: List["OptimizedVariant"],
        costs: List["CostEstimate"]
    ) -> SelectionResult:
        """
        Select the best variant according to this policy.
        
        Args:
            variants: List of valid variants.
            costs: Corresponding cost estimates.
        
        Returns:
            SelectionResult with the chosen variant.
        """
        if not variants:
            raise ValueError("Cannot select from empty variant list")
        
        if len(variants) != len(costs):
            raise ValueError("variants and costs must have same length")
        
        # Compute scores for all variants
        scores = []
        for variant, cost in zip(variants, costs):
            score = self.compute_score(variant, cost)
            scores.append(score)
        
        # Select minimum score (lower is better)
        best_idx = min(range(len(scores)), key=lambda i: scores[i].score)
        selected = variants[best_idx]
        selected_score = scores[best_idx]
        
        # Generate rationale
        rationale = self._generate_rationale(selected, selected_score, scores)
        
        return SelectionResult(
            selected=selected,
            selected_score=selected_score,
            all_scores=scores,
            policy_name=self.name,
            rationale=rationale,
        )
    
    def _generate_rationale(
        self,
        selected: "OptimizedVariant",
        selected_score: PolicyScore,
        all_scores: List[PolicyScore]
    ) -> str:
        """Generate human-readable selection rationale."""
        if len(all_scores) == 1:
            return f"Only candidate: {selected.variant_id}"
        
        return (
            f"Policy '{self.name}' selected {selected.variant_id} "
            f"(score={selected_score.score:.4f}) from {len(all_scores)} candidates. "
            f"{selected_score.explanation}"
        )
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"
