"""
SOAC Explainability Package
============================

Explainable optimization reports.
"""

from .report import (
    VariantStatus,
    VariantExplanation,
    SelectionExplanation,
    ExplainabilityReport,
    generate_markdown,
    create_explainability_report,
)

__all__ = [
    "VariantStatus",
    "VariantExplanation",
    "SelectionExplanation",
    "ExplainabilityReport",
    "generate_markdown",
    "create_explainability_report",
]
