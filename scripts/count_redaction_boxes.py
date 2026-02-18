"""
Redaction box detection and counting for scanned PDFs.
Uses connected components analysis on thresholded images to identify
solid black rectangles (redaction boxes) in scanned documents.
"""
import cv2
import numpy as np
import fitz  # PyMuPDF
import os
import sys


def _compute_rectangularity(labels, label_id, stats):
    """Compute how rectangular a connected component is using minAreaRect."""
    mask = (labels == label_id).astype(np.uint8)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return 0.0
    contour = max(contours, key=cv2.contourArea)
    if len(contour) < 5:
        return 0.0
    rect = cv2.minAreaRect(contour)
    rect_area = rect[1][0] * rect[1][1]
    if rect_area == 0:
        return 0.0
    comp_area = stats[label_id, cv2.CC_STAT_AREA]
    return comp_area / rect_area


def _is_text_neighbor(candidate, all_components, stats):
    """
    Check if a small candidate is part of a text line.
    A component surrounded by many similarly-sized dark components
    at the same vertical position is likely a text character.
    """
    cy = candidate["y"] + candidate["h"] // 2
    cx = candidate["x"] + candidate["w"] // 2
    y_tolerance = max(candidate["h"], 20)  # same line = similar y

    neighbors = 0
    for i in range(1, len(stats)):
        sx = stats[i, cv2.CC_STAT_LEFT]
        sy = stats[i, cv2.CC_STAT_TOP]
        sw = stats[i, cv2.CC_STAT_WIDTH]
        sh = stats[i, cv2.CC_STAT_HEIGHT]
        sa = stats[i, cv2.CC_STAT_AREA]
        scy = sy + sh // 2

        if sa < 30:  # skip tiny noise
            continue
        # Same horizontal band?
        if abs(scy - cy) > y_tolerance:
            continue
        # Not counting itself (by position)
        if sx == candidate["x"] and sy == candidate["y"]:
            continue
        # Nearby horizontally (within ~300px = ~1 inch at 300dpi)
        scx = sx + sw // 2
        if abs(scx - cx) < 300:
            neighbors += 1

    return neighbors >= 4  # 4+ nearby dark items = likely text line


def count_redaction_boxes(pdf_path, dpi=300, debug_dir=None,
                          dark_thresh=70, min_fill=0.78, min_area=150,
                          min_minor=5, min_major=15):
    """
    Count solid black redaction boxes in a scanned PDF.

    Uses connected components on a binary threshold image.
    Redaction boxes are distinguished from text by:
    1. High fill ratio (solid rectangle vs complex character shapes)
    2. Rectangularity check via minAreaRect
    3. Text-line context check (characters cluster on same baseline)

    Returns:
        (total_count, per_page_counts, per_page_details)
    """
    doc = fitz.open(pdf_path)
    total = 0
    page_counts = []
    page_details = []

    for page_num in range(len(doc)):
        page = doc[page_num]
        mat = fitz.Matrix(dpi / 72, dpi / 72)
        pix = page.get_pixmap(matrix=mat)
        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.h, pix.w, pix.n
        )

        if pix.n == 4:
            img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGBA2BGR)
        elif pix.n == 3:
            img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        else:
            img_bgr = cv2.cvtColor(img_array, cv2.COLOR_GRAY2BGR)

        gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)

        # Binary threshold: pixels darker than dark_thresh become white (foreground)
        _, binary = cv2.threshold(gray, dark_thresh, 255, cv2.THRESH_BINARY_INV)

        # Minimal opening to remove 1-2 pixel noise specks
        # Do NOT use closing - that would merge adjacent boxes
        kernel_open = np.ones((2, 2), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel_open)

        # Connected components analysis
        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(binary)

        # First pass: basic size/fill filter
        candidates = []
        rejected = []

        for i in range(1, num_labels):  # skip background label 0
            x = stats[i, cv2.CC_STAT_LEFT]
            y = stats[i, cv2.CC_STAT_TOP]
            w = stats[i, cv2.CC_STAT_WIDTH]
            h = stats[i, cv2.CC_STAT_HEIGHT]
            area = stats[i, cv2.CC_STAT_AREA]
            bbox_area = w * h
            fill = area / bbox_area if bbox_area > 0 else 0

            reason = None

            if area < min_area:
                reason = f"area={area}<{min_area}"
            elif min(w, h) < min_minor:
                reason = f"minor={min(w, h)}<{min_minor}"
            elif max(w, h) < min_major:
                reason = f"major={max(w, h)}<{min_major}"
            elif fill < min_fill:
                reason = f"fill={fill:.3f}<{min_fill}"
            # Very thin long lines are borders/rules, not redaction boxes
            elif min(w, h) <= 3 and max(w, h) > 80:
                reason = f"thin_line={w}x{h}"

            if reason:
                rejected.append({
                    "x": x, "y": y, "w": w, "h": h,
                    "area": area, "fill": fill, "reason": reason,
                    "label": i,
                })
            else:
                candidates.append({
                    "x": x, "y": y, "w": w, "h": h,
                    "area": area, "fill": fill,
                    "label": i,
                })

        # Second pass: rectangularity + text-line check on candidates
        boxes = []
        for c in candidates:
            reason = None

            # Rectangularity check: how close to a perfect rectangle?
            rect_score = _compute_rectangularity(labels, c["label"], stats)
            c["rect"] = rect_score

            if rect_score < 0.82:
                reason = f"rect={rect_score:.3f}<0.82"
            # For small components, also check if they're in a text line
            elif c["area"] < 800 and min(c["w"], c["h"]) < 25:
                if _is_text_neighbor(c, None, stats):
                    reason = f"text_context(area={c['area']},min={min(c['w'],c['h'])})"

            if reason:
                rejected.append({
                    "x": c["x"], "y": c["y"], "w": c["w"], "h": c["h"],
                    "area": c["area"], "fill": c["fill"], "reason": reason,
                    "label": c["label"],
                })
            else:
                boxes.append(c)

        count = len(boxes)
        total += count
        page_counts.append(count)
        page_details.append({"boxes": boxes, "rejected": rejected})

        if debug_dir:
            os.makedirs(debug_dir, exist_ok=True)
            debug_img = img_bgr.copy()

            # Draw accepted boxes in green with numbers
            for j, b in enumerate(boxes):
                cv2.rectangle(
                    debug_img,
                    (b["x"], b["y"]),
                    (b["x"] + b["w"], b["y"] + b["h"]),
                    (0, 255, 0), 2,
                )
                label = f'{j + 1}'
                cv2.putText(
                    debug_img, label,
                    (b["x"], b["y"] - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 200, 0), 1,
                )

            # Draw rejected candidates in red (only significant ones)
            for r in rejected:
                if r["area"] > 50:
                    cv2.rectangle(
                        debug_img,
                        (r["x"], r["y"]),
                        (r["x"] + r["w"], r["y"] + r["h"]),
                        (0, 0, 255), 1,
                    )

            stem = os.path.splitext(os.path.basename(pdf_path))[0]
            # Shorten the name for readability
            if "Easy" in pdf_path or "Deidentification_0" in stem:
                tag = "easy"
            elif "Medium" in pdf_path or "Medium" in stem:
                tag = "medium"
            elif "Hard" in pdf_path or "Hard" in stem:
                tag = "hard"
            else:
                tag = stem[:20]

            out_path = os.path.join(debug_dir, f"{tag}_p{page_num + 1}.png")
            cv2.imwrite(out_path, debug_img)

    doc.close()
    return total, page_counts, page_details


