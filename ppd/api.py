"""Backend API exposed to the web UI via pywebview."""

from __future__ import annotations

import base64
import json
import os
import re
import shutil
import traceback
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import fitz
import yaml

from ppd.assistant import apply_action, chat_response, chat_response_structured, get_greeting_and_insights
from ppd.ats import compute_ats_score, compute_skill_match, skill_gap_analysis
from ppd.build import build_pdf as compile_pdf
from ppd.design import ensure_reference_design, enrich_design_from_pdf
from ppd.preview_render import render_pdf_pages
from ppd.forensics import write_design_spec
from ppd.import_file import SUPPORTED_SUFFIXES, import_file
from ppd.paths import app_root, ensure_runtime_dirs, seed_default_files
from ppd.workspace import WorkspacePaths
from ppd.resume_v2 import (
    StructuredResume,
    dump_structured,
    legacy_to_structured,
    load_structured,
    structured_from_dict,
    structured_to_dict,
    structured_to_legacy,
)
from ppd.schema import Resume
from ppd.template_catalog import (
    SOURCE_TEMPLATE_ID,
    USER_TEMPLATE_PREFIX,
    resolve_typst_template,
    scan_custom_templates,
    source_label_from_spec,
    template_list,
    uses_design_vars,
)

PROJECT_ROOT = app_root()

TEMPLATE_MAP = {
    "modern": "ats-standard",
    "executive": "ats-standard",
    "creative": "ats-standard",
    "standard": "ats-standard",
}


