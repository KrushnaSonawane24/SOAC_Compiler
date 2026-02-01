# Optimization in SOAC

SOAC generates multiple optimized variants and selects the best one using compiler logic (passes, cost models, constraints, and policies).

## Optimization techniques

- FP16 quantization
- INT8 quantization
- Structured pruning
- Baseline (no optimization)

## Adaptive Learning Optimizer (ALO)

ALO is not ML-based. It is a compiler decision engine that performs:

- Variant generation
- Benchmarking
- Cost estimation
- Constraint checking
- Policy-driven selection

## Policies

Common policies include:

- Latency-first (default)
- Accuracy-first
- Mobile-first

Policies never bypass constraints. If a variant violates correctness rules, it is rejected even if it is faster.
