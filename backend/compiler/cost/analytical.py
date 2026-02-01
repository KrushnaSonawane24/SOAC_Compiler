"""
SOAC Analytical Cost Model
==========================

Deterministic cost estimation based on IR structure analysis.

This cost model estimates latency, memory, and other metrics WITHOUT
requiring actual benchmarks. It uses:
    - Operator FLOP counts
    - Tensor shape analysis
    - Hardware-specific lookup tables

GUARANTEES:
    - Fully deterministic: same input always produces same output
    - No ML training: uses analytical formulas only
    - No external dependencies: works offline
    - Coexists with EmpiricalCostModel
"""

from typing import TYPE_CHECKING, Dict, Any, Optional, Tuple
import logging

from .base import CostModel
from .types import CostEstimate, CostExplanation

if TYPE_CHECKING:
    from backend.compiler.ir import IRGraph, IROperator, IRTensor
    from backend.optimizer.metadata import OptimizedVariant

logger = logging.getLogger(__name__)


# =============================================================================
# OPERATOR FLOP TABLES
# =============================================================================

# FLOPs per operation for common operators
# These are multipliers applied to input/output dimensions
OPERATOR_FLOP_MULTIPLIERS: Dict[str, float] = {
    # Convolution: 2 * N * C_out * H_out * W_out * C_in * K_h * K_w
    "Conv": 2.0,
    "ConvTranspose": 2.0,
    
    # Matrix operations: 2 * M * N * K
    "MatMul": 2.0,
    "Gemm": 2.0,
    
    # Elementwise: 1 op per element
    "Relu": 1.0,
    "Sigmoid": 4.0,  # exp, add, div
    "Tanh": 6.0,     # exp, sub, add, div
    "Add": 1.0,
    "Sub": 1.0,
    "Mul": 1.0,
    "Div": 1.0,
    "Sqrt": 4.0,
    "Exp": 4.0,
    "Log": 4.0,
    
    # Reduction operations
    "ReduceMean": 2.0,  # sum + div
    "ReduceSum": 1.0,
    "ReduceMax": 1.0,
    "ReduceMin": 1.0,
    
    # Normalization
    "BatchNormalization": 4.0,  # mean, var, normalize, scale/shift
    "LayerNormalization": 4.0,
    "InstanceNormalization": 4.0,
    
    # Pooling
    "MaxPool": 1.0,
    "AveragePool": 2.0,  # sum + div
    "GlobalAveragePool": 2.0,
    
    # Attention
    "Softmax": 5.0,  # exp, sum, div per row
    
    # Reshape operations (no FLOPs, just memory)
    "Reshape": 0.0,
    "Transpose": 0.0,
    "Flatten": 0.0,
    "Squeeze": 0.0,
    "Unsqueeze": 0.0,
    
    # Default for unknown operators
    "_default": 1.0,
}

# Estimated GFLOPS for different hardware targets
HARDWARE_GFLOPS: Dict[str, float] = {
    "cpu": 100.0,        # ~100 GFLOPS for typical CPU
    "gpu": 10000.0,      # ~10 TFLOPS for typical GPU
    "mobile_cpu": 20.0,  # ~20 GFLOPS for mobile CPU
    "mobile_gpu": 500.0, # ~500 GFLOPS for mobile GPU
    "tpu": 50000.0,      # ~50 TFLOPS for TPU
    "npu": 5000.0,       # ~5 TFLOPS for typical NPU
}

# Memory bandwidth in GB/s
HARDWARE_BANDWIDTH: Dict[str, float] = {
    "cpu": 50.0,
    "gpu": 900.0,
    "mobile_cpu": 20.0,
    "mobile_gpu": 50.0,
    "tpu": 1500.0,
    "npu": 200.0,
}


# =============================================================================
# ANALYTICAL COST MODEL
# =============================================================================

