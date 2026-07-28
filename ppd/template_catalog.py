"""Resume template catalog — ATS-friendly options + uploaded design."""

from __future__ import annotations

from pathlib import Path
from typing import Any

SOURCE_TEMPLATE_ID = "source"
USER_TEMPLATE_PREFIX = "user_"

ATS_TEMPLATES: list[dict[str, Any]] = [
    {
        "id": "ats-standard",
        "name": "ATS Standard",
        "description": "Classic serif, centered header. Reliable for every job application.",
        "ats_friendly": True,
        "category": "ats",
        "tag": "Classic",
    },
    {
        "id": "ats-modern",
        "name": "ATS Modern",
        "description": "Clean sans-serif with centered sections and dot-separated contact.",
        "ats_friendly": True,
        "category": "ats",
        "tag": "Modern",
    },
    {
        "id": "ats-bold",
        "name": "ATS Bold",
        "description": "Strong typography and thick rules — confident, eye-catching header.",
        "ats_friendly": True,
        "category": "ats",
        "tag": "Bold",
    },
    {
        "id": "ats-tech",
        "name": "ATS Tech",
        "description": "Developer-friendly layout with teal accent bar and split header.",
        "ats_friendly": True,
        "category": "ats",
        "tag": "Tech",
    },
    {
        "id": "ats-creative",
        "name": "ATS Creative",
        "description": "Contemporary split header with accent stripe — stands out, stays parseable.",
        "ats_friendly": True,
        "category": "ats",
        "tag": "Creative",
    },
    {
        "id": "ats-minimal",
        "name": "ATS Minimal",
        "description": "Airy whitespace and light type — refined, uncluttered, modern.",
        "ats_friendly": True,
        "category": "ats",
        "tag": "Minimal",
    },
    {
        "id": "ats-elegant",
        "name": "ATS Elegant",
        "description": "Serif centered layout with italic section titles — polished and timeless.",
        "ats_friendly": True,
        "category": "ats",
        "tag": "Elegant",
    },
    {
        "id": "ats-swiss",
        "name": "ATS Swiss",
        "description": "Grid-precise Helvetica-style layout with uppercase micro-labels.",
        "ats_friendly": True,
        "category": "ats",
        "tag": "Swiss",
    },
    {
        "id": "ats-executive",
        "name": "ATS Executive",
        "description": "Navy accents and double rules — authoritative senior-level presence.",
        "ats_friendly": True,
        "category": "ats",
        "tag": "Executive",
    },
    {
        "id": "ats-professional",
        "name": "ATS Professional",
        "description": "Traditional left-aligned layout with horizontal name rule.",
        "ats_friendly": True,
        "category": "ats",
        "tag": "Professional",
    },
    {
        "id": "ats-compact",
        "name": "ATS Compact",
        "description": "Tighter spacing — fits more content on two pages.",
        "ats_friendly": True,
        "category": "ats",
        "tag": "Compact",
    },
    {
        "id": "resume-io-clone",
        "name": "Sidebar Pro",
        "description": "Two-column sidebar layout. Visual impact; prefer ATS templates for portals.",
        "ats_friendly": False,
        "category": "visual",
        "tag": "Visual",
    },
]

V2_TEMPLATE_IDS = frozenset(t["id"] for t in ATS_TEMPLATES if t["id"].startswith("ats-"))
DESIGN_TEMPLATE_IDS = frozenset({"anshual-frontend", "resume-io-clone"})


def scan_custom_templates(custom_templates_dir: Path | None) -> list[dict[str, Any]]:
    """Scan the custom templates directory for .typ files uploaded by the user."""
    if not custom_templates_dir or not custom_templates_dir.exists():
        return []
    results: list[dict[str, Any]] = []
    for f in sorted(custom_templates_dir.glob("*.typ")):
        stem = f.stem
        safe = _sanitize_template_name(stem)
        tid = f"{USER_TEMPLATE_PREFIX}{safe}"
        name = stem.replace("-", " ").replace("_", " ").title()
        results.append({
            "id": tid,
            "name": name,
            "description": f"Custom template: {name}",
            "ats_friendly": True,
            "category": "custom",
            "tag": "Custom",
        })
    return results


def _sanitize_template_name(name: str) -> str:
    import re
    return re.sub(r"[^a-zA-Z0-9_-]", "", name)[:64] or "unnamed"


def template_list(
    has_upload_design: bool,
    source_label: str | None = None,
    custom_templates_dir: Path | None = None,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []

    if has_upload_design:
        items.append(
            {
                "id": SOURCE_TEMPLATE_ID,
                "name": source_label or "Your Upload",
                "description": "Exact copy of your uploaded PDF — fonts, colors, and layout preserved.",
                "ats_friendly": True,
                "category": "upload",
                "tag": "Default",
                "default": True,
            }
        )

    for entry in ATS_TEMPLATES:
        item = dict(entry)
        item["default"] = not has_upload_design and entry["id"] == "ats-standard"
        items.append(item)

    custom = scan_custom_templates(custom_templates_dir)
    items.extend(custom)

    return items


def resolve_typst_template(selected_id: str, design_spec_path: Path | None) -> str:
    if selected_id == SOURCE_TEMPLATE_ID:
        if design_spec_path and design_spec_path.exists():
            from ppd.design import template_from_spec

            return template_from_spec(design_spec_path)
        return "anshual-frontend"
    return selected_id


def uses_design_vars(typst_key: str) -> bool:
    return typst_key in DESIGN_TEMPLATE_IDS


def uses_v2_yaml(typst_key: str) -> bool:
    if typst_key in V2_TEMPLATE_IDS:
        return True
    if typst_key.startswith(USER_TEMPLATE_PREFIX):
        return True
    return False


def source_label_from_spec(design_spec_path: Path | None) -> str:
    if not design_spec_path or not design_spec_path.exists():
        return "Your Upload"
    try:
        import json

        data = json.loads(design_spec_path.read_text(encoding="utf-8"))
        tid = str(data.get("template_id", "custom")).replace("-", " ").title()
        return f"Your Upload ({tid})"
    except Exception:
        return "Your Upload"
