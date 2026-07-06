import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import fitz
from PIL import Image

from app.db.models import OCRResult

logger = logging.getLogger(__name__)


class OCREngineError(Exception):
    """Raised when OCR processing fails."""


class OCREngineUnavailable(Exception):
    """Raised when the OCR engine cannot be initialized."""


def _detect_tesseract_cmd() -> Optional[str]:
    """Auto-detect the Tesseract executable in common locations."""

    env_cmd = os.getenv("TESSERACT_CMD")
    if env_cmd and Path(env_cmd).exists():
        return env_cmd

    candidates = [
        Path(os.getenv("ProgramFiles", "")) / "Tesseract-OCR" / "tesseract.exe",
        Path(os.getenv("ProgramFiles(x86)", "")) / "Tesseract-OCR" / "tesseract.exe",
        Path(os.getenv("LOCALAPPDATA", "")) / "Programs" / "Tesseract-OCR" / "tesseract.exe",
        Path("C:/Program Files/Tesseract-OCR/tesseract.exe"),
        Path("C:/Program Files (x86)/Tesseract-OCR/tesseract.exe"),
    ]

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    return None


def _ensure_tesseract_available() -> str:
    """Ensure pytesseract and the Tesseract binary are available.

    Returns the detected tesseract command path.

    Raises:
        OCREngineUnavailable: If pytesseract or the Tesseract binary is missing.
    """
    try:
        import pytesseract  # noqa: F401
    except ImportError as exc:
        raise OCREngineUnavailable("pytesseract Python package is not installed.") from exc

    tesseract_cmd = _detect_tesseract_cmd()
    if tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    elif os.getenv("TESSERACT_CMD"):
        tesseract_cmd = os.getenv("TESSERACT_CMD")
        pytesseract.pytesseract.tesseract_cmd = tesseract_cmd

    try:
        import pytesseract
        pytesseract.get_tesseract_version()
    except EnvironmentError as exc:
        checked_paths = ", ".join(str(p) for p in [
            Path(os.getenv("ProgramFiles", "")) / "Tesseract-OCR" / "tesseract.exe",
            Path(os.getenv("ProgramFiles(x86)", "")) / "Tesseract-OCR" / "tesseract.exe",
            Path(os.getenv("LOCALAPPDATA", "")) / "Programs" / "Tesseract-OCR" / "tesseract.exe",
        ])
        raise OCREngineUnavailable(
            f"Tesseract OCR executable not found. Checked common paths: {checked_paths}. "
            "Install Tesseract OCR from https://github.com/tesseract-ocr/tesseract or set TESSERACT_CMD."
        ) from exc

    return tesseract_cmd or "tesseract"


def _render_page_to_image(page: fitz.Page) -> Image.Image:
    mat = fitz.Matrix(2.0, 2.0)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    return Image.frombytes("RGB", [pix.width, pix.height], pix.samples)


