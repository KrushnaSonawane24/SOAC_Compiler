"""
SOAC ONNX Runtime Deployment
============================

Package ONNX model for CPU deployment with ONNX Runtime.
"""

import logging
import shutil
import json
from pathlib import Path
from typing import Optional

try:
    import onnx
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False

try:
    import onnxruntime as ort
    ONNXRUNTIME_AVAILABLE = True
except ImportError:
    ONNXRUNTIME_AVAILABLE = False

from .exceptions import DeploymentError
from .metadata import DeploymentArtifact, TargetPlatform, ArtifactStatus, create_skipped_artifact


logger = logging.getLogger(__name__)


def is_onnxruntime_available() -> bool:
    """Check if ONNX Runtime deployment is available."""
    return ONNX_AVAILABLE


def create_onnxruntime_package(
    onnx_path: Path,
    output_dir: Path,
    model_name: str = "model",
) -> DeploymentArtifact:
    """
    Create ONNX Runtime deployment package.
    
    Creates a directory with:
    - model.onnx - The optimized model
    - metadata.json - Model metadata
    - inference.py - Simple inference script
    
    Args:
        onnx_path: Path to source ONNX model.
        output_dir: Directory to create package in.
        model_name: Name for the model.
    
    Returns:
        DeploymentArtifact with result.
    """
    if not ONNX_AVAILABLE:
        return create_skipped_artifact(
            TargetPlatform.CPU,
            "onnx",
            "ONNX not available"
        )
    
    onnx_path = Path(onnx_path)
    output_dir = Path(output_dir)
    package_dir = output_dir / f"{model_name}_onnxruntime"
    package_dir.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Creating ONNX Runtime package: {package_dir}")
    
    try:
        # Copy model
        model_dest = package_dir / "model.onnx"
        shutil.copy2(onnx_path, model_dest)
        
        # Load model to get metadata
        model = onnx.load(str(onnx_path))
        
        # Extract input/output info
        inputs = []
        for inp in model.graph.input:
            # Skip initializers
            init_names = {i.name for i in model.graph.initializer}
            if inp.name in init_names:
                continue
            
            shape = []
            if inp.type.HasField("tensor_type"):
                for dim in inp.type.tensor_type.shape.dim:
                    if dim.HasField("dim_value"):
                        shape.append(dim.dim_value)
                    else:
                        shape.append(-1)
            
            inputs.append({
                "name": inp.name,
                "shape": shape,
            })
        
        outputs = []
        for out in model.graph.output:
            shape = []
            if out.type.HasField("tensor_type"):
                for dim in out.type.tensor_type.shape.dim:
                    if dim.HasField("dim_value"):
                        shape.append(dim.dim_value)
                    else:
                        shape.append(-1)
            
            outputs.append({
                "name": out.name,
                "shape": shape,
            })
        
        # Write metadata
        metadata = {
            "model_name": model_name,
            "format": "onnx",
            "runtime": "onnxruntime",
            "inputs": inputs,
            "outputs": outputs,
            "opset_version": model.opset_import[0].version if model.opset_import else 0,
        }
        
        metadata_path = package_dir / "metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Create inference script
        inference_script = '''"""
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
'''
        
        script_path = package_dir / "inference.py"
        script_path.write_text(inference_script)
        
        # Calculate total size
        total_size = sum(f.stat().st_size for f in package_dir.rglob("*") if f.is_file())
        
        logger.info(f"ONNX Runtime package created: {package_dir}")
        
        return DeploymentArtifact(
            platform=TargetPlatform.CPU,
            format="onnx",
            path=package_dir,
            size_bytes=total_size,
            status=ArtifactStatus.SUCCESS,
            metadata={"inputs": inputs, "outputs": outputs},
        )
        
    except Exception as e:
        logger.error(f"ONNX Runtime packaging failed: {e}")
        return DeploymentArtifact(
            platform=TargetPlatform.CPU,
            format="onnx",
            path=None,
            size_bytes=0,
            status=ArtifactStatus.FAILED,
            error_message=str(e),
        )


def validate_onnxruntime_package(package_dir: Path) -> bool:
    """Validate ONNX Runtime package."""
    package_dir = Path(package_dir)
    
    required_files = ["model.onnx", "metadata.json", "inference.py"]
    
    for f in required_files:
        if not (package_dir / f).exists():
            return False
    
    return True
