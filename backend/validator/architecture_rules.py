"""
SOAC Architecture Rules
=======================

Architecture fingerprinting rules for identifying supported models.

APPROACH:
    - Operator pattern matching (e.g., DepthwiseConv + ReLU6 → MobileNet)
    - Layer counting (e.g., 18 residual blocks → ResNet18)
    - Known structural signatures (kernel sizes, strides)

NO FILENAME GUESSING - Only analyze actual graph structure.
"""

from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass

from .metadata import ModelType, ArchitectureInfo, SUPPORTED_ARCHITECTURES


# =============================================================================
# OPERATOR FINGERPRINTS
# =============================================================================

@dataclass
class ArchitectureFingerprint:
    """
    Fingerprint pattern for identifying architectures.
    
    Attributes:
        name: Canonical architecture name
        required_ops: Operators that MUST be present
        forbidden_ops: Operators that MUST NOT be present
        min_conv_count: Minimum number of Conv operations
        max_conv_count: Maximum number of Conv operations
        signature_patterns: Specific operator sequences to look for
    """
    name: str
    required_ops: Set[str]
    forbidden_ops: Set[str] = None
    min_conv_count: int = 0
    max_conv_count: int = 1000
    signature_patterns: List[Tuple[str, ...]] = None
    model_type: ModelType = ModelType.CLASSIFICATION


# MobileNet family - characterized by DepthwiseConv
MOBILENET_FINGERPRINTS = [
    ArchitectureFingerprint(
        name="mobilenet_v2",
        required_ops={"Conv", "Relu", "Add"},
        min_conv_count=30,
        max_conv_count=100,
        model_type=ModelType.CLASSIFICATION,
    ),
    ArchitectureFingerprint(
        name="mobilenet_v3_small",
        required_ops={"Conv", "Sigmoid", "Mul"},  # SE blocks use sigmoid
        min_conv_count=20,
        max_conv_count=80,
        model_type=ModelType.CLASSIFICATION,
    ),
    ArchitectureFingerprint(
        name="mobilenet_v3_large",
        required_ops={"Conv", "Sigmoid", "Mul"},
        min_conv_count=50,
        max_conv_count=150,
        model_type=ModelType.CLASSIFICATION,
    ),
]

# ResNet family - characterized by residual connections (Add)
RESNET_FINGERPRINTS = [
    ArchitectureFingerprint(
        name="resnet18",
        required_ops={"Conv", "Relu", "Add", "GlobalAveragePool"},
        min_conv_count=15,
        max_conv_count=25,
        model_type=ModelType.CLASSIFICATION,
    ),
    ArchitectureFingerprint(
        name="resnet50",
        required_ops={"Conv", "Relu", "Add", "GlobalAveragePool"},
        min_conv_count=45,
        max_conv_count=70,
        model_type=ModelType.CLASSIFICATION,
    ),
]

# EfficientNet - characterized by SE blocks and Swish activation
EFFICIENTNET_FINGERPRINTS = [
    ArchitectureFingerprint(
        name="efficientnet_b0",
        required_ops={"Conv", "Sigmoid", "Mul", "Add"},
        min_conv_count=30,
        max_conv_count=80,
        model_type=ModelType.CLASSIFICATION,
    ),
]

# ShuffleNet - characterized by channel shuffle operations
SHUFFLENET_FINGERPRINTS = [
    ArchitectureFingerprint(
        name="shufflenet_v2",
        required_ops={"Conv", "Relu", "Concat", "Reshape"},
        min_conv_count=20,
        max_conv_count=60,
        model_type=ModelType.CLASSIFICATION,
    ),
]

# SqueezeNet - Fire modules with squeeze/expand
SQUEEZENET_FINGERPRINTS = [
    ArchitectureFingerprint(
        name="squeezenet1_0",
        required_ops={"Conv", "Relu", "Concat", "MaxPool"},
        min_conv_count=20,
        max_conv_count=35,
        model_type=ModelType.CLASSIFICATION,
    ),
    ArchitectureFingerprint(
        name="squeezenet1_1",
        required_ops={"Conv", "Relu", "Concat", "MaxPool"},
        min_conv_count=20,
        max_conv_count=35,
        model_type=ModelType.CLASSIFICATION,
    ),
]

