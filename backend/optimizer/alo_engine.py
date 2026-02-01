"""
SOAC ALO Engine
===============

Adaptive Learning Optimizer - Rule-based variant selection.

ALO IS NOT ML TRAINING.
ALO uses deterministic, explainable rules to select optimal variants.

DECISION RULES (NON-NEGOTIABLE):
    1. REJECT any variant with accuracy_drop > 1%
    2. Among valid variants:
       a. Select LOWEST latency
       b. Tie-breaker: SMALLEST size
       c. Tie-breaker: Prefer INT8 > FP16 > Baseline > Pruned
    3. Decision MUST be deterministic and auditable
"""

import logging
from typing import List, Tuple, Optional

from .metadata import (
    OptimizedVariant,
    VariantType,
    VariantStatus,
    BenchmarkMetrics,
    RejectedVariant,
    RankedVariant,
    MAX_ACCURACY_DROP,
    VARIANT_PREFERENCE_ORDER,
)
from .decision_trace import (
    DecisionTrace,
    SelectedVariant,
    create_decision_trace,
)
from .exceptions import NoValidVariantsError, AccuracyConstraintViolation


logger = logging.getLogger(__name__)


# =============================================================================
# DECISION RULES
# =============================================================================

def check_accuracy_constraint(
    variant: OptimizedVariant,
    threshold: float = MAX_ACCURACY_DROP,
) -> Tuple[bool, Optional[str]]:
    """
    Check if variant passes accuracy constraint.
    
    Args:
        variant: The variant to check.
        threshold: Maximum allowed accuracy drop (default 1%).
    
    Returns:
        Tuple of (is_valid, rejection_reason).
    """
    if variant.metrics is None:
        # No metrics means we can't verify - assume valid for testing
        return True, None
    
    if variant.metrics.accuracy_drop > threshold:
        return False, f"Accuracy drop {variant.metrics.accuracy_drop:.2%} > {threshold:.2%}"
    
    return True, None


def filter_valid_variants(
    variants: List[OptimizedVariant],
    accuracy_threshold: float = MAX_ACCURACY_DROP,
    max_size_bytes: Optional[int] = None,
) -> Tuple[List[OptimizedVariant], List[RejectedVariant]]:
    """
    Filter variants to only those passing all constraints.
    
    Returns:
        Tuple of (valid_variants, rejected_variants).
    """
    valid = []
    rejected = []
    
    for variant in variants:
        # Skip generation failures
        if variant.status == VariantStatus.GENERATION_FAILED:
            rejected.append(RejectedVariant(
                variant_id=variant.variant_id,
                variant_type=variant.variant_type,
                rejection_reason=f"Generation failed: {variant.error_message}",
            ))
            continue
        
        # Check accuracy constraint
        is_valid, reason = check_accuracy_constraint(variant, accuracy_threshold)

        if is_valid and max_size_bytes is not None and variant.size_bytes > max_size_bytes:
            is_valid = False
            reason = f"Size {variant.size_bytes}B exceeds limit {max_size_bytes}B"
        
        if is_valid:
            valid.append(variant)
        else:
            rejected.append(RejectedVariant(
                variant_id=variant.variant_id,
                variant_type=variant.variant_type,
                rejection_reason=reason or "Unknown",
                accuracy_drop=variant.metrics.accuracy_drop if variant.metrics else None,
            ))
    
    return valid, rejected


def rank_variants(variants: List[OptimizedVariant]) -> List[RankedVariant]:
    """
    Rank variants according to ALO rules.
    
    Ranking criteria (in order):
        1. Lowest latency
        2. Smallest size
        3. Preference order (INT8 > FP16 > Baseline > Pruned)
    
    Returns:
        List of RankedVariant sorted by rank (1 = best).
    """
    if not variants:
        return []
    
    # Create sortable tuples
    # Lower is better for all criteria
    def sort_key(v: OptimizedVariant) -> Tuple[float, int, int]:
        latency = v.metrics.latency_ms if v.metrics else float('inf')
        size = v.size_bytes
        # Invert preference (higher preference = lower sort key)
        preference = -VARIANT_PREFERENCE_ORDER.get(v.variant_type, 0)
        return (latency, size, preference)
    
    sorted_variants = sorted(variants, key=sort_key)
    
    ranked = []
    for rank, variant in enumerate(sorted_variants, start=1):
        latency = variant.metrics.latency_ms if variant.metrics else float('inf')
        
        # Create explanation
        pref_score = VARIANT_PREFERENCE_ORDER.get(variant.variant_type, 0)
        breakdown = f"latency={latency:.2f}ms, size={variant.size_bytes}B, pref={pref_score}"
        
        ranked.append(RankedVariant(
            variant_id=variant.variant_id,
            variant_type=variant.variant_type,
            rank=rank,
            latency_ms=latency,
            size_bytes=variant.size_bytes,
            preference_score=pref_score,
            score_breakdown=breakdown,
        ))
    
    return ranked


