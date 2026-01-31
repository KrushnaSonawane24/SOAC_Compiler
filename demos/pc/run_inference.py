import argparse
import os
import sys
import time
import numpy as np

# Try to import tensorrt
try:
    import tensorrt as trt
    from cuda.bindings import runtime as cudart
except ImportError:
    print("Error: TensorRT or cuda-python not installed.")
    print("Please install: pip install tensorrt cuda-python")
    sys.exit(1)

class TensorRTInference:
    def __init__(self, engine_path):
        self.logger = trt.Logger(trt.Logger.WARNING)
        self.runtime = trt.Runtime(self.logger)
        
        print(f"Loading engine from {engine_path}...")
        with open(engine_path, "rb") as f:
            self.engine = self.runtime.deserialize_cuda_engine(f.read())
            
        self.context = self.engine.create_execution_context()
        self.inputs = []
        self.outputs = []
        self.allocations = []
        
        # Setup I/O bindings
        for i in range(self.engine.num_io_tensors):
            name = self.engine.get_tensor_name(i)
            is_input = self.engine.get_tensor_mode(name) == trt.TensorIOMode.INPUT
            dtype = self.engine.get_tensor_dtype(name)
            shape = self.engine.get_tensor_shape(name)
            
            # Handle dynamic shapes if necessary (here assuming static for simplicity as per requirements)
            if -1 in shape:
                print(f"Warning: Dynamic shape detected for {name}: {shape}. Using default profile.")
            
            # Create host buffer
            size = trt.volume(shape)
            # Map TRT dtype to numpy dtype
            np_dtype = np.float32
            if dtype == trt.float16:
                np_dtype = np.float16
            elif dtype == trt.int8:
                np_dtype = np.int8
            elif dtype == trt.int32:
                np_dtype = np.int32
                
            host_mem = np.zeros(shape, dtype=np_dtype)
            
            # Allocate device memory
            nbytes = host_mem.nbytes
            err, ptr = cudart.cudaMalloc(nbytes)
            if err != cudart.cudaError_t.cudaSuccess:
                raise RuntimeError(f"cudaMalloc failed for {name}")
                
            binding = {
                "name": name,
                "host": host_mem,
                "device": ptr,
                "size": nbytes,
                "shape": shape,
                "dtype": np_dtype
            }
            
            self.allocations.append(binding)
            if is_input:
                self.inputs.append(binding)
            else:
                self.outputs.append(binding)
                
            self.context.set_tensor_address(name, int(ptr))

    def infer(self, input_data_map=None):
        """
        Run inference.
        input_data_map: dict of input_name -> numpy array
        """
        # Load inputs to host buffers
        for binding in self.inputs:
            if input_data_map and binding["name"] in input_data_map:
                data = input_data_map[binding["name"]]
                np.copyto(binding["host"], data.reshape(binding["shape"]))
            else:
                # Fill with random data if not provided
                if input_data_map is None:
                     binding["host"] = np.random.random(binding["shape"]).astype(binding["dtype"])

            # Copy host to device
            err = cudart.cudaMemcpy(binding["device"], binding["host"].ctypes.data, binding["size"], cudart.cudaMemcpyKind.cudaMemcpyHostToDevice)
            if err[0] != cudart.cudaError_t.cudaSuccess:
                 raise RuntimeError(f"cudaMemcpy H2D failed for {binding['name']}")

        # Run inference
        self.context.execute_async_v3(0)

        # Copy device to host
        for binding in self.outputs:
            err = cudart.cudaMemcpy(binding["host"].ctypes.data, binding["device"], binding["size"], cudart.cudaMemcpyKind.cudaMemcpyDeviceToHost)
            if err[0] != cudart.cudaError_t.cudaSuccess:
                 raise RuntimeError(f"cudaMemcpy D2H failed for {binding['name']}")

        return {b["name"]: b["host"] for b in self.outputs}

    def cleanup(self):
        for binding in self.allocations:
            cudart.cudaFree(binding["device"])

def main():
    parser = argparse.ArgumentParser(description="Run TensorRT Inference")
    parser.add_argument("engine", help="Path to the TensorRT .engine or .plan file")
    args = parser.parse_args()

    if not os.path.exists(args.engine):
        print(f"Error: File {args.engine} not found.")
        sys.exit(1)

    try:
        trt_infer = TensorRTInference(args.engine)
        
        print("Warming up...")
        for _ in range(10):
            trt_infer.infer()
            
        print("Running benchmark (100 iterations)...")
        start_time = time.time()
        for _ in range(100):
            trt_infer.infer()
        end_time = time.time()
        
        avg_time = (end_time - start_time) / 100 * 1000 # ms
        print(f"Average Inference Time: {avg_time:.4f} ms")
        print(f"Throughput: {1000/avg_time:.2f} FPS")
        
        print("Inference successful.")
        
    except Exception as e:
        print(f"Failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
