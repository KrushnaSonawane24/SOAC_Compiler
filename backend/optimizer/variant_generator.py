"""
SOAC Variant Generator
======================

Generates optimized model variants from canonical ONNX.

VARIANTS PRODUCED:
    1. Baseline - Original model (no changes)
    2. FP16 - 16-bit floating point quantization
    3. INT8 - 8-bit integer quantization
    4. Pruned - Structured pruning (conservative)

GUARANTEES:
    - Each variant is independently hashable
    - Generation is deterministic
    - Failures are clean and explicit
"""

import logging
import shutil
from pathlib import Path
from typing import List, Optional
import tempfile

try:
    import onnx
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False

from backend.compiler.hashing import compute_graph_hash

from .metadata import (
    VariantType,
    VariantStatus,
    OptimizedVariant,
    BenchmarkMetrics,
)
from .exceptions import VariantGenerationError
from .quantization import (
    quantize_to_fp16,
    quantize_to_int8_dynamic,
    can_quantize_to_fp16,
    can_quantize_to_int8,
)
from .pruning import prune_zero_channels, can_prune


logger = logging.getLogger(__name__)


def generate_variant_id(variant_type: VariantType, input_hash: str) -> str:
    """Generate unique variant ID."""
    return f"{variant_type.value}_{input_hash[:12]}"


def _create_baseline_variant(
    input_path: Path,
    output_dir: Path,
    input_hash: str,
) -> OptimizedVariant:
    """Create baseline variant (copy of original)."""
    variant_id = generate_variant_id(VariantType.BASELINE, input_hash)
    output_path = output_dir / f"{variant_id}.onnx"
    
    # Copy original model
    shutil.copy2(input_path, output_path)
    
    return OptimizedVariant(
        variant_id=variant_id,
        variant_type=VariantType.BASELINE,
        onnx_path=output_path,
        graph_hash=input_hash,  # Same as input
        size_bytes=output_path.stat().st_size,
        status=VariantStatus.VALID,
        metadata={"source": "baseline_copy"},
    )


def _create_fp16_variant(
    input_path: Path,
    output_dir: Path,
    input_hash: str,
) -> OptimizedVariant:
    """Create FP16 quantized variant."""
    variant_id = generate_variant_id(VariantType.FP16, input_hash)
    output_path = output_dir / f"{variant_id}.onnx"
    
    try:
        if not can_quantize_to_fp16(input_path):
            return OptimizedVariant(
                variant_id=variant_id,
                variant_type=VariantType.FP16,
                onnx_path=output_path,
                graph_hash="",
                size_bytes=0,
                status=VariantStatus.GENERATION_FAILED,
                error_message="FP16 quantization not supported for this model",
            )
        
        quantize_to_fp16(input_path, output_path)
        
        # Compute hash of quantized model
        model = onnx.load(str(output_path))
        variant_hash = compute_graph_hash(model)
        
        return OptimizedVariant(
            variant_id=variant_id,
            variant_type=VariantType.FP16,
            onnx_path=output_path,
            graph_hash=variant_hash,
            size_bytes=output_path.stat().st_size,
            status=VariantStatus.VALID,
            metadata={"quantization_method": "float16"},
        )
        
    except Exception as e:
        logger.warning(f"FP16 variant generation failed: {e}")
        return OptimizedVariant(
            variant_id=variant_id,
            variant_type=VariantType.FP16,
            onnx_path=output_path,
            graph_hash="",
            size_bytes=0,
            status=VariantStatus.GENERATION_FAILED,
            error_message=str(e),
        )


def _create_int8_variant(
    input_path: Path,
    output_dir: Path,
    input_hash: str,
) -> OptimizedVariant:
    """Create INT8 quantized variant."""
    variant_id = generate_variant_id(VariantType.INT8, input_hash)
    output_path = output_dir / f"{variant_id}.onnx"
    
    try:
        if not can_quantize_to_int8(input_path):
            return OptimizedVariant(
                variant_id=variant_id,
                variant_type=VariantType.INT8,
                onnx_path=output_path,
                graph_hash="",
                size_bytes=0,
                status=VariantStatus.GENERATION_FAILED,
                error_message="INT8 quantization not supported for this model",
            )
        
        quantize_to_int8_dynamic(input_path, output_path)
        
        # Compute hash
        model = onnx.load(str(output_path))
        variant_hash = compute_graph_hash(model)
        
        return OptimizedVariant(
            variant_id=variant_id,
            variant_type=VariantType.INT8,
            onnx_path=output_path,
            graph_hash=variant_hash,
            size_bytes=output_path.stat().st_size,
            status=VariantStatus.VALID,
            metadata={"quantization_method": "int8_dynamic"},
        )
        
    except Exception as e:
        logger.warning(f"INT8 variant generation failed: {e}")
        return OptimizedVariant(
            variant_id=variant_id,
            variant_type=VariantType.INT8,
            onnx_path=output_path,
            graph_hash="",
            size_bytes=0,
            status=VariantStatus.GENERATION_FAILED,
            error_message=str(e),
        )


