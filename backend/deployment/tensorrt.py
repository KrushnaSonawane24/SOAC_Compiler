"""
SOAC TensorRT Deployment
========================

Build TensorRT engine for GPU deployment.
Supports FP16 and INT8 with calibration.
"""

import logging
import os
import numpy as np
from pathlib import Path
from typing import Optional, List, Dict, Any, Generator

try:
    import tensorrt as trt
    # pycuda/cuda-python are checked at runtime/calibration
    TENSORRT_AVAILABLE = True
except ImportError:
    TENSORRT_AVAILABLE = False
    trt = None

try:
    import onnx
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False

from .exceptions import TensorRTConversionError
from .metadata import DeploymentArtifact, TargetPlatform, ArtifactStatus, create_skipped_artifact


logger = logging.getLogger(__name__)


def is_tensorrt_available() -> bool:
    """Check if TensorRT is available."""
    return TENSORRT_AVAILABLE


if TENSORRT_AVAILABLE:
    # Try to import cuda-python for memory management
    try:
        from cuda.bindings import runtime as cudart
        CUDA_AVAILABLE = True
        USE_PYCUDA = False
    except ImportError:
        try:
            from cuda import cudart
            CUDA_AVAILABLE = True
            USE_PYCUDA = False
        except ImportError:
            try:
                import pycuda.driver as cuda
                import pycuda.autoinit
                CUDA_AVAILABLE = True
                USE_PYCUDA = True
            except ImportError:
                CUDA_AVAILABLE = False
                USE_PYCUDA = False

    class Calibrator(trt.IInt8EntropyCalibrator2):
        """
        INT8 Entropy Calibrator 2.
        Feeds data to TensorRT during calibration.
        """
        def __init__(self, data_loader: Generator[Dict[str, np.ndarray], None, None], cache_file: str):
            super().__init__()
            self.data_loader = data_loader
            self.cache_file = cache_file
            self.batch_size = 1 
            self.current_batch = None
            self.d_inputs = {} # Pointers to device memory
            self.allocation_size = {}
            
            if not CUDA_AVAILABLE:
                logger.warning("No CUDA python bindings found. INT8 calibration will fail.")

        def get_batch_size(self):
            return self.batch_size

        def get_batch(self, names):
            try:
                # Get next batch
                data_batch = next(self.data_loader)
                # data_batch is dict: {input_name: numpy_array}
                
                if not CUDA_AVAILABLE:
                    return None 
                
                # Create list of pointers matching 'names' order
                batch_ptrs = []
                
                for name in names:
                    if name not in data_batch:
                        logger.error(f"Calibration data missing for input: {name}")
                        return None
                        
                    data = data_batch[name]
                    # Ensure data is contiguous and float32 (calibration usually runs in fp32)
                    data = np.ascontiguousarray(data.astype(np.float32))
                    
                    # Allocate device memory if needed
                    nbytes = data.nbytes
                    
                    if name not in self.d_inputs or self.allocation_size.get(name) < nbytes:
                        if USE_PYCUDA:
                            self.d_inputs[name] = cuda.mem_alloc(nbytes)
                            self.allocation_size[name] = nbytes
                        else:
                            # cuda-python
                            err, ptr = cudart.cudaMalloc(nbytes)
                            if err != cudart.cudaError_t.cudaSuccess:
                                logger.error(f"cudaMalloc failed: {err}")
                                return None
                            self.d_inputs[name] = ptr
                            self.allocation_size[name] = nbytes
                            
                    # Copy data to device
                    if USE_PYCUDA:
                        cuda.memcpy_htod(self.d_inputs[name], data)
                        batch_ptrs.append(int(self.d_inputs[name]))
                    else:
                        err, = cudart.cudaMemcpy(self.d_inputs[name], data.ctypes.data, nbytes, cudart.cudaMemcpyKind.cudaMemcpyHostToDevice)
                        if err != cudart.cudaError_t.cudaSuccess:
                            logger.error(f"cudaMemcpy failed: {err}")
                            return None
                        batch_ptrs.append(int(self.d_inputs[name]))
                        
                return batch_ptrs
                
            except StopIteration:
                return None
            except Exception as e:
                logger.error(f"Calibration error: {e}")
                return None

        def read_calibration_cache(self):
            # If there is a cache, use it to skip calibration
            if os.path.exists(self.cache_file):
                with open(self.cache_file, "rb") as f:
                    return f.read()
            return None

        def write_calibration_cache(self, cache):
            with open(self.cache_file, "wb") as f:
                f.write(cache)
            
        def free(self):
            # Free memory
            if USE_PYCUDA:
                pass # PyCUDA handles cleanup automatically usually
            else:
                for ptr in self.d_inputs.values():
                    cudart.cudaFree(ptr)
            self.d_inputs = {}

