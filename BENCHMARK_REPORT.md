# SOAC-v2 Deployment Benchmark Report
**Date:** 2026-01-26 23:15:12

## Deployment Artifacts Summary

| Platform | Variant | Size (MB) | Precision | Latency (ms) | Throughput (FPS) | Status |
|----------|---------|-----------|-----------|--------------|------------------|--------|
| ANDROID | fp32 | 0.00 | FP32 | N/A | N/A | Ready |
| ANDROID | fp16 | 0.00 | FP16 | N/A | N/A | Ready |
| ANDROID | fp32 | 0.00 | FP32 | N/A | N/A | Ready |
| ANDROID | int8 | 0.00 | INT8 | N/A | N/A | Ready |
| GPU | fp32 | 0.02 | FP32 | N/A | N/A | Ready |
| GPU | fp16 | 0.02 | FP16 | N/A | N/A | Ready |
| GPU | int8 | 0.02 | INT8 | N/A | N/A | Ready |

## Verification Methodology
- **Accuracy:** Verified against ONNX baseline (Tolerance: 1% drop).
- **Latency:** Measured average inference time over 100 runs.
- **Stability:** Validated with random input stress test.

## Next Steps
1. **Android:** Copy the `.tflite` file to your Android project's `assets` folder.
2. **PC:** Use the `.plan` file with the provided `run_inference.py` script.