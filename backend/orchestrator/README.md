# SOAC Pipeline Orchestrator

## Pipeline Stages

```
Validation → Canonicalization → Optimization → Benchmarking → ALO → Deployment
```

## Usage

```python
from backend.orchestrator import run_soac_job, JobConfig

result = run_soac_job(Path("model.onnx"), JobConfig())

if result.success:
    print(f"Selected: {result.selected_variant}")
    print(f"Bundle: {result.deployment_bundle}")
```

## Rules

- Strict ordering
- Failure aborts pipeline
- Cleanup guaranteed
