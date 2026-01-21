# SOAC Model Validator

## Overview

Strict validation layer that enforces SOAC's allowlist of supported inference models.

## Supported Formats

| Extension | Format | Full Validation |
|-----------|--------|-----------------|
| `.onnx` | ONNX | ✅ Yes |
| `.pt`, `.pth` | PyTorch | Requires conversion |
| `.h5`, `.keras` | Keras | Requires conversion |
| `.tflite` | TensorFlow Lite | Requires conversion |
| `.mlmodel` | CoreML | Requires conversion |
| `.pkl`, `.joblib` | Pickle | Requires conversion |

## Supported Architectures

### Classification
- MobileNetV2, MobileNetV3 (Small/Large)
- ResNet18, ResNet50
- EfficientNet-B0
- ShuffleNet-V2
- SqueezeNet 1.0/1.1

### Detection
- SSD-MobileNet-V2
- YOLOv5n, YOLOv5s

### Audio
- YAMNet
- Wav2Vec2-Tiny

## Rejection Codes

| Code | Meaning |
|------|---------|
| `FORMAT_NOT_SUPPORTED` | File format not in allowed list |
| `ARCHITECTURE_NOT_SUPPORTED` | Model not in supported architectures |
| `TRAINING_GRAPH_DETECTED` | Contains training ops (Adam, SGD, etc.) |
| `NON_DETERMINISTIC_OPS` | Contains random operators |
| `INVALID_INPUT_SHAPE` | Input shape invalid for architecture |

## Usage

```python
from backend.validator import validate_model, ModelValidationError

try:
    metadata = validate_model(Path("model.onnx"))
    print(f"Architecture: {metadata.architecture.name}")
    print(f"Type: {metadata.model_type.value}")
except ModelValidationError as e:
    print(f"Rejected: [{e.reason_code}] {e.message}")
```
