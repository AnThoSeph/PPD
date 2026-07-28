"""Per-client workspace paths for REST/mobile API."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ppd.paths import app_root

_SAFE_ID = re.compile(r"[^a-zA-Z0-9_-]+")


def sanitize_workspace_id(workspace_id: str) -> str:
    cleaned = _SAFE_ID.sub("", (workspace_id or "default").strip())[:64]
    return cleaned or "default"


@dataclass(frozen=True)
class WorkspacePaths:
    """Filesystem locations for one PPD workspace."""

    workspace_id: str
    root: Path
    data: Path
    resume: Path
    output: Path
    output_dir: Path
    preview_png: Path
    preview_pages_dir: Path
    source_preview_png: Path
    source_dir: Path
    raw_txt: Path
    design_spec: Path
    jobs_file: Path
    config: Path
    custom_templates_dir: Path

    @classmethod
    def from_id(cls, workspace_id: str) -> WorkspacePaths:
        wid = sanitize_workspace_id(workspace_id)
        base = app_root()
        if wid == "default":
            data = base / "data"
            output_dir = base / "output"
            custom_templates = data / "templates"
        else:
            ws = base / "workspaces" / wid
            data = ws / "data"
            output_dir = ws / "output"
            custom_templates = data / "templates"
        return cls(
            workspace_id=wid,
            root=base,
            data=data,
            resume=data / "resume.yaml",
            output=output_dir / "resume.pdf",
            output_dir=output_dir,
            preview_png=output_dir / "preview.png",
            preview_pages_dir=output_dir / "preview-pages",
            source_preview_png=output_dir / "source-preview.png",
            source_dir=data / "source",
            raw_txt=data / "raw-extract.txt",
            design_spec=base / "workspaces" / wid / "design-spec.json"
            if wid != "default"
            else base / "design-spec.json",
            jobs_file=data / "jobs.json",
            config=data / "config.yaml",
            custom_templates_dir=custom_templates,
        )

    def ensure_dirs(self) -> None:
        for path in (
            self.data,
            self.source_dir,
            self.output_dir,
            self.design_spec.parent,
            self.custom_templates_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)
