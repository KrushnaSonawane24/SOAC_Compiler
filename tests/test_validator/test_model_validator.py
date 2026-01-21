"""
Tests for Model Validator
=========================

Tests covering:
    - Supported model acceptance
    - Unsupported architecture rejection
    - Training graph rejection
    - Random operator rejection
    - Format validation
"""

import pytest
from pathlib import Path

from backend.validator import (
    validate_model,
    ModelValidationError,
    UnsupportedFormatError,
    UnsupportedArchitectureError,
    TrainingGraphError,
    NonDeterministicOpError,
    ModelParsingError,
    ModelMetadata,
    ModelType,
    get_supported_formats,
    get_supported_architectures,
)
from backend.validator.op_blacklist import (
    check_for_training_ops,
    check_for_random_ops,
)


class TestSupportedFormats:
    """Test format validation."""
    
    def test_supported_formats_list(self):
        """Check supported formats are correctly listed."""
        formats = get_supported_formats()
        
        assert ".onnx" in formats
        assert ".pt" in formats
        assert ".pth" in formats
        assert ".h5" in formats
        assert ".pkl" in formats
        assert ".joblib" in formats
        assert ".tflite" in formats
        assert ".mlmodel" in formats
    
    def test_unsupported_format_rejected(self, unsupported_format_file):
        """Unsupported format raises UnsupportedFormatError."""
        with pytest.raises(UnsupportedFormatError) as exc_info:
            validate_model(unsupported_format_file)
        
        assert exc_info.value.reason_code == "FORMAT_NOT_SUPPORTED"
        assert ".unsupported" in str(exc_info.value)
    
    def test_nonexistent_file_rejected(self, temp_dir):
        """Nonexistent file raises ModelParsingError."""
        with pytest.raises(ModelParsingError) as exc_info:
            validate_model(temp_dir / "nonexistent.onnx")
        
        assert exc_info.value.reason_code == "MODEL_PARSE_ERROR"


class TestValidModels:
    """Test that valid supported models are accepted."""
    
    def test_valid_mobilenet_accepted(self, valid_mobilenet_onnx):
        """Valid MobileNet-like model is accepted."""
        metadata = validate_model(valid_mobilenet_onnx)
        
        assert isinstance(metadata, ModelMetadata)
        assert metadata.is_valid is True
        assert metadata.model_type == ModelType.CLASSIFICATION
        assert "mobilenet" in metadata.architecture.name
    
    def test_valid_resnet18_accepted(self, valid_resnet18_onnx):
        """Valid ResNet18-like model is accepted."""
        metadata = validate_model(valid_resnet18_onnx)
        
        assert isinstance(metadata, ModelMetadata)
        assert metadata.is_valid is True
        assert metadata.model_type == ModelType.CLASSIFICATION
        assert "resnet" in metadata.architecture.name
    
    def test_metadata_contains_required_fields(self, valid_mobilenet_onnx):
        """Metadata has all required fields populated."""
        metadata = validate_model(valid_mobilenet_onnx)
        
        assert metadata.file_path is not None
        assert metadata.file_hash is not None
        assert len(metadata.file_hash) == 64  # SHA-256
        assert metadata.operator_count > 0
        assert len(metadata.operators) > 0


class TestTrainingGraphRejection:
    """Test that training graphs are rejected."""
    
    def test_training_ops_detected(self):
        """Training operators are correctly identified."""
        operators = ["Conv", "Relu", "Adam", "SGD", "Conv"]
        training_ops = check_for_training_ops(operators)
        
        assert "Adam" in training_ops
        assert "SGD" in training_ops
    
    def test_training_graph_rejected(self, training_graph_onnx):
        """Model with training operators is rejected."""
        with pytest.raises(TrainingGraphError) as exc_info:
            validate_model(training_graph_onnx)
        
        assert exc_info.value.reason_code == "TRAINING_GRAPH_DETECTED"
        assert len(exc_info.value.forbidden_ops) > 0
    
    def test_optimizer_ops_blacklisted(self):
        """All optimizer operators are detected."""
        operators = ["Adam", "SGD", "RMSprop", "Adagrad", "Momentum"]
        training_ops = check_for_training_ops(operators)
        
        assert len(training_ops) == 5
    
    def test_loss_functions_blacklisted(self):
        """Loss function operators are detected."""
        operators = ["SoftmaxCrossEntropyLoss", "NLLLoss", "MSELoss"]
        training_ops = check_for_training_ops(operators)
        
        assert len(training_ops) == 3