class AnalyticalCostModel(CostModel):
    """
    Analytical cost model based on theoretical FLOP analysis.
    
    Estimates costs WITHOUT running actual benchmarks by:
        1. Counting FLOPs from IR structure
        2. Estimating memory from tensor shapes
        3. Using hardware lookup tables for throughput
    
    Properties:
        - Deterministic: Same IR always produces same estimate
        - No training: Pure analytical formulas
        - No I/O: Works without external resources
    
    Use Cases:
        - Quick cost estimates before benchmarking
        - Comparison when benchmarks unavailable
        - What-if analysis with modified configurations
    
    Limitations:
        - Less accurate than empirical measurements
        - Doesn't account for memory bandwidth effects
        - Assumes perfect parallelization
    """
    
    name = "analytical_cost_model"
    
    def __init__(self, target_hardware: str = "cpu"):
        """
        Initialize analytical cost model.
        
        Args:
            target_hardware: Target hardware for estimates (cpu, gpu, etc.)
        """
        self.target_hardware = target_hardware.lower()
        self.gflops = HARDWARE_GFLOPS.get(self.target_hardware, 100.0)
        self.bandwidth_gbps = HARDWARE_BANDWIDTH.get(self.target_hardware, 50.0)
    
    def estimate_operator_flops(self, op: "IROperator", tensors: Dict[str, "IRTensor"]) -> int:
        """
        Estimate FLOPs for a single operator.
        
        Args:
            op: IR operator
            tensors: Dictionary of all tensors in the graph
        
        Returns:
            Estimated FLOPs for this operator
        """
        op_type = op.op_type
        multiplier = OPERATOR_FLOP_MULTIPLIERS.get(op_type, OPERATOR_FLOP_MULTIPLIERS["_default"])
        
        if multiplier == 0:
            return 0
        
        # Get input/output shapes
        total_elements = 0
        for input_name in op.inputs:
            if input_name in tensors:
                tensor = tensors[input_name]
                if tensor.shape:
                    elements = 1
                    for dim in tensor.shape:
                        if dim is not None and dim > 0:
                            elements *= dim
                    total_elements += elements
        
        # Special handling for specific operators
        if op_type in ("Conv", "ConvTranspose"):
            return self._estimate_conv_flops(op, tensors)
        elif op_type in ("MatMul", "Gemm"):
            return self._estimate_matmul_flops(op, tensors)
        else:
            return int(total_elements * multiplier)
    
    def _estimate_conv_flops(self, op: "IROperator", tensors: Dict[str, "IRTensor"]) -> int:
        """Estimate FLOPs for convolution operator."""
        # Formula: 2 * N * C_out * H_out * W_out * C_in * K_h * K_w
        
        # Try to get kernel size from attributes
        kernel_shape = op.get_attribute("kernel_shape", [3, 3])
        if not isinstance(kernel_shape, (list, tuple)):
            kernel_shape = [3, 3]
        
        k_h = kernel_shape[0] if len(kernel_shape) > 0 else 3
        k_w = kernel_shape[1] if len(kernel_shape) > 1 else 3
        
        # Get input shape
        if op.inputs and op.inputs[0] in tensors:
            input_tensor = tensors[op.inputs[0]]
            shape = input_tensor.shape
            if len(shape) >= 4:
                n, c_in, h, w = shape[0] or 1, shape[1] or 64, shape[2] or 224, shape[3] or 224
            else:
                n, c_in, h, w = 1, 64, 224, 224
        else:
            n, c_in, h, w = 1, 64, 224, 224
        
        # Get output channels from weights
        c_out = c_in  # Default
        if len(op.inputs) > 1 and op.inputs[1] in tensors:
            weight_tensor = tensors[op.inputs[1]]
            if weight_tensor.shape and len(weight_tensor.shape) >= 1:
                c_out = weight_tensor.shape[0] or c_in
        
        # Estimate output size (assuming same padding and stride 1)
        strides = op.get_attribute("strides", [1, 1])
        s_h = strides[0] if len(strides) > 0 else 1
        s_w = strides[1] if len(strides) > 1 else 1
        h_out = (h + s_h - 1) // s_h
        w_out = (w + s_w - 1) // s_w
        
        flops = 2 * n * c_out * h_out * w_out * c_in * k_h * k_w
        return int(flops)
    
    def _estimate_matmul_flops(self, op: "IROperator", tensors: Dict[str, "IRTensor"]) -> int:
        """Estimate FLOPs for matrix multiplication."""
        # Formula: 2 * M * N * K
        
        if len(op.inputs) < 2:
            return 0
        
        # Get shapes
        a_shape = tensors.get(op.inputs[0])
        b_shape = tensors.get(op.inputs[1])
        
        if a_shape is None or b_shape is None:
            return 1000000  # Default estimate
        
        a_dims = a_shape.shape
        b_dims = b_shape.shape
        
        if len(a_dims) < 2 or len(b_dims) < 2:
            return 1000000
        
        m = a_dims[-2] or 1
        k = a_dims[-1] or 1
        n = b_dims[-1] or 1
        
        # Account for batch dimensions
        batch = 1
        for dim in a_dims[:-2]:
            if dim is not None and dim > 0:
                batch *= dim
        
        return int(2 * batch * m * n * k)
    
    def estimate_graph_flops(self, graph: "IRGraph") -> int:
        """
        Estimate total FLOPs for an IR graph.
        
        Args:
            graph: IR graph to analyze
        
        Returns:
            Total estimated FLOPs
        """
        total_flops = 0
        for op in graph.operators:
            total_flops += self.estimate_operator_flops(op, graph.tensors)
        return total_flops
    
    def estimate_memory_bytes(self, graph: "IRGraph") -> int:
        """
        Estimate peak memory usage in bytes.
        
        This estimates the memory needed to store all tensors.
        
        Args:
            graph: IR graph to analyze
        
        Returns:
            Estimated peak memory in bytes
        """
        # Sum all tensor sizes
        total_bytes = 0
        for tensor in graph.tensors.values():
            if tensor.memory_bytes is not None:
                total_bytes += tensor.memory_bytes
            elif tensor.shape:
                elements = 1
                for dim in tensor.shape:
                    if dim is not None and dim > 0:
                        elements *= dim
                # Assume 4 bytes per element (float32)
                total_bytes += elements * 4
        
        return total_bytes
    
    def estimate_latency_from_graph(self, graph: "IRGraph") -> float:
        """
        Estimate latency from IR graph structure.
        
        Args:
            graph: IR graph to analyze
        
        Returns:
            Estimated latency in milliseconds
        """
        flops = self.estimate_graph_flops(graph)
        
        # Convert GFLOPS to FLOPS/second, then to milliseconds
        flops_per_second = self.gflops * 1e9
        
        if flops_per_second <= 0:
            return float('inf')
        
        latency_seconds = flops / flops_per_second
        latency_ms = latency_seconds * 1000.0
        
        # Add memory overhead estimate
        memory_bytes = self.estimate_memory_bytes(graph)
        memory_overhead_ms = (memory_bytes / (self.bandwidth_gbps * 1e9)) * 1000.0
        
        return latency_ms + memory_overhead_ms
    
    def estimate_latency(self, variant: "OptimizedVariant") -> float:
        """
        Estimate latency for an optimized variant.
        
        Uses file size as a proxy when IR is not available.
        """
        # If variant has actual benchmark data, prefer that
        if variant.metrics is not None:
            return variant.metrics.latency_ms
        
        # Estimate from file size (rough heuristic)
        # Assumes ~1ms per MB for typical models on CPU
        size_mb = variant.size_bytes / (1024 * 1024)
        
        # Adjust for hardware
        hardware_factor = 100.0 / self.gflops  # Normalize to CPU baseline
        
        return size_mb * hardware_factor * 10.0  # 10ms per MB baseline
    
    def estimate_memory(self, variant: "OptimizedVariant") -> int:
        """
        Estimate memory usage for a variant.
        
        Uses file size as primary estimate (model must fit in memory).
        """
        # File size is minimum memory needed
        return variant.size_bytes * 2  # 2x for activations
    
    def estimate_size(self, variant: "OptimizedVariant") -> int:
        """Get file size."""
        return variant.size_bytes
    
    def estimate_accuracy_drop(self, variant: "OptimizedVariant") -> float:
        """
        Estimate accuracy drop based on quantization level.
        
        Uses heuristics based on variant type.
        """
        if variant.metrics is not None:
            return variant.metrics.accuracy_drop
        
        # Heuristic estimates based on quantization
        variant_type = variant.variant_type.value.lower()
        
        if "int8" in variant_type:
            return 0.01  # 1% estimated drop
        elif "int4" in variant_type:
            return 0.05  # 5% estimated drop
        elif "dynamic" in variant_type:
            return 0.005  # 0.5% estimated drop
        elif "pruned" in variant_type:
            return 0.02  # 2% estimated drop
        else:
            return 0.0  # Baseline, no drop
    
    def explain(self, variant: "OptimizedVariant") -> CostExplanation:
        """
        Generate analytical cost explanation.
        
        Shows how estimates were computed.
        """
        latency = self.estimate_latency(variant)
        memory = self.estimate_memory(variant)
        size = self.estimate_size(variant)
        accuracy_drop = self.estimate_accuracy_drop(variant)
        
        summary = (
            f"Analytical estimate for {variant.variant_type.value}: "
            f"~{latency:.2f}ms latency on {self.target_hardware}"
        )
        
        return CostExplanation(
            variant_id=variant.variant_id,
            summary=summary,
            latency_breakdown=f"~{latency:.2f}ms (analytical, {self.gflops} GFLOPS assumed)",
            memory_breakdown=f"~{memory/(1024*1024):.2f}MB (2x file size heuristic)",
            size_breakdown=f"{size/(1024*1024):.2f}MB (actual file size)",
            accuracy_note=f"~{accuracy_drop:.2%} estimated drop (heuristic)",
            details={
                "cost_model": self.name,
                "target_hardware": self.target_hardware,
                "gflops_assumed": self.gflops,
                "bandwidth_gbps": self.bandwidth_gbps,
                "method": "analytical",
            },
        )


# =============================================================================
# FACTORY FUNCTIONS
# =============================================================================

def create_cpu_cost_model() -> AnalyticalCostModel:
    """Create analytical cost model for CPU."""
    return AnalyticalCostModel(target_hardware="cpu")


def create_gpu_cost_model() -> AnalyticalCostModel:
    """Create analytical cost model for GPU."""
    return AnalyticalCostModel(target_hardware="gpu")


def create_mobile_cost_model() -> AnalyticalCostModel:
    """Create analytical cost model for mobile."""
    return AnalyticalCostModel(target_hardware="mobile_cpu")
