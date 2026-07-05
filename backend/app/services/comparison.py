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


def _safe_point(value: Any) -> Optional[List[float]]:
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return [float(value[0]), float(value[1])]
    return None


def _compute_entity_bbox(entity_data: Dict[str, Any]) -> Optional[List[float]]:
    entity_type = str(entity_data.get("type", "")).upper()

    if entity_type == "LINE":
        start = _safe_point(entity_data.get("start_point")) or [0.0, 0.0]
        end = _safe_point(entity_data.get("end_point")) or [0.0, 0.0]
        xs = [start[0], end[0]]
        ys = [start[1], end[1]]
        return [min(xs), min(ys), max(xs), max(ys)]

    if entity_type == "CIRCLE":
        center = _safe_point(entity_data.get("center")) or [0.0, 0.0]
        radius = float(entity_data.get("radius") or 0.0)
        return [center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius]

    if entity_type == "ARC":
        center = _safe_point(entity_data.get("center")) or [0.0, 0.0]
        radius = float(entity_data.get("radius") or 0.0)
        return [center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius]

    if entity_type in {"POLYLINE", "LWPOLYLINE"}:
        vertices = entity_data.get("vertices") or []
        valid = [v for v in vertices if v and isinstance(v, (list, tuple)) and len(v) >= 2]
        if not valid:
            return None
        xs = [float(v[0]) for v in valid]
        ys = [float(v[1]) for v in valid]
        return [min(xs), min(ys), max(xs), max(ys)]

    return None


def _calculate_iou(bbox1: List[float], bbox2: List[float]) -> float:
    x1 = max(bbox1[0], bbox2[0])
    y1 = max(bbox1[1], bbox2[1])
    x2 = min(bbox1[2], bbox2[2])
    y2 = min(bbox1[3], bbox2[3])

    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area1 = (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1])
    area2 = (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1])
    union = area1 + area2 - intersection

    return intersection / union if union > 0 else 0.0


