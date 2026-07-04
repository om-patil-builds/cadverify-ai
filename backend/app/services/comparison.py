import logging
import re
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.db.models import ComparisonResult, DXFEntity, PDFParse, Upload

logger = logging.getLogger(__name__)


class ComparisonError(ValueError):
    """Raised when a comparison cannot be completed."""


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    cleaned = re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)
    return " ".join(cleaned.lower().split())


def compare_upload_data(upload_id: int, db: Session) -> Dict[str, Any]:
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise ComparisonError(f"Upload with id {upload_id} was not found")

    pdf_parse = (
        db.query(PDFParse)
        .filter(PDFParse.upload_id == upload_id)
        .order_by(PDFParse.id.desc())
        .first()
    )
    if not pdf_parse:
        raise ComparisonError("No parsed PDF information found for this upload")

    dxf_entities = (
        db.query(DXFEntity)
        .filter(DXFEntity.upload_id == upload_id)
        .order_by(DXFEntity.id)
        .all()
    )

    pdf_blocks = [
        {
            "page": block.get("page"),
            "text": block.get("text"),
            "bbox": block.get("bbox"),
            "normalized_text": _normalize_text(block.get("text")),
        }
        for block in pdf_parse.text_blocks or []
    ]

    dxf_texts = [
        {
            "id": entity.id,
            "type": entity.entity_type,
            "layer": entity.layer,
            "value": entity.data.get("value"),
            "insertion_point": entity.data.get("insertion_point"),
            "normalized_text": _normalize_text(entity.data.get("value")),
        }
        for entity in dxf_entities
        if entity.entity_type in {"TEXT", "MTEXT"}
    ]

    unmatched_dxf = dxf_texts.copy()
    matched: List[Dict[str, Any]] = []
    missing: List[Dict[str, Any]] = []

    for pdf_block in pdf_blocks:
        if not pdf_block["normalized_text"]:
            missing.append(
                {
                    "page": pdf_block["page"],
                    "text": pdf_block["text"],
                    "bbox": pdf_block["bbox"],
                }
            )
            continue

        match_index: Optional[int] = None
        for idx, dxf_text in enumerate(unmatched_dxf):
            if dxf_text["normalized_text"] == pdf_block["normalized_text"]:
                match_index = idx
                break

        if match_index is None:
            missing.append(
                {
                    "page": pdf_block["page"],
                    "text": pdf_block["text"],
                    "bbox": pdf_block["bbox"],
                }
            )
            continue

        matched_dxf = unmatched_dxf.pop(match_index)
        matched.append(
            {
                "pdf_text_block": {
                    "page": pdf_block["page"],
                    "text": pdf_block["text"],
                    "bbox": pdf_block["bbox"],
                },
                "dxf_entity": {
                    "id": matched_dxf["id"],
                    "type": matched_dxf["type"],
                    "layer": matched_dxf["layer"],
                    "value": matched_dxf["value"],
                    "insertion_point": matched_dxf["insertion_point"],
                },
            }
        )

    extra = [
        {
            "id": dxf_text["id"],
            "type": dxf_text["type"],
            "layer": dxf_text["layer"],
            "value": dxf_text["value"],
            "insertion_point": dxf_text["insertion_point"],
        }
        for dxf_text in unmatched_dxf
    ]

    matched_count = len(matched)
    missing_count = len(missing)
    extra_count = len(extra)
    total_count = matched_count + missing_count + extra_count
    accuracy = round((matched_count / total_count) * 100, 2) if total_count > 0 else 100.0

    comparison_payload = {
        "upload_id": upload_id,
        "status": "completed",
        "accuracy": accuracy,
        "matched_count": matched_count,
        "missing_count": missing_count,
        "extra_count": extra_count,
        "matched": matched,
        "missing": missing,
        "extra": extra,
    }

    try:
        db.query(ComparisonResult).filter(ComparisonResult.upload_id == upload_id).delete(synchronize_session=False)
        db.add(
            ComparisonResult(
                upload_id=upload_id,
                status="completed",
                accuracy=accuracy,
                matched_count=matched_count,
                missing_count=missing_count,
                extra_count=extra_count,
                matched=matched,
                missing=missing,
                extra=extra,
            )
        )
        db.commit()
    except Exception as exc:
        logger.exception("Failed to save comparison result", extra={"upload_id": upload_id})
        db.rollback()
        raise ComparisonError("Comparison completed, but failed to save the result.") from exc

    return comparison_payload
