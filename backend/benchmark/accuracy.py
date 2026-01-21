"""
SOAC Accuracy Measurement
=========================

Top-1 accuracy evaluation for ONNX models.

GUARANTEES:
    - Deterministic evaluation
    - Same dataset for all models
    - No sampling or approximation
"""

import logging
from pathlib import Path
from typing import Optional, List
import numpy as np

try:
    import onnxruntime as ort
    ONNXRUNTIME_AVAILABLE = True
except ImportError:
    ONNXRUNTIME_AVAILABLE = False

from .exceptions import AccuracyMeasurementError, AccuracyConstraintViolation, InferenceError
from .result import AccuracyResult
from .dataset import ReferenceDataset, DatasetSample
from .metrics import MAX_ACCURACY_DROP, calculate_accuracy_drop, MIN_EVAL_SAMPLES


logger = logging.getLogger(__name__)


def create_inference_session(model_path: Path) -> "ort.InferenceSession":
    """
    Create ONNX Runtime inference session.
    
    Args:
        model_path: Path to ONNX model.
    
    Returns:
        InferenceSession ready for inference.
    """
    if not ONNXRUNTIME_AVAILABLE:
        raise AccuracyMeasurementError("onnxruntime not available")
    
    try:
        # Use CPU for deterministic results
        providers = ['CPUExecutionProvider']
        session = ort.InferenceSession(str(model_path), providers=providers)
        return session
    except Exception as e:
        raise AccuracyMeasurementError(f"Failed to load model: {e}", e)


def run_inference(
    session: "ort.InferenceSession",
    input_data: np.ndarray,
) -> np.ndarray:
    """
    Run inference on a single input.
    
    Returns:
        Output tensor (logits or probabilities).
    """
    input_name = session.get_inputs()[0].name
    
    try:
        outputs = session.run(None, {input_name: input_data})
        return outputs[0]
    except Exception as e:
        raise InferenceError("inference", str(e), e)


def get_prediction(output: np.ndarray) -> int:
    """
    Get predicted class from model output.
    
    Assumes output is logits or probabilities with shape (batch, num_classes).
    """
    # Handle batch dimension
    if len(output.shape) > 1:
        output = output[0]
    
    return int(np.argmax(output))


def evaluate_accuracy(
    model_path: Path,
    dataset: ReferenceDataset,
    baseline_accuracy: Optional[float] = None,
) -> AccuracyResult:
    """
    Evaluate model accuracy on dataset.
    
    Args:
        model_path: Path to ONNX model.
        dataset: Reference dataset for evaluation.
        baseline_accuracy: Baseline accuracy for computing drop.
    
    Returns:
        AccuracyResult with accuracy metrics.
    
    Raises:
        AccuracyMeasurementError: If evaluation fails.
    """
    model_path = Path(model_path)
    
    if len(dataset) < MIN_EVAL_SAMPLES:
        raise AccuracyMeasurementError(
            f"Dataset too small: {len(dataset)} < {MIN_EVAL_SAMPLES}"
        )
    
    logger.info(f"Evaluating accuracy: {model_path} on {len(dataset)} samples")
    
    # Create session
    session = create_inference_session(model_path)
    
    # Evaluate
    correct = 0
    total = len(dataset)
    
    for sample in dataset:
        try:
            output = run_inference(session, sample.input_data)
            prediction = get_prediction(output)
            
            if prediction == sample.label:
                correct += 1
        except Exception as e:
            logger.warning(f"Inference failed for sample {sample.sample_id}: {e}")
            # Count as incorrect
    
    accuracy = correct / total if total > 0 else 0.0
    
    # Calculate drop if baseline provided
    is_baseline = baseline_accuracy is None
    accuracy_drop = 0.0 if is_baseline else calculate_accuracy_drop(baseline_accuracy, accuracy)
    
    logger.info(f"Accuracy: {accuracy:.4f} ({correct}/{total})")
    
    return AccuracyResult(
        accuracy=accuracy,
        correct=correct,
        total=total,
        accuracy_drop=accuracy_drop,
        is_baseline=is_baseline,
        model_path=str(model_path),
    )


def verify_accuracy_constraint(
    baseline_result: AccuracyResult,
    optimized_result: AccuracyResult,
    threshold: float = MAX_ACCURACY_DROP,
) -> bool:
    """
    Verify that accuracy drop is within threshold.
    
    Args:
        baseline_result: Baseline model accuracy result.
        optimized_result: Optimized model accuracy result.
        threshold: Maximum allowed accuracy drop.
    
    Returns:
        True if within threshold.
    
    Raises:
        AccuracyConstraintViolation: If threshold exceeded.
    """
    drop = calculate_accuracy_drop(
        baseline_result.accuracy,
        optimized_result.accuracy
    )
    
    if drop > threshold:
        raise AccuracyConstraintViolation(
            baseline=baseline_result.accuracy,
            measured=optimized_result.accuracy,
            threshold=threshold,
        )
    
    return True


def compare_accuracy(
    baseline_path: Path,
    optimized_path: Path,
    dataset: ReferenceDataset,
    threshold: float = MAX_ACCURACY_DROP,
) -> tuple:
    """
    Compare accuracy between baseline and optimized model.
    
    Returns:
        Tuple of (baseline_result, optimized_result, is_valid).
    """
    # Evaluate baseline
    baseline_result = evaluate_accuracy(baseline_path, dataset, baseline_accuracy=None)
    
    # Evaluate optimized
    optimized_result = evaluate_accuracy(
        optimized_path,
        dataset,
        baseline_accuracy=baseline_result.accuracy
    )
    
    # Check constraint
    is_valid = optimized_result.accuracy_drop <= threshold
    
    return baseline_result, optimized_result, is_valid
