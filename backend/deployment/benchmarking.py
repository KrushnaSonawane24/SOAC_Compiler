"""
SOAC Deployment Benchmarking
============================

Benchmarking tools for deployment artifacts (TFLite, TensorRT).
"""

import time
import logging
import numpy as np
from pathlib import Path
from typing import Optional, Tuple, List

try:
    import tensorflow as tf
    TFLITE_AVAILABLE = True
except ImportError:
    TFLITE_AVAILABLE = False

try:
    import tensorrt as trt
    import pycuda.driver as cuda
    import pycuda.autoinit  # Initialize CUDA
    TENSORRT_AVAILABLE = True
except ImportError:
    TENSORRT_AVAILABLE = False

logger = logging.getLogger(__name__)

def benchmark_tflite(
    model_path: Path,
    num_runs: int = 50,
    warmup_runs: int = 10,
    input_shape: Optional[Tuple] = None,
) -> Tuple[float, float]:
    """
    Benchmark TFLite model latency.
    
    Args:
        model_path: Path to .tflite model.
        num_runs: Number of measurement runs.
        warmup_runs: Number of warmup runs.
        input_shape: Optional explicit input shape.
        
    Returns:
        Tuple of (latency_ms, throughput_fps).
    """
    if not TFLITE_AVAILABLE:
        return 0.0, 0.0
        
    try:
        interpreter = tf.lite.Interpreter(model_path=str(model_path))
        interpreter.allocate_tensors()
        
        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()
        
        # Create dummy input
        input_shape = input_shape or input_details[0]['shape']
        input_dtype = input_details[0]['dtype']
        dummy_input = np.random.random(input_shape).astype(input_dtype)
        
        # Warmup
        for _ in range(warmup_runs):
            interpreter.set_tensor(input_details[0]['index'], dummy_input)
            interpreter.invoke()
            interpreter.get_tensor(output_details[0]['index'])
            
        # Measure
        latencies = []
        for _ in range(num_runs):
            start = time.perf_counter()
            interpreter.set_tensor(input_details[0]['index'], dummy_input)
            interpreter.invoke()
            interpreter.get_tensor(output_details[0]['index'])
            latencies.append((time.perf_counter() - start) * 1000)
            
        median_latency = np.median(latencies)
        return float(median_latency), 1000.0 / median_latency
        
    except Exception as e:
        logger.error(f"TFLite benchmark failed: {e}")
        return 0.0, 0.0

def benchmark_tensorrt(
    engine_path: Path,
    num_runs: int = 50,
    warmup_runs: int = 10,
) -> Tuple[float, float]:
    """
    Benchmark TensorRT engine latency.
    
    Args:
        engine_path: Path to .plan/.engine file.
        num_runs: Number of measurement runs.
        warmup_runs: Number of warmup runs.
        
    Returns:
        Tuple of (latency_ms, throughput_fps).
    """
    if not TENSORRT_AVAILABLE:
        return 0.0, 0.0
        
    try:
        TRT_LOGGER = trt.Logger(trt.Logger.WARNING)
        with open(engine_path, "rb") as f, trt.Runtime(TRT_LOGGER) as runtime:
            engine = runtime.deserialize_cuda_engine(f.read())
            
            with engine.create_execution_context() as context:
                # Allocate buffers
                inputs, outputs, bindings, stream = [], [], [], cuda.Stream()
                
                for binding in engine:
                    size = trt.volume(engine.get_binding_shape(binding))
                    dtype = trt.nptype(engine.get_binding_dtype(binding))
                    
                    # Allocate host and device memory
                    host_mem = cuda.pagelocked_empty(size, dtype)
                    device_mem = cuda.mem_alloc(host_mem.nbytes)
                    
                    bindings.append(int(device_mem))
                    
                    if engine.binding_is_input(binding):
                        inputs.append({"host": host_mem, "device": device_mem})
                        # Fill input
                        np.copyto(host_mem, np.random.random(size).astype(dtype))
                    else:
                        outputs.append({"host": host_mem, "device": device_mem})

                # Warmup
                for _ in range(warmup_runs):
                    # Transfer input data to device
                    for inp in inputs:
                        cuda.memcpy_htod_async(inp["device"], inp["host"], stream)
                    # Run inference
                    context.execute_async_v2(bindings=bindings, stream_handle=stream.handle)
                    # Transfer predictions back
                    for out in outputs:
                        cuda.memcpy_dtoh_async(out["host"], out["device"], stream)
                    stream.synchronize()

                # Measure
                latencies = []
                for _ in range(num_runs):
                    start = time.perf_counter()
                    
                    for inp in inputs:
                        cuda.memcpy_htod_async(inp["device"], inp["host"], stream)
                        
                    context.execute_async_v2(bindings=bindings, stream_handle=stream.handle)
                    
                    for out in outputs:
                        cuda.memcpy_dtoh_async(out["host"], out["device"], stream)
                    stream.synchronize()
                    
                    latencies.append((time.perf_counter() - start) * 1000)
                
                median_latency = np.median(latencies)
                return float(median_latency), 1000.0 / median_latency

    except Exception as e:
        logger.error(f"TensorRT benchmark failed: {e}")
        return 0.0, 0.0
