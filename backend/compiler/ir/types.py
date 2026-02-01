"""
SOAC IR Type Definitions
========================

Core type enumerations for the SOAC IR.
"""

from enum import Enum, auto
from typing import Tuple, Union, Optional


class IRDataType(str, Enum):
    """Data types supported in SOAC IR."""
    
    # Floating point
    FLOAT32 = "float32"
    FLOAT16 = "float16"
    BFLOAT16 = "bfloat16"
    FLOAT64 = "float64"
    
    # Integer
    INT8 = "int8"
    INT16 = "int16"
    INT32 = "int32"
    INT64 = "int64"
    UINT8 = "uint8"
    UINT16 = "uint16"
    UINT32 = "uint32"
    UINT64 = "uint64"
    
    # Boolean
    BOOL = "bool"
    
    # Complex
    COMPLEX64 = "complex64"
    COMPLEX128 = "complex128"
    
    # String (rare in ML)
    STRING = "string"
    
    @classmethod
    def from_onnx(cls, onnx_type: int) -> "IRDataType":
        """Convert ONNX TensorProto.DataType to IRDataType."""
        # ONNX type enum values
        mapping = {
            1: cls.FLOAT32,   # FLOAT
            2: cls.UINT8,
            3: cls.INT8,
            4: cls.UINT16,
            5: cls.INT16,
            6: cls.INT32,
            7: cls.INT64,
            8: cls.STRING,
            9: cls.BOOL,
            10: cls.FLOAT16,
            11: cls.FLOAT64,
            12: cls.UINT32,
            13: cls.UINT64,
            14: cls.COMPLEX64,
            15: cls.COMPLEX128,
            16: cls.BFLOAT16,
        }
        return mapping.get(onnx_type, cls.FLOAT32)
    
    @property
    def byte_size(self) -> int:
        """Size in bytes per element."""
        sizes = {
            "float32": 4, "float16": 2, "bfloat16": 2, "float64": 8,
            "int8": 1, "int16": 2, "int32": 4, "int64": 8,
            "uint8": 1, "uint16": 2, "uint32": 4, "uint64": 8,
            "bool": 1, "complex64": 8, "complex128": 16, "string": 8,
        }
        return sizes.get(self.value, 4)


class IRLayout(str, Enum):
    """Memory layout for tensors."""
    
    NCHW = "nchw"  # PyTorch default: Batch, Channel, Height, Width
    NHWC = "nhwc"  # TensorFlow default: Batch, Height, Width, Channel
    NC = "nc"      # Batch, Channel (1D after flatten)
    NCW = "ncw"    # 1D conv: Batch, Channel, Width
    NCDHW = "ncdhw"  # 3D: Batch, Channel, Depth, Height, Width
    NDHWC = "ndhwc"  # 3D TF format
    
    # Special layouts
    UNDEFINED = "undefined"
    SCALAR = "scalar"


# Type alias for shape dimensions
# None represents dynamic dimension
IRShape = Tuple[Optional[int], ...]


def shape_to_str(shape: IRShape) -> str:
    """Convert shape tuple to string representation."""
    dims = []
    for d in shape:
        if d is None:
            dims.append("?")
        else:
            dims.append(str(d))
    return f"({', '.join(dims)})"


def compute_num_elements(shape: IRShape) -> Optional[int]:
    """Compute number of elements from shape. Returns None if any dim is dynamic."""
    result = 1
    for d in shape:
        if d is None:
            return None
        result *= d
    return result
