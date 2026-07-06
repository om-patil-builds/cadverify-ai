import logging
import re
import math
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.db.models import ComparisonResult, DXFEntity, PDFParse, Upload

logger = logging.getLogger(__name__)


class ComparisonError(ValueError):
    """Raised when a comparison cannot be completed."""


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    cleaned = re.sub(r"[^\w\s\.\-±Ø°%/]", " ", text, flags=re.UNICODE)
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

    if entity_type in {"CIRCLE", "ARC"}:
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

    if entity_type in {"TEXT", "MTEXT"}:
        insert = _safe_point(entity_data.get("insertion_point")) or [0.0, 0.0]
        height = float(entity_data.get("height") or 10.0)
        length = len(str(entity_data.get("value") or "")) * height * 0.6
        return [insert[0], insert[1] - height, insert[0] + length, insert[1] + height]

    return None


def _calculate_iou(bbox1: List[float], bbox2: List[float]) -> float:
    x1 = max(bbox1[0], bbox2[0])
    y1 = max(bbox1[1], bbox2[1])
    x2 = min(bbox1[2], bbox2[2])
    y2 = min(bbox1[3], bbox2[3])

    intersection = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    area1 = max(1e-5, (bbox1[2] - bbox1[0]) * (bbox1[3] - bbox1[1]))
    area2 = max(1e-5, (bbox2[2] - bbox2[0]) * (bbox2[3] - bbox2[1]))
    union = area1 + area2 - intersection

    return intersection / union if union > 0 else 0.0


def calculate_registration(
    dxf_texts: List[Dict[str, Any]], pdf_blocks: List[Dict[str, Any]]
) -> Tuple[float, float, float, float]:
    """Calculates scaling and translation mapping DXF to PDF coordinates using unique text matches."""
    dxf_counts = {}
    for t in dxf_texts:
        txt = t["normalized_text"]
        if len(txt) >= 2:
            dxf_counts[txt] = dxf_counts.get(txt, 0) + 1

    pdf_counts = {}
    for b in pdf_blocks:
        txt = b["normalized_text"]
        if len(txt) >= 2:
            pdf_counts[txt] = pdf_counts.get(txt, 0) + 1

    unique_matches = []
    for txt, count in dxf_counts.items():
        if count == 1 and pdf_counts.get(txt) == 1:
            unique_matches.append(txt)

    pairs = []
    for txt in unique_matches:
        d_item = next(t for t in dxf_texts if t["normalized_text"] == txt)
        p_item = next(b for b in pdf_blocks if b["normalized_text"] == txt)
        if d_item["insertion_point"] and p_item["bbox"]:
            dp = d_item["insertion_point"]
            pb = p_item["bbox"]
            pc = [(pb[0] + pb[2]) / 2.0, (pb[1] + pb[3]) / 2.0]
            pairs.append((dp[0], dp[1], pc[0], pc[1]))

    n = len(pairs)
    logger.info("Coordinate registration matches found", extra={"match_count": n})

    if n >= 2:
        try:
            import numpy as np
            x_d = np.array([p[0] for p in pairs])
            y_d = np.array([p[1] for p in pairs])
            x_p = np.array([p[2] for p in pairs])
            y_p = np.array([p[3] for p in pairs])

            var_xd = np.var(x_d)
            var_yd = np.var(y_d)

            s_x = float(np.cov(x_d, x_p)[0, 1] / var_xd) if var_xd > 1e-5 else 1.0
            t_x = float(np.mean(x_p) - s_x * np.mean(x_d))

            s_y = float(np.cov(y_d, y_p)[0, 1] / var_yd) if var_yd > 1e-5 else -1.0
            t_y = float(np.mean(y_p) - s_y * np.mean(y_d))

            return s_x, t_x, s_y, t_y
        except Exception as exc:
            logger.warning("Fitted alignment registration failed. Defaulting to bounding box mapping.", exc_info=exc)

    # Fallback Bounding Box mapping
    valid_dxf = [t["insertion_point"] for t in dxf_texts if t["insertion_point"]]
    valid_pdf = [b["bbox"] for b in pdf_blocks if b["bbox"]]

    if valid_dxf and valid_pdf:
        dxs = [p[0] for p in valid_dxf]
        dys = [p[1] for p in valid_dxf]
        pxs = [b[0] for b in valid_pdf] + [b[2] for b in valid_pdf]
        pys = [b[1] for b in valid_pdf] + [b[3] for b in valid_pdf]

        d_w = max(dxs) - min(dxs)
        d_h = max(dys) - min(dys)
        p_w = max(pxs) - min(pxs)
        p_h = max(pys) - min(pys)

        s_x = p_w / d_w if d_w > 0 else 1.0
        t_x = min(pxs) - s_x * min(dxs)
        s_y = -(p_h / d_h) if d_h > 0 else -1.0
        t_y = max(pys) - s_y * min(dys)
        return s_x, t_x, s_y, t_y

    return 1.0, 0.0, -1.0, 800.0


