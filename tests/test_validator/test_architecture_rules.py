"""
Tests for Architecture Rules
=============================

Tests for architecture fingerprinting and detection.
"""

import pytest

from backend.validator.architecture_rules import (
    detect_architecture,
    is_supported_architecture,
    match_fingerprint,
    count_operators,
    is_valid_classification_input,
    is_valid_detection_input,
    is_valid_audio_input,
    normalize_shape,
    ALL_FINGERPRINTS,
)
from backend.validator.metadata import ModelType


class TestShapeNormalization:
    """Test shape normalization."""
    
    def test_normalize_static_shape(self):
        """Static shapes are preserved."""
        shape = (1, 3, 224, 224)
        normalized = normalize_shape(shape)
        
        assert normalized == (1, 3, 224, 224)
    
    def test_normalize_none_to_dynamic(self):
        """None becomes -1 (dynamic)."""
        shape = (None, 3, 224, 224)
        normalized = normalize_shape(shape)
        
        assert normalized == (-1, 3, 224, 224)
    
    def test_normalize_string_batch(self):
        """String 'batch' becomes -1."""
        shape = ("batch", 3, 224, 224)
        normalized = normalize_shape(shape)
        
        assert normalized == (-1, 3, 224, 224)


class TestInputShapeValidation:
    """Test input shape validation."""
    
    def test_valid_classification_nchw(self):
        """NCHW classification shape is valid."""
        assert is_valid_classification_input((1, 3, 224, 224)) is True
    
    def test_valid_classification_dynamic_batch(self):
        """Dynamic batch classification is valid."""
        assert is_valid_classification_input((-1, 3, 224, 224)) is True
    
    def test_invalid_classification_wrong_size(self):
        """Wrong image size is invalid."""
        assert is_valid_classification_input((1, 3, 512, 512)) is False
    
    def test_valid_detection_300(self):
        """300x300 detection shape is valid."""
        assert is_valid_detection_input((1, 3, 300, 300)) is True
    
    def test_valid_detection_640(self):
        """640x640 detection shape is valid."""
        assert is_valid_detection_input((1, 3, 640, 640)) is True
    
    def test_valid_audio_shape(self):
        """16000 sample audio shape is valid."""
        assert is_valid_audio_input((1, 16000)) is True


class TestOperatorCounting:
    """Test operator counting."""
    
    def test_count_operators(self):
        """Operators are correctly counted."""
        operators = ["Conv", "Relu", "Conv", "Relu", "Conv"]
        counts = count_operators(operators)
        
        assert counts["Conv"] == 3
        assert counts["Relu"] == 2


class TestArchitectureDetection:
    """Test architecture detection from operator patterns."""
    
    def test_detect_mobilenet_pattern(self):
        """MobileNet pattern is detected."""
        # MobileNet-like operators
        operators = ["Conv", "Relu", "Add"] * 35 + ["GlobalAveragePool"]
        
        arch = detect_architecture(operators, (1, 3, 224, 224))
        
        assert arch is not None
        assert "mobilenet" in arch.name.lower()
    
    def test_detect_resnet_pattern(self):
        """ResNet pattern is detected."""
        # ResNet18-like operators
        operators = ["Conv", "Relu", "Add"] * 18 + ["GlobalAveragePool"]
        
        arch = detect_architecture(operators, (1, 3, 224, 224))
        
        assert arch is not None
        assert "resnet" in arch.name.lower()
    
    def test_no_detection_for_unknown(self):
        """Unknown patterns return None."""
        operators = ["CustomOp1", "CustomOp2", "CustomOp3"]
        
        arch = detect_architecture(operators, (1, 3, 224, 224))
        
        assert arch is None
    
    def test_empty_operators_return_none(self):
        """Empty operator list returns None."""
        arch = detect_architecture([], (1, 3, 224, 224))
        
        assert arch is None


class TestSupportedArchitectureCheck:
    """Test supported architecture checking."""
    
    def test_mobilenet_v2_supported(self):
        """MobileNetV2 is supported."""
        assert is_supported_architecture("mobilenet_v2") is True
    
    def test_resnet50_supported(self):
        """ResNet50 is supported."""
        assert is_supported_architecture("resnet50") is True
    
    def test_yolov5n_supported(self):
        """YOLOv5n is supported."""
        assert is_supported_architecture("yolov5n") is True
    
    def test_custom_not_supported(self):
        """Custom architectures are not supported."""
        assert is_supported_architecture("custom_cnn") is False
    
    def test_case_insensitive(self):
        """Architecture check is case-insensitive."""
        assert is_supported_architecture("MobileNet_V2") is True
        assert is_supported_architecture("RESNET50") is True


class TestFingerprintMatching:
    """Test fingerprint matching scores."""
    
    def test_fingerprint_scores(self):
        """Fingerprint matching produces scores."""
        operators = ["Conv", "Relu", "Add", "GlobalAveragePool"]
        counts = count_operators(operators)
        
        for fingerprint in ALL_FINGERPRINTS:
            score = match_fingerprint(operators, counts, fingerprint)
            assert 0.0 <= score <= 1.0
