import logging
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import ComparisonResult, DXFEntity, PDFParse, Upload
from app.services.comparison import ComparisonError, compare_geometry, compare_upload_data
from app.services.dxf_parser import DXFParseError, parse_dxf
from app.services.pdf_parser import PDFParseError, parse_pdf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/uploads", tags=["Uploads"])


@router.get("")
def list_uploads(db: Session = Depends(get_db)) -> Dict[str, Any]:
    uploads = db.query(Upload).order_by(Upload.created_at.desc()).all()
    comparison_count = db.query(ComparisonResult).count()
    return {
        "count": len(uploads),
        "comparison_count": comparison_count,
        "uploads": [
            {
                "id": upload.id,
                "pdf_filename": upload.pdf_filename,
                "dxf_filename": upload.dxf_filename,
                "created_at": upload.created_at.isoformat(),
            }
            for upload in uploads
        ],
    }


@router.get("/{upload_id}")
def get_upload(upload_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail=f"Upload with id {upload_id} was not found")
    return {
        "id": upload.id,
        "pdf_filename": upload.pdf_filename,
        "dxf_filename": upload.dxf_filename,
        "pdf_path": upload.pdf_path,
        "dxf_path": upload.dxf_path,
        "created_at": upload.created_at.isoformat(),
        "status": "uploaded",
    }


@router.delete("/{upload_id}", status_code=204)
def delete_upload(upload_id: int, db: Session = Depends(get_db)) -> None:
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail=f"Upload with id {upload_id} was not found")

    pdf_path = Path(upload.pdf_path)
    dxf_path = Path(upload.dxf_path)

    try:
        pdf_path.unlink(missing_ok=True)
        dxf_path.unlink(missing_ok=True)
    except Exception as exc:
        logger.exception("Failed to delete upload files", extra={"upload_id": upload_id, "pdf_path": str(pdf_path), "dxf_path": str(dxf_path)})
        raise HTTPException(status_code=500, detail="Failed to delete upload files") from exc

    db.delete(upload)
    db.commit()


@router.get("/{upload_id}/download/pdf")
def download_upload_pdf(upload_id: int, db: Session = Depends(get_db)) -> FileResponse:
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail=f"Upload with id {upload_id} was not found")

    pdf_path = Path(upload.pdf_path)
    if not pdf_path.exists() or not pdf_path.is_file():
        raise HTTPException(status_code=404, detail="PDF file not found for this upload")

    return FileResponse(path=str(pdf_path), filename=upload.pdf_filename, media_type='application/pdf')


@router.get("/{upload_id}/download/dxf")
def download_upload_dxf(upload_id: int, db: Session = Depends(get_db)) -> FileResponse:
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail=f"Upload with id {upload_id} was not found")

    dxf_path = Path(upload.dxf_path)
    if not dxf_path.exists() or not dxf_path.is_file():
        raise HTTPException(status_code=404, detail="DXF file not found for this upload")

    return FileResponse(path=str(dxf_path), filename=upload.dxf_filename, media_type='application/dxf')


@router.get("/{upload_id}/parse")
def parse_upload_dxf(upload_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Parse the DXF file associated with an uploaded drawing record."""
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail=f"Upload with id {upload_id} was not found")

    dxf_path = Path(upload.dxf_path)
    if not dxf_path.exists() or not dxf_path.is_file():
        raise HTTPException(status_code=404, detail="DXF file is missing for this upload")

    try:
        logger.info("Parsing started", extra={"upload_id": upload_id, "file_path": str(dxf_path)})
        parsed_result = parse_dxf(str(dxf_path), db=db, upload_id=upload_id)
        entity_count = sum(parsed_result.get("summary", {}).values())
        logger.info("Parsing completed", extra={"upload_id": upload_id, "entity_count": entity_count})
        return {
            "upload_id": upload_id,
            "dxf_path": str(dxf_path),
            "parsed": parsed_result,
        }
    except DXFParseError as exc:
        logger.exception("DXF parsing error", extra={"upload_id": upload_id, "file_path": str(dxf_path)})
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive fallback for runtime errors
        logger.exception("Unexpected DXF parsing failure", extra={"upload_id": upload_id, "file_path": str(dxf_path)})
        raise HTTPException(status_code=500, detail="Failed to parse DXF file") from exc


@router.get("/{upload_id}/parse-pdf")
def parse_upload_pdf(upload_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Parse the PDF file associated with an uploaded drawing record."""
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail=f"Upload with id {upload_id} was not found")

    pdf_path = Path(upload.pdf_path)
    if not pdf_path.exists() or not pdf_path.is_file():
        raise HTTPException(status_code=404, detail="PDF file is missing for this upload")

    try:
        logger.info("PDF parsing started", extra={"upload_id": upload_id, "file_path": str(pdf_path)})
        parsed_result = parse_pdf(str(pdf_path), db=db, upload_id=upload_id)
        logger.info("PDF parsing completed", extra={"upload_id": upload_id, "page_count": parsed_result.get("page_count", 0)})
        return {
            "upload_id": upload_id,
            "pdf_path": str(pdf_path),
            "parsed": parsed_result,
        }
    except PDFParseError as exc:
        logger.exception("PDF parsing error", extra={"upload_id": upload_id, "file_path": str(pdf_path)})
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive fallback for runtime errors
        logger.exception("Unexpected PDF parsing failure", extra={"upload_id": upload_id, "file_path": str(pdf_path)})
        raise HTTPException(status_code=500, detail="Failed to parse PDF file") from exc


