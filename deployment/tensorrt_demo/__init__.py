"""
SOAC TensorRT Demo Package
==========================

Generates TensorRT PC demos with conditional GPU support.

BEHAVIOR:
    GPU Available:    Generate engine + Python demo
    GPU Unavailable:  Generate stub + README explaining requirements

Usage:
    from backend.deployment.tensorrt_demo import generate_tensorrt_demo
    
    result = generate_tensorrt_demo(
        onnx_path=Path("model.onnx"),
        output_dir=Path("output/"),
    )
    
    if result["available"]:
        print(f"Full demo at: {result['path']}")
    else:
        print(f"Stub generated: {result['reason']}")
"""

from .generator import generate_tensorrt_demo

__all__ = ["generate_tensorrt_demo"]