def transform_bbox(bbox: List[float], s_x: float, t_x: float, s_y: float, t_y: float) -> List[float]:
    x1, y1, x2, y2 = bbox
    tx1, ty1 = s_x * x1 + t_x, s_y * y1 + t_y
    tx2, ty2 = s_x * x2 + t_x, s_y * y2 + t_y
    return [min(tx1, tx2), min(ty1, ty2), max(tx1, tx2), max(ty1, ty2)]


def _classify_category(text: str, bbox: Optional[List[float]], p_w: float, p_h: float, layer: Optional[str] = None) -> str:
    txt_lower = text.lower()
    layer_lower = (layer or "").lower()

    # Title Block Check (bottom right or contains keywords)
    is_title_keyword = any(k in txt_lower for k in ["part no", "dwg no", "revision", "material", "scale", "date", "approved", "drawn by", "sheet"])
    is_bottom_right = False
    if bbox:
        centroid_x = (bbox[0] + bbox[2]) / 2.0
        centroid_y = (bbox[1] + bbox[3]) / 2.0
        if centroid_x > p_w * 0.55 and centroid_y > p_h * 0.55:
            is_bottom_right = True

    if is_title_keyword or is_bottom_right or "title" in layer_lower or "border" in layer_lower:
        return "title_block"

    # Dimension Check
    is_dim_val = bool(re.search(r"\b\d+(\.\d+)?\b", txt_lower))
    is_dim_sym = any(s in txt_lower for s in ["±", "ø", "%%c", "dia", "rad", "r ", "°", "deg"])
    if is_dim_sym or (is_dim_val and ("dim" in layer_lower or "dimension" in layer_lower)):
        return "dimensions"

    # Annotations Check
    return "annotations"


def compare_geometry(pdf_text_blocks: List[Dict[str, Any]], dxf_entities: List[DXFEntity]) -> Dict[str, Any]:
    # Placeholder for backwards compatibility
    return {
        "accuracy": 100.0,
        "entity_types": {},
        "summary": {"matched": 0, "missing": 0, "extra": 0, "changed": 0}
    }