def run_ocr_on_pdf(file_path: str, dpi: int = 200) -> Dict[str, Any]:
    """Run OCR on a PDF file and return structured text blocks.

    Args:
        file_path: Path to the PDF file on disk.
        dpi: Resolution for rendering PDF pages to images before OCR.

    Returns:
        A dictionary containing page_count and ocr_pages with extracted blocks.

    Raises:
        OCREngineUnavailable: If pytesseract or Tesseract binary is missing.
        OCREngineError: If OCR processing fails.
    """
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        raise OCREngineError(f"PDF file not found: {path}")

    detected_cmd = _ensure_tesseract_available()
    logger.info("OCR engine detected", extra={"tesseract_cmd": detected_cmd, "file_path": str(path)})

    try:
        document = fitz.open(str(path))
    except Exception as exc:
        logger.exception("PyMuPDF image extraction failed", extra={"file_path": str(path)})
        raise OCREngineError(f"PyMuPDF image extraction failed: {path}") from exc

    page_count = document.page_count
    logger.info("OCR started", extra={"file_path": str(path), "page_count": page_count})

    ocr_pages: List[Dict[str, Any]] = []
    start_time = time.perf_counter()

    try:
        import pytesseract

        for page_number in range(page_count):
            page_start = time.perf_counter()
            page = document.load_page(page_number)
            image = _render_page_to_image(page)

            try:
                ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            except Exception as exc:
                logger.exception("Tesseract inference failed", extra={"file_path": str(path), "page": page_number + 1})
                raise OCREngineError(f"Tesseract inference failed on page {page_number + 1}") from exc

            blocks: List[Dict[str, Any]] = []
            n = len(ocr_data.get("text", []))
            for i in range(n):
                text = (ocr_data["text"][i] or "").strip()
                if not text:
                    continue

                confidence = float(ocr_data.get("conf", ["0"])[i] or 0)
                x = int(ocr_data.get("left", [0])[i] or 0)
                y = int(ocr_data.get("top", [0])[i] or 0)
                w = int(ocr_data.get("width", [0])[i] or 0)
                h = int(ocr_data.get("height", [0])[i] or 0)

                blocks.append(
                    {
                        "text": text,
                        "bbox": [x, y, x + w, y + h],
                        "confidence": round(confidence, 2),
                        "page": page_number + 1,
                    }
                )

            page_elapsed = time.perf_counter() - page_start
            logger.info(
                "OCR page processed",
                extra={"file_path": str(path), "page": page_number + 1, "blocks": len(blocks), "elapsed_sec": round(page_elapsed, 3)},
            )

            ocr_pages.append(
                {
                    "page": page_number + 1,
                    "text_block_count": len(blocks),
                    "blocks": blocks,
                }
            )
    except OCREngineError:
        raise
    except Exception as exc:
        logger.exception("OCR processing failed", extra={"file_path": str(path)})
        raise OCREngineError("OCR processing failed.") from exc
    finally:
        document.close()

    elapsed = time.perf_counter() - start_time
    total_blocks = sum(page.get("text_block_count", 0) for page in ocr_pages)

    logger.info(
        "OCR completed",
        extra={
            "file_path": str(path),
            "page_count": page_count,
            "text_block_count": total_blocks,
            "elapsed_sec": round(elapsed, 3),
        },
    )

    return {
        "page_count": page_count,
        "ocr_pages": ocr_pages,
        "text_block_count": total_blocks,
    }


def save_ocr_results(upload_id: int, ocr_result: Dict[str, Any], db, image_dir: Optional[Path] = None) -> None:
    """Persist OCR results to the database.

    One ``OCRResult`` record is created per page.

    Args:
        upload_id: Upload record id.
        ocr_result: Result from :func:`run_ocr_on_pdf`.
        db: SQLAlchemy session.
        image_dir: Optional directory to persist rendered page images.

    Raises:
        OCREngineError: If database persistence fails.
    """
    try:
        db.query(OCRResult).filter(OCRResult.upload_id == upload_id).delete(synchronize_session=False)

        records = []
        for page_data in ocr_result.get("ocr_pages", []):
            image_path = None
            if image_dir is not None:
                image_dir.mkdir(parents=True, exist_ok=True)
                image_path = str(image_dir / f"upload_{upload_id}_page_{page_data['page']}.png")

            records.append(
                OCRResult(
                    upload_id=upload_id,
                    page_number=page_data["page"],
                    image_path=image_path,
                    ocr_data=page_data,
                    text_block_count=page_data.get("text_block_count", 0),
                )
            )

        db.add_all(records)
        db.commit()
        logger.info(
            "OCR results saved",
            extra={"upload_id": upload_id, "pages": len(records), "text_blocks": sum(r.text_block_count for r in records)},
        )
    except Exception as exc:
        logger.exception("Failed to save OCR results", extra={"upload_id": upload_id})
        db.rollback()
        raise OCREngineError("OCR completed, but failed to save results.") from exc
