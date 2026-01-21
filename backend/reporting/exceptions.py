"""
SOAC Reporting Exceptions
=========================

Exceptions for report generation.
"""


class ReportingError(Exception):
    """Base reporting error."""
    pass


class PDFGenerationError(ReportingError):
    """PDF generation failed."""
    pass


class ChartGenerationError(ReportingError):
    """Chart generation failed."""
    pass


class ExportError(ReportingError):
    """Export failed."""
    pass
