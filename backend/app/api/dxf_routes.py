import logging
from pathlib import Path
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import DXFEntity, Upload
from app.services.dxf_parser import DXFParseError, parse_dxf

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/uploads", tags=["Uploads"])


@router.get("")
def list_uploads(db: Session = Depends(get_db)) -> Dict[str, Any]:
    uploads = db.query(Upload).order_by(Upload.created_at.desc()).all()
    return {
        "count": len(uploads),
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
