# SOAC Compiler Pipeline (Step-by-step)

SOAC executes compilation through explicit compiler passes, not ad-hoc scripts. Each pass has a single responsibility, produces traceable output, and runs deterministically.

## Step 1 — Input validation

- File extension whitelist
- MIME type verification
- Magic byte checks
- File size limits
- Training graph rejection (only inference models allowed)

## Step 2 — Frontend conversion

- All models are converted into ONNX
- PyTorch and TensorFlow are treated as frontend languages
- Training-only operators are blocked

## Step 3 — Lowering to SOAC IR

The ONNX graph is lowered into compiler IR objects like:

- IRTensor
- IROperator
- IRGraph

IR is designed to be immutable and deterministic, so the same model yields the same IR.

## Step 4 — Compiler passes

Passes execute sequentially (typical order):

- ValidateIRPass
- CanonicalizeIRPass
- InferShapesPass
- InferMemoryPass
- GenerateVariantsPass
- BenchmarkVariantsPass
- SelectVariantPass
- LowerToBackendPass

## Step 5 — Backend lowering

The selected variant is lowered into deployable targets such as:

- TFLite
- TensorRT (if GPU is available)
- ONNX Runtime
