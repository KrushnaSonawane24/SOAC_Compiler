# SOAC Architecture Overview

SOAC follows a layered compiler architecture inspired by LLVM-style design: frontend formats are lowered into a dedicated IR, then transformed by compiler passes, evaluated by cost models and constraints, and finally lowered into deployment artifacts.

## High-level architecture

```text
Frontend Formats (ONNX / H5 / PyTorch)
            |
            v
ONNX Frontend (normalization + conversion)
            |
            v
SOAC IR (Intermediate Representation)
            |
            v
Compiler Passes (validation, canonicalization, variants, ...)
            |
            v
Cost Models + Constraints (latency/size/memory + accuracy rules)
            |
            v
Policy-Driven Selection (choose best valid variant)
            |
            v
Backend Lowering
            |
            v
Deployment Artifacts (TFLite / TensorRT / ONNX Runtime demos)
```

## Key layers

### 1) Frontend layer

- Accepts pretrained inference models only
- Supported formats:
  - ONNX (.onnx)
  - TensorFlow / Keras (.h5)
  - PyTorch (.pt / .pth)
- All inputs are converted into ONNX and treated as a frontend language, not the compiler core

### 2) Compiler core (SOAC IR)

- SOAC defines its own Intermediate Representation
- ONNX graphs are lowered into SOAC IR
- All compiler logic operates on SOAC IR, not on ONNX
- This IR boundary is what makes SOAC behave like a compiler

### 3) Optimization and decision layer

- Multiple optimized variants are generated
- Cost models estimate performance (latency, size, memory)
- Constraints enforce correctness (accuracy bounds and safety rules)
- Policies decide which valid variant wins

### 4) Backend layer

SOAC emits deployable outputs, such as:

- TFLite (Android)
- TensorRT (GPU, when available)
- ONNX Runtime (CPU)