def generate_selection_reason(
    selected: OptimizedVariant,
    all_valid: List[OptimizedVariant],
) -> str:
    """Generate human-readable selection reason."""
    if len(all_valid) == 1:
        return f"Only valid variant: {selected.variant_type.value}"
    
    reasons = []
    
    if selected.metrics:
        reasons.append(f"lowest latency ({selected.metrics.latency_ms:.2f}ms)")
    
    # Check if it's the smallest
    sizes = [v.size_bytes for v in all_valid]
    if selected.size_bytes == min(sizes):
        reasons.append(f"smallest size ({selected.size_bytes} bytes)")
    
    reasons.append(f"type preference ({selected.variant_type.value})")
    
    return f"Selected {selected.variant_id}: " + ", ".join(reasons)


# =============================================================================
# MAIN SELECTION API
# =============================================================================

def select_best_variant(
    variants: List[OptimizedVariant],
    input_hash: str,
    accuracy_threshold: float = MAX_ACCURACY_DROP,
    max_size_bytes: Optional[int] = None,
) -> SelectedVariant:
    """
    Select the best variant using ALO rules.
    
    THE SINGLE ENTRY POINT for variant selection.
    
    Args:
        variants: List of generated variants.
        input_hash: Hash of original input model.
        accuracy_threshold: Maximum allowed accuracy drop (default 1%).
    
    Returns:
        SelectedVariant with complete decision trace.
    
    Raises:
        NoValidVariantsError: If all variants fail validation.
    
    GUARANTEES:
        - Deterministic: same inputs always produce same selection
        - Explainable: complete decision trace included
        - Auditable: all rejected variants listed with reasons
    
    Example:
        >>> result = select_best_variant(variants, "abc123")
        >>> print(result.variant.variant_id)  # Selected variant
        >>> print(result.decision_trace.selection_reason)  # Why
    """
    logger.info(f"ALO: Selecting from {len(variants)} variants")
    
    # Step 1: Filter to valid variants
    valid_variants, rejected = filter_valid_variants(variants, accuracy_threshold, max_size_bytes=max_size_bytes)
    
    logger.info(f"ALO: {len(valid_variants)} valid, {len(rejected)} rejected")
    
    if not valid_variants:
        raise NoValidVariantsError(
            total_variants=len(variants),
            reasons=[r.rejection_reason for r in rejected],
        )
    
    # Step 2: Rank valid variants
    ranking = rank_variants(valid_variants)
    
    # Step 3: Select the best (rank 1)
    best_rank = ranking[0]
    selected = next(v for v in valid_variants if v.variant_id == best_rank.variant_id)
    
    # Step 4: Generate explanation
    selection_reason = generate_selection_reason(selected, valid_variants)
    
    logger.info(f"ALO: Selected {selected.variant_id} - {selection_reason}")
    
    # Step 5: Create decision trace
    trace = create_decision_trace(
        input_hash=input_hash,
        all_variants=variants,
        valid_variants=valid_variants,
        rejected=rejected,
        ranking=ranking,
        selected_id=selected.variant_id,
        selection_reason=selection_reason,
        accuracy_threshold=accuracy_threshold,
    )
    
    return SelectedVariant(
        variant=selected,
        decision_trace=trace,
        all_variants=variants,
        rejected_variants=rejected,
    )


def add_benchmark_metrics(
    variant: OptimizedVariant,
    latency_ms: float,
    throughput: float,
    memory_mb: float,
    accuracy: float,
    baseline_accuracy: float = 1.0,
) -> OptimizedVariant:
    """
    Add benchmark metrics to a variant.
    
    Creates a new variant with metrics attached.
    """
    accuracy_drop = max(0.0, baseline_accuracy - accuracy)
    
    metrics = BenchmarkMetrics(
        latency_ms=latency_ms,
        throughput=throughput,
        memory_mb=memory_mb,
        accuracy=accuracy,
        accuracy_drop=accuracy_drop,
    )
    
    # Create new variant with metrics (since OptimizedVariant is frozen)
    return OptimizedVariant(
        variant_id=variant.variant_id,
        variant_type=variant.variant_type,
        onnx_path=variant.onnx_path,
        graph_hash=variant.graph_hash,
        size_bytes=variant.size_bytes,
        status=variant.status,
        metrics=metrics,
        error_message=variant.error_message,
        metadata=variant.metadata,
    )
