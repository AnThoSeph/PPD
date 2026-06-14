"""Unified import from PDF or image files."""

from __future__ import annotations

from pathlib import Path

from ppd.import_image import IMAGE_SUFFIXES, extract_text_lines
from ppd.import_pdf import extract_text_lines as extract_pdf_lines
from ppd.import_pdf import lines_to_resume
from ppd.import_semantic import import_pdf_structured, lines_to_structured
from ppd.resume_v2 import dump_structured, structured_to_legacy
from ppd.schema import Resume, dump_resume

SUPPORTED_SUFFIXES = {".pdf", *IMAGE_SUFFIXES}


def extract_lines(source_path: Path) -> list[str]:
    suffix = source_path.suffix.lower()
    if suffix == ".pdf":
        return extract_pdf_lines(source_path)
    if suffix in IMAGE_SUFFIXES:
        return extract_text_lines(source_path)
    raise ValueError(f"Unsupported file type: {suffix}. Use PDF or image ({', '.join(sorted(SUPPORTED_SUFFIXES))}).")


def import_file(source_path: Path, output_yaml: Path, raw_txt: Path) -> Resume:
    """Extract content from PDF or image into structured v2 YAML."""
    if source_path.suffix.lower() == ".pdf":
        structured = import_pdf_structured(source_path, output_yaml, raw_txt)
        return structured_to_legacy(structured)

    lines = extract_lines(source_path)
    raw_txt.parent.mkdir(parents=True, exist_ok=True)
    raw_txt.write_text("\n".join(lines), encoding="utf-8")

    structured = lines_to_structured(lines)
    dump_structured(structured, output_yaml)
    return structured_to_legacy(structured)
