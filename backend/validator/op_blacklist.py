"""
SOAC Operator Blacklist
=======================

Lists of forbidden operators that indicate training graphs
or non-deterministic behavior.

DESIGN PRINCIPLE:
    If ANY blacklisted operator is present, the model is REJECTED.
    There are NO exceptions or overrides.
"""

from typing import FrozenSet


# =============================================================================
# TRAINING OPERATORS - Indicate model is a training graph
# =============================================================================

TRAINING_OPTIMIZERS: FrozenSet[str] = frozenset({
    # PyTorch/ONNX Optimizers
    "Adam",
    "Adagrad",
    "SGD",
    "Momentum",
    "RMSprop",
    "Adadelta",
    "Adamax",
    "LAMB",
    "LARS",
    
    # TensorFlow Optimizers
    "ApplyAdam",
    "ApplyAdagrad",
    "ApplyGradientDescent",
    "ApplyMomentum",
    "ApplyRMSProp",
    "ResourceApplyAdam",
    "ResourceApplyGradientDescent",
    
    # Generic Gradient Operations
    "GradientDescent",
    "ApplyGradient",
    "AccumulateGrad",
})

TRAINING_LOSS_FUNCTIONS: FrozenSet[str] = frozenset({
    # Cross-Entropy Losses
    "SoftmaxCrossEntropyLoss",
    "SoftmaxCrossEntropyWithLogits",
    "SparseSoftmaxCrossEntropyWithLogits",
    "NLLLoss",
    "NegativeLogLikelihoodLoss",
    "CrossEntropyLoss",
    
    # Other Losses
    "MSELoss",
    "L1Loss",
    "SmoothL1Loss",
    "BCELoss",
    "BCEWithLogitsLoss",
    "CTCLoss",
    "KLDivLoss",
    "HuberLoss",
    "CosineEmbeddingLoss",
    "TripletMarginLoss",
})

GRADIENT_OPERATIONS: FrozenSet[str] = frozenset({
    # Gradient Computation
    "Gradient",
    "StopGradient",
    "PreventGradient",
    "GradientTape",
    
    # Backward Pass
    "Backward",
    "BackwardPass",
    
    # Gradient Clipping
    "ClipByNorm",
    "ClipByGlobalNorm",
    "ClipByValue",
})

TRAINING_SPECIFIC_OPS: FrozenSet[str] = frozenset({
    # Dropout with training mode
    "TrainableDropout",
    
    # Batch Norm training mode
    "BatchNormTraining",
    "FusedBatchNormTraining",
    
    # Variable Operations (training state)
    "Variable",
    "VariableV2",
    "AssignVariable",
    "AssignVariableOp",
    "ReadVariableOp",
    
    # Weight Updates
    "ResourceScatterAdd",
    "ResourceScatterUpdate",
})


# =============================================================================
# NON-DETERMINISTIC OPERATORS - Prevent reproducible inference
# =============================================================================

RANDOM_OPERATORS: FrozenSet[str] = frozenset({
    # ONNX Random Ops
    "RandomNormal",
    "RandomNormalLike",
    "RandomUniform",
    "RandomUniformLike",
    "Multinomial",
    "Bernoulli",
    
    # TensorFlow Random Ops
    "RandomStandardNormal",
    "RandomShuffle",
    "TruncatedNormal",
    "RandomCrop",
    
    # PyTorch Random Ops
    "rand",
    "randn",
    "randint",
    "randperm",
})


# =============================================================================
# UNSAFE/UNSUPPORTED OPERATORS
# =============================================================================

UNSAFE_OPERATORS: FrozenSet[str] = frozenset({
    # File I/O (security risk)
    "ReadFile",
    "WriteFile",
    "MatchingFiles",
    
    # Network Operations
    "HTTPRequest",
    "RPCCall",
    
    # Control Flow (complex to optimize)
    "While",
    "Loop",
    "If",
    "Switch",
    "Merge",
    
    # Dynamic Operations
    "TensorArray",
    "TensorArrayV2",
    "TensorArrayV3",
})


# =============================================================================
# COMBINED BLACKLISTS
# =============================================================================

ALL_TRAINING_OPERATORS: FrozenSet[str] = (
    TRAINING_OPTIMIZERS |
    TRAINING_LOSS_FUNCTIONS |
    GRADIENT_OPERATIONS |
    TRAINING_SPECIFIC_OPS
)
"""All operators that indicate a training graph."""


ALL_FORBIDDEN_OPERATORS: FrozenSet[str] = (
    ALL_TRAINING_OPERATORS |
    RANDOM_OPERATORS |
    UNSAFE_OPERATORS
)
"""All operators that are forbidden in SOAC models."""


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def check_for_training_ops(operators: list[str]) -> list[str]:
    """
    Check if any operators are training-related.
    
    Args:
        operators: List of operator names from the model.
    
    Returns:
        List of training operators found (empty if none).
    """
    found = []
    operators_set = set(op.lower() for op in operators)
    
    for op in operators:
        op_lower = op.lower()
        # Check exact match
        if op in ALL_TRAINING_OPERATORS:
            found.append(op)
        # Check case-insensitive match
        elif any(blacklisted.lower() == op_lower for blacklisted in ALL_TRAINING_OPERATORS):
            found.append(op)
    
    return found


def check_for_random_ops(operators: list[str]) -> list[str]:
    """
    Check if any operators are non-deterministic.
    
    Args:
        operators: List of operator names from the model.
    
    Returns:
        List of random operators found (empty if none).
    """
    found = []
    
    for op in operators:
        op_lower = op.lower()
        if op in RANDOM_OPERATORS:
            found.append(op)
        elif any(blacklisted.lower() == op_lower for blacklisted in RANDOM_OPERATORS):
            found.append(op)
        # Also check for common random patterns
        elif "random" in op_lower or "rand" in op_lower:
            found.append(op)
    
    return found


def check_for_forbidden_ops(operators: list[str]) -> list[str]:
    """
    Check for any forbidden operators.
    
    Args:
        operators: List of operator names from the model.
    
    Returns:
        List of forbidden operators found (empty if none).
    """
    found = []
    
    for op in operators:
        if op in ALL_FORBIDDEN_OPERATORS:
            found.append(op)
    
    return found


def is_dropout_training_mode(node_attrs: dict) -> bool:
    """
    Check if a Dropout node is in training mode.
    
    Dropout with training=True or ratio>0 at inference is suspicious.
    
    Args:
        node_attrs: Node attributes dictionary.
    
    Returns:
        True if Dropout appears to be in training mode.
    """
    # Check for training_mode attribute
    if node_attrs.get("training_mode", 0) == 1:
        return True
    
    # Check for is_test attribute (TensorFlow style)
    if node_attrs.get("is_test", 1) == 0:
        return True
    
    return False


def is_batchnorm_training_mode(node_attrs: dict) -> bool:
    """
    Check if a BatchNormalization node is in training mode.
    
    Args:
        node_attrs: Node attributes dictionary.
    
    Returns:
        True if BatchNorm is in training mode.
    """
    # Check for training_mode attribute
    if node_attrs.get("training_mode", 0) == 1:
        return True
    
    # Check for is_test attribute
    if node_attrs.get("is_test", 1) == 0:
        return True
    
    return False
