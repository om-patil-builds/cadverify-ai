import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from app.db.models import Upload

logger = logging.getLogger(__name__)


class ReportGenerationError(ValueError):
    """Raised when a report cannot be generated."""


def _build_report_pdf(
    file_path: Path,
    upload: Upload,
    comparison: Optional[Dict[str, Any]] = None,
    pdf_parse: Optional[Dict[str, Any]] = None,
) -> Path:
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Heading1"],
        fontSize=22,
        spaceAfter=14,
        textColor=colors.HexColor("#0e7490"),
    )
    heading_style = ParagraphStyle(
        "ReportHeading",
        parent=styles["Heading2"],
        fontSize=14,
        spaceAfter=8,
        textColor=colors.HexColor("#164e63"),
    )
    body_style = ParagraphStyle(
        "ReportBody",
        parent=styles["BodyText"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#0f172a"),
    )
    label_style = ParagraphStyle(
        "ReportLabel",
        parent=styles["BodyText"],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#475569"),
    )

    story = []
    story.append(Paragraph("CADVerify AI", title_style))
    story.append(Paragraph("Engineering Drawing Verification Report", body_style))
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Upload Information", heading_style))
    upload_data = [
        [Paragraph("Upload ID", label_style), Paragraph(str(upload.id), body_style)],
        [Paragraph("PDF Filename", label_style), Paragraph(upload.pdf_filename, body_style)],
        [Paragraph("DXF Filename", label_style), Paragraph(upload.dxf_filename, body_style)],
        [Paragraph("Upload Date", label_style), Paragraph(upload.created_at.isoformat(), body_style)],
        [Paragraph("Comparison Date", label_style), Paragraph(datetime.utcnow().isoformat(), body_style)],
    ]
    upload_table = Table(upload_data, colWidths=[2.2 * inch, 4 * inch])
    upload_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#0f172a")),
                ("ALIGN", (0, 0), (0, -1), "LEFT"),
                ("ALIGN", (1, 0), (1, -1), "LEFT"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(upload_table)
    story.append(Spacer(1, 0.2 * inch))

    story.append(Paragraph("Parsing Status", heading_style))
    dxf_status = "Completed" if comparison else "Not Available"
    pdf_status = "Completed" if pdf_parse else "Not Available"
    parsing_data = [
        [Paragraph("DXF Parsing Status", label_style), Paragraph(dxf_status, body_style)],
        [Paragraph("PDF Parsing Status", label_style), Paragraph(pdf_status, body_style)],
    ]
    parsing_table = Table(parsing_data, colWidths=[2.2 * inch, 4 * inch])
    parsing_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(parsing_table)
    story.append(Spacer(1, 0.2 * inch))

    if comparison:
        story.append(Paragraph("Comparison Results", heading_style))
        overall_result = "PASS" if comparison.get("accuracy", 0) >= 90 else "FAIL"
        result_color = colors.HexColor("#16a34a") if overall_result == "PASS" else colors.HexColor("#dc2626")
        result_style = ParagraphStyle(
            "OverallResult",
            parent=body_style,
            fontSize=12,
            textColor=result_color,
            fontName="Helvetica-Bold",
        )
        comparison_data = [
            [Paragraph("Accuracy", label_style), Paragraph(f"{comparison.get('accuracy', 0)}%", body_style)],
            [Paragraph("Matched", label_style), Paragraph(str(comparison.get("matched_count", 0)), body_style)],
            [Paragraph("Missing", label_style), Paragraph(str(comparison.get("missing_count", 0)), body_style)],
            [Paragraph("Extra", label_style), Paragraph(str(comparison.get("extra_count", 0)), body_style)],
            [Paragraph("Overall Result", label_style), Paragraph(overall_result, result_style)],
        ]
        comparison_table = Table(comparison_data, colWidths=[2.2 * inch, 4 * inch])
        comparison_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#f1f5f9")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(comparison_table)

    file_path.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(
        str(file_path),
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )
    doc.build(story)
    return file_path


def generate_report(
    upload: Upload,
    comparison: Optional[Dict[str, Any]] = None,
    pdf_parse: Optional[Dict[str, Any]] = None,
    output_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    report_filename = f"report_{upload.id}_{timestamp}.pdf"
    report_path = (output_dir or Path("output") / "reports") / report_filename

    try:
        pdf_path = _build_report_pdf(report_path, upload, comparison, pdf_parse)
        return {
            "report_filename": report_filename,
            "report_path": str(pdf_path),
            "status": "completed",
        }
    except Exception as exc:
        logger.exception("Failed to generate report", extra={"upload_id": upload.id})
        raise ReportGenerationError("Failed to generate report.") from exc
