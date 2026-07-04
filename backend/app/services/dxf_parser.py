import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import ezdxf

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


def parse_dxf(file_path: str) -> Dict[str, Any]:
    """Parse a DXF file and return structured engineering entities.

    Args:
        file_path: Path to the DXF file on disk.

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

    for entity in msp:
        entity_type = entity.dxftype()

        if entity_type == "LINE":
            entities["lines"].append(
                {
                    "type": "LINE",
                    "layer": entity.dxf.layer,
                    "start_point": _safe_point(entity.dxf.start),
                    "end_point": _safe_point(entity.dxf.end),
                }
            )
        elif entity_type == "CIRCLE":
            entities["circles"].append(
                {
                    "type": "CIRCLE",
                    "layer": entity.dxf.layer,
                    "center": _safe_point(entity.dxf.center),
                    "radius": _safe_value(entity.dxf.radius),
                }
            )
        elif entity_type == "ARC":
            entities["arcs"].append(
                {
                    "type": "ARC",
                    "layer": entity.dxf.layer,
                    "center": _safe_point(entity.dxf.center),
                    "radius": _safe_value(entity.dxf.radius),
                    "start_angle": _safe_value(entity.dxf.start_angle),
                    "end_angle": _safe_value(entity.dxf.end_angle),
                }
            )
        elif entity_type in {"LWPOLYLINE", "POLYLINE"}:
            vertices = []
            if entity_type == "LWPOLYLINE":
                for point in entity.get_points():
                    vertices.append(_safe_point(point))
            else:
                for vertex in entity.vertices:
                    vertices.append(_safe_point(vertex.dxf.location))

            entities["polylines"].append(
                {
                    "type": entity_type,
                    "layer": entity.dxf.layer,
                    "vertices": vertices,
                    "closed": bool(getattr(entity.dxf, "closed", False)),
                }
            )
        elif entity_type == "SPLINE":
            control_points = []
            for point in entity.control_points:
                control_points.append(_safe_point(point))
            entities["polylines"].append(
                {
                    "type": "SPLINE",
                    "layer": entity.dxf.layer,
                    "control_points": control_points,
                    "degree": _safe_value(entity.dxf.degree),
                }
            )
        elif entity_type == "TEXT":
            entities["texts"].append(
                {
                    "type": "TEXT",
                    "layer": entity.dxf.layer,
                    "value": _safe_value(entity.dxf.text),
                    "insertion_point": _safe_point(entity.dxf.insert),
                    "height": _safe_value(entity.dxf.height),
                }
            )
        elif entity_type == "MTEXT":
            entities["texts"].append(
                {
                    "type": "MTEXT",
                    "layer": entity.dxf.layer,
                    "value": _safe_value(entity.dxf.text),
                    "insertion_point": _safe_point(entity.dxf.insert),
                    "height": _safe_value(getattr(entity.dxf, "char_height", None)),
                }
            )
        elif entity_type == "INSERT":
            entities["blocks"].append(
                {
                    "type": "INSERT",
                    "layer": entity.dxf.layer,
                    "name": _safe_value(entity.dxf.name),
                    "insertion_point": _safe_point(entity.dxf.insert),
                    "scale": _safe_value(entity.dxf.scale),
                    "rotation": _safe_value(entity.dxf.rotation),
                }
            )

    summary = {
        "lines": len(entities["lines"]),
        "circles": len(entities["circles"]),
        "arcs": len(entities["arcs"]),
        "texts": len(entities["texts"]),
        "blocks": len(entities["blocks"]),
    }

    result = {"summary": summary, "entities": entities}
    logger.info(
        "Parsing DXF completed",
        extra={
            "file_path": str(path),
            "entity_count": sum(summary.values()),
        },
    )
    return result
