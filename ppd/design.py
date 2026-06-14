"""Map imported PDF design forensics to Typst template variables."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from ppd.paths import templates_dir

DEFAULTS = {
    "template_id": "anshual-frontend",
    "header_bg": "#000000",
    "header_text": "#ffffff",
    "sidebar_bg": "#000000",
    "accent": "#000000",
    "main_text": "#000000",
    "muted": "#333333",
    "font_body": "Century Gothic",
    "font_heading": "Century Gothic",
}

REFERENCE_DIR = templates_dir() / "reference"
REFERENCE_DESIGN = REFERENCE_DIR / "design.json"
REFERENCE_PDF = REFERENCE_DIR / "resume-template.pdf"


def reference_design_path() -> Path | None:
    if REFERENCE_DESIGN.exists():
        return REFERENCE_DESIGN
    return None


def ensure_reference_design(dest: Path) -> Path | None:
    """Copy bundled reference design.json next to the app on first run."""
    src = reference_design_path()
    if not src:
        return None
    dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists():
        shutil.copy2(src, dest)
    return dest


def _luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    if len(h) != 6:
        return 128.0
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return 0.299 * r + 0.587 * g + 0.114 * b


def default_template_name() -> str:
    if REFERENCE_DESIGN.exists():
        return "anshual-frontend"
    return "resume-io-clone"


def template_from_spec(spec_path: Path | None) -> str:
    ref = reference_design_path()
    if ref:
        try:
            data = json.loads(ref.read_text(encoding="utf-8"))
            tid = data.get("template_id") or data.get("layout")
            if tid:
                return str(tid)
        except (json.JSONDecodeError, OSError):
            pass

    if not spec_path or not spec_path.exists():
        return default_template_name()
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return default_template_name()

    if spec.get("layout_hint") == "anshual-frontend":
        return "anshual-frontend"
    if spec.get("layout_hint") == "single-column":
        left_blocks = [b for b in spec.get("text_blocks_sample", []) if b.get("x0", 999) < 180]
        if len(left_blocks) >= 4:
            return "resume-io-clone"
        return "anshual-frontend"
    return default_template_name()


def vars_from_spec(spec_path: Path | None) -> dict[str, str]:
    if spec_path and spec_path.exists():
        try:
            data = json.loads(spec_path.read_text(encoding="utf-8"))
            if "header_bg" in data or "template_id" in data:
                merged = dict(DEFAULTS)
                merged.update({k: str(v) for k, v in data.items() if isinstance(v, (str, int, float))})
                return merged
        except (json.JSONDecodeError, OSError):
            pass

    ref = reference_design_path()
    if ref:
        try:
            data = json.loads(ref.read_text(encoding="utf-8"))
            merged = dict(DEFAULTS)
            merged.update({k: str(v) for k, v in data.items() if isinstance(v, (str, int, float))})
            return merged
        except (json.JSONDecodeError, OSError):
            pass

    if not spec_path or not spec_path.exists():
        return dict(DEFAULTS)
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return dict(DEFAULTS)

    colors = [c["hex"] for c in spec.get("colors", []) if c.get("hex")]
    if not colors:
        return dict(DEFAULTS)

    unique = list(dict.fromkeys(colors))
    by_lum = sorted(unique, key=_luminance)
    sidebar = by_lum[0]
    accent = by_lum[-1]
    if _luminance(accent) > 180 and len(by_lum) > 2:
        accent = by_lum[len(by_lum) // 2]
    if sidebar == accent and len(by_lum) > 1:
        accent = by_lum[1]

    result = dict(DEFAULTS)
    result.update({"sidebar_bg": sidebar, "accent": accent, "header_bg": sidebar})
    return result


def enrich_design_from_pdf(pdf_path: Path, spec_path: Path) -> dict:
    """Analyze uploaded PDF and write a full design profile for template rendering."""
    from ppd.forensics import analyze_pdf

    spec = analyze_pdf(pdf_path)
    profile = dict(DEFAULTS)
    profile.update(vars_from_spec(spec_path if spec_path.exists() else None))

    colors = [c["hex"] for c in spec.get("colors", []) if c.get("hex")]
    if colors:
        unique = list(dict.fromkeys(colors))
        by_lum = sorted(unique, key=_luminance)
        dark = by_lum[0]
        profile["header_bg"] = dark
        profile["sidebar_bg"] = dark
        if _luminance(dark) < 40:
            profile["header_text"] = "#ffffff"

    fonts = spec.get("fonts", [])
    if fonts:
        profile["font_body"] = fonts[0].get("name", profile["font_body"])
        profile["font_heading"] = fonts[0].get("name", profile["font_heading"])

    sizes = [s["size"] for s in spec.get("font_sizes_pt", []) if s.get("size")]
    if sizes:
        profile["name_size_pt"] = max(sizes)
        body_sizes = [s for s in sizes if s < max(sizes)]
        if body_sizes:
            profile["body_size_pt"] = max(body_sizes)
        profile["section_size_pt"] = profile.get("body_size_pt", 11) + 3

    layout = spec.get("layout_hint", "single-column")
    if layout == "anshual-frontend":
        profile["template_id"] = "anshual-frontend"
    elif layout == "sidebar-left":
        profile["template_id"] = "resume-io-clone"
    else:
        profile["template_id"] = "anshual-frontend"

    profile["layout_hint"] = layout
    profile["source_pdf"] = str(pdf_path)

    for key in ("name_size_pt", "section_size_pt", "body_size_pt", "page_margin_x_pt", "page_margin_y_pt"):
        if key in profile:
            try:
                profile[key] = float(profile[key])
            except (TypeError, ValueError):
                profile.pop(key, None)

    spec_path.parent.mkdir(parents=True, exist_ok=True)
    spec_path.write_text(json.dumps(profile, indent=2), encoding="utf-8")
    return profile


def write_design_vars(spec_path: Path | None, output_path: Path) -> Path:
    vars_data = vars_from_spec(spec_path)
    for key in ("name_size_pt", "section_size_pt", "body_size_pt", "page_margin_x_pt", "page_margin_y_pt"):
        if key in vars_data:
            try:
                vars_data[key] = float(vars_data[key])
            except (TypeError, ValueError):
                vars_data.pop(key, None)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(vars_data, indent=2), encoding="utf-8")
    return output_path
