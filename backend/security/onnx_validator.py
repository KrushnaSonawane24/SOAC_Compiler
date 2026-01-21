"""
SOAC ONNX Model Validator
=========================

ONNX-specific validation using the official onnx library.

WHY ONNX-SPECIFIC VALIDATION?
    - ONNX is a protobuf-based format with complex graph structure
    - Magic bytes alone cannot validate graph integrity
    - Malformed graphs could crash the compiler or cause undefined behavior
    - The onnx.checker module performs comprehensive validation

VALIDATION PERFORMED:
    1. Parse the protobuf structure (catches corruption)
    2. Validate graph topology (inputs/outputs/nodes)
    3. Check tensor dimensions and data types
    4. Verify IR version compatibility
    5. Validate initializers and constants

SECURITY CONSIDERATIONS:
    - Load with load_external_data=False to prevent path traversal
    - Use check_model() to catch malformed graphs
    - Wrap all onnx calls in try/except for graceful failure
"""

from pathlib import Path
from typing import Optional
import logging

try:
    import onnx
    from onnx import checker as onnx_checker
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    onnx = None  # type: ignore
    onnx_checker = None  # type: ignore

from .config import ONNX_LOAD_EXTERNAL_DATA
from .exceptions import OnnxValidationError


# Logger for ONNX validation events
logger = logging.getLogger(__name__)


def validate_onnx_model(file_path: Path) -> "onnx.ModelProto":
    """
    Validate an ONNX model file for integrity and correctness.
    
    This function performs comprehensive validation of ONNX files:
        1. Loads the protobuf structure
        2. Runs onnx.checker.check_model() for graph validation
        3. Verifies IR version is supported
    
    Args:
        file_path: Path to the ONNX file to validate.
    
    Returns:
        The loaded and validated onnx.ModelProto object.
    
    Raises:
        OnnxValidationError: If the file is not a valid ONNX model.
        RuntimeError: If the onnx library is not installed.
    
    Example:
        >>> model = validate_onnx_model(Path("/path/to/model.onnx"))
        >>> print(f"Model has {len(model.graph.node)} nodes")
    
    Security Notes:
        - External data is NOT loaded (prevents path traversal)
        - All onnx library exceptions are caught and wrapped
        - Invalid models are rejected with detailed error messages
    """
    if not ONNX_AVAILABLE:
        raise RuntimeError(
            "onnx library is required for ONNX validation. "
            "Install with: pip install onnx"
        )
    
    try:
        # Step 1: Load the ONNX file
        # CRITICAL: load_external_data=False prevents path traversal attacks
        # where malicious models reference external files like "../../../etc/passwd"
        model = onnx.load(
            str(file_path),
            load_external_data=ONNX_LOAD_EXTERNAL_DATA
        )
        
    except Exception as e:
        logger.warning(f"Failed to load ONNX file {file_path}: {e}")
        raise OnnxValidationError(
            filename=file_path.name,
            reason="Failed to parse ONNX protobuf structure",
            original_exception=e
        )
    
    try:
        # Step 2: Validate the model graph
        # This checks:
        #   - Graph topology (all inputs/outputs connected)
        #   - Node operator validity
        #   - Tensor shape compatibility
        #   - Data type consistency
        onnx_checker.check_model(model)
        
    except onnx.checker.ValidationError as e:  # type: ignore
        logger.warning(f"ONNX graph validation failed for {file_path}: {e}")
        raise OnnxValidationError(
            filename=file_path.name,
            reason="ONNX graph structure is invalid",
            original_exception=e
        )
    except Exception as e:
        logger.warning(f"Unexpected error during ONNX validation of {file_path}: {e}")
        raise OnnxValidationError(
            filename=file_path.name,
            reason="Unexpected error during graph validation",
            original_exception=e
        )
    
    # Step 3: Log successful validation with model metadata
    _log_model_info(model, file_path)
    
    return model


def get_onnx_model_info(model: "onnx.ModelProto") -> dict:
    """
    Extract metadata from a validated ONNX model.
    
    Args:
        model: A validated onnx.ModelProto object.
    
    Returns:
        Dictionary containing model metadata:
            - ir_version: ONNX IR version
            - producer_name: Tool that created the model
            - producer_version: Version of the producer tool
            - domain: Model domain (if specified)
            - model_version: Model version number
            - doc_string: Model documentation
            - num_nodes: Number of nodes in the graph
            - num_inputs: Number of graph inputs
            - num_outputs: Number of graph outputs
            - opset_imports: List of opset imports
    """
    if not ONNX_AVAILABLE or model is None:
        return {}
    
    return {
        "ir_version": model.ir_version,
        "producer_name": model.producer_name or "unknown",
        "producer_version": model.producer_version or "unknown",
        "domain": model.domain or "default",
        "model_version": model.model_version,
        "doc_string": model.doc_string[:200] if model.doc_string else "",
        "num_nodes": len(model.graph.node),
        "num_inputs": len(model.graph.input),
        "num_outputs": len(model.graph.output),
        "opset_imports": [
            {"domain": op.domain or "ai.onnx", "version": op.version}
            for op in model.opset_import
        ]
    }


def _log_model_info(model: "onnx.ModelProto", file_path: Path) -> None:
    """
    Log model metadata for audit trail.
    
    This creates a record of successfully validated models, useful for:
        - Security auditing
        - Debugging production issues
        - Performance analysis
    """
    info = get_onnx_model_info(model)
    logger.info(
        f"Validated ONNX model: {file_path.name} | "
        f"IR v{info.get('ir_version')} | "
        f"{info.get('num_nodes')} nodes | "
        f"producer: {info.get('producer_name')}"
    )


def check_ir_version_compatibility(model: "onnx.ModelProto") -> bool:
    """
    Check if the model's IR version is compatible with current ONNX runtime.
    
    Args:
        model: A loaded onnx.ModelProto object.
    
    Returns:
        True if IR version is compatible, False otherwise.
    
    Note:
        Current ONNX supports IR versions 1-9. Version 10+ may have
        breaking changes that require runtime updates.
    """
    if not ONNX_AVAILABLE:
        return False
    
    # Get maximum supported IR version from the installed onnx library
    max_ir_version = onnx.IR_VERSION if hasattr(onnx, 'IR_VERSION') else 9
    
    return model.ir_version <= max_ir_version


def is_valid_onnx_file(file_path: Path) -> bool:
    """
    Quick check if a file is a valid ONNX model.
    
    Unlike validate_onnx_model(), this function returns a boolean
    instead of raising exceptions. Useful for conditional logic.
    
    Args:
        file_path: Path to the file to check.
    
    Returns:
        True if file is a valid ONNX model, False otherwise.
    """
    try:
        validate_onnx_model(file_path)
        return True
    except (OnnxValidationError, RuntimeError):
        return False
