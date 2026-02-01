# Accuracy and Benchmarking Guarantees

In SOAC, accuracy is treated as a correctness constraint, not a “nice-to-have” metric.

## Accuracy rule

- Accuracy drop must be <= 2%
- Any variant violating this rule is rejected by the compiler

## Benchmarked metrics

- Top-1 accuracy
- Latency (ms)
- Model size (MB)
- Memory usage

## Reports generated

- JSON
- CSV
- PDF
- Visual charts
- Explainability report (what changed and why)