class TestRandomOpRejection:
    """Test that non-deterministic operators are rejected."""
    
    def test_random_ops_detected(self):
        """Random operators are correctly identified."""
        operators = ["Conv", "RandomNormal", "Relu"]
        random_ops = check_for_random_ops(operators)
        
        assert "RandomNormal" in random_ops
    
    def test_random_graph_rejected(self, random_ops_onnx):
        """Model with random operators is rejected."""
        with pytest.raises(NonDeterministicOpError) as exc_info:
            validate_model(random_ops_onnx)
        
        assert exc_info.value.reason_code == "NON_DETERMINISTIC_OPS"
    
    def test_all_random_ops_detected(self):
        """All random operators are detected."""
        operators = ["RandomNormal", "RandomUniform", "Multinomial", "Bernoulli"]
        random_ops = check_for_random_ops(operators)
        
        assert len(random_ops) == 4


class TestUnsupportedArchitecture:
    """Test that unsupported architectures are rejected."""
    
    def test_custom_cnn_rejected(self, custom_cnn_onnx):
        """Custom CNN not matching any fingerprint is rejected."""
        with pytest.raises(UnsupportedArchitectureError) as exc_info:
            validate_model(custom_cnn_onnx)
        
        assert exc_info.value.reason_code == "ARCHITECTURE_NOT_SUPPORTED"
    
    def test_supported_architectures_list(self):
        """Check supported architectures are correctly listed."""
        archs = get_supported_architectures()
        
        # Classification
        assert "mobilenet_v2" in archs
        assert "resnet18" in archs
        assert "resnet50" in archs
        assert "efficientnet_b0" in archs
        assert "shufflenet_v2" in archs
        assert "squeezenet1_0" in archs
        
        # Detection
        assert "ssd_mobilenet_v2" in archs
        assert "yolov5n" in archs
        assert "yolov5s" in archs
        
        # Audio
        assert "yamnet" in archs
        assert "wav2vec2_tiny" in archs


class TestExceptionDetails:
    """Test that exceptions contain proper details."""
    
    def test_exception_has_reason_code(self, custom_cnn_onnx):
        """Exceptions have reason_code attribute."""
        with pytest.raises(ModelValidationError) as exc_info:
            validate_model(custom_cnn_onnx)
        
        assert hasattr(exc_info.value, "reason_code")
        assert exc_info.value.reason_code is not None
    
    def test_exception_has_context(self, custom_cnn_onnx):
        """Exceptions have context dictionary."""
        with pytest.raises(ModelValidationError) as exc_info:
            validate_model(custom_cnn_onnx)
        
        assert hasattr(exc_info.value, "context")
        assert isinstance(exc_info.value.context, dict)
    
    def test_exception_to_dict(self, custom_cnn_onnx):
        """Exceptions can be converted to dict."""
        with pytest.raises(ModelValidationError) as exc_info:
            validate_model(custom_cnn_onnx)
        
        error_dict = exc_info.value.to_dict()
        
        assert "error" in error_dict
        assert "reason_code" in error_dict
        assert "context" in error_dict


class TestMetadataSerialization:
    """Test that metadata can be serialized."""
    
    def test_metadata_to_dict(self, valid_mobilenet_onnx):
        """Metadata can be converted to dictionary."""
        metadata = validate_model(valid_mobilenet_onnx)
        
        result = metadata.to_dict()
        
        assert isinstance(result, dict)
        assert "is_valid" in result
        assert "model_type" in result
        assert "architecture" in result
        assert "inputs" in result
        assert "outputs" in result
    
    def test_metadata_is_frozen(self, valid_mobilenet_onnx):
        """Metadata is immutable."""
        metadata = validate_model(valid_mobilenet_onnx)
        
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            metadata.is_valid = False