def compare_geometry(pdf_text_blocks: List[Dict[str, Any]], dxf_entities: List[DXFEntity]) -> Dict[str, Any]:
    geometry_entity_types = {"LINE", "CIRCLE", "ARC", "POLYLINE", "LWPOLYLINE"}

    geometry_entities = []
    for entity in dxf_entities:
        if str(entity.entity_type).upper() not in geometry_entity_types:
            continue
        bbox = _compute_entity_bbox(entity.data or {})
        geometry_entities.append(
            {
                "id": entity.id,
                "type": str(entity.entity_type).upper(),
                "layer": entity.layer,
                "bbox": bbox,
            }
        )

    pdf_bboxes = [
        {
            "page": block.get("page"),
            "bbox": block.get("bbox"),
            "text": block.get("text"),
        }
        for block in (pdf_text_blocks or [])
        if block.get("bbox") and len(block.get("bbox")) == 4
    ]

    by_type: Dict[str, List[Dict[str, Any]]] = {}
    for entity in geometry_entities:
        etype = str(entity["type"]).lower() + "s"
        by_type.setdefault(etype, []).append(entity)

    results: Dict[str, Any] = {}
    all_matched: List[Dict[str, Any]] = []
    all_missing: List[Dict[str, Any]] = []
    all_extra: List[Dict[str, Any]] = []
    all_changed: List[Dict[str, Any]] = []

    overlap_threshold = 0.3
    changed_area_threshold = 0.5

    for etype, entities in by_type.items():
        matched: List[Dict[str, Any]] = []
        missing: List[Dict[str, Any]] = []
        extra: List[Dict[str, Any]] = []
        changed: List[Dict[str, Any]] = []
        used_pdf_indices = set()

        for entity in entities:
            entity_bbox = entity.get("bbox")
            if not entity_bbox:
                extra.append(
                    {
                        "category": "geometry",
                        "type": entity["type"],
                        "dxf_id": entity["id"],
                        "layer": entity["layer"],
                        "reason": "no_bbox",
                    }
                )
                continue

            best_match_idx = None
            best_iou = 0.0

            for idx, pdf_block in enumerate(pdf_bboxes):
                if idx in used_pdf_indices:
                    continue
                iou = _calculate_iou(entity_bbox, pdf_block["bbox"])
                if iou > best_iou:
                    best_iou = iou
                    best_match_idx = idx

            if best_match_idx is not None and best_iou > overlap_threshold:
                used_pdf_indices.add(best_match_idx)
                pdf_block = pdf_bboxes[best_match_idx]

                entity_area = (entity_bbox[2] - entity_bbox[0]) * (entity_bbox[3] - entity_bbox[1])
                pdf_area = (pdf_block["bbox"][2] - pdf_block["bbox"][0]) * (pdf_block["bbox"][3] - pdf_block["bbox"][1])

                is_changed = False
                if entity_area > 0 and pdf_area > 0:
                    area_ratio = max(entity_area, pdf_area) / min(entity_area, pdf_area)
                    if area_ratio > (1 + changed_area_threshold):
                        is_changed = True

                entry = {
                    "category": "geometry",
                    "type": entity["type"],
                    "dxf_id": entity["id"],
                    "layer": entity["layer"],
                    "iou": round(best_iou, 3),
                    "page": pdf_block.get("page"),
                }

                if is_changed:
                    entry.update(
                        {
                            "change_type": "geometry_changed",
                            "entity_bbox": [round(v, 2) for v in entity_bbox],
                            "pdf_bbox": [round(v, 2) for v in pdf_block["bbox"]],
                            "area_ratio": round(max(entity_area, pdf_area) / min(entity_area, pdf_area), 2),
                        }
                    )
                    changed.append(entry)
                else:
                    matched.append(entry)
            else:
                extra.append(
                    {
                        "category": "geometry",
                        "type": entity["type"],
                        "dxf_id": entity["id"],
                        "layer": entity["layer"],
                        "reason": "no_overlap",
                    }
                )

        for idx, pdf_block in enumerate(pdf_bboxes):
            if idx not in used_pdf_indices:
                missing.append(
                    {
                        "category": "geometry",
                        "type": "text_bbox",
                        "page": pdf_block.get("page"),
                        "pdf_text": pdf_block.get("text"),
                        "bbox": [round(v, 2) for v in pdf_block["bbox"]],
                        "reason": "no_dxf_overlap",
                    }
                )

        type_total = len(matched) + len(missing) + len(extra) + len(changed)
        type_accuracy = round((len(matched) / type_total) * 100, 2) if type_total > 0 else 100.0

        results[etype] = {
            "accuracy": type_accuracy,
            "matched_count": len(matched),
            "missing_count": len(missing),
            "extra_count": len(extra),
            "changed_count": len(changed),
            "total": type_total,
            "matched": matched,
            "missing": missing,
            "extra": extra,
            "changed": changed,
        }

        all_matched.extend(matched)
        all_missing.extend(missing)
        all_extra.extend(extra)
        all_changed.extend(changed)

    overall_total = len(all_matched) + len(all_missing) + len(all_extra) + len(all_changed)
    overall_accuracy = round((len(all_matched) / overall_total) * 100, 2) if overall_total > 0 else 100.0

    return {
        "accuracy": overall_accuracy,
        "entity_types": results,
        "summary": {
            "matched": len(all_matched),
            "missing": len(all_missing),
            "extra": len(all_extra),
            "changed": len(all_changed),
        },
    }


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

    geometry = compare_geometry(
        pdf_parse.text_blocks or [],
        dxf_entities,
    )

    overall_matched_count = matched_count + geometry["summary"]["matched"]
    overall_missing_count = missing_count + geometry["summary"]["missing"]
    overall_extra_count = extra_count + geometry["summary"]["extra"]
    overall_changed_count = geometry["summary"]["changed"]

    geometry_changed_entities: List[Dict[str, Any]] = []
    for etype_data in geometry["entity_types"].values():
        geometry_changed_entities.extend(etype_data.get("changed", []))

    combined_changed = [
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

    combined_matched = (
        [{"category": "text", **item} for item in matched]
        + [
            {"category": "geometry", **item}
            for etype_data in geometry["entity_types"].values()
            for item in etype_data.get("matched", [])
        ]
    )
    combined_missing = (
        [{"category": "text", **item} for item in missing]
        + [
            {"category": "geometry", **item}
            for etype_data in geometry["entity_types"].values()
            for item in etype_data.get("missing", [])
        ]
    )
    combined_extra = (
        [{"category": "text", **item} for item in extra]
        + [
            {"category": "geometry", **item}
            for etype_data in geometry["entity_types"].values()
            for item in etype_data.get("extra", [])
        ]
    )

    overall_total = overall_matched_count + overall_missing_count + overall_extra_count + overall_changed_count
    overall_accuracy = round((overall_matched_count / overall_total) * 100, 2) if overall_total > 0 else 100.0

    comparison_payload = {
        "upload_id": upload_id,
        "status": "completed",
        "accuracy": overall_accuracy,
        "matched_count": overall_matched_count,
        "missing_count": overall_missing_count,
        "extra_count": overall_extra_count,
        "changed_count": overall_changed_count,
        "matched": combined_matched,
        "missing": combined_missing,
        "extra": combined_extra,
        "changed": combined_changed,
        "geometry": geometry,
    }

    try:
        db.query(ComparisonResult).filter(ComparisonResult.upload_id == upload_id).delete(synchronize_session=False)
        db.add(
            ComparisonResult(
                upload_id=upload_id,
                status="completed",
                accuracy=overall_accuracy,
                matched_count=overall_matched_count,
                missing_count=overall_missing_count,
                extra_count=overall_extra_count,
                matched=combined_matched,
                missing=combined_missing,
                extra=combined_extra,
            )
        )
        db.commit()
    except Exception as exc:
        logger.exception("Failed to save comparison result", extra={"upload_id": upload_id})
        db.rollback()
        raise ComparisonError("Comparison completed, but failed to save the result.") from exc

    return comparison_payload