# Detection models
DETECTION_FINGERPRINTS = [
    ArchitectureFingerprint(
        name="ssd_mobilenet_v2",
        required_ops={"Conv", "Relu"},
        min_conv_count=40,
        max_conv_count=150,
        model_type=ModelType.DETECTION,
    ),
    ArchitectureFingerprint(
        name="yolov5n",
        required_ops={"Conv", "Sigmoid", "Mul", "Concat"},
        min_conv_count=50,
        max_conv_count=150,
        model_type=ModelType.DETECTION,
    ),
    ArchitectureFingerprint(
        name="yolov5s",
        required_ops={"Conv", "Sigmoid", "Mul", "Concat"},
        min_conv_count=80,
        max_conv_count=200,
        model_type=ModelType.DETECTION,
    ),
]

# Audio models
AUDIO_FINGERPRINTS = [
    ArchitectureFingerprint(
        name="yamnet",
        required_ops={"Conv"},
        min_conv_count=5,
        max_conv_count=50,
        model_type=ModelType.AUDIO,
    ),
    ArchitectureFingerprint(
        name="wav2vec2_tiny",
        required_ops={"Conv", "LayerNormalization"},
        min_conv_count=5,
        max_conv_count=40,
        model_type=ModelType.AUDIO,
    ),
]

# All fingerprints combined
ALL_FINGERPRINTS: List[ArchitectureFingerprint] = (
    MOBILENET_FINGERPRINTS +
    RESNET_FINGERPRINTS +
    EFFICIENTNET_FINGERPRINTS +
    SHUFFLENET_FINGERPRINTS +
    SQUEEZENET_FINGERPRINTS +
    DETECTION_FINGERPRINTS +
    AUDIO_FINGERPRINTS
)


# =============================================================================
# INPUT SHAPE RULES
# =============================================================================

CLASSIFICATION_INPUT_SHAPES = [
    (1, 3, 224, 224),
    (-1, 3, 224, 224),  # Dynamic batch
    (1, 224, 224, 3),   # NHWC format
    (-1, 224, 224, 3),
]

DETECTION_INPUT_SHAPES_300 = [
    (1, 3, 300, 300),
    (-1, 3, 300, 300),
]

DETECTION_INPUT_SHAPES_640 = [
    (1, 3, 640, 640),
    (-1, 3, 640, 640),
]

AUDIO_INPUT_SHAPES = [
    (1, 16000),
    (-1, 16000),
    (1, 1, 16000),
    (-1, 1, 16000),
]


def normalize_shape(shape: tuple) -> tuple:
    """
    Normalize shape to canonical form.
    
    Replaces dynamic dimensions (None, -1, 'batch') with -1.
    """
    normalized = []
    for dim in shape:
        if dim is None or dim == "batch" or (isinstance(dim, str) and "batch" in dim.lower()):
            normalized.append(-1)
        elif isinstance(dim, int):
            normalized.append(dim)
        else:
            # Unknown dimension type - treat as dynamic
            normalized.append(-1)
    return tuple(normalized)


def is_valid_classification_input(shape: tuple) -> bool:
    """Check if shape is valid for classification models."""
    normalized = normalize_shape(shape)
    
    # Check against known classification shapes
    for valid_shape in CLASSIFICATION_INPUT_SHAPES:
        if len(normalized) == len(valid_shape):
            # Allow -1 (dynamic) to match any value
            match = True
            for n, v in zip(normalized, valid_shape):
                if v != -1 and n != v:
                    match = False
                    break
            if match:
                return True
    
    return False


def is_valid_detection_input(shape: tuple) -> bool:
    """Check if shape is valid for detection models."""
    normalized = normalize_shape(shape)
    
    valid_shapes = DETECTION_INPUT_SHAPES_300 + DETECTION_INPUT_SHAPES_640
    for valid_shape in valid_shapes:
        if len(normalized) == len(valid_shape):
            match = True
            for n, v in zip(normalized, valid_shape):
                if v != -1 and n != v:
                    match = False
                    break
            if match:
                return True
    
    return False


