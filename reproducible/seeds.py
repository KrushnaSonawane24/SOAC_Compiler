"""
SOAC Reproducible Seeds
=======================

Manages random seeds for reproducible builds.
"""

import random
import os
from typing import Optional
from contextlib import contextmanager

# Default reproducible seed
DEFAULT_REPRODUCIBLE_SEED = 42


class SeedManager:
    """
    Manages random seeds for reproducible builds.
    
    In reproducible mode, all random operations use fixed seeds.
    """
    
    def __init__(self, reproducible: bool = False, seed: int = DEFAULT_REPRODUCIBLE_SEED):
        self.reproducible = reproducible
        self.seed = seed
        self._original_state: Optional[tuple] = None
    
    def __enter__(self):
        """Enter reproducible context."""
        if self.reproducible:
            self._original_state = random.getstate()
            random.seed(self.seed)
            
            # Also set numpy seed if available
            try:
                import numpy as np
                self._numpy_state = np.random.get_state()
                np.random.seed(self.seed)
            except ImportError:
                self._numpy_state = None
            
            # Set environment variable for other libraries
            os.environ['PYTHONHASHSEED'] = str(self.seed)
        
        return self
    
    def __exit__(self, *args):
        """Exit reproducible context."""
        if self.reproducible and self._original_state:
            random.setstate(self._original_state)
            
            if self._numpy_state is not None:
                try:
                    import numpy as np
                    np.random.set_state(self._numpy_state)
                except ImportError:
                    pass
            
            if 'PYTHONHASHSEED' in os.environ:
                del os.environ['PYTHONHASHSEED']
    
    def get_subseed(self, name: str) -> int:
        """Get a deterministic subseed based on name."""
        if not self.reproducible:
            return random.randint(0, 2**31 - 1)
        
        # Deterministic subseed based on name
        import hashlib
        h = hashlib.sha256(f"{self.seed}:{name}".encode())
        return int.from_bytes(h.digest()[:4], 'big') % (2**31 - 1)


@contextmanager
def reproducible_context(enabled: bool = True, seed: int = DEFAULT_REPRODUCIBLE_SEED):
    """Context manager for reproducible operations."""
    manager = SeedManager(reproducible=enabled, seed=seed)
    with manager:
        yield manager


def set_all_seeds(seed: int) -> None:
    """Set all random seeds."""
    random.seed(seed)
    
    try:
        import numpy as np
        np.random.seed(seed)
    except ImportError:
        pass
    
    os.environ['PYTHONHASHSEED'] = str(seed)
