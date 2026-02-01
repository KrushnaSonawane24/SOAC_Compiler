"""
SOAC Android Demo Package
=========================

Generates ready-to-run Android Studio projects with TFLite models.

Usage:
    from backend.deployment.android import generate_android_demo
    
    result = generate_android_demo(
        tflite_path=Path("model.tflite"),
        output_dir=Path("output/"),
    )
    
    if result["success"]:
        print(f"Demo at: {result['path']}")
        print(f"Zip at: {result['zip_path']}")
"""

from .generator import generate_android_demo

__all__ = ["generate_android_demo"]
