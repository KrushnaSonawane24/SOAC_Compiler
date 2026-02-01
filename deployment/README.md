# SOAC Deployment Engine

## Targets

| Target | Format | Tool |
|--------|--------|------|
| Android | `.tflite` | TensorFlow Lite |
| iOS | `.mlmodel` | coremltools |
| CPU | `.onnx` pkg | ONNX Runtime |
| GPU | `.plan` | TensorRT |

## Usage

```python
from backend.deployment import generate_deployment_artifacts

bundle = generate_deployment_artifacts(
    onnx_path,
    variant_id="int8_abc123",
    source_hash="abc123",
    output_dir=Path("./deploy"),
)

print(bundle.successful_count)
```

## Graceful Handling

Missing toolchains are skipped with clear status.