class PPDApi:
    """JS-callable API: pywebview.api.method()"""

    def __init__(self, workspace_id: str = "default") -> None:
        self._paths = WorkspacePaths.from_id(workspace_id)
        self._paths.ensure_dirs()
        self._uploaded_path: Path | None = None
        self._template = "standard"
        self._preview_template_id = "ats-standard"
        self._window = None
        ensure_reference_design(self._paths.design_spec)
        self._get_source_path()
        if self._uploaded_path and self._uploaded_path.suffix.lower() == ".pdf" and not self._paths.design_spec.exists():
            try:
                enrich_design_from_pdf(self._uploaded_path, self._paths.design_spec)
            except Exception:
                pass
        self._preview_template_id = (
            SOURCE_TEMPLATE_ID if self._has_upload_design() else "ats-standard"
        )

    def set_window(self, window) -> None:
        self._window = window

    def ping(self) -> dict[str, Any]:
        ensure_runtime_dirs()
        return {"ok": True, "root": str(PROJECT_ROOT)}

    def get_initial_state(self) -> dict[str, Any]:
        try:
            ensure_runtime_dirs()
            seed_default_files()
            yaml_text = self._read_yaml()
            if not yaml_text.strip():
                yaml_text = self._default_yaml_hint()
            structured = self._load_structured_safe()
            legacy = structured_to_legacy(structured) if structured else self._safe_parse(yaml_text)
            ats = compute_ats_score(yaml_text)
            skills = compute_skill_match(yaml_text)
            assistant = get_greeting_and_insights(yaml_text)
            source = self._get_source_path()
            preview_image, preview_mode = self._best_preview(fast=True)
            page_urls = self._load_cached_preview_pages() if preview_mode == "live" else []
            return {
                "ok": True,
                "yaml": yaml_text,
                "user_name": legacy.basics.name if legacy else "Your Name",
                "user_title": legacy.basics.title if legacy else "Professional",
                "structured": structured_to_dict(structured) if structured else None,
                "template": self._template,
                "preview_template_id": self._preview_template_id,
                "preview_template": self._import_template_name(),
                "templates": self._template_catalog(),
                "ats_score": ats["score"],
                "ats_label": ats["label"],
                "skill_match": skills["percent"],
                "sync_status": "SYNCED" if self._paths.resume.exists() else "UNSAVED",
                "assistant_message": assistant["message"],
                "suggestions": assistant["suggestions"],
                "preview_image": preview_image,
                "preview_images": page_urls or ([preview_image] if preview_image else []),
                "preview_page_count": len(page_urls) if page_urls else (1 if preview_image else 0),
                "preview_mode": preview_mode,
                "source_filename": source.name if source else None,
                "stats": self._editor_stats(yaml_text),
            }
        except Exception as exc:
            return {"ok": False, "message": str(exc), "yaml": self._read_yaml() or self._default_yaml_hint()}

    def upload_and_process(self) -> dict[str, Any]:
        """Pick file, extract content, save YAML, build PDF — one step."""
        try:
            picked = self.pick_and_upload()
            if not picked.get("ok"):
                return picked
            return self._process_uploaded()
        except Exception as exc:
            return {"ok": False, "message": f"{exc}\n{traceback.format_exc()[-400:]}"}

    def pick_and_upload(self) -> dict[str, Any]:
        try:
            if not self._window:
                return {"ok": False, "message": "Window not ready. Restart the app."}
            import webview

            file_types = (
                "Resume files (*.pdf;*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.tif;*.tiff)",
                "All files (*.*)",
            )
            result = self._window.create_file_dialog(
                webview.OPEN_DIALOG,
                allow_multiple=False,
                file_types=file_types,
            )
            if not result:
                return {"ok": False, "message": "No file selected.", "cancelled": True}
            source = Path(result[0] if isinstance(result, (list, tuple)) else result)
            if source.suffix.lower() not in SUPPORTED_SUFFIXES:
                return {
                    "ok": False,
                    "message": f"Unsupported file type. Use: {', '.join(sorted(SUPPORTED_SUFFIXES))}",
                }
            self._paths.source_dir.mkdir(parents=True, exist_ok=True)
            dest = self._paths.source_dir / f"upload{source.suffix.lower()}"
            shutil.copy2(source, dest)
            self._uploaded_path = dest
            return {"ok": True, "filename": source.name, "path": str(dest)}
        except Exception as exc:
            return {"ok": False, "message": f"Upload failed: {exc}"}

    def upload_from_bytes(self, filename: str, data: bytes) -> dict[str, Any]:
        """Save uploaded file bytes (REST/mobile — no file dialog)."""
        try:
            suffix = Path(filename).suffix.lower()
            if suffix not in SUPPORTED_SUFFIXES:
                return {
                    "ok": False,
                    "message": f"Unsupported file type. Use: {', '.join(sorted(SUPPORTED_SUFFIXES))}",
                }
            self._paths.source_dir.mkdir(parents=True, exist_ok=True)
            dest = self._paths.source_dir / f"upload{suffix}"
            dest.write_bytes(data)
            self._uploaded_path = dest
            return {"ok": True, "filename": filename, "path": str(dest)}
        except Exception as exc:
            return {"ok": False, "message": f"Upload failed: {exc}"}

    def upload_and_process_bytes(self, filename: str, data: bytes) -> dict[str, Any]:
        """Upload bytes then extract content in one step."""
        picked = self.upload_from_bytes(filename, data)
        if not picked.get("ok"):
            return picked
        return self._process_uploaded()

    def export_pdf_bytes(self, content: str | None = None) -> dict[str, Any]:
        """Build PDF and return bytes (REST/mobile — no Save As dialog)."""
        try:
            if not content or not str(content).strip():
                if self._paths.resume.exists():
                    content = self._paths.resume.read_text(encoding="utf-8")
                else:
                    return {"ok": False, "message": "No resume data to export."}
            built = self.build_pdf(content, template_ui=None)
            if not built.get("ok"):
                return built
            if not self._paths.output.exists():
                return {"ok": False, "message": "PDF was not created."}
            resume = self._validate_content(content)
            safe_name = re.sub(r'[<>:"/\\|?*]+', "", resume.basics.name).strip().replace(" ", "_")
            pdf_b64 = base64.b64encode(self._paths.output.read_bytes()).decode("ascii")
            return {
                "ok": True,
                "message": "PDF exported.",
                "filename": f"{safe_name or 'Resume'}_Resume.pdf",
                "pdf_base64": pdf_b64,
                "path": str(self._paths.output),
                "preview_mode": built.get("preview_mode", "live"),
                **{k: built[k] for k in ("preview_image", "preview_images", "preview_page_count") if k in built},
            }
        except Exception as exc:
            return {"ok": False, "message": f"Export failed: {exc}"}

    def extract_content(self) -> dict[str, Any]:
        try:
            if not self._uploaded_path or not self._uploaded_path.exists():
                return {"ok": False, "message": "Upload a PDF or image first (sidebar: Upload PDF/Image)."}
            return self._process_uploaded()
        except Exception as exc:
            return {"ok": False, "message": str(exc)}

    def _process_uploaded(self) -> dict[str, Any]:
        assert self._uploaded_path is not None
        source_preview = self._render_file_preview(self._uploaded_path)
        resume = import_file(self._uploaded_path, self._paths.resume, self._paths.raw_txt)
        yaml_text = self._paths.resume.read_text(encoding="utf-8")
        structured = load_structured(self._paths.resume)
        if self._uploaded_path.suffix.lower() == ".pdf":
            try:
                enrich_design_from_pdf(self._uploaded_path, self._paths.design_spec)
                self._preview_template_id = SOURCE_TEMPLATE_ID
            except Exception:
                try:
                    write_design_spec(self._uploaded_path, self._paths.design_spec)
                except Exception:
                    pass

        ats = compute_ats_score(yaml_text)
        skills = compute_skill_match(yaml_text)
        assistant = get_greeting_and_insights(yaml_text)

        try:
            preview_image = self._rebuild_live_preview(yaml_text)
            preview_mode = "live"
        except Exception:
            preview_image = source_preview
            preview_mode = "original"
            if preview_image:
                self._cache_source_preview(preview_image)

        payload = self._preview_payload() if preview_mode == "live" else {
            "preview_image": preview_image,
            "preview_images": [preview_image] if preview_image else [],
            "preview_page_count": 1 if preview_image else 0,
        }

        return {
            "ok": True,
            "yaml": yaml_text,
            "message": (
                f"Imported {resume.basics.name}: {len(resume.experience)} jobs, "
                f"{len(resume.skills)} skill groups, {len(resume.education)} education entries. "
                "Edit YAML, then Update Preview to see changes."
            ),
            "preview_mode": preview_mode,
            "preview_template_id": self._preview_template_id,
            "preview_template": self._import_template_name(),
            "templates": self._template_catalog(),
            "source_filename": self._uploaded_path.name,
            "user_name": resume.basics.name,
            "user_title": resume.basics.title or "Professional",
            "ats_score": ats["score"],
            "ats_label": ats["label"],
            "skill_match": skills["percent"],
            "assistant_message": assistant["message"],
            "suggestions": assistant["suggestions"],
            "stats": self._editor_stats(yaml_text),
            "structured": structured_to_dict(structured),
            "raw_lines": len(self._paths.raw_txt.read_text(encoding="utf-8").splitlines()) if self._paths.raw_txt.exists() else 0,
            "sync_status": "SYNCED",
            **payload,
        }

    def get_structured_resume(self) -> dict[str, Any]:
        try:
            structured = self._load_structured_safe()
            if not structured:
                return {"ok": False, "message": "No resume data yet."}
            yaml_text = self._read_yaml()
            return {
                "ok": True,
                "structured": structured_to_dict(structured),
                "yaml": yaml_text,
            }
        except Exception as exc:
            return {"ok": False, "message": str(exc)}

    def save_structured_resume(self, data: dict[str, Any]) -> dict[str, Any]:
        """Save full structured resume document and refresh scores."""
        try:
            structured = structured_from_dict(data.get("resume", data))
            if data.get("resume", data).get("visible_sections"):
                structured.visible_sections = data["resume"]["visible_sections"]
            if data.get("resume", data).get("visible_skill_categories"):
                structured.visible_skill_categories = data["resume"]["visible_skill_categories"]
            dump_structured(structured, self._paths.resume)
            yaml_text = self._paths.resume.read_text(encoding="utf-8")
            legacy = structured_to_legacy(structured)
            ats = compute_ats_score(yaml_text)
            skills = compute_skill_match(yaml_text)
            return {
                "ok": True,
                "message": "Section saved.",
                "yaml": yaml_text,
                "user_name": legacy.basics.name,
                "user_title": legacy.basics.title or "Professional",
                "ats_score": ats["score"],
                "ats_label": ats["label"],
                "skill_match": skills["percent"],
                "stats": self._editor_stats(yaml_text),
                "sync_status": "SYNCED",
                "structured": structured_to_dict(structured),
            }
        except Exception as exc:
            return {"ok": False, "message": str(exc)}

    def save_and_preview(self, data: dict[str, Any]) -> dict[str, Any]:
        """Save structured resume and rebuild live preview."""
        try:
            saved = self.save_structured_resume(data)
            if not saved.get("ok"):
                return saved
            preview = self._rebuild_live_preview()
            payload = self._preview_payload()
            return {
                **saved,
                "preview_mode": "live",
                "message": "Preview updated.",
                **payload,
            }
        except Exception as exc:
            return {"ok": False, "message": f"Preview update failed: {exc}"}

    def save_yaml(self, content: str) -> dict[str, Any]:
        try:
            structured = self._persist_resume(content)
            resume = structured_to_legacy(structured)
            yaml_text = self._paths.resume.read_text(encoding="utf-8")
            ats = compute_ats_score(yaml_text)
            skills = compute_skill_match(yaml_text)
            return {
                "ok": True,
                "message": "Saved successfully.",
                "yaml": yaml_text,
                "user_name": resume.basics.name,
                "user_title": resume.basics.title or "Professional",
                "ats_score": ats["score"],
                "ats_label": ats["label"],
                "skill_match": skills["percent"],
                "stats": self._editor_stats(yaml_text),
                "sync_status": "SYNCED",
            }
        except Exception as exc:
            return {"ok": False, "message": str(exc)}

    def validate_yaml(self, content: str) -> dict[str, Any]:
        try:
            resume = self._validate_content(content)
            return {
                "ok": True,
                "message": f"Valid — {resume.basics.name}, {len(resume.experience)} experience entries.",
            }
        except Exception as exc:
            return {"ok": False, "message": str(exc)}

    def refresh_preview(self) -> dict[str, Any]:
        """Legacy alias — use update_preview with editor content instead."""
        if not self._paths.resume.exists():
            return {"ok": False, "message": "No resume data yet. Upload a PDF or image first."}
        content = self._paths.resume.read_text(encoding="utf-8")
        return self.update_preview(content)

    def update_preview(self, content: str) -> dict[str, Any]:
        """Save YAML and rebuild preview."""
        try:
            structured = self._persist_resume(content)
            resume = structured_to_legacy(structured)
            yaml_text = self._paths.resume.read_text(encoding="utf-8")
            self._rebuild_live_preview()
            ats = compute_ats_score(yaml_text)
            skills = compute_skill_match(yaml_text)
            payload = self._preview_payload()
            return {
                "ok": True,
                "message": "Preview updated from your YAML edits.",
                "preview_mode": "live",
                "user_name": resume.basics.name,
                "user_title": resume.basics.title or "Professional",
                "ats_score": ats["score"],
                "ats_label": ats["label"],
                "skill_match": skills["percent"],
                "stats": self._editor_stats(yaml_text),
                "sync_status": "SYNCED",
                **payload,
            }
        except Exception as exc:
            return {"ok": False, "message": f"Preview update failed: {exc}"}

    def export_pdf(self, content: str) -> dict[str, Any]:
        """Build PDF and let the user pick save location + filename."""
        return self.export_pdf_save_as(content)

    def export_pdf_save_as(self, content: str) -> dict[str, Any]:
        """Build PDF, then show a Save As dialog."""
        try:
            if not self._window:
                return {"ok": False, "message": "Window not ready. Restart the app."}

            if not content or not str(content).strip():
                if self._paths.resume.exists():
                    content = self._paths.resume.read_text(encoding="utf-8")
                else:
                    return {"ok": False, "message": "No resume data to export. Upload or edit your resume first."}

            built = self.build_pdf(content, template_ui=None)
            if not built.get("ok"):
                return built

            import webview

            resume = self._validate_content(content)
            safe_name = re.sub(r'[<>:"/\\|?*]+', "", resume.basics.name).strip().replace(" ", "_")
            default_name = f"{safe_name or 'Resume'}_Resume.pdf"

            result = self._window.create_file_dialog(
                webview.SAVE_DIALOG,
                save_filename=default_name,
                file_types=("PDF files (*.pdf)", "All files (*.*)"),
            )
            if not result:
                return {
                    "ok": True,
                    "cancelled": True,
                    "message": "Export cancelled — PDF is still at output/resume.pdf",
                    "path": str(self._paths.output),
                    **{k: built[k] for k in ("preview_image", "preview_images", "preview_page_count", "preview_mode") if k in built},
                }

            dest = Path(result if isinstance(result, str) else result[0])
            if dest.suffix.lower() != ".pdf":
                dest = dest.with_suffix(".pdf")
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self._paths.output, dest)

            return {
                "ok": True,
                "message": f"Saved to {dest}",
                "path": str(dest),
                "preview_mode": built.get("preview_mode", "live"),
                **{k: built[k] for k in ("preview_image", "preview_images", "preview_page_count") if k in built},
            }
        except Exception as exc:
            return {"ok": False, "message": f"Export failed: {exc}"}

    def _structured_from_content(self, content: str) -> StructuredResume:
        raw = yaml.safe_load(content)
        if not isinstance(raw, dict):
            raise ValueError("YAML must be a mapping at the top level.")
        if "resume" in raw:
            return structured_from_dict(raw)
        return legacy_to_structured(Resume.model_validate(raw))

    def _persist_resume(self, content: str) -> StructuredResume:
        structured = self._structured_from_content(content)
        dump_structured(structured, self._paths.resume)
        return structured

    def build_pdf(self, content: str, template_ui: str | None = None) -> dict[str, Any]:
        """Export/build PDF. No template_ui = main export (original design when imported)."""
        try:
            structured = self._persist_resume(content)
            resume = structured_to_legacy(structured)

            if template_ui:
                template_key = TEMPLATE_MAP.get(template_ui, "resume-io-clone")
                design_path = self._paths.design_spec if uses_design_vars(template_key) and self._paths.design_spec.exists() else None
                path = compile_pdf(
                    template_name=template_key,
                    output_path=self._paths.output_dir / "resume-template.pdf",
                    resume_path=self._paths.resume,
                    config_path=self._paths.config,
                    design_spec_path=design_path,
                    custom_templates_dir=self._paths.custom_templates_dir,
                )
                result: dict[str, Any] = {
                    "ok": True,
                    "message": f"Template PDF saved: {path}",
                    "path": str(path),
                }
                preview = self._render_preview(path)
                if preview:
                    result["preview_image"] = preview
                    result["preview_mode"] = "template"
                return result

            template_key = self._import_template_name()
            design_path = self._paths.design_spec if uses_design_vars(template_key) and self._paths.design_spec.exists() else None
            path = compile_pdf(
                template_name=template_key,
                output_path=self._paths.output,
                resume_path=self._paths.resume,
                config_path=self._paths.config,
                design_spec_path=design_path,
                custom_templates_dir=self._paths.custom_templates_dir,
            )
            result = {
                "ok": True,
                "message": f"PDF exported: {path}",
                "path": str(path),
                "preview_mode": "live",
                "used_original": False,
                **self._preview_payload(path),
            }
            return result
        except Exception as exc:
            return {"ok": False, "message": f"Export failed: {exc}"}

    def get_templates(self) -> dict[str, Any]:
        return {
            "ok": True,
            "templates": self._template_catalog(),
            "selected": self._preview_template_id,
        }

    def set_preview_template(self, template_id: str) -> dict[str, Any]:
        known = {t["id"] for t in self._template_catalog()}
        if template_id not in known:
            return {"ok": False, "message": f"Unknown template: {template_id}"}
        if template_id == SOURCE_TEMPLATE_ID and not self._has_upload_design():
            return {"ok": False, "message": "Upload a PDF first to use your original design."}
        self._preview_template_id = template_id
        try:
            if self._paths.resume.exists():
                self._rebuild_live_preview()
            return {
                "ok": True,
                "preview_template_id": template_id,
                "preview_template": self._import_template_name(),
                "templates": self._template_catalog(),
                "preview_mode": "live",
                **self._preview_payload(),
            }
        except Exception as exc:
            return {"ok": False, "message": str(exc)}

    def set_preview_style(self, style: str) -> dict[str, Any]:
        """Legacy alias — maps old style names to template ids."""
        mapping = {"source_design": SOURCE_TEMPLATE_ID, "ats": "ats-standard"}
        tid = mapping.get(style)
        if not tid:
            return {"ok": False, "message": f"Unknown style: {style}"}
        return self.set_preview_template(tid)

    def set_template(self, template_ui: str) -> dict[str, Any]:
        if template_ui not in TEMPLATE_MAP:
            return {"ok": False, "message": f"Unknown template: {template_ui}"}
        self._template = template_ui
        return {"ok": True, "template": template_ui}

    def upload_template(self, filename: str, data: bytes) -> dict[str, Any]:
        """Save an uploaded .typ file as a custom template and return updated template list."""
        try:
            if not filename.lower().endswith(".typ"):
                return {"ok": False, "message": "Only .typ files are accepted as templates."}
            safe_name = re.sub(r"[^a-zA-Z0-9._-]", "", Path(filename).stem)[:64]
            if not safe_name:
                return {"ok": False, "message": "Invalid template filename."}
            dest = self._paths.custom_templates_dir / f"{safe_name}.typ"
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            return {
                "ok": True,
                "template_id": f"{USER_TEMPLATE_PREFIX}{safe_name}",
                "templates": self._template_catalog(),
            }
        except Exception as exc:
            return {"ok": False, "message": f"Template upload failed: {exc}"}

    def pick_and_upload_template(self) -> dict[str, Any]:
        """Desktop file dialog to pick a .typ template file and register it."""
        try:
            if not self._window:
                return {"ok": False, "message": "Window not ready. Restart the app."}
            import webview

            result = self._window.create_file_dialog(
                webview.OPEN_DIALOG,
                allow_multiple=False,
                file_types=("Typst templates (*.typ)", "All files (*.*)"),
            )
            if not result:
                return {"ok": False, "message": "No file selected.", "cancelled": True}
            source = Path(result[0] if isinstance(result, (list, tuple)) else result)
            return self.upload_template(source.name, source.read_bytes())
        except Exception as exc:
            return {"ok": False, "message": f"Template upload failed: {exc}"}

    def analyze_design(self) -> dict[str, Any]:
        if not self._uploaded_path or self._uploaded_path.suffix.lower() != ".pdf":
            return {"ok": False, "message": "Upload a PDF first."}
        try:
            profile = enrich_design_from_pdf(self._uploaded_path, self._paths.design_spec)
            self._preview_template_id = SOURCE_TEMPLATE_ID
            if self._paths.resume.exists():
                self._rebuild_live_preview()
            payload = self._preview_payload()
            return {
                "ok": True,
                "message": (
                    f"Design captured: {profile.get('template_id', 'custom')} template, "
                    f"font {profile.get('font_body', '?')}, header {profile.get('header_bg', '?')}."
                ),
                "preview_template_id": self._preview_template_id,
                "preview_template": self._import_template_name(),
                "templates": self._template_catalog(),
                "preview_mode": "live",
                **payload,
            }
        except Exception as exc:
            return {"ok": False, "message": str(exc)}

    def get_assistant(self, content: str) -> dict[str, Any]:
        data = get_greeting_and_insights(content)
        ats = compute_ats_score(content)
        skills = compute_skill_match(content)
        return {**data, "ats_score": ats["score"], "ats_label": ats["label"], "skill_match": skills["percent"]}

    def apply_suggestion(self, content: str, action_id: str) -> dict[str, Any]:
        result = apply_action(content, action_id)
        ats = compute_ats_score(result["yaml"])
        skills = compute_skill_match(result["yaml"])
        assistant = get_greeting_and_insights(result["yaml"])
        return {
            "ok": True,
            "yaml": result["yaml"],
            "message": result["message"],
            "ats_score": ats["score"],
            "ats_label": ats["label"],
            "skill_match": skills["percent"],
            "assistant_message": assistant["message"],
            "suggestions": assistant["suggestions"],
            "stats": self._editor_stats(result["yaml"]),
        }

    def send_chat(self, content: str, message: str) -> dict[str, Any]:
        result = chat_response_structured(content, message)
        return {"ok": True, **result}

    def get_skill_gap(self, content: str) -> dict[str, Any]:
        gap = skill_gap_analysis(content)
        return {
            "ok": True,
            "recommendation": gap["recommendation"],
            "matched_skills": gap["matched_skills"],
            "missing_skills": gap["missing_skills"],
        }

    def search_yaml(self, content: str, query: str) -> dict[str, Any]:
        if not query.strip():
            return {"ok": True, "matches": [], "count": 0}
        lines = content.splitlines()
        matches = [i + 1 for i, line in enumerate(lines) if query.lower() in line.lower()]
        return {"ok": True, "matches": matches, "count": len(matches)}

    def open_pdf(self) -> dict[str, Any]:
        if self._paths.output.exists():
            os.startfile(self._paths.output)
            return {"ok": True, "message": "Opened PDF."}
        return {"ok": False, "message": "No PDF yet — click Export PDF first."}

    def get_jobs(self) -> dict[str, Any]:
        jobs = self._load_jobs()
        return {"ok": True, "jobs": jobs, "stats": self._job_stats(jobs)}

    def add_job(self, payload_or_company: Any = "", role: str = "") -> dict[str, Any]:
        """Add a job application. Accepts a dict payload or legacy (company, role) strings."""
        if isinstance(payload_or_company, dict):
            payload = dict(payload_or_company)
            company = str(payload.get("company", "")).strip()
            job_role = str(payload.get("role", "")).strip()
        else:
            company = str(payload_or_company or "").strip()
            job_role = str(role or "").strip()
            payload = {"company": company, "role": job_role}
        if not company or not job_role:
            return {"ok": False, "message": "Company and role are required."}
        jobs = self._load_jobs()
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        job = self._normalize_job({
            "id": payload.get("id") or uuid.uuid4().hex[:12],
            "company": company,
            "role": job_role,
            "status": payload.get("status") or "applied",
            "date_applied": payload.get("date_applied") or payload.get("date") or now,
            "location": payload.get("location") or "",
            "job_url": payload.get("job_url") or "",
            "salary_range": payload.get("salary_range") or "",
            "source": payload.get("source") or "",
            "contact_name": payload.get("contact_name") or "",
            "contact_email": payload.get("contact_email") or "",
            "resume_template": payload.get("resume_template") or "",
            "priority": payload.get("priority") or "medium",
            "follow_up_date": payload.get("follow_up_date") or "",
            "notes": payload.get("notes") or "",
            "created_at": now,
            "updated_at": now,
        })
        jobs.insert(0, job)
        self._save_jobs(jobs)
        return {"ok": True, "jobs": jobs, "stats": self._job_stats(jobs), "job": job}

    def update_job(self, job_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        if not job_id:
            return {"ok": False, "message": "Job id is required."}
        jobs = self._load_jobs()
        idx = next((i for i, j in enumerate(jobs) if j.get("id") == job_id), None)
        if idx is None:
            return {"ok": False, "message": "Job not found."}
        updated = self._normalize_job({**jobs[idx], **payload, "id": job_id})
        updated["updated_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        jobs[idx] = updated
        self._save_jobs(jobs)
        return {"ok": True, "jobs": jobs, "stats": self._job_stats(jobs), "job": updated}

    def delete_job(self, job_id: str) -> dict[str, Any]:
        if not job_id:
            return {"ok": False, "message": "Job id is required."}
        jobs = self._load_jobs()
        before = len(jobs)
        jobs = [j for j in jobs if j.get("id") != job_id]
        if len(jobs) == before:
            return {"ok": False, "message": "Job not found."}
        self._save_jobs(jobs)
        return {"ok": True, "jobs": jobs, "stats": self._job_stats(jobs)}

    def _load_jobs(self) -> list[dict[str, Any]]:
        if not self._paths.jobs_file.exists():
            return []
        try:
            raw = json.loads(self._paths.jobs_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        jobs = raw.get("jobs", []) if isinstance(raw, dict) else []
        if not isinstance(jobs, list):
            return []
        normalized = [self._normalize_job(j) for j in jobs if isinstance(j, dict)]
        if normalized != jobs:
            self._save_jobs(normalized)
        return normalized

    def _save_jobs(self, jobs: list[dict[str, Any]]) -> None:
        self._paths.jobs_file.parent.mkdir(parents=True, exist_ok=True)
        self._paths.jobs_file.write_text(json.dumps({"jobs": jobs}, indent=2), encoding="utf-8")

    def _normalize_job(self, job: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        status = str(job.get("status") or "applied").lower()
        valid_statuses = {"wishlist", "applied", "screening", "interview", "offer", "rejected", "withdrawn"}
        if status not in valid_statuses:
            status = "applied"
        priority = str(job.get("priority") or "medium").lower()
        if priority not in {"low", "medium", "high"}:
            priority = "medium"
        date_applied = job.get("date_applied") or job.get("date") or now
        return {
            "id": job.get("id") or uuid.uuid4().hex[:12],
            "company": str(job.get("company") or "").strip(),
            "role": str(job.get("role") or "").strip(),
            "status": status,
            "date_applied": str(date_applied)[:10],
            "location": str(job.get("location") or "").strip(),
            "job_url": str(job.get("job_url") or "").strip(),
            "salary_range": str(job.get("salary_range") or "").strip(),
            "source": str(job.get("source") or "").strip(),
            "contact_name": str(job.get("contact_name") or "").strip(),
            "contact_email": str(job.get("contact_email") or "").strip(),
            "resume_template": str(job.get("resume_template") or "").strip(),
            "priority": priority,
            "follow_up_date": str(job.get("follow_up_date") or "")[:10],
            "notes": str(job.get("notes") or "").strip(),
            "created_at": str(job.get("created_at") or date_applied)[:10],
            "updated_at": str(job.get("updated_at") or date_applied)[:10],
        }

    def _job_stats(self, jobs: list[dict[str, Any]]) -> dict[str, int]:
        active = {"wishlist", "applied", "screening", "interview"}
        return {
            "total": len(jobs),
            "active": sum(1 for j in jobs if j.get("status") in active),
            "interview": sum(1 for j in jobs if j.get("status") == "interview"),
            "offer": sum(1 for j in jobs if j.get("status") == "offer"),
            "rejected": sum(1 for j in jobs if j.get("status") == "rejected"),
            "follow_up_due": sum(1 for j in jobs if self._follow_up_due(j)),
        }

    @staticmethod
    def _follow_up_due(job: dict[str, Any]) -> bool:
        follow_up = job.get("follow_up_date") or ""
        status = job.get("status") or ""
        if not follow_up or status in {"offer", "rejected", "withdrawn"}:
            return False
        try:
            return follow_up <= datetime.now(timezone.utc).strftime("%Y-%m-%d")
        except Exception:
            return False

    def _default_yaml_hint(self) -> str:
        return (
            "# Upload your resume PDF using the sidebar button,\n"
            "# or paste/edit YAML below.\n"
            "basics:\n  name: Your Name\n  title: Your Title\n  email: you@email.com\n"
        )

    def _read_yaml(self) -> str:
        if self._paths.resume.exists():
            return self._paths.resume.read_text(encoding="utf-8")
        return ""

    def _validate_content(self, content: str) -> Resume:
        if not content or not content.strip():
            raise ValueError("Editor is empty.")
        raw = yaml.safe_load(content)
        if not isinstance(raw, dict):
            raise ValueError("YAML must be a mapping at the top level.")
        if "note" in raw and "basics" not in raw and "resume" not in raw:
            raise ValueError("Remove import note header or paste resume content.")
        if "resume" in raw:
            return structured_to_legacy(structured_from_dict(raw))
        return Resume.model_validate(raw)

    def _load_structured_safe(self):
        if not self._paths.resume.exists():
            return None
        try:
            return load_structured(self._paths.resume)
        except Exception:
            legacy = self._safe_parse(self._read_yaml())
            return legacy_to_structured(legacy) if legacy else None

    def _safe_parse(self, content: str) -> Resume | None:
        try:
            return self._validate_content(content) if content.strip() else None
        except Exception:
            return None

    def _editor_stats(self, content: str) -> dict[str, int]:
        lines = content.splitlines() if content else []
        return {"lines": len(lines), "chars": len(content)}

    def _has_upload_design(self) -> bool:
        return bool(
            (self._paths.design_spec.exists())
            or (self._uploaded_path and self._uploaded_path.suffix.lower() == ".pdf")
        )

    def _template_catalog(self) -> list[dict[str, Any]]:
        return template_list(
            self._has_upload_design(),
            source_label_from_spec(self._paths.design_spec if self._paths.design_spec.exists() else None),
            custom_templates_dir=self._paths.custom_templates_dir,
        )

    def _import_template_name(self) -> str:
        return resolve_typst_template(self._preview_template_id, self._paths.design_spec)

    def _rebuild_live_preview(self, content: str | None = None) -> str | None:
        if content:
            self._validate_content(content)
        template_key = self._import_template_name()
        design_path = self._paths.design_spec if uses_design_vars(template_key) and self._paths.design_spec.exists() else None
        path = compile_pdf(
            template_name=template_key,
            output_path=self._paths.output,
            resume_path=self._paths.resume,
            config_path=self._paths.config,
            design_spec_path=design_path,
            custom_templates_dir=self._paths.custom_templates_dir,
        )
        return self._render_preview(path)

    def _render_preview(self, pdf_path: Path) -> str | None:
        pages = self._render_preview_pages(pdf_path)
        return pages[0] if pages else None

    def _render_preview_pages(self, pdf_path: Path) -> list[str]:
        try:
            urls = render_pdf_pages(pdf_path, self._paths.preview_pages_dir, scale=1.4)
            if urls:
                self._paths.preview_png.parent.mkdir(parents=True, exist_ok=True)
                first = self._paths.preview_pages_dir / "page-1.png"
                if first.exists():
                    self._paths.preview_png.write_bytes(first.read_bytes())
            return urls
        except Exception:
            return []

    def _preview_payload(self, pdf_path: Path | None = None) -> dict[str, Any]:
        path = pdf_path or self._paths.output
        pages = self._render_preview_pages(path) if path.exists() else []
        return {
            "preview_image": pages[0] if pages else None,
            "preview_images": pages,
            "preview_page_count": len(pages),
        }

    def _best_preview(self, fast: bool = False) -> tuple[str | None, str]:
        if self._paths.preview_pages_dir.exists():
            pages = sorted(self._paths.preview_pages_dir.glob("page-*.png"))
            if pages:
                b64 = base64.b64encode(pages[0].read_bytes()).decode("ascii")
                return f"data:image/png;base64,{b64}", "live"
        if self._paths.preview_png.exists() and self._paths.output.exists():
            b64 = base64.b64encode(self._paths.preview_png.read_bytes()).decode("ascii")
            return f"data:image/png;base64,{b64}", "live"
        if fast:
            source_preview = self._source_preview_data_url()
            if source_preview:
                return source_preview, "original"
            return None, "none"
        yaml_text = self._read_yaml()
        if yaml_text.strip() and self._safe_parse(yaml_text):
            try:
                preview = self._rebuild_live_preview(yaml_text)
                if preview:
                    return preview, "live"
            except Exception:
                pass
        source_preview = self._source_preview_data_url()
        if source_preview:
            return source_preview, "original"
        return None, "none"

    def _load_cached_preview_pages(self) -> list[str]:
        if not self._paths.preview_pages_dir.exists():
            return []
        urls: list[str] = []
        for path in sorted(self._paths.preview_pages_dir.glob("page-*.png")):
            b64 = base64.b64encode(path.read_bytes()).decode("ascii")
            urls.append(f"data:image/png;base64,{b64}")
        return urls

    def _get_source_path(self) -> Path | None:
        if self._uploaded_path and self._uploaded_path.exists():
            return self._uploaded_path
        if self._paths.source_dir.exists():
            for ext in sorted(SUPPORTED_SUFFIXES):
                candidate = self._paths.source_dir / f"upload{ext}"
                if candidate.exists():
                    self._uploaded_path = candidate
                    return candidate
        return None

    def _cache_source_preview(self, data_url: str | None) -> None:
        if not data_url or not data_url.startswith("data:image/png;base64,"):
            return
        self._paths.source_preview_png.parent.mkdir(parents=True, exist_ok=True)
        self._paths.source_preview_png.write_bytes(base64.b64decode(data_url.split(",", 1)[1]))

    def _source_preview_data_url(self) -> str | None:
        source = self._get_source_path()
        if source:
            preview = self._render_file_preview(source)
            if preview:
                self._cache_source_preview(preview)
                return preview
        if self._paths.source_preview_png.exists():
            b64 = base64.b64encode(self._paths.source_preview_png.read_bytes()).decode("ascii")
            return f"data:image/png;base64,{b64}"
        return None

    def _render_file_preview(self, file_path: Path) -> str | None:
        try:
            if file_path.suffix.lower() == ".pdf":
                pages = render_pdf_pages(file_path, self._paths.preview_pages_dir, scale=1.2)
                return pages[0] if pages else None
            from PIL import Image
            import io

            img = Image.open(file_path)
            img.thumbnail((400, 566))
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('ascii')}"
        except Exception:
            return None

    def _preview_data_url(self) -> str | None:
        source_preview = self._source_preview_data_url()
        if source_preview:
            return source_preview
        if self._paths.preview_png.exists():
            b64 = base64.b64encode(self._paths.preview_png.read_bytes()).decode("ascii")
            return f"data:image/png;base64,{b64}"
        if self._paths.output.exists():
            return self._render_preview(self._paths.output)
        return None
