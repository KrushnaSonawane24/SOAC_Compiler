"""
SOAC Intermediate Representation (IR)
=====================================

The formal IR for the SOAC compiler.

This package provides:
    - IRDataType, IRLayout, IRShape: Type definitions
    - IRTensor: Tensor representation with shape, dtype, layout
    - IROperator: Operator representation with attributes
    - IRGraph: Complete graph representation with deterministic hashing

IMMUTABILITY:
    All IR objects are frozen dataclasses - immutable after construction.

DETERMINISM:
    IR hashing is deterministic - same graph always produces same hash.

Example:
    >>> from backend.compiler.ir import IRGraph, IRTensor, IROperator
    >>> tensor = IRTensor(name="x", shape=(1, 3, 224, 224), dtype=IRDataType.FLOAT32)
    >>> graph = IRGraph.from_onnx(model)
    >>> print(graph.hash())  # Deterministic hash
"""

from .types import IRDataType, IRLayout, IRShape
from .tensor import IRTensor
from .operator import IROperator
from .graph import IRGraph
from .hashing import compute_ir_hash
from .extended_metadata import (
    ExtendedMetadata,
    DataLayout,
    DataLayoutHint,
    FusionStrategy,
    FusionHint,
    HardwareTarget,
    AffinityLevel,
    HardwareAffinityTag,
)

__all__ = [
    "IRDataType",
    "IRLayout", 
    "IRShape",
    "IRTensor",
    "IROperator",
    "IRGraph",
    "compute_ir_hash",
    # Extended metadata (opt-in)
    "ExtendedMetadata",
    "DataLayout",
    "DataLayoutHint",
    "FusionStrategy",
    "FusionHint",
    "HardwareTarget",
    "AffinityLevel",
    "HardwareAffinityTag",
]