def _create_pruned_variant(
    input_path: Path,
    output_dir: Path,
    input_hash: str,
) -> OptimizedVariant:
    """Create pruned variant."""
    variant_id = generate_variant_id(VariantType.PRUNED, input_hash)
    output_path = output_dir / f"{variant_id}.onnx"
    
    try:
        if not can_prune(input_path):
            return OptimizedVariant(
                variant_id=variant_id,
                variant_type=VariantType.PRUNED,
                onnx_path=output_path,
                graph_hash="",
                size_bytes=0,
                status=VariantStatus.GENERATION_FAILED,
                error_message="Pruning not supported for this model",
            )
        
        _, pruning_info = prune_zero_channels(input_path, output_path)
        
        # Compute hash
        model = onnx.load(str(output_path))
        variant_hash = compute_graph_hash(model)
        
        return OptimizedVariant(
            variant_id=variant_id,
            variant_type=VariantType.PRUNED,
            onnx_path=output_path,
            graph_hash=variant_hash,
            size_bytes=output_path.stat().st_size,
            status=VariantStatus.VALID,
            metadata={"pruning_info": pruning_info},
        )
        
    except Exception as e:
        logger.warning(f"Pruned variant generation failed: {e}")
        return OptimizedVariant(
            variant_id=variant_id,
            variant_type=VariantType.PRUNED,
            onnx_path=output_path,
            graph_hash="",
            size_bytes=0,
            status=VariantStatus.GENERATION_FAILED,
            error_message=str(e),
        )


def generate_variants(
    canonical_onnx_path: Path,
    input_hash: str,
    output_dir: Optional[Path] = None,
    variant_types: Optional[List[VariantType]] = None,
) -> List[OptimizedVariant]:
    """
    Generate all optimized variants from canonical ONNX.
    
    Args:
        canonical_onnx_path: Path to canonical ONNX model.
        input_hash: Hash of the input model.
        output_dir: Directory to save variants (defaults to temp).
        variant_types: Types of variants to generate (defaults to all).
    
    Returns:
        List of OptimizedVariant (may include failed variants).
    
    GUARANTEES:
        - Deterministic: same input always produces same variants
        - Each variant independently hashable
        - Failed variants are included with error info
    """
    if not ONNX_AVAILABLE:
        raise VariantGenerationError("all", "ONNX not available")
    
    canonical_onnx_path = Path(canonical_onnx_path)
    
    if output_dir is None:
        output_dir = Path(tempfile.mkdtemp(prefix="soac_variants_"))
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
    
    if variant_types is None:
        variant_types = [
            VariantType.BASELINE,
            VariantType.FP16,
            VariantType.INT8,
            VariantType.PRUNED,
        ]
    
    variants = []
    
    for vtype in variant_types:
        logger.info(f"Generating {vtype.value} variant...")
        
        if vtype == VariantType.BASELINE:
            variant = _create_baseline_variant(canonical_onnx_path, output_dir, input_hash)
        elif vtype == VariantType.FP16:
            variant = _create_fp16_variant(canonical_onnx_path, output_dir, input_hash)
        elif vtype == VariantType.INT8:
            variant = _create_int8_variant(canonical_onnx_path, output_dir, input_hash)
        elif vtype == VariantType.PRUNED:
            variant = _create_pruned_variant(canonical_onnx_path, output_dir, input_hash)
        else:
            continue
        
        variants.append(variant)
        
        if variant.status == VariantStatus.VALID:
            logger.info(f"  ✓ {vtype.value}: {variant.size_bytes} bytes")
        else:
            logger.warning(f"  ✗ {vtype.value}: {variant.error_message}")
    
    return variants


def get_variant_summary(variants: List[OptimizedVariant]) -> dict:
    """Get summary of generated variants."""
    total = len(variants)
    successful = sum(1 for v in variants if v.status == VariantStatus.VALID)
    failed = total - successful
    
    return {
        "total": total,
        "successful": successful,
        "failed": failed,
        "variants": [
            {
                "type": v.variant_type.value,
                "status": v.status.value,
                "size_bytes": v.size_bytes if v.is_valid else 0,
            }
            for v in variants
        ],
    }