def is_valid_audio_input(shape: tuple) -> bool:
    """Check if shape is valid for audio models."""
    normalized = normalize_shape(shape)
    
    for valid_shape in AUDIO_INPUT_SHAPES:
        if len(normalized) == len(valid_shape):
            match = True
            for n, v in zip(normalized, valid_shape):
                if v != -1 and n != v:
                    match = False
                    break
            if match:
                return True
    
    return False


# =============================================================================
# ARCHITECTURE DETECTION
# =============================================================================

def count_operators(operators: List[str]) -> Dict[str, int]:
    """Count occurrences of each operator type."""
    counts = {}
    for op in operators:
        counts[op] = counts.get(op, 0) + 1
    return counts


def match_fingerprint(
    operators: List[str],
    op_counts: Dict[str, int],
    fingerprint: ArchitectureFingerprint
) -> float:
    """
    Calculate match score between model operators and fingerprint.
    
    Returns:
        Confidence score from 0.0 to 1.0.
    """
    score = 0.0
    max_score = 0.0
    
    operator_set = set(operators)
    
    # Check required operators
    required_ops = fingerprint.required_ops or set()
    max_score += len(required_ops) * 2
    for op in required_ops:
        if op in operator_set:
            score += 2
        else:
            # Check case-insensitive
            if any(op.lower() == o.lower() for o in operator_set):
                score += 1.5
    
    # Check forbidden operators
    forbidden_ops = fingerprint.forbidden_ops or set()
    max_score += len(forbidden_ops)
    for op in forbidden_ops:
        if op not in operator_set:
            score += 1
    
    # Check Conv count
    conv_count = sum(
        count for op, count in op_counts.items()
        if "conv" in op.lower()
    )
    
    max_score += 2
    if fingerprint.min_conv_count <= conv_count <= fingerprint.max_conv_count:
        score += 2
    elif conv_count > 0:
        # Partial score if close
        if conv_count >= fingerprint.min_conv_count * 0.7:
            score += 1
    
    if max_score == 0:
        return 0.0
    
    return score / max_score


def detect_architecture(
    operators: List[str],
    input_shape: Optional[tuple] = None
) -> Optional[ArchitectureInfo]:
    """
    Detect model architecture from operator list.
    
    Args:
        operators: List of operator names from the model.
        input_shape: Input tensor shape (optional, used for validation).
    
    Returns:
        ArchitectureInfo if recognized, None otherwise.
    """
    if not operators:
        return None
    
    op_counts = count_operators(operators)
    
    best_match: Optional[ArchitectureFingerprint] = None
    best_score = 0.0
    
    for fingerprint in ALL_FINGERPRINTS:
        score = match_fingerprint(operators, op_counts, fingerprint)
        
        if score > best_score and score >= 0.5:  # Require at least 50% match
            best_score = score
            best_match = fingerprint
    
    if best_match is None:
        return None
    
    # Validate input shape if provided
    if input_shape is not None:
        if best_match.model_type == ModelType.CLASSIFICATION:
            if not is_valid_classification_input(input_shape):
                return None
        elif best_match.model_type == ModelType.DETECTION:
            if not is_valid_detection_input(input_shape):
                return None
        elif best_match.model_type == ModelType.AUDIO:
            if not is_valid_audio_input(input_shape):
                return None
    
    # Get architecture info from registry
    arch_info = SUPPORTED_ARCHITECTURES.get(best_match.name)
    if arch_info is None:
        return None
    
    return ArchitectureInfo(
        name=best_match.name,
        family=arch_info.get("family", "unknown"),
        variant=arch_info.get("variants", [""])[0] if arch_info.get("variants") else "",
        confidence=best_score,
    )


def is_supported_architecture(architecture_name: str) -> bool:
    """Check if architecture name is in the supported list."""
    return architecture_name.lower() in SUPPORTED_ARCHITECTURES
