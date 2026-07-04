import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import ezdxf
from sqlalchemy.orm import Session

from app.db.models import DXFEntity

logger = logging.getLogger(__name__)


class DXFParseError(ValueError):
    """Raised when a DXF file cannot be parsed."""


def _safe_point(value: Any) -> Optional[List[float]]:
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return [float(value[0]), float(value[1])]
    return None


def _safe_value(value: Any) -> Optional[Any]:
    if value is None:
        return None
    if isinstance(value, (int, float, str, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [float(v) if isinstance(v, (int, float)) else str(v) for v in value]
    return str(value)


def parse_dxf(file_path: str, db: Session | None = None, upload_id: int | None = None) -> Dict[str, Any]:
    """Parse a DXF file and return structured engineering entities.

    Args:
        file_path: Path to the DXF file on disk.
        db: Optional SQLAlchemy session for persistence of parsed entities.
        upload_id: Optional upload record id to link parsed entities.

    Returns:
        A dictionary containing a summary and categorized entities.

    Raises:
        DXFParseError: If the file is missing, unreadable, or not a valid DXF.
    """
    path = Path(file_path)
    logger.info("Parsing DXF started", extra={"file_path": str(path)})

    if not path.exists():
        raise DXFParseError(f"DXF file not found: {path}")
    if not path.is_file():
        raise DXFParseError(f"DXF path is not a file: {path}")

    try:
        doc = ezdxf.readfile(str(path))
    except FileNotFoundError as exc:
        logger.exception("DXF file missing during parse", extra={"file_path": str(path)})
        raise DXFParseError(f"DXF file not found: {path}") from exc
    except ezdxf.DXFStructureError as exc:
        logger.exception("Invalid DXF structure", extra={"file_path": str(path)})
        raise DXFParseError(f"Invalid DXF file: {path}") from exc
    except Exception as exc:  # pragma: no cover - defensive fallback
        logger.exception("Corrupted DXF file", extra={"file_path": str(path)})
        raise DXFParseError(f"Corrupted or unreadable DXF file: {path}") from exc

    msp = doc.modelspace()

    entities: Dict[str, List[Dict[str, Any]]] = {
        "lines": [],
        "circles": [],
        "arcs": [],
        "texts": [],
        "polylines": [],
        "blocks": [],
    }

    parsed_records: List[Dict[str, Any]] = []

    for entity in msp:
        entity_type = entity.dxftype()
        parsed_entity: Dict[str, Any] = {
            "type": entity_type,
            "layer": getattr(entity.dxf, "layer", None),
        }

        if entity_type == "LINE":
            parsed_entity.update(
                {
                    "start_point": _safe_point(entity.dxf.start),
                    "end_point": _safe_point(entity.dxf.end),
                }
            )
            entities["lines"].append(parsed_entity)
        elif entity_type == "CIRCLE":
            parsed_entity.update(
                {
                    "center": _safe_point(entity.dxf.center),
                    "radius": _safe_value(entity.dxf.radius),
                }
            )
            entities["circles"].append(parsed_entity)
        elif entity_type == "ARC":
            parsed_entity.update(
                {
                    "center": _safe_point(entity.dxf.center),
                    "radius": _safe_value(entity.dxf.radius),
                    "start_angle": _safe_value(entity.dxf.start_angle),
                    "end_angle": _safe_value(entity.dxf.end_angle),
                }
            )
            entities["arcs"].append(parsed_entity)
        elif entity_type in {"LWPOLYLINE", "POLYLINE"}:
            vertices: List[Optional[List[float]]] = []
            if entity_type == "LWPOLYLINE":
                for point in entity.get_points():
                    vertices.append(_safe_point(point))
            else:
                for vertex in entity.vertices:
                    vertices.append(_safe_point(vertex.dxf.location))
            parsed_entity.update(
                {
                    "vertices": vertices,
                    "closed": bool(getattr(entity.dxf, "closed", False)),
                }
            )
            entities["polylines"].append(parsed_entity)
        elif entity_type == "TEXT":
            parsed_entity.update(
                {
                    "value": _safe_value(entity.dxf.text),
                    "insertion_point": _safe_point(entity.dxf.insert),
                    "height": _safe_value(entity.dxf.height),
                }
            )
            entities["texts"].append(parsed_entity)
        elif entity_type == "MTEXT":
            parsed_entity.update(
                {
                    "value": _safe_value(entity.dxf.text),
                    "insertion_point": _safe_point(entity.dxf.insert),
                    "height": _safe_value(getattr(entity.dxf, "char_height", None)),
                }
            )
            entities["texts"].append(parsed_entity)
        elif entity_type == "INSERT":
            parsed_entity.update(
                {
                    "name": _safe_value(entity.dxf.name),
                    "insertion_point": _safe_point(entity.dxf.insert),
                    "scale": _safe_value(entity.dxf.scale),
                    "rotation": _safe_value(entity.dxf.rotation),
                }
            )
            entities["blocks"].append(parsed_entity)
        else:
            continue

        parsed_records.append(parsed_entity)

    summary = {
        "lines": len(entities["lines"]),
        "circles": len(entities["circles"]),
        "arcs": len(entities["arcs"]),
        "texts": len(entities["texts"]),
        "blocks": len(entities["blocks"]),
        "polylines": len(entities["polylines"]),
    }

    result = {"summary": summary, "entities": entities}

    if db is not None and upload_id is not None:
        logger.info("Saving parsed DXF entities to database", extra={"file_path": str(path), "entity_count": len(parsed_records), "upload_id": upload_id})
        try:
            db.query(DXFEntity).filter(DXFEntity.upload_id == upload_id).delete(synchronize_session=False)
            db.add_all(
                [
                    DXFEntity(
                        upload_id=upload_id,
                        entity_type=record["type"],
                        layer=record.get("layer"),
                        data=record,
                    )
                    for record in parsed_records
                ]
            )
            db.commit()
        except Exception as exc:
            logger.exception("Failed to save parsed DXF entities", extra={"upload_id": upload_id})
            db.rollback()
            raise DXFParseError("DXF parsed successfully but failed to save parsed entities.") from exc

    logger.info(
        "Parsing DXF completed",
        extra={
            "file_path": str(path),
            "entity_count": sum(summary.values()),
        },
    )
    return result
