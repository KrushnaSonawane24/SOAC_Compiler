"""
SOAC Optimizer Package
======================

Optimization Engine and Adaptive Learning Optimizer (ALO).

PUBLIC API:
    - generate_variants(path, hash) -> List[OptimizedVariant]
    - select_best_variant(variants, hash) -> SelectedVariant

VARIANT TYPES:
    - Baseline - Original model
    - FP16 - 16-bit floating point
    - INT8 - 8-bit integer
    - Pruned - Structured pruning

ALO RULES:
    1. Reject accuracy drop > 2%
    2. Select lowest latency
    3. Tie-break: smallest size
    4. Tie-break: INT8 > FP16 > Baseline > Pruned
"""

# Main public API
from .variant_generator import (
    generate_variants,
    get_variant_summary,
    generate_variant_id,
)

from .alo_engine import (
    select_best_variant,
    add_benchmark_metrics,
    filter_valid_variants,
    rank_variants,
)

# Data structures
from .metadata import (
    VariantType,
    VariantStatus,
    OptimizedVariant,
    BenchmarkMetrics,
    RejectedVariant,
    RankedVariant,
    MAX_ACCURACY_DROP,
)

from .decision_trace import (
    DecisionTrace,
    SelectedVariant,
    create_decision_trace,
)

# Quantization & Pruning
from .quantization import (
    quantize_to_fp16,
    quantize_to_int8_dynamic,
    can_quantize_to_fp16,
    can_quantize_to_int8,
    get_quantization_support,
)

from .pruning import (
    prune_zero_channels,
    can_prune,
    analyze_pruning_opportunities,
)

# Exceptions
from .exceptions import (
    OptimizerError,
    VariantGenerationError,
    QuantizationError,
    PruningError,
    AccuracyConstraintViolation,
    NoValidVariantsError,
    BenchmarkError,
)

__version__ = "1.0.0"

__all__ = [
    # Main API
    "generate_variants",
    "select_best_variant",
    "get_variant_summary",
    "add_benchmark_metrics",
    
    # Data structures
    "VariantType",
    "VariantStatus",
    "OptimizedVariant",
    "BenchmarkMetrics",
    "RejectedVariant",
    "RankedVariant",
    "DecisionTrace",
    "SelectedVariant",
    
    # Quantization
    "quantize_to_fp16",
    "quantize_to_int8_dynamic",
    "can_quantize_to_fp16",
    "can_quantize_to_int8",
    
    # Pruning
    "prune_zero_channels",
    "can_prune",
    
    # Exceptions
    "OptimizerError",
    "VariantGenerationError",
    "QuantizationError",
    "PruningError",
    "AccuracyConstraintViolation",
    "NoValidVariantsError",
    "BenchmarkError",
    
    # Constants
    "MAX_ACCURACY_DROP",
]
