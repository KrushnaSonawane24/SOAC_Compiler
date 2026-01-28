# SOAC-v2 Unified Architecture & Deployment Pipeline

This document outlines the unified architecture and deployment pipeline for the Self-Optimizing AI Compiler (SOAC-v2), designed to deliver production-ready AI models for Android (TFLite) and NVIDIA PC (TensorRT).

## 1. High-Level Architecture

The system follows a strict, stage-gated pipeline architecture:

```mermaid
graph LR
    User[User/Frontend] --> API[FastAPI Backend]
    API --> Validator[Model Validator]
    Validator --> Canonicalizer[ONNX Canonicalizer]
    Canonicalizer --> Optimizer[Optimization Engine]
    Optimizer --> ALO[ALO Selection Strategy]
    ALO --> Deployment[Deployment Packaging]
    Deployment --> Artifacts[Final Artifacts]
```

### Core Components

1.  **Frontend (React + Vite):**
    -   User interface for uploading models and monitoring jobs.
    -   Secure JWT authentication.
    -   Real-time status updates via polling.

2.  **Backend (FastAPI):**
    -   **Validation Gate:** Ensures uploaded models are valid (ONNX/PyTorch/TensorFlow) and virus-free.
    -   **Canonicalization:** Converts all inputs to a standardized ONNX Intermediate Representation (IR v8, Opset 13).
    -   **Optimization:** Applies quantization (INT8, FP16), pruning, and graph fusion.
    -   **ALO (Adaptive Latency Optimization):** Selects the best variant based on constraints (Size < 200MB, Accuracy Drop < 1%).
    -   **Deployment:** Generates platform-specific artifacts.

## 2. Deployment Pipeline Details

The deployment pipeline is designed to be failure-safe and deterministic.

### A. Android Deployment (TFLite)
-   **Toolchain:** `onnx2tf` (superior to standard TFLite converter for ONNX compatibility).
-   **Variants:**
    -   **INT8:** Fully quantized using calibration data (per-tensor).
    -   **FP16:** Reduced precision for GPU/NPU acceleration.
    -   **FP32:** Baseline fallback.
-   **Calibration:** Automated generation of calibration data to ensure accurate INT8 conversion.
-   **Output:** `.tflite` files compatible with Android API 23+.

### B. NVIDIA PC Deployment (TensorRT)
-   **Toolchain:** `TensorRT` + `cuda-python`.
-   **Variants:**
    -   **INT8:** Uses `IInt8EntropyCalibrator2` with custom CUDA memory management.
    -   **FP16:** High-performance mixed precision.
    -   **FP32:** Baseline.
-   **Constraints:** Strict memory allocation and static graph optimization.
-   **Output:** `.plan` (serialized engine) files.

## 3. Directory Structure

```
soac_MODEL/
├── backend/
│   ├── api/            # REST API endpoints
│   ├── deployment/     # Deployment logic (TFLite/TensorRT)
│   ├── optimizer/      # Quantization & Pruning
│   └── validator/      # Input validation
├── demos/
│   ├── android/        # Android integration guide
│   └── pc/             # PC inference scripts
├── frontend/           # React application
└── verify_deployment_out/ # Generated artifacts
```

## 4. Usage Guide

### Running the System
1.  **Backend:** `venv\Scripts\python -m uvicorn backend.api:app --reload`
2.  **Frontend:** `npm start` (in `frontend/` dir)

### Verifying Deployment
Run the verification script to generate artifacts from a dummy model:
```bash
venv\Scripts\python verify_deployment.py
```

### Generating Reports
Generate a benchmark report for the created artifacts:
```bash
venv\Scripts\python generate_benchmark_report.py verify_deployment_out\artifacts
```
