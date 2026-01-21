"""
SOAC PDF Report Generation
==========================

Generate professional PDF reports.
"""

import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

from .models import ReportData, ReportVerdict
from .exceptions import PDFGenerationError

logger = logging.getLogger(__name__)

# Try to import reportlab
try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch, cm
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
        Image, PageBreak, HRFlowable
    )
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("ReportLab not available. PDF reports will not be generated.")


def generate_pdf_report(data: ReportData, output_dir: Path, chart_paths: dict = None) -> Optional[Path]:
    """Generate PDF report."""
    if not REPORTLAB_AVAILABLE:
        logger.warning("ReportLab not available - skipping PDF generation")
        return None
    
    path = output_dir / "soac_report.pdf"
    
    try:
        doc = SimpleDocTemplate(
            str(path),
            pagesize=A4,
            rightMargin=1*cm,
            leftMargin=1*cm,
            topMargin=1*cm,
            bottomMargin=1*cm,
        )
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1e1e2e'),
        )
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceBefore=15,
            spaceAfter=10,
            textColor=colors.HexColor('#4f46e5'),
        )
        body_style = styles['Normal']
        
        # Content
        content = []
        
        # Title
        content.append(Paragraph("SOAC Optimization Report", title_style))
        content.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#4f46e5')))
        content.append(Spacer(1, 20))
        
        # 1. Job Summary
        content.append(Paragraph("1. Job Summary", heading_style))
        job_data = [
            ["Job ID", data.job_id],
            ["User", data.user_id],
            ["Timestamp", data.timestamp],
            ["Build Mode", data.build_mode.upper()],
            ["Compilation Policy", data.compilation_policy.replace('_', ' ').title()],
        ]
        job_table = Table(job_data, colWidths=[3*cm, 12*cm])
        job_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
        ]))
        content.append(job_table)
        content.append(Spacer(1, 15))
        
        # 2. Input Model Details
        content.append(Paragraph("2. Input Model Details", heading_style))
        model_data = [
            ["Model Type", data.model_info.model_type],
            ["Architecture", data.model_info.architecture],
            ["Original Size", f"{data.model_info.original_size_bytes / 1024 / 1024:.2f} MB"],
            ["Task Type", data.model_info.task_type.title()],
        ]
        model_table = Table(model_data, colWidths=[3*cm, 12*cm])
        model_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
        ]))
        content.append(model_table)
        content.append(Spacer(1, 15))
        
        # 3. Optimization Summary
        content.append(Paragraph("3. Optimization Summary", heading_style))
        selected = next((v for v in data.variants if v.status == 'selected'), None)
        rejected = [v for v in data.variants if v.status == 'rejected']
        
        opt_text = f"""
        <b>Variants Generated:</b> {len(data.variants)}<br/>
        <b>Selected Variant:</b> {data.selected_variant_id or 'None'}<br/>
        <b>Rejected Variants:</b> {len(rejected)}
        """
        content.append(Paragraph(opt_text, body_style))
        
        if rejected:
            content.append(Spacer(1, 10))
            content.append(Paragraph("<b>Rejection Reasons:</b>", body_style))
            for v in rejected:
                content.append(Paragraph(f"• {v.variant_id}: {v.rejection_reason}", body_style))
        
        content.append(Spacer(1, 15))
        
        # 4. Accuracy Verification
        content.append(Paragraph("4. Accuracy Verification", heading_style))
        acc = data.accuracy_verification
        acc_status = "✓ PASSED" if acc.passed else "✗ FAILED"
        acc_color = colors.HexColor('#10b981') if acc.passed else colors.HexColor('#ef4444')
        
        acc_data = [
            ["Baseline Accuracy", f"{acc.baseline_accuracy * 100:.2f}%"],
            ["Optimized Accuracy", f"{acc.optimized_accuracy * 100:.2f}%"],
            ["Accuracy Delta", f"{acc.accuracy_delta * 100:.2f}%"],
            ["Threshold", f"≤ {acc.threshold * 100:.1f}%"],
            ["Status", acc_status],
        ]
        acc_table = Table(acc_data, colWidths=[3*cm, 12*cm])
        acc_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f3f4f6')),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('PADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
            ('TEXTCOLOR', (1, 4), (1, 4), acc_color),
        ]))
        content.append(acc_table)
        content.append(Spacer(1, 15))
        
        # 5. Performance Benchmarks
        content.append(Paragraph("5. Performance Benchmarks", heading_style))
        if data.variants:
            bench_header = ["Variant", "Latency (ms)", "Memory (MB)", "Size (MB)"]
            bench_data = [bench_header]
            for v in data.variants:
                bench_data.append([
                    v.variant_id[:20],
                    f"{v.latency_ms:.2f}",
                    f"{v.memory_mb:.1f}",
                    f"{v.size_bytes / 1024 / 1024:.2f}",
                ])
            
            bench_table = Table(bench_data, colWidths=[5*cm, 3*cm, 3*cm, 3*cm])
            bench_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4f46e5')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('PADDING', (0, 0), (-1, -1), 6),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
                ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ]))
            content.append(bench_table)
        content.append(Spacer(1, 15))
        
        # 6. Explainable Optimization Decision
        content.append(Paragraph("6. Explainable Optimization Decision", heading_style))
        explain_text = f"""
        <b>Policy Influence:</b> {data.policy_influence}<br/><br/>
        <b>Constraint Enforcement:</b> {data.constraint_statement}<br/><br/>
        <b>Selection Rationale:</b> {data.selection_reason}
        """
        content.append(Paragraph(explain_text, body_style))
        content.append(Spacer(1, 15))
        
        # 7. Reproducibility Proof
        content.append(Paragraph("7. Reproducibility Proof", heading_style))
        if data.build_fingerprint:
            content.append(Paragraph(f"<b>Build Fingerprint:</b>", body_style))
            content.append(Paragraph(f"<font face='Courier' size='8'>{data.build_fingerprint}</font>", body_style))
        content.append(Spacer(1, 5))
        content.append(Paragraph(f"<b>Guarantee:</b> {data.deterministic_guarantee}", body_style))
        content.append(Spacer(1, 15))
        
        # 8. Final Verdict
        content.append(Paragraph("8. Final Verdict", heading_style))
        verdict_color = colors.HexColor('#10b981') if data.verdict == ReportVerdict.PASSED else colors.HexColor('#ef4444')
        verdict_text = f"✓ {data.verdict.value}" if data.verdict == ReportVerdict.PASSED else f"✗ {data.verdict.value}"
        
        verdict_style = ParagraphStyle(
            'Verdict',
            parent=body_style,
            fontSize=18,
            textColor=verdict_color,
            fontName='Helvetica-Bold',
            alignment=TA_CENTER,
        )
        content.append(Paragraph(verdict_text, verdict_style))
        content.append(Spacer(1, 10))
        content.append(Paragraph(data.deployment_readiness, body_style))
        
        # Build PDF
        doc.build(content)
        return path
        
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        raise PDFGenerationError(f"Failed to generate PDF: {e}")
