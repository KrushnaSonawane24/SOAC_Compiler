# SOAC Benchmark Engine

## Metrics

| Metric | Method |
|--------|--------|
| Accuracy | Top-1 on dataset |
| Latency | Median of N runs |
| Memory | Peak RSS |
| Size | File size |

## Usage

```python
from backend.benchmark import benchmark_model, evaluate_accuracy

# Full benchmark
result = benchmark_model(onnx_path, dataset)
print(result.latency.median_ms)
print(result.accuracy.accuracy)

# Accuracy only
acc = evaluate_accuracy(onnx_path, dataset)
```

## Accuracy Enforcement

```
IF accuracy_drop > 2%:
    is_valid = False
```
