"""
SOAC Cross-Job Optimization Cache
==================================

Deterministic read-only cache for optimization decisions.

Enables reuse of previous optimization decisions across jobs
with matching IR and configuration hashes.

GUARANTEES:
    - Read-only: No mutation of cached data
    - Deterministic: Same key always returns same value
    - No learning: Pure lookup, no feedback loops
    - Thread-safe: Safe for concurrent access
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Tuple
import json
import hashlib
import threading
from datetime import datetime, timezone
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


# =============================================================================
# CACHE ENTRY
# =============================================================================

@dataclass
class CacheEntry:
    """
    A single cache entry for an optimization decision.
    
    Stores the result of a previous optimization run for reuse.
    """
    # Key components
    ir_hash: str
    config_hash: str
    
    # Decision data
    selected_variant_id: str
    selected_variant_type: str
    
    # Metadata
    decision_reason: str
    constraints_satisfied: bool
    policy_used: str
    
    # Metrics at decision time
    latency_ms: float = 0.0
    size_bytes: int = 0
    accuracy_drop: float = 0.0
    
    # Provenance
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    job_id: Optional[str] = None
    
    def cache_key(self) -> str:
        """Generate the cache lookup key."""
        return f"{self.ir_hash}:{self.config_hash}"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "ir_hash": self.ir_hash,
            "config_hash": self.config_hash,
            "selected_variant_id": self.selected_variant_id,
            "selected_variant_type": self.selected_variant_type,
            "decision_reason": self.decision_reason,
            "constraints_satisfied": self.constraints_satisfied,
            "policy_used": self.policy_used,
            "latency_ms": self.latency_ms,
            "size_bytes": self.size_bytes,
            "accuracy_drop": self.accuracy_drop,
            "created_at": self.created_at,
            "job_id": self.job_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CacheEntry":
        return cls(
            ir_hash=data["ir_hash"],
            config_hash=data["config_hash"],
            selected_variant_id=data["selected_variant_id"],
            selected_variant_type=data["selected_variant_type"],
            decision_reason=data["decision_reason"],
            constraints_satisfied=data["constraints_satisfied"],
            policy_used=data["policy_used"],
            latency_ms=data.get("latency_ms", 0.0),
            size_bytes=data.get("size_bytes", 0),
            accuracy_drop=data.get("accuracy_drop", 0.0),
            created_at=data.get("created_at", ""),
            job_id=data.get("job_id"),
        )


@dataclass
class CacheLookupResult:
    """
    Result of a cache lookup.
    
    Indicates whether a cache hit occurred and provides the entry if found.
    """
    hit: bool
    entry: Optional[CacheEntry] = None
    miss_reason: Optional[str] = None
    
    @property
    def is_hit(self) -> bool:
        return self.hit
    
    @property
    def is_miss(self) -> bool:
        return not self.hit


# =============================================================================
# OPTIMIZATION CACHE
# =============================================================================

class OptimizationCache:
    """
    Deterministic cross-job optimization cache.
    
    Stores and retrieves previous optimization decisions based on
    IR hash and configuration hash.
    
    Key Features:
        - Deterministic: Same key always returns same value
        - Read-only lookups: No side effects on lookup
        - No learning: Pure storage, no adaptation
        - Thread-safe: Concurrent access supported
    
    Design:
        - Key: (ir_hash, config_hash) tuple
        - Value: CacheEntry with decision and metrics
        - Storage: In-memory with optional persistence
    
    Example:
        >>> cache = OptimizationCache()
        >>> result = cache.lookup(ir_hash, config_hash)
        >>> if result.is_hit:
        ...     print(f"Cached decision: {result.entry.selected_variant_id}")
    """
    
    def __init__(self, persist_path: Optional[Path] = None):
        """
        Initialize optimization cache.
        
        Args:
            persist_path: Optional path for persistent storage
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._persist_path = persist_path
        
        # Load from disk if path provided
        if persist_path and persist_path.exists():
            self._load_from_disk()
    
    def lookup(self, ir_hash: str, config_hash: str) -> CacheLookupResult:
        """
        Look up a cached optimization decision.
        
        This is a READ-ONLY operation with no side effects.
        
        Args:
            ir_hash: Hash of the IR graph
            config_hash: Hash of the configuration
        
        Returns:
            CacheLookupResult indicating hit/miss and entry if found
        """
        key = f"{ir_hash}:{config_hash}"
        
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                logger.debug(f"Cache hit for {key[:16]}...")
                return CacheLookupResult(hit=True, entry=entry)
            else:
                logger.debug(f"Cache miss for {key[:16]}...")
                return CacheLookupResult(
                    hit=False, 
                    miss_reason="No entry found for this IR + config combination"
                )
    
    def store(self, entry: CacheEntry) -> None:
        """
        Store an optimization decision in the cache.
        
        Args:
            entry: The cache entry to store
        """
        key = entry.cache_key()
        
        with self._lock:
            self._cache[key] = entry
            logger.debug(f"Cached decision for {key[:16]}...")
            
            # Persist if path configured
            if self._persist_path:
                self._save_to_disk()
    
    def contains(self, ir_hash: str, config_hash: str) -> bool:
        """Check if cache contains an entry."""
        key = f"{ir_hash}:{config_hash}"
        with self._lock:
            return key in self._cache
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            entries = list(self._cache.values())
        
        if not entries:
            return {
                "total_entries": 0,
                "policies_used": {},
                "avg_latency_ms": 0,
                "avg_size_mb": 0,
            }
        
        policies = {}
        total_latency = 0.0
        total_size = 0
        
        for entry in entries:
            policies[entry.policy_used] = policies.get(entry.policy_used, 0) + 1
            total_latency += entry.latency_ms
            total_size += entry.size_bytes
        
        return {
            "total_entries": len(entries),
            "policies_used": policies,
            "avg_latency_ms": total_latency / len(entries),
            "avg_size_mb": (total_size / len(entries)) / (1024 * 1024),
        }
    
    def clear(self) -> None:
        """Clear all cache entries."""
        with self._lock:
            self._cache.clear()
            logger.info("Optimization cache cleared")
    
    def export(self) -> List[Dict[str, Any]]:
        """Export all cache entries as a list of dicts."""
        with self._lock:
            return [entry.to_dict() for entry in self._cache.values()]
    
    def import_entries(self, entries: List[Dict[str, Any]]) -> int:
        """
        Import cache entries from a list of dicts.
        
        Returns:
            Number of entries imported
        """
        count = 0
        with self._lock:
            for data in entries:
                try:
                    entry = CacheEntry.from_dict(data)
                    self._cache[entry.cache_key()] = entry
                    count += 1
                except (KeyError, TypeError) as e:
                    logger.warning(f"Failed to import cache entry: {e}")
        
        logger.info(f"Imported {count} cache entries")
        return count
    
    def _save_to_disk(self) -> None:
        """Persist cache to disk."""
        if not self._persist_path:
            return
        
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._persist_path, 'w') as f:
                json.dump(self.export(), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    def _load_from_disk(self) -> None:
        """Load cache from disk."""
        if not self._persist_path or not self._persist_path.exists():
            return
        
        try:
            with open(self._persist_path, 'r') as f:
                entries = json.load(f)
            self.import_entries(entries)
        except Exception as e:
            logger.error(f"Failed to load cache: {e}")


# =============================================================================
# CACHE MANAGER (SINGLETON)
# =============================================================================

_global_cache: Optional[OptimizationCache] = None
_cache_lock = threading.Lock()


def get_optimization_cache(persist_path: Optional[Path] = None) -> OptimizationCache:
    """
    Get the global optimization cache instance.
    
    Thread-safe singleton accessor.
    
    Args:
        persist_path: Optional path for persistence (only used on first call)
    
    Returns:
        The global OptimizationCache instance
    """
    global _global_cache
    
    with _cache_lock:
        if _global_cache is None:
            _global_cache = OptimizationCache(persist_path)
        return _global_cache


def reset_optimization_cache() -> None:
    """Reset the global optimization cache."""
    global _global_cache
    
    with _cache_lock:
        _global_cache = None


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def compute_cache_key(ir_hash: str, config_hash: str) -> str:
    """Compute a cache key from IR and config hashes."""
    return f"{ir_hash}:{config_hash}"


def create_cache_entry(
    ir_hash: str,
    config_hash: str,
    variant_id: str,
    variant_type: str,
    policy: str,
    reason: str,
    constraints_met: bool = True,
    latency_ms: float = 0.0,
    size_bytes: int = 0,
    accuracy_drop: float = 0.0,
    job_id: Optional[str] = None,
) -> CacheEntry:
    """
    Create a cache entry from optimization results.
    
    Convenience function for creating entries with common parameters.
    """
    return CacheEntry(
        ir_hash=ir_hash,
        config_hash=config_hash,
        selected_variant_id=variant_id,
        selected_variant_type=variant_type,
        decision_reason=reason,
        constraints_satisfied=constraints_met,
        policy_used=policy,
        latency_ms=latency_ms,
        size_bytes=size_bytes,
        accuracy_drop=accuracy_drop,
        job_id=job_id,
    )