def compare_upload_data(upload_id: int, db: Session) -> Dict[str, Any]:
    upload = db.query(Upload).filter(Upload.id == upload_id).first()
    if not upload:
        raise ComparisonError(f"Upload with id {upload_id} was not found")

    pdf_parse = db.query(PDFParse).filter(PDFParse.upload_id == upload_id).order_by(PDFParse.id.desc()).first()
    if not pdf_parse:
        raise ComparisonError("No parsed PDF information found for this upload")

    dxf_entities = db.query(DXFEntity).filter(DXFEntity.upload_id == upload_id).order_by(DXFEntity.id).all()

    # 1. Collect elements
    pdf_blocks = [
        {
            "page": block.get("page", 1),
            "text": block.get("text", ""),
            "bbox": block.get("bbox"),
            "normalized_text": _normalize_text(block.get("text")),
            "confidence": block.get("confidence", 100.0)
        }
        for block in pdf_parse.text_blocks or []
    ]

    dxf_texts = []
    dxf_geometry = []
    for entity in dxf_entities:
        etype = entity.entity_type.upper()
        if etype in {"TEXT", "MTEXT"}:
            bbox = _compute_entity_bbox(entity.data or {})
            dxf_texts.append({
                "id": entity.id,
                "type": etype,
                "layer": entity.layer,
                "value": entity.data.get("value", ""),
                "insertion_point": entity.data.get("insertion_point"),
                "bbox": bbox,
                "normalized_text": _normalize_text(entity.data.get("value")),
            })
        elif etype in {"LINE", "CIRCLE", "ARC", "POLYLINE", "LWPOLYLINE"}:
            bbox = _compute_entity_bbox(entity.data or {})
            if bbox:
                dxf_geometry.append({
                    "id": entity.id,
                    "type": etype,
                    "layer": entity.layer,
                    "bbox": bbox,
                })

    # 2. Coordinate registration
    s_x, t_x, s_y, t_y = calculate_registration(dxf_texts, pdf_blocks)
    logger.info("Alignment matrix calculated", extra={"s_x": s_x, "t_x": t_x, "s_y": s_y, "t_y": t_y})

    # Transform DXF geometry and texts
    for item in dxf_texts:
        if item["bbox"]:
            item["bbox"] = transform_bbox(item["bbox"], s_x, t_x, s_y, t_y)
    for item in dxf_geometry:
        item["bbox"] = transform_bbox(item["bbox"], s_x, t_x, s_y, t_y)

    # 3. Classify Page dimensions (from max bounding box)
    valid_pdf_boxes = [b["bbox"] for b in pdf_blocks if b["bbox"]]
    p_w = max(b[2] for b in valid_pdf_boxes) if valid_pdf_boxes else 800.0
    p_h = max(b[3] for b in valid_pdf_boxes) if valid_pdf_boxes else 600.0

    # 4. Compare text-based layers (Dimensions, Annotations, Title Block)
    unmatched_dxf_texts = dxf_texts.copy()
    matched_texts = []
    missing_texts = []

    for pdf_block in pdf_blocks:
        norm = pdf_block["normalized_text"]
        if not norm:
            continue

        best_idx = None
        best_dist = float("inf")
        # Match spatially and textually
        for idx, d_text in enumerate(unmatched_dxf_texts):
            if d_text["normalized_text"] == norm:
                # Spatial distance check to ensure exact match is nearby
                if pdf_block["bbox"] and d_text["bbox"]:
                    pd_center = [(pdf_block["bbox"][0] + pdf_block["bbox"][2]) / 2.0, (pdf_block["bbox"][1] + pdf_block["bbox"][3]) / 2.0]
                    dx_center = [(d_text["bbox"][0] + d_text["bbox"][2]) / 2.0, (d_text["bbox"][1] + d_text["bbox"][3]) / 2.0]
                    dist = math.hypot(pd_center[0] - dx_center[0], pd_center[1] - dx_center[1])
                    if dist < best_dist:
                        best_dist = dist
                        best_idx = idx

        if best_idx is not None:
            matched_dxf = unmatched_dxf_texts.pop(best_idx)
            matched_texts.append((pdf_block, matched_dxf))
        else:
            missing_texts.append(pdf_block)

    extra_texts = unmatched_dxf_texts

    # 5. Geometry comparison (spatial mapping)
    # Since scanned drawings have no vector elements, we match DXF geometry entities with overlapping OCR/PDF boxes
    # or identify them as extra. (In a real system, pixel alignment check is done).
    unmatched_dxf_geometry = dxf_geometry.copy()
    matched_geometry = []
    extra_geometry = []

    for geom in dxf_geometry:
        best_iou = 0.0
        best_block = None
        for block in pdf_blocks:
            if block["bbox"]:
                iou = _calculate_iou(geom["bbox"], block["bbox"])
                if iou > best_iou:
                    best_iou = iou
                    best_block = block

        if best_block and best_iou > 0.1:
            matched_geometry.append((geom, best_block, best_iou))
            if geom in unmatched_dxf_geometry:
                unmatched_dxf_geometry.remove(geom)
        else:
            extra_geometry.append(geom)

    # 6. Group into the 5 reviewer categories
    results = {
        "geometry": {"matched": [], "missing": [], "extra": [], "changed": [], "accuracy": 100.0},
        "dimensions": {"matched": [], "missing": [], "extra": [], "changed": [], "accuracy": 100.0},
        "annotations": {"matched": [], "missing": [], "extra": [], "changed": [], "accuracy": 100.0},
        "title_block": {"matched": [], "missing": [], "extra": [], "changed": [], "accuracy": 100.0},
    }

    risk_locations = []

    # Map matched text
    for p_block, d_text in matched_texts:
        cat = _classify_category(p_block["text"], p_block["bbox"], p_w, p_h, d_text["layer"])
        results[cat]["matched"].append({
            "dxf_id": d_text["id"],
            "layer": d_text["layer"],
            "dxf_value": d_text["value"],
            "pdf_value": p_block["text"],
            "bbox": p_block["bbox"],
            "confidence": p_block["confidence"],
        })

    # Map missing text
    for p_block in missing_texts:
        cat = _classify_category(p_block["text"], p_block["bbox"], p_w, p_h)
        item = {
            "pdf_value": p_block["text"],
            "bbox": p_block["bbox"],
            "reason": "missing_in_dxf",
        }
        results[cat]["missing"].append(item)

        # Create Risk Location
        risk_locations.append({
            "category": cat,
            "severity": "high" if cat == "title_block" else "medium",
            "confidence": int(p_block.get("confidence", 90)),
            "description": f"Missing element in DXF: '{p_block['text']}'",
            "bbox": p_block["bbox"],
            "page": p_block["page"],
        })

    # Map extra text
    for d_text in extra_texts:
        cat = _classify_category(d_text["value"], d_text["bbox"], p_w, p_h, d_text["layer"])
        item = {
            "dxf_id": d_text["id"],
            "dxf_value": d_text["value"],
            "layer": d_text["layer"],
            "bbox": d_text["bbox"],
            "reason": "extra_in_dxf",
        }
        results[cat]["extra"].append(item)

        # Create Risk Location
        risk_locations.append({
            "category": cat,
            "severity": "medium",
            "confidence": 95,
            "description": f"Extra element in DXF: '{d_text['value']}'",
            "bbox": d_text["bbox"],
            "page": 1,
        })

    # Map geometry
    for geom, block, iou in matched_geometry:
        results["geometry"]["matched"].append({
            "dxf_id": geom["id"],
            "type": geom["type"],
            "layer": geom["layer"],
            "bbox": geom["bbox"],
            "iou": iou,
        })

    for geom in extra_geometry:
        results["geometry"]["extra"].append({
            "dxf_id": geom["id"],
            "type": geom["type"],
            "layer": geom["layer"],
            "bbox": geom["bbox"],
            "reason": "geometry_extra",
        })
        risk_locations.append({
            "category": "geometry",
            "severity": "high",
            "confidence": 95,
            "description": f"Extra geometry entity ({geom['type']}) found on layer '{geom['layer']}'",
            "bbox": geom["bbox"],
            "page": 1,
        })

    for geom in unmatched_dxf_geometry:
        # Avoid duplicate risk entries
        pass

    # 7. Compute Accuracies per category
    for cat, data in results.items():
        m_c = len(data["matched"])
        mis_c = len(data["missing"])
        ex_c = len(data["extra"])
        tot = m_c + mis_c + ex_c
        data["accuracy"] = round((m_c / tot) * 100, 2) if tot > 0 else 100.0
        data["matched_count"] = m_c
        data["missing_count"] = mis_c
        data["extra_count"] = ex_c
        data["changed_count"] = 0

    # Overall calculation
    tot_matched = sum(results[c]["matched_count"] for c in results)
    tot_missing = sum(results[c]["missing_count"] for c in results)
    tot_extra = sum(results[c]["extra_count"] for c in results)
    overall_tot = tot_matched + tot_missing + tot_extra
    overall_accuracy = round((tot_matched / overall_tot) * 100, 2) if overall_tot > 0 else 100.0

    comparison_payload = {
        "upload_id": upload_id,
        "status": "completed",
        "accuracy": overall_accuracy,
        "matched_count": tot_matched,
        "missing_count": tot_missing,
        "extra_count": tot_extra,
        "changed_count": 0,
        "matched": matched_texts, # preserved shape
        "missing": missing_texts, # preserved shape
        "extra": extra_texts, # preserved shape
        "changed": [],
        "categories": results,
        "risk_locations": risk_locations,
    }

    # Save to Database
    try:
        db.query(ComparisonResult).filter(ComparisonResult.upload_id == upload_id).delete(synchronize_session=False)
        db.add(
            ComparisonResult(
                upload_id=upload_id,
                status="completed",
                accuracy=overall_accuracy,
                matched_count=tot_matched,
                missing_count=tot_missing,
                extra_count=tot_extra,
                matched=results,  # saving categorized JSON representation
                missing=risk_locations,  # saving risk location JSON
                extra={},
            )
        )
        db.commit()
    except Exception as exc:
        logger.exception("Failed to save comparison result to database", extra={"upload_id": upload_id})
        db.rollback()
        raise ComparisonError("Comparison completed but database persistence failed.") from exc

    return comparison_payload