else:
    class Calibrator:
        """Dummy Calibrator when TensorRT is not available."""
        pass


def _generate_calibration_data_generator(onnx_path: Path, num_samples: int = 10) -> Generator[Dict[str, np.ndarray], None, None]:
    """Generate dummy calibration data generator."""
    try:
        model = onnx.load(str(onnx_path))
        
        # Prepare shapes
        input_info = {}
        for input_tensor in model.graph.input:
            name = input_tensor.name
            shape = []
            for dim in input_tensor.type.tensor_type.shape.dim:
                if dim.dim_value > 0:
                    shape.append(dim.dim_value)
                else:
                    shape.append(1) 
            input_info[name] = shape
            
        for _ in range(num_samples):
            batch = {}
            for name, shape in input_info.items():
                # Random uniform data
                data = np.random.uniform(0.0, 1.0, shape).astype(np.float32)
                batch[name] = data
            yield batch
            
    except Exception as e:
        logger.warning(f"Failed to generate calibration data: {e}")
        yield {}


def build_tensorrt_engine(
    onnx_path: Path,
    output_path: Path,
    precision: str = "fp16",
    max_batch_size: int = 1,
) -> DeploymentArtifact:
    """
    Build TensorRT engine from ONNX model.
    
    Args:
        onnx_path: Path to source ONNX model.
        output_path: Path to save TensorRT engine.
        precision: Precision mode (fp32, fp16, int8).
        max_batch_size: Maximum batch size.
    
    Returns:
        DeploymentArtifact with result.
    """
    if not TENSORRT_AVAILABLE:
        return create_skipped_artifact(
            TargetPlatform.GPU,
            "tensorrt_engine",
            "TensorRT not available"
        )
    
    onnx_path = Path(onnx_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Building TensorRT engine: {onnx_path} (Precision: {precision})")
    
    calibrator = None
    
    try:
        TRT_LOGGER = trt.Logger(trt.Logger.WARNING)
        builder = trt.Builder(TRT_LOGGER)
        
        # EXPLICIT_BATCH is needed for ONNX
        network_flags = 1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH)
        network = builder.create_network(network_flags)
        
        parser = trt.OnnxParser(network, TRT_LOGGER)
        
        with open(onnx_path, 'rb') as f:
            if not parser.parse(f.read()):
                errors = []
                for i in range(parser.num_errors):
                    errors.append(parser.get_error(i).desc())
                raise TensorRTConversionError(f"ONNX parsing failed: {errors}")
        
        config = builder.create_builder_config()
        # Memory pool limit (formerly workspace size)
        config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, 1 << 30) # 1GB
        
        if precision == "fp16":
            if builder.platform_has_fast_fp16:
                config.set_flag(trt.BuilderFlag.FP16)
            else:
                logger.warning("FP16 not supported on this platform, falling back to FP32")
                
        elif precision == "int8":
            if builder.platform_has_fast_int8:
                config.set_flag(trt.BuilderFlag.INT8)
                
                # Setup Calibrator
                cache_file = str(output_path.with_suffix(".cache"))
                data_gen = _generate_calibration_data_generator(onnx_path)
                calibrator = Calibrator(data_gen, cache_file)
                config.int8_calibrator = calibrator
                
            else:
                logger.warning("INT8 not supported on this platform, falling back to FP16/FP32")
                if builder.platform_has_fast_fp16:
                    config.set_flag(trt.BuilderFlag.FP16)

        # Build Serialized Network
        plan = builder.build_serialized_network(network, config)
        
        if calibrator and hasattr(calibrator, 'free'):
            calibrator.free()
        
        if plan is None:
            raise TensorRTConversionError("Engine build failed (returned None)")
        
        with open(output_path, "wb") as f:
            f.write(plan)
            
        # Check size constraint (< 200MB)
        size_mb = output_path.stat().st_size / (1024 * 1024)
        if size_mb > 200:
             raise TensorRTConversionError(f"Model size {size_mb:.2f}MB exceeds 200MB limit")
             
        return DeploymentArtifact(
            platform=TargetPlatform.GPU,
            format="tensorrt_engine",
            path=output_path,
            status=ArtifactStatus.SUCCESS,
            size_bytes=output_path.stat().st_size,
            metadata={
                "precision": precision,
                "converter": "tensorrt"
            }
        )

    except Exception as e:
        logger.error(f"TensorRT conversion error: {str(e)}")
        if calibrator and hasattr(calibrator, 'free'):
            calibrator.free()
        return DeploymentArtifact(
            platform=TargetPlatform.GPU,
            format="tensorrt_engine",
            path=output_path,
            status=ArtifactStatus.FAILED,
            size_bytes=0,
            error_message=str(e)
        )
