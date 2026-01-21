"""
Tests for Graph Normalizer
==========================

Tests for graph normalization functions.
"""

import pytest

from backend.compiler.graph_normalizer import (
    normalize_name,
    create_name_mapping,
    topological_sort_nodes,
    normalize_graph,
)


class TestNameNormalization:
    """Tests for tensor name normalization."""
    
    def test_normalize_simple_name(self):
        """Simple names are preserved."""
        assert normalize_name("input") == "input"
        assert normalize_name("output") == "output"
    
    def test_removes_tf_prefix(self):
        """TensorFlow prefixes are removed."""
        assert normalize_name("TF:conv1/weights") == "conv1_weights"
        assert normalize_name("keras/dense/bias") == "dense_bias"
    
    def test_replaces_special_chars(self):
        """Special characters become underscores."""
        assert normalize_name("layer-1:output") == "layer_1_output"
        assert normalize_name("conv.bn.relu") == "conv_bn_relu"
    
    def test_lowercase(self):
        """Names are lowercased."""
        assert normalize_name("CONV1") == "conv1"
        assert normalize_name("BatchNorm2d") == "batchnorm2d"
    
    def test_collapse_underscores(self):
        """Multiple underscores are collapsed."""
        assert normalize_name("a___b") == "a_b"
        assert normalize_name("_leading_") == "leading"
    
    def test_empty_becomes_tensor(self):
        """Empty names become 'tensor'."""
        assert normalize_name("") == "tensor"
        assert normalize_name("___") == "tensor"


class TestTopologicalSort:
    """Tests for node topological sorting."""
    
    def test_sort_linear_graph(self):
        """Linear graph maintains order."""
        import onnx
        from onnx import helper
        
        nodes = [
            helper.make_node('Relu', ['a'], ['b']),
            helper.make_node('Relu', ['b'], ['c']),
            helper.make_node('Relu', ['c'], ['d']),
        ]
        
        sorted_nodes = topological_sort_nodes(nodes, {'a'}, set())
        
        # Order should be preserved since it's already correct
        assert [n.output[0] for n in sorted_nodes] == ['b', 'c', 'd']
    
    def test_sort_handles_multiple_inputs(self):
        """Nodes with multiple inputs are handled."""
        import onnx
        from onnx import helper
        
        nodes = [
            helper.make_node('Add', ['a', 'b'], ['c']),
        ]
        
        sorted_nodes = topological_sort_nodes(nodes, {'a', 'b'}, set())
        
        assert len(sorted_nodes) == 1
        assert sorted_nodes[0].output[0] == 'c'


class TestGraphNormalization:
    """Tests for full graph normalization."""
    
    def test_normalize_simple_graph(self, simple_onnx_model):
        """Simple graph can be normalized."""
        normalized = normalize_graph(simple_onnx_model)
        
        # Should still have nodes
        assert len(normalized.graph.node) > 0
        
        # Names should be lowercase
        for node in normalized.graph.node:
            for output in node.output:
                if output:
                    assert output == output.lower()
