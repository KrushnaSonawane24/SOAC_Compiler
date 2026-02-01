"""
SOAC Backend Package
===================

Self-Optimizing AI Compiler backend services.
"""

__version__ = "1.0.0"

import logging
import onnx.helper
import numpy as np

if "object" not in np.__dict__:
    np.object = object
if "bool" not in np.__dict__:
    np.bool = bool
if "int" not in np.__dict__:
    np.int = int
if "float" not in np.__dict__:
    np.float = float
if "cast" not in np.__dict__:
    class _NpCast:
        def __getitem__(self, dtype):
            dt = np.dtype(dtype)
            def _cast(x, dt=dt):
                return np.asarray(x, dtype=dt)
            return _cast
    np.cast = _NpCast()

_make_attribute = onnx.helper.make_attribute
def _patched_make_attribute(key, value, doc_string=None, attr_type=None):
    if key == "shape" and isinstance(value, (list, tuple)) and len(value) == 0:
        from onnx import AttributeProto
        return _make_attribute(key, value, doc_string=doc_string, attr_type=AttributeProto.INTS)
    return _make_attribute(key, value, doc_string=doc_string, attr_type=attr_type)
onnx.helper.make_attribute = _patched_make_attribute

if not hasattr(onnx.helper, 'float32_to_bfloat16'):
    logging.getLogger(__name__).warning("Patching onnx.helper.float32_to_bfloat16 for onnx-graphsurgeon compatibility")
    def float32_to_bfloat16(x):
        return 0
    onnx.helper.float32_to_bfloat16 = float32_to_bfloat16
