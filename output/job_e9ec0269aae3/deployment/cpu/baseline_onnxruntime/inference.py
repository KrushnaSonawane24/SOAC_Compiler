"""
ONNX Runtime Inference Script
==============================

Usage:
    import numpy as np
    from inference import run_inference
    
    input_data = np.random.randn(1, 3, 224, 224).astype(np.float32)
    output = run_inference(input_data)
"""

import onnxruntime as ort
import numpy as np
from pathlib import Path

MODEL_PATH = Path(__file__).parent / "model.onnx"

_session = None

def get_session():
    global _session
    if _session is None:
        _session = ort.InferenceSession(str(MODEL_PATH), providers=['CPUExecutionProvider'])
    return _session

def run_inference(input_data: np.ndarray) -> np.ndarray:
    """Run inference on input data."""
    session = get_session()
    input_name = session.get_inputs()[0].name
    outputs = session.run(None, {input_name: input_data})
    return outputs[0]

if __name__ == "__main__":
    # Example usage
    import json
    
    with open(Path(__file__).parent / "metadata.json") as f:
        meta = json.load(f)
    
    print(f"Model: {meta['model_name']}")
    print(f"Inputs: {meta['inputs']}")
