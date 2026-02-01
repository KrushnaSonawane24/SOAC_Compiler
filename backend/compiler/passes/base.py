"""
SOAC Compiler Pass Base Classes
===============================

Abstract base class and common types for compiler passes.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Generic, TypeVar
from datetime import datetime, timezone
import time
import logging


logger = logging.getLogger(__name__)


# Type variables for generic pass typing
InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


@dataclass
class TraceEntry:
    """
    A single entry in the explainability trace.
    
    Records decisions made during pass execution.
    """
    
    pass_name: str
    timestamp: str
    action: str
    details: Dict[str, Any] = field(default_factory=dict)
    duration_ms: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "pass_name": self.pass_name,
            "timestamp": self.timestamp,
            "action": self.action,
            "details": self.details,
            "duration_ms": self.duration_ms,
        }


@dataclass
class PassContext:
    """
    Context shared across all compiler passes.
    
    Accumulates metadata and trace entries throughout compilation.
    """
    
    job_id: str
    config: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    trace_entries: List[TraceEntry] = field(default_factory=list)
    logs: List[str] = field(default_factory=list)
    
    def log(self, message: str) -> None:
        """Add a log message."""
        timestamp = datetime.now(timezone.utc).isoformat()
        self.logs.append(f"[{timestamp}] {message}")
        logger.info(f"[{self.job_id}] {message}")
    
    def add_trace(
        self,
        pass_name: str,
        action: str,
        details: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[float] = None,
    ) -> None:
        """Add a trace entry."""
        entry = TraceEntry(
            pass_name=pass_name,
            timestamp=datetime.now(timezone.utc).isoformat(),
            action=action,
            details=details or {},
            duration_ms=duration_ms,
        )
        self.trace_entries.append(entry)
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        return self.config.get(key, default)
    
    def set_metadata(self, key: str, value: Any) -> None:
        """Set a metadata value."""
        self.metadata[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize context to dictionary."""
        return {
            "job_id": self.job_id,
            "config": self.config,
            "metadata": self.metadata,
            "trace_entries": [t.to_dict() for t in self.trace_entries],
            "logs": self.logs,
        }


@dataclass
class PassResult(Generic[OutputT]):
    """
    Result of a compiler pass execution.
    
    Contains:
        - success: Whether the pass succeeded
        - output: The transformed data
        - duration_ms: Execution time
        - trace: Explainability entry
        - error: Error message if failed
    """
    
    success: bool
    output: Optional[OutputT]
    duration_ms: float
    trace: TraceEntry
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        return {
            "success": self.success,
            "duration_ms": self.duration_ms,
            "trace": self.trace.to_dict(),
            "error": self.error,
        }


class BasePass(ABC, Generic[InputT, OutputT]):
    """
    Abstract base class for all SOAC compiler passes.
    
    Each pass:
        - Accepts input data and context
        - Returns transformed output
        - Is deterministic (same input -> same output)
        - Logs decisions for explainability
        - Produces trace entries for audit
    
    Example:
        >>> class MyPass(BasePass[IRGraph, IRGraph]):
        ...     name = "my_pass"
        ...     
        ...     def run(self, input: IRGraph, ctx: PassContext) -> PassResult[IRGraph]:
        ...         # Transform input
        ...         return PassResult(success=True, output=transformed, ...)
    """
    
    # Pass name (override in subclass)
    name: str = "base_pass"
    
    # Pass description
    description: str = "Base compiler pass"
    
    @abstractmethod
    def run(self, input: InputT, ctx: PassContext) -> PassResult[OutputT]:
        """
        Execute the pass.
        
        Args:
            input: Input data to transform
            ctx: Shared context
        
        Returns:
            PassResult containing success status and output
        
        MUST be deterministic - same input always produces same output.
        """
        pass
    
    def __call__(self, input: InputT, ctx: PassContext) -> PassResult[OutputT]:
        """
        Execute pass with timing and error handling.
        
        This is the preferred way to run a pass.
        """
        start = time.perf_counter()
        
        try:
            ctx.log(f"Starting pass: {self.name}")
            result = self.run(input, ctx)
            
            duration = (time.perf_counter() - start) * 1000
            result.trace.duration_ms = duration
            
            ctx.add_trace(
                pass_name=self.name,
                action="completed" if result.success else "failed",
                details={"duration_ms": duration, "error": result.error},
                duration_ms=duration,
            )
            
            ctx.log(f"Pass {self.name} completed in {duration:.2f}ms")
            return result
            
        except Exception as e:
            duration = (time.perf_counter() - start) * 1000
            error_msg = str(e)
            
            ctx.log(f"Pass {self.name} failed: {error_msg}")
            ctx.add_trace(
                pass_name=self.name,
                action="error",
                details={"error": error_msg},
                duration_ms=duration,
            )
            
            trace = TraceEntry(
                pass_name=self.name,
                timestamp=datetime.now(timezone.utc).isoformat(),
                action="error",
                details={"error": error_msg},
                duration_ms=duration,
            )
            
            return PassResult(
                success=False,
                output=None,
                duration_ms=duration,
                trace=trace,
                error=error_msg,
            )
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}')"
