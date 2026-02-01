"""
SOAC Benchmark Variants Pass
============================

Benchmarks generated model variants for performance comparison.

This pass wraps the existing benchmark infrastructure.
"""

from datetime import datetime, timezone
from typing import List
from dataclasses import dataclass
import logging

from .base import BasePass, PassContext, PassResult, TraceEntry
from backend.optimizer.metadata import OptimizedVariant
from backend.optimizer import add_benchmark_metrics

logger = logging.getLogger(__name__)


@dataclass
class BenchmarkInput:
    """Input for benchmark pass."""
    variants: List[OptimizedVariant]
    warmup_runs: int = 5
    measured_runs: int = 20


class BenchmarkVariantsPass(BasePass):
    """
    Benchmark model variants.
    
    Measures:
        1. Latency (median, p99)
        2. Throughput
        3. Memory usage
        4. Accuracy vs baseline
    
    Uses the existing benchmark infrastructure.
    """
    
    name = "benchmark_variants"
    description = "Measure variant performance"
    
    def run(
        self, 
        input: BenchmarkInput, 
        ctx: PassContext
    ) -> PassResult[List[OptimizedVariant]]:
        """Execute benchmark pass."""
        from backend.benchmark import (
            measure_latency, 
            measure_memory, 
            create_sample_input,
            create_synthetic_dataset,
            evaluate_accuracy,
        )
        
        start_time = datetime.now(timezone.utc)
        
        # Create synthetic dataset for accuracy
        dataset = create_synthetic_dataset(num_samples=20, seed=42)
        baseline_accuracy = None
        
        benchmarked = []
        
        for variant in input.variants:
            if not variant.is_valid:
                benchmarked.append(variant)
                continue
            
            try:
                # Create sample input
                sample_input = create_sample_input(variant.onnx_path)
                
                # Measure latency
                latency = measure_latency(
                    variant.onnx_path,
                    sample_input,
                    warmup_runs=input.warmup_runs,
                    measured_runs=input.measured_runs,
                )
                
                # Measure memory
                memory = measure_memory(variant.onnx_path, sample_input)
                
                # Get accuracy
                acc_result = evaluate_accuracy(
                    variant.onnx_path,
                    dataset,
                    baseline_accuracy=baseline_accuracy,
                )
                
                if baseline_accuracy is None:
                    baseline_accuracy = acc_result.accuracy
                
                # Add metrics to variant
                variant = add_benchmark_metrics(
                    variant,
                    latency_ms=latency.median_ms,
                    throughput=1000 / latency.median_ms,
                    memory_mb=memory.peak_mb,
                    accuracy=acc_result.accuracy,
                    baseline_accuracy=baseline_accuracy,
                )
                
                ctx.log(f"Benchmarked {variant.variant_type.value}: {latency.median_ms:.2f}ms")
                
            except Exception as e:
                ctx.log(f"Benchmark failed for {variant.variant_type.value}: {e}")
            
            benchmarked.append(variant)
        
        # Count benchmarked
        benchmarked_count = sum(1 for v in benchmarked if v.metrics is not None)
        
        ctx.log(f"Benchmarked {benchmarked_count}/{len(input.variants)} variants")
        ctx.set_metadata("variants_benchmarked", benchmarked_count)
        
        trace = TraceEntry(
            pass_name=self.name,
            timestamp=start_time.isoformat(),
            action="benchmarked",
            details={
                "total_variants": len(input.variants),
                "benchmarked": benchmarked_count,
                "baseline_accuracy": baseline_accuracy,
            },
        )
        
        return PassResult(
            success=True,
            output=benchmarked,
            duration_ms=0.0,
            trace=trace,
        )
