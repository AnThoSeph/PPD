"""Render PDF pages to preview images."""

from __future__ import annotations

import base64
from pathlib import Path

import fitz

PREVIEW_DIR_NAME = "preview-pages"


def render_pdf_pages(pdf_path: Path, output_dir: Path, scale: float = 1.5) -> list[str]:
    """Render every PDF page to PNG; return data URLs for the web UI."""
    output_dir.mkdir(parents=True, exist_ok=True)
    for old in output_dir.glob("page-*.png"):
        old.unlink(missing_ok=True)

    doc = fitz.open(pdf_path)
    urls: list[str] = []
    matrix = fitz.Matrix(scale, scale)
    for i, page in enumerate(doc):
        pix = page.get_pixmap(matrix=matrix)
        out = output_dir / f"page-{i + 1}.png"
        pix.save(str(out))
        b64 = base64.b64encode(out.read_bytes()).decode("ascii")
        urls.append(f"data:image/png;base64,{b64}")
    doc.close()
    return urls


def first_page_data_url(pdf_path: Path, fallback_png: Path | None = None, scale: float = 1.5) -> str | None:
    urls = render_pdf_pages(pdf_path, pdf_path.parent / PREVIEW_DIR_NAME, scale=scale)
    if urls:
        if fallback_png:
            fallback_png.parent.mkdir(parents=True, exist_ok=True)
            (pdf_path.parent / PREVIEW_DIR_NAME / "page-1.png").replace(fallback_png)
        return urls[0]
    return None
