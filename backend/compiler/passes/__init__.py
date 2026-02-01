"""
SOAC Compiler Passes
====================

Explicit compiler passes for the SOAC compilation pipeline.

This package provides:
    - BasePass: Abstract base class for all passes
    - PassContext: Context shared across passes
    - PassResult: Result of pass execution
    
    Lowering:
        - LowerONNXToSOACIRPass: Convert ONNX to SOAC IR
    
    Validation & Canonicalization:
        - ValidateIRPass: Validate IR structure
        - CanonicalizeIRPass: Normalize IR
        - InferShapesPass: Infer tensor shapes
        - InferMemoryPass: Compute memory estimates
    
    Optimization:
        - GenerateVariantsPass: Create optimized variants
        - BenchmarkVariantsPass: Measure variant performance
        - SelectVariantPass: Choose best variant
        - LowerToBackendPass: Generate deployment artifacts

All passes are:
    - Deterministic: Same input always produces same output
    - Logged: All decisions are recorded
    - Explainable: Trace entries for audit
"""

from .base import (
    BasePass,
    PassContext,
    PassResult,
    TraceEntry,
)
from .lower_onnx import LowerONNXToSOACIRPass
from .validate_ir import ValidateIRPass
from .canonicalize_ir import CanonicalizeIRPass
from .infer_shapes import InferShapesPass
from .infer_memory import InferMemoryPass
from .generate_variants import GenerateVariantsPass
from .benchmark import BenchmarkVariantsPass
from .select_variant import SelectVariantPass
from .lower_backend import LowerToBackendPass

__all__ = [
    # Base classes
    "BasePass",
    "PassContext", 
    "PassResult",
    "TraceEntry",
    
    # Passes
    "LowerONNXToSOACIRPass",
    "ValidateIRPass",
    "CanonicalizeIRPass",
    "InferShapesPass",
    "InferMemoryPass",
    "GenerateVariantsPass",
    "BenchmarkVariantsPass",
    "SelectVariantPass",
    "LowerToBackendPass",
]
