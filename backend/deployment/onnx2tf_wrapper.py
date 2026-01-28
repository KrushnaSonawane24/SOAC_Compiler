
import sys
import logging
import onnx.helper

# Patch ONNX helper for onnx-graphsurgeon compatibility
# This is needed because onnx-graphsurgeon expects float32_to_bfloat16 which might be missing in some ONNX versions
if not hasattr(onnx.helper, 'float32_to_bfloat16'):
    def float32_to_bfloat16(x):
        return 0
    onnx.helper.float32_to_bfloat16 = float32_to_bfloat16

from onnx2tf import onnx2tf

if __name__ == "__main__":
    sys.exit(onnx2tf.main())
