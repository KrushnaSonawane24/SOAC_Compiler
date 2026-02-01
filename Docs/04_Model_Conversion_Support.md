# Supported Model Formats

SOAC supports pretrained inference models only.

## Supported formats

- ONNX: `.onnx` (preferred)
- TensorFlow / Keras: `.h5` (must be a full saved model)
- PyTorch: `.pt` / `.pth` (full model only)

## Common upload mistake (important)

This will fail because it saves weights only:

```python
model.save_weights("model.h5")
```

Correct approach (full model):

```python
model.save("model.h5")
```

## Why training models are rejected

Training graphs often include:

- Optimizers
- Loss functions
- Random operations

SOAC blocks these to guarantee:

- Security (no unexpected execution paths)
- Determinism (repeatable builds and benchmarks)
- Correct benchmarking (inference-only behavior)
