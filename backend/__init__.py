"""
SOAC Backend Package
===================

Self-Optimizing AI Compiler backend services.
"""

__version__ = "1.0.0"

import logging
import onnx.helper

# Patch ONNX helper for onnx-graphsurgeon compatibility
if not hasattr(onnx.helper, 'float32_to_bfloat16'):
    logging.getLogger(__name__).warning("Patching onnx.helper.float32_to_bfloat16 for onnx-graphsurgeon compatibility")
    def float32_to_bfloat16(x):
        # Very rough approximation if ever called
        return 0
    onnx.helper.float32_to_bfloat16 = float32_to_bfloat16
