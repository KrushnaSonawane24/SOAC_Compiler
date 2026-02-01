# What is SOAC?

SOAC (Self-Optimizing AI Compiler) treats pretrained AI models the same way traditional compilers treat programs.

- C/C++ code is compiled by GCC or LLVM
- Java code is compiled into bytecode
- SOAC compiles pretrained AI models into optimized, secure, and deployable artifacts for real devices

## What SOAC is not

- Not a training framework
- Not AutoML
- Not a simple model converter
- Not a benchmark script

## What SOAC is

- A compiler
- Deterministic and reproducible (same inputs produce the same outputs)
- Constraint-based (accuracy is enforced as correctness)
- Explainable (every decision is logged and traceable)
- Secure by design
- Produces real deployment demos

## One-line definition

SOAC is a deterministic, constraint-based AI compiler that converts pretrained models into optimized, deployable artifacts with accuracy guarantees.

## Why SOAC exists

Most existing tools do parts of the job:

- Convert models
- Optimize models
- Benchmark models

But they do not treat model conversion and optimization as a compiler problem with a formal IR, explicit passes, constraints, and verifiable outputs.

SOAC solves this by:

- Introducing a formal Intermediate Representation (SOAC IR)
- Applying compiler passes in a deterministic pipeline
- Using cost models and constraints to select variants
- Producing outputs you can audit, reproduce, and deploy
