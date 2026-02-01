# SOAC Optimization Engine & ALO

## Overview

Generates optimized variants and selects the best using **deterministic rules**.

## Key Guarantee

> **ALO uses NO ML/training. All decisions are rule-based and auditable.**

## Variants Generated

| Type | Method |
|------|--------|
| Baseline | Copy of original |
| FP16 | Float16 quantization |
| INT8 | Dynamic INT8 quantization |
| Pruned | Zero-channel removal |

## ALO Decision Rules

```
1. REJECT if accuracy_drop > 2%
2. SELECT lowest latency
3. TIE: smallest size
4. TIE: INT8 > FP16 > Baseline > Pruned
```

## Usage

```python
from backend.optimizer import generate_variants, select_best_variant

# Generate all variants
variants = generate_variants(onnx_path, input_hash, output_dir)

# Select best using ALO
result = select_best_variant(variants, input_hash)

# Access decision
print(result.variant.variant_id)
print(result.decision_trace.selection_reason)
```

## Decision Trace

Every selection includes full audit trail:
- Which variants were generated
- Why each was rejected/ranked
- Complete score breakdown
