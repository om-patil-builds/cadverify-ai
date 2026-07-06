import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import fitz
from sqlalchemy.orm import Session

from app.db.models import OCRResult, PDFParse
from app.services.ocr_engine import OCREngineError, OCREngineUnavailable, run_ocr_on_pdf

logger = logging.getLogger(__name__)


class PDFParseError(ValueError):
    """Raised when a PDF file cannot be parsed."""


def _safe_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    return str(value).strip() or None


def _extract_block_text(block: Dict[str, Any]) -> Optional[str]:
    text = _safe_text(block.get("text"))
    if text:
        return text

    lines = block.get("lines", [])
    processed_lines = []
    for line in lines:
        spans = line.get("spans", [])
        span_text = "".join(_safe_text(span.get("text")) or "" for span in spans)
        if span_text:
            processed_lines.append(span_text)

    return _safe_text("\n".join(processed_lines)) if processed_lines else None


_IMAGE_DIR: Path = Path(__file__).resolve().parent.parent.parent / "output" / "ocr_images"


def parse_pdf(file_path: str, db: Session | None = None, upload_id: int | None = None) -> Dict[str, Any]:
    """Parse a PDF file and return structured drawing metadata, text blocks, and OCR results.

    Args:
        file_path: Path to the PDF file on disk.
        db: Optional SQLAlchemy session for persistence of parsed information.
        upload_id: Optional upload record id to link parsed PDF information.

    Returns:
        A dictionary containing parsed PDF metadata, text blocks, and OCR statistics.

    Raises:
        PDFParseError: If the file is missing, unreadable, or not a valid PDF.
    """
    path = Path(file_path)
    logger.info("Parsing PDF started", extra={"file_path": str(path)})

    if not path.exists():
        raise PDFParseError(f"PDF file not found: {path}")
    if not path.is_file():
        raise PDFParseError(f"PDF path is not a file: {path}")

    try:
        document = fitz.open(str(path))
    except Exception as exc:
        logger.exception("Failed to open PDF file", extra={"file_path": str(path)})
        raise PDFParseError(f"Unable to read PDF file: {path}") from exc

    page_count = document.page_count
    metadata_raw = document.metadata or {}
    metadata = {
        "title": _safe_text(metadata_raw.get("title")),
        "author": _safe_text(metadata_raw.get("author")),
        "creator": _safe_text(metadata_raw.get("creator")),
        "producer": _safe_text(metadata_raw.get("producer")),
        "creation_date": _safe_text(metadata_raw.get("creationDate")),
    }

    text_blocks: List[Dict[str, Any]] = []
    total_text_count = 0

    for page_number in range(page_count):
        page = document.load_page(page_number)
        page_blocks = page.get_text("dict").get("blocks", [])

        for block in page_blocks:
            if block.get("type") != 0:
                continue

            text = _extract_block_text(block)
            if not text:
                continue

            bbox = block.get("bbox")
            text_blocks.append(
                {
                    "page": page_number + 1,
                    "bbox": [float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])] if bbox else None,
                    "text": text,
                }
            )
            total_text_count += len(text.split())

    ocr_status = "not_run"
    ocr_text_block_count = 0
    ocr_pages: List[Dict[str, Any]] = []
    ocr_error = None

    if db is not None and upload_id is not None:
        try:
            ocr_result = run_ocr_on_pdf(str(path))
            ocr_pages = ocr_result.get("ocr_pages", [])
            ocr_text_block_count = ocr_result.get("text_block_count", 0)
            ocr_status = "completed"

            from app.services.ocr_engine import save_ocr_results

            save_ocr_results(upload_id=upload_id, ocr_result=ocr_result, db=db, image_dir=_IMAGE_DIR)
        except OCREngineUnavailable as exc:
            logger.warning("OCR skipped: engine unavailable", extra={"upload_id": upload_id, "error": str(exc)})
            ocr_status = "unavailable"
            ocr_error = str(exc)
        except OCREngineError as exc:
            logger.error("OCR failed", extra={"upload_id": upload_id, "error": str(exc)})
            ocr_status = "failed"
            ocr_error = str(exc)

    result = {
        "page_count": page_count,
        "metadata": metadata,
        "text_blocks": text_blocks,
        "text_block_count": len(text_blocks),
        "total_text_count": total_text_count,
        "ocr": {
            "status": ocr_status,
            "text_block_count": ocr_text_block_count,
            "pages": ocr_pages,
            "error": ocr_error,
        },
    }

    if db is not None and upload_id is not None:
        logger.info("Saving parsed PDF information to database", extra={"file_path": str(path), "upload_id": upload_id})
        try:
            db.query(PDFParse).filter(PDFParse.upload_id == upload_id).delete(synchronize_session=False)
            db.add(
                PDFParse(
                    upload_id=upload_id,
                    page_count=page_count,
                    metadata_json=metadata,
                    text_blocks=text_blocks,
                    text_block_count=len(text_blocks),
                    total_text_count=total_text_count,
                )
            )
            db.commit()
        except Exception as exc:
            logger.exception("Failed to save parsed PDF information", extra={"upload_id": upload_id})
            db.rollback()
            raise PDFParseError("PDF parsed successfully but failed to save parsed information.") from exc

    logger.info(
        "Parsing PDF completed",
        extra={"file_path": str(path), "page_count": page_count, "text_blocks": len(text_blocks), "ocr_status": ocr_status},
    )
    return result
