"""Extract design DNA from a Resume.io PDF for template tuning."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import fitz


def _rgb_to_hex(color: object) -> str | None:
    """Convert PyMuPDF span color to hex. Color may be int (sRGB) or float tuple."""
    if color is None:
        return None
    if isinstance(color, int):
        # Packed sRGB integer from PyMuPDF
        r = (color >> 16) & 0xFF
        g = (color >> 8) & 0xFF
        b = color & 0xFF
        return f"#{r:02x}{g:02x}{b:02x}"
    if isinstance(color, (tuple, list)):
        if len(color) < 3:
            return None
        if all(isinstance(c, float) for c in color[:3]):
            r, g, b = (int(max(0.0, min(1.0, c)) * 255) for c in color[:3])
        else:
            r, g, b = (int(c) & 0xFF for c in color[:3])
        return f"#{r:02x}{g:02x}{b:02x}"
    return None


def _luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return 128.0
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return 0.299 * r + 0.587 * g + 0.114 * b


def analyze_pdf(pdf_path: Path) -> dict:
    doc = fitz.open(pdf_path)
    page = doc[0]
    rect = page.rect
    font_counter: Counter[str] = Counter()
    size_counter: Counter[float] = Counter()
    color_counter: Counter[str] = Counter()
    blocks_meta: list[dict] = []

    text_dict = page.get_text("dict")
    for block in text_dict.get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                text = span.get("text", "").strip()
                if not text:
                    continue
                font = span.get("font", "unknown")
                size = round(span.get("size", 0), 1)
                color = _rgb_to_hex(span.get("color"))
                font_counter[font] += 1
                size_counter[size] += 1
                if color:
                    color_counter[color] += 1
                bbox = span.get("bbox", [0, 0, 0, 0])
                blocks_meta.append({
                    "text": text[:80], "font": font, "size": size, "color": color,
                    "x0": round(bbox[0], 1), "y0": round(bbox[1], 1),
                    "x1": round(bbox[2], 1), "y1": round(bbox[3], 1),
                })

    blocks_meta.sort(key=lambda b: (b["y0"], b["x0"]))
    page_width = rect.width
    page_height = rect.height
    left_blocks = [b for b in blocks_meta if b["x0"] < page_width * 0.35]
    right_blocks = [b for b in blocks_meta if b["x0"] >= page_width * 0.35]

    dark_hex = {h for h in color_counter if h and _luminance(h) < 45}
    has_header_bar = any(
        b.get("color") in dark_hex
        and b["y0"] < page_height * 0.22
        and (b["x1"] - b["x0"]) > page_width * 0.55
        for b in blocks_meta
    )

    if not has_header_bar:
        for draw in page.get_drawings():
            fill = draw.get("fill")
            rect = draw.get("rect")
            if not rect or not fill or len(fill) < 3:
                continue
            if max(fill[:3]) > 0.05:
                continue
            width = rect.x1 - rect.x0
            height = rect.y1 - rect.y0
            if width > page_width * 0.7 and height > 15 and rect.y0 < page_height * 0.25:
                has_header_bar = True
                break

    if has_header_bar:
        layout_hint = "anshual-frontend"
    elif left_blocks and right_blocks and len(left_blocks) > 3:
        layout_hint = "sidebar-left"
    else:
        layout_hint = "single-column"

    spec = {
        "source_pdf": str(pdf_path),
        "page": {"width_pt": round(rect.width, 1), "height_pt": round(rect.height, 1)},
        "layout_hint": layout_hint,
        "fonts": [{"name": f, "count": c} for f, c in font_counter.most_common(10)],
        "font_sizes_pt": [{"size": s, "count": c} for s, c in size_counter.most_common(10)],
        "colors": [{"hex": h, "count": c} for h, c in color_counter.most_common(10)],
        "text_blocks_sample": blocks_meta[:40],
    }
    doc.close()
    return spec


def write_design_spec(pdf_path: Path, output_path: Path) -> dict:
    spec = analyze_pdf(pdf_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(spec, indent=2), encoding="utf-8")
    return spec