@router.get("/{upload_id}/parsed-pdf")
def get_parsed_pdf(upload_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail=f"Upload with id {upload_id} was not found")

    pdf_parse = (
        db.query(PDFParse)
        .filter(PDFParse.upload_id == upload_id)
        .order_by(PDFParse.id.desc())
        .first()
    )
    if not pdf_parse:
        raise HTTPException(status_code=404, detail="No parsed PDF information found for this upload")

    return {
        "upload_id": upload_id,
        "page_count": pdf_parse.page_count,
        "metadata": pdf_parse.metadata_json,
        "text_block_count": pdf_parse.text_block_count,
        "total_text_count": pdf_parse.total_text_count,
        "text_blocks": pdf_parse.text_blocks,
        "created_at": pdf_parse.created_at.isoformat(),
    }


@router.get("/{upload_id}/parsed-entities")
def get_parsed_entities(upload_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail=f"Upload with id {upload_id} was not found")

    entities = (
        db.query(DXFEntity)
        .filter(DXFEntity.upload_id == upload_id)
        .order_by(DXFEntity.id)
        .all()
    )

    summary: Dict[str, int] = {}
    for entity in entities:
        key = f"{entity.entity_type.lower()}s"
        summary[key] = summary.get(key, 0) + 1

    return {
        "upload_id": upload_id,
        "entity_count": len(entities),
        "summary": summary,
        "entities": [
            {
                "id": entity.id,
                "type": entity.entity_type,
                "layer": entity.layer,
                "data": entity.data,
            }
            for entity in entities
        ],
    }


@router.get("/{upload_id}/compare")
def compare_upload(upload_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise HTTPException(status_code=404, detail=f"Upload with id {upload_id} was not found")

    try:
        comparison_data = compare_upload_data(upload_id=upload_id, db=db)

        dxf_entities = (
            db.query(DXFEntity)
            .filter(DXFEntity.upload_id == upload_id)
            .order_by(DXFEntity.id)
            .all()
        )
        pdf_parse = (
            db.query(PDFParse)
            .filter(PDFParse.upload_id == upload_id)
            .order_by(PDFParse.id.desc())
            .first()
        )
        geometry = compare_geometry(pdf_parse.text_blocks if pdf_parse else [], dxf_entities)

        geometry_changed_entities = []
        for etype_data in geometry["entity_types"].values():
            geometry_changed_entities.extend(etype_data.get("changed", []))

        comparison_data["changed_count"] = geometry["summary"]["changed"]
        comparison_data["changed"] = [
            {
                "category": "geometry",
                "type": item["type"],
                "dxf_id": item["dxf_id"],
                "layer": item["layer"],
                "change_type": "geometry_changed",
                "iou": item.get("iou"),
                "page": item.get("page"),
                "entity_bbox": item.get("entity_bbox"),
                "pdf_bbox": item.get("pdf_bbox"),
                "area_ratio": item.get("area_ratio"),
            }
            for item in geometry_changed_entities
        ]
        comparison_data["geometry"] = geometry

        return comparison_data
    except ComparisonError as exc:
        logger.exception("Comparison error", extra={"upload_id": upload_id})
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive fallback for runtime errors
        logger.exception("Unexpected comparison failure", extra={"upload_id": upload_id})
        raise HTTPException(status_code=500, detail="Failed to compare upload data") from exc


@router.get("/{upload_id}/comparison")
def get_comparison_result(upload_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
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
        raise HTTPException(status_code=404, detail="No comparison result found for this upload")

    geometry_payload = {
        "accuracy": comparison.accuracy,
        "entity_types": {},
        "summary": {"matched": 0, "missing": 0, "extra": 0, "changed": 0},
    }

    try:
        dxf_entities = (
            db.query(DXFEntity)
            .filter(DXFEntity.upload_id == upload_id)
            .order_by(DXFEntity.id)
            .all()
        )
        pdf_parse = (
            db.query(PDFParse)
            .filter(PDFParse.upload_id == upload_id)
            .order_by(PDFParse.id.desc())
            .first()
        )
        geometry_payload = compare_geometry(pdf_parse.text_blocks if pdf_parse else [], dxf_entities)
    except Exception as exc:  # pragma: no cover - defensive fallback for runtime errors
        logger.exception("Geometry enrichment failed", extra={"upload_id": upload_id})

    geometry_changed_entities = []
    for etype_data in geometry_payload.get("entity_types", {}).values():
        geometry_changed_entities.extend(etype_data.get("changed", []))

    changed_items = [
        {
            "category": "geometry",
            "type": item["type"],
            "dxf_id": item["dxf_id"],
            "layer": item["layer"],
            "change_type": "geometry_changed",
            "iou": item.get("iou"),
            "page": item.get("page"),
            "entity_bbox": item.get("entity_bbox"),
            "pdf_bbox": item.get("pdf_bbox"),
            "area_ratio": item.get("area_ratio"),
        }
        for item in geometry_changed_entities
    ]

    return {
        "upload_id": upload_id,
        "status": comparison.status,
        "accuracy": comparison.accuracy,
        "matched_count": comparison.matched_count,
        "missing_count": comparison.missing_count,
        "extra_count": comparison.extra_count,
        "changed_count": geometry_payload["summary"]["changed"],
        "matched": comparison.matched,
        "missing": comparison.missing,
        "extra": comparison.extra,
        "categories": comparison.matched,
        "risk_locations": comparison.missing,
        "created_at": comparison.created_at.isoformat(),
    }

