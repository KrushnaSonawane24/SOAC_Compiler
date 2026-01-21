# SOAC ONNX Canonicalizer

## Overview

Converts all supported formats to a **single canonical ONNX representation**.

## Key Guarantee

> **Same input always produces same output hash.**

## Supported Formats

| Format | Extension | Method |
|--------|-----------|--------|
| ONNX | `.onnx` | Normalize |
| Keras | `.h5`, `.keras` | tf2onnx |
| SavedModel | directory | tf2onnx |
| TFLite | `.tflite` | tf2onnx |
| CoreML | `.mlmodel` | coremltools |

## Canonicalization Rules

1. **Opset**: Fixed to 17
2. **Node Sorting**: Topological + alphabetical
3. **Name Normalization**: Lowercase, no special chars
4. **Graph Cleanup**: Remove unused initializers, Identity nodes
5. **Shape Inference**: Complete all tensor shapes
6. **Validation**: ONNX checker verification

## Usage

```python
from backend.compiler import canonicalize_model

result = canonicalize_model(Path("model.h5"))
print(result.graph_hash)   # Deterministic hash
print(result.onnx_path)    # Path to canonical .onnx
```

## Dependencies

- `onnx>=1.15.0`
- `tf2onnx>=1.16.0` (for TF conversion)
- `onnxruntime>=1.16.0` (optional, for shape inference)
