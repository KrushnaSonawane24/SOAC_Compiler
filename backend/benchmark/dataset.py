"""
SOAC Dataset Interface
======================

Interface for reference datasets used in accuracy evaluation.

REQUIREMENTS:
    - Dataset must be explicitly provided
    - No automatic downloads
    - Same dataset for baseline and optimized models
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional, Iterator, Any
from pathlib import Path
import numpy as np

from .exceptions import DatasetError


@dataclass
class DatasetSample:
    """
    A single dataset sample.
    
    Attributes:
        input_data: Input tensor data (numpy array)
        label: Ground truth label (class index)
        sample_id: Optional identifier
    """
    input_data: np.ndarray
    label: int
    sample_id: Optional[str] = None


class ReferenceDataset:
    """
    Reference dataset for accuracy evaluation.
    
    This is an abstract interface. Actual datasets should
    implement the required methods.
    """
    
    def __init__(
        self,
        samples: List[DatasetSample],
        name: str = "reference_dataset",
        num_classes: int = 1000,
    ):
        if not samples:
            raise DatasetError("Dataset cannot be empty")
        
        self.samples = samples
        self.name = name
        self.num_classes = num_classes
    
    def __len__(self) -> int:
        return len(self.samples)
    
    def __iter__(self) -> Iterator[DatasetSample]:
        return iter(self.samples)
    
    def __getitem__(self, idx: int) -> DatasetSample:
        return self.samples[idx]
    
    def get_batch(self, batch_size: int) -> Iterator[List[DatasetSample]]:
        """Yield batches of samples."""
        for i in range(0, len(self.samples), batch_size):
            yield self.samples[i:i + batch_size]
    
    def get_input_shape(self) -> Tuple[int, ...]:
        """Get shape of input data."""
        return self.samples[0].input_data.shape
    
    def get_labels(self) -> List[int]:
        """Get all labels."""
        return [s.label for s in self.samples]


def create_synthetic_dataset(
    num_samples: int = 100,
    input_shape: Tuple[int, ...] = (1, 3, 224, 224),
    num_classes: int = 1000,
    seed: int = 42,
) -> ReferenceDataset:
    """
    Create a synthetic dataset for testing.
    
    This generates random data - NOT for real evaluation.
    Only use for testing the benchmark infrastructure.
    
    Args:
        num_samples: Number of samples to generate.
        input_shape: Shape of each input.
        num_classes: Number of classes.
        seed: Random seed for reproducibility.
    
    Returns:
        ReferenceDataset with synthetic data.
    """
    np.random.seed(seed)
    
    samples = []
    for i in range(num_samples):
        input_data = np.random.randn(*input_shape).astype(np.float32)
        label = np.random.randint(0, num_classes)
        samples.append(DatasetSample(
            input_data=input_data,
            label=label,
            sample_id=f"synthetic_{i}",
        ))
    
    return ReferenceDataset(
        samples=samples,
        name="synthetic_test_dataset",
        num_classes=num_classes,
    )


def load_dataset_from_numpy(
    inputs_path: Path,
    labels_path: Path,
    name: str = "numpy_dataset",
) -> ReferenceDataset:
    """
    Load dataset from numpy files.
    
    Args:
        inputs_path: Path to .npy file with inputs (N, C, H, W).
        labels_path: Path to .npy file with labels (N,).
        name: Dataset name.
    
    Returns:
        ReferenceDataset.
    """
    try:
        inputs = np.load(str(inputs_path))
        labels = np.load(str(labels_path))
    except Exception as e:
        raise DatasetError(f"Failed to load numpy files: {e}", e)
    
    if len(inputs) != len(labels):
        raise DatasetError(
            f"Input/label count mismatch: {len(inputs)} vs {len(labels)}"
        )
    
    samples = []
    for i, (inp, lbl) in enumerate(zip(inputs, labels)):
        samples.append(DatasetSample(
            input_data=inp.astype(np.float32),
            label=int(lbl),
            sample_id=f"{name}_{i}",
        ))
    
    num_classes = int(labels.max()) + 1
    
    return ReferenceDataset(
        samples=samples,
        name=name,
        num_classes=num_classes,
    )