def main():
    pdf_dir = os.path.join(os.path.dirname(__file__), "..", "all_phi")
    debug_dir = os.path.join(pdf_dir, "debug2")

    expected = {
        "PDF_Deid_Deidentification_0.pdf": ("Easy", 42),
        "PDF_Deid_Deidentification_Medium_0.pdf": ("Medium", 47),
        "PDF_Deid_Deidentification_Hard_0.pdf": ("Hard", 43),
    }

    for filename, (label, exp_count) in expected.items():
        path = os.path.join(pdf_dir, filename)
        if not os.path.exists(path):
            print(f"[SKIP] {label}: {filename} not found")
            continue

        total, per_page, details = count_redaction_boxes(
            path, debug_dir=debug_dir
        )

        diff = total - exp_count
        sign = "+" if diff > 0 else ""
        print(f"\n{'='*60}")
        print(f"{label}: {total}/{exp_count} (diff: {sign}{diff})")
        print(f"{'='*60}")

        for pnum, (pcount, pdetail) in enumerate(zip(per_page, details)):
            print(f"  Page {pnum + 1}: {pcount} boxes")
            # Show size distribution
            if pdetail["boxes"]:
                widths = [b["w"] for b in pdetail["boxes"]]
                heights = [b["h"] for b in pdetail["boxes"]]
                fills = [b["fill"] for b in pdetail["boxes"]]
                rects = [b.get("rect", 0) for b in pdetail["boxes"]]
                print(f"    Width range:  {min(widths)}-{max(widths)}")
                print(f"    Height range: {min(heights)}-{max(heights)}")
                print(f"    Fill range:   {min(fills):.3f}-{max(fills):.3f}")
                print(f"    Rect range:   {min(rects):.3f}-{max(rects):.3f}")
                # Show smallest boxes for inspection
                small = sorted(pdetail["boxes"], key=lambda b: b["area"])[:3]
                for s in small:
                    print(f"    Smallest: {s['w']}x{s['h']} area={s['area']} "
                          f"fill={s['fill']:.3f} rect={s.get('rect',0):.3f}")

            # Show significant rejected candidates
            sig_rejected = [r for r in pdetail["rejected"] if r["area"] > 200]
            if sig_rejected:
                print(f"    Rejected (area>200): {len(sig_rejected)}")
                for r in sig_rejected[:5]:
                    print(f"      {r['w']}x{r['h']} area={r['area']} "
                          f"fill={r['fill']:.3f} reason={r['reason']}")

    print(f"\nDebug images saved to: {debug_dir}")


if __name__ == "__main__":
    main()
