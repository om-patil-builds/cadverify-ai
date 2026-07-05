import logging
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import ComparisonResult, PDFParse, Report, Upload
from app.services.report_generator import ReportGenerationError, generate_report

logger = logging.getLogger(__name__)

REPORT_DIR: Path = Path(__file__).resolve().parent.parent.parent / "reports"

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("")
def list_reports(db: Session = Depends(get_db)) -> Dict[str, Any]:
    reports = db.query(Report).order_by(Report.created_at.desc()).all()
    return {
        "count": len(reports),
        "reports": [
            {
                "id": report.id,
                "upload_id": report.upload_id,
                "report_filename": report.report_filename,
                "status": report.status,
                "accuracy": report.accuracy,
                "matched_count": report.matched_count,
                "missing_count": report.missing_count,
                "extra_count": report.extra_count,
                "created_at": report.created_at.isoformat(),
            }
            for report in reports
        ],
    }


@router.post("/{upload_id}/generate")
def generate_report_for_upload(upload_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail=f"Upload with id {upload_id} was not found")

    comparison = (
        db.query(ComparisonResult)
        .filter(ComparisonResult.upload_id == upload_id)
        .order_by(ComparisonResult.id.desc())
        .first()
    )
    if not comparison:
        raise HTTPException(status_code=400, detail="Comparison result is required to generate a report")

    pdf_parse = (
        db.query(PDFParse)
        .filter(PDFParse.upload_id == upload_id)
        .order_by(PDFParse.id.desc())
        .first()
    )

    try:
        result = generate_report(
            upload=upload,
            comparison={
                "accuracy": comparison.accuracy,
                "matched_count": comparison.matched_count,
                "missing_count": comparison.missing_count,
                "extra_count": comparison.extra_count,
            },
            pdf_parse={"page_count": pdf_parse.page_count, "text_block_count": pdf_parse.text_block_count} if pdf_parse else None,
            output_dir=REPORT_DIR,
        )
    except ReportGenerationError as exc:
        logger.exception("Report generation error", extra={"upload_id": upload_id})
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive fallback for runtime errors
        logger.exception("Unexpected report generation failure", extra={"upload_id": upload_id})
        raise HTTPException(status_code=500, detail="Failed to generate report") from exc

    overall_result = "PASS" if comparison.accuracy >= 90 else "FAIL"
    report_record = Report(
        upload_id=upload_id,
        report_filename=result["report_filename"],
        report_path=result["report_path"],
        status=overall_result,
        accuracy=comparison.accuracy,
        matched_count=comparison.matched_count,
        missing_count=comparison.missing_count,
        extra_count=comparison.extra_count,
    )
    db.add(report_record)
    db.commit()
    db.refresh(report_record)

    return {
        "id": report_record.id,
        "upload_id": upload_id,
        "report_filename": report_record.report_filename,
        "status": report_record.status,
        "accuracy": report_record.accuracy,
        "matched_count": report_record.matched_count,
        "missing_count": report_record.missing_count,
        "extra_count": report_record.extra_count,
        "created_at": report_record.created_at.isoformat(),
    }


@router.get("/{report_id}/download")
def download_report(report_id: int, db: Session = Depends(get_db)) -> FileResponse:
    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail=f"Report with id {report_id} was not found")

    report_path = Path(report.report_path)
    if not report_path.exists() or not report_path.is_file():
        raise HTTPException(status_code=404, detail="Report file not found")

    return FileResponse(path=str(report_path), filename=report.report_filename, media_type="application/pdf")


@router.get("/uploads/{upload_id}")
def get_report_by_upload(upload_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    report = (
        db.query(Report)
        .filter(Report.upload_id == upload_id)
        .order_by(Report.id.desc())
        .first()
    )
    if not report:
        raise HTTPException(status_code=404, detail="No report found for this upload")

    return {
        "id": report.id,
        "upload_id": report.upload_id,
        "report_filename": report.report_filename,
        "status": report.status,
        "accuracy": report.accuracy,
        "matched_count": report.matched_count,
        "missing_count": report.missing_count,
        "extra_count": report.extra_count,
        "created_at": report.created_at.isoformat(),
    }
