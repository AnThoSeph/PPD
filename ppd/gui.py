"""PPD desktop application."""

from __future__ import annotations

import os
import shutil
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

import yaml

from ppd.build import build_pdf
from ppd.paths import app_root, ensure_runtime_dirs, seed_default_files
from ppd.forensics import write_design_spec
from ppd.import_file import SUPPORTED_SUFFIXES, import_file
from ppd.schema import dump_resume, load_resume

PROJECT_ROOT = app_root()
DEFAULT_RESUME = PROJECT_ROOT / "data" / "resume.yaml"
DEFAULT_OUTPUT = PROJECT_ROOT / "output" / "resume.pdf"
SOURCE_DIR = PROJECT_ROOT / "data" / "source"
RAW_TXT = PROJECT_ROOT / "data" / "raw-extract.txt"
DESIGN_SPEC = PROJECT_ROOT / "design-spec.json"

FILE_TYPES = [
    ("Resume files", "*.pdf *.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff"),
    ("PDF", "*.pdf"),
    ("Images", "*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff"),
    ("All files", "*.*"),
]


class PPDApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("PPD — Personal Resume Editor")
        self.geometry("960x720")
        self.minsize(800, 600)

        self.uploaded_path: Path | None = None
        self._build_ui()
        self._load_yaml_file()

    def _build_ui(self) -> None:
        style = ttk.Style(self)
        if "vista" in style.theme_names():
            style.theme_use("vista")

        toolbar = ttk.Frame(self, padding=8)
        toolbar.pack(fill=tk.X)

        ttk.Button(toolbar, text="Upload PDF / Image", command=self.upload_file).pack(side=tk.LEFT)
        ttk.Button(toolbar, text="Extract Content", command=self.extract_content).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(toolbar, text="Analyze Design", command=self.analyze_design).pack(side=tk.LEFT, padx=(8, 0))

        ttk.Label(toolbar, text="Template:").pack(side=tk.LEFT, padx=(16, 4))
        self.template_var = tk.StringVar(value="resume-io-clone")
        ttk.Combobox(
            toolbar,
            textvariable=self.template_var,
            values=["resume-io-clone", "compact"],
            state="readonly",
            width=18,
        ).pack(side=tk.LEFT)

        main = ttk.Frame(self, padding=(8, 0, 8, 8))
        main.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main, text="Resume content (YAML) — edit and save before building:").pack(anchor=tk.W)
        self.editor = scrolledtext.ScrolledText(main, wrap=tk.NONE, font=("Consolas", 10))
        self.editor.pack(fill=tk.BOTH, expand=True, pady=(4, 8))

        actions = ttk.Frame(main)
        actions.pack(fill=tk.X)

        ttk.Button(actions, text="Save YAML", command=self.save_yaml).pack(side=tk.LEFT)
        ttk.Button(actions, text="Validate", command=self.validate_yaml).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(actions, text="Build PDF", command=self.build_resume).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(actions, text="Open PDF", command=self.open_pdf).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(actions, text="Reload", command=self._load_yaml_file).pack(side=tk.LEFT, padx=(8, 0))

        self.status_var = tk.StringVar(value="Ready — upload a PDF or image to get started.")
        ttk.Label(self, textvariable=self.status_var, padding=(8, 4)).pack(fill=tk.X, anchor=tk.W)

        self.upload_label = ttk.Label(toolbar, text="No file uploaded", foreground="#666")
        self.upload_label.pack(side=tk.RIGHT)

    def _set_status(self, message: str) -> None:
        self.status_var.set(message)
        self.update_idletasks()

    def _run_async(self, task, on_success, on_error) -> None:
        def worker() -> None:
            try:
                result = task()
                self.after(0, lambda: on_success(result))
            except Exception as exc:
                self.after(0, lambda: on_error(exc))

        threading.Thread(target=worker, daemon=True).start()

    def _load_yaml_file(self) -> None:
        path = DEFAULT_RESUME
        if not path.exists():
            draft = DEFAULT_RESUME.with_suffix(".draft.yaml")
            path = draft if draft.exists() else path
        if path.exists():
            self.editor.delete("1.0", tk.END)
            self.editor.insert(tk.END, path.read_text(encoding="utf-8"))
            self._set_status(f"Loaded {path.relative_to(PROJECT_ROOT)}")
        else:
            self._set_status("No resume.yaml yet — upload a file and extract content.")

    def upload_file(self) -> None:
        chosen = filedialog.askopenfilename(title="Select resume PDF or image", filetypes=FILE_TYPES)
        if not chosen:
            return

        source = Path(chosen)
        if source.suffix.lower() not in SUPPORTED_SUFFIXES:
            messagebox.showerror("Unsupported file", f"Use one of: {', '.join(sorted(SUPPORTED_SUFFIXES))}")
            return

        SOURCE_DIR.mkdir(parents=True, exist_ok=True)
        dest = SOURCE_DIR / f"upload{source.suffix.lower()}"
        shutil.copy2(source, dest)
        self.uploaded_path = dest
        self.upload_label.config(text=source.name)
        self._set_status(f"Uploaded {source.name} — click Extract Content")

    def extract_content(self) -> None:
        if not self.uploaded_path or not self.uploaded_path.exists():
            messagebox.showinfo("No file", "Upload a PDF or image first.")
            return

        self._set_status("Extracting text…")

        def task():
            return import_file(self.uploaded_path, DEFAULT_RESUME, RAW_TXT)

        def on_success(resume):
            from ppd.schema import dump_resume

            DEFAULT_RESUME.parent.mkdir(parents=True, exist_ok=True)
            dump_resume(resume, DEFAULT_RESUME)
            yaml_text = DEFAULT_RESUME.read_text(encoding="utf-8")
            self.editor.delete("1.0", tk.END)
            self.editor.insert(tk.END, yaml_text)
            self._set_status(
                f"Extracted {resume.basics.name!r} — {len(resume.experience)} jobs. Review YAML, Save, then Build."
            )
            messagebox.showinfo(
                "Extract complete",
                "Content extracted into the editor.\n\n"
                "Review and fix any sections, click Save YAML, then Build PDF.",
            )

        def on_error(exc):
            self._set_status("Extract failed.")
            messagebox.showerror("Extract failed", str(exc))

        self._run_async(task, on_success, on_error)

    def analyze_design(self) -> None:
        path = self.uploaded_path
        if not path or path.suffix.lower() != ".pdf":
            messagebox.showinfo("PDF required", "Upload a PDF first to analyze fonts, colors, and layout.")
            return

        self._set_status("Analyzing design…")

        def task():
            return write_design_spec(path, DESIGN_SPEC)

        def on_success(spec):
            layout = spec.get("layout_hint", "unknown")
            colors = ", ".join(c["hex"] for c in spec.get("colors", [])[:3])
            self._set_status(f"Design analyzed — layout: {layout}. See design-spec.json")
            messagebox.showinfo(
                "Design analysis",
                f"Layout: {layout}\nTop colors: {colors or 'n/a'}\n\n"
                f"Saved to design-spec.json — use these to tune templates/resume-io-clone.typ",
            )

        def on_error(exc):
            self._set_status("Analysis failed.")
            messagebox.showerror("Analysis failed", str(exc))

        self._run_async(task, on_success, on_error)

    def save_yaml(self) -> None:
        text = self.editor.get("1.0", tk.END).strip()
        if not text:
            messagebox.showwarning("Empty", "Nothing to save.")
            return
        try:
            raw = yaml.safe_load(text)
            if not isinstance(raw, dict):
                raise ValueError("YAML must be a mapping at the top level.")
            if "note" in raw and "basics" not in raw:
                raise ValueError("Remove the import 'note' header or save the draft content below it.")
            resume = load_resume_from_dict(raw)
            DEFAULT_RESUME.parent.mkdir(parents=True, exist_ok=True)
            dump_resume(resume, DEFAULT_RESUME)
            self._set_status(f"Saved {DEFAULT_RESUME.relative_to(PROJECT_ROOT)}")
            messagebox.showinfo("Saved", f"Resume saved to {DEFAULT_RESUME.name}")
        except Exception as exc:
            messagebox.showerror("Save failed", str(exc))

    def validate_yaml(self) -> None:
        try:
            resume = load_resume_from_editor(self.editor)
            self._set_status(f"Valid — {resume.basics.name!r}, {len(resume.experience)} experience entries")
            messagebox.showinfo("Valid", f"Resume is valid.\n{resume.basics.name} — {len(resume.experience)} jobs")
        except Exception as exc:
            messagebox.showerror("Validation failed", str(exc))

    def build_resume(self) -> None:
        try:
            resume = load_resume_from_editor(self.editor)
            DEFAULT_RESUME.parent.mkdir(parents=True, exist_ok=True)
            dump_resume(resume, DEFAULT_RESUME)
        except Exception as exc:
            messagebox.showerror("YAML error", f"Fix YAML before building:\n{exc}")
            return

        self._set_status("Building PDF…")
        template = self.template_var.get()

        def task():
            return build_pdf(template_name=template, output_path=DEFAULT_OUTPUT)

        def on_success(path):
            self._set_status(f"Built {path.relative_to(PROJECT_ROOT)}")
            if messagebox.askyesno("PDF ready", f"Saved to {path.name}\n\nOpen it now?"):
                os.startfile(path)

        def on_error(exc):
            self._set_status("Build failed.")
            messagebox.showerror("Build failed", str(exc))

        self._run_async(task, on_success, on_error)

    def open_pdf(self) -> None:
        if DEFAULT_OUTPUT.exists():
            os.startfile(DEFAULT_OUTPUT)
        else:
            messagebox.showinfo("No PDF", "Build a PDF first.")


def load_resume_from_dict(raw: dict):
    """Validate dict without writing to disk."""
    from ppd.schema import Resume

    return Resume.model_validate(raw)


def load_resume_from_editor(editor: scrolledtext.ScrolledText):
    text = editor.get("1.0", tk.END).strip()
    raw = yaml.safe_load(text)
    if not isinstance(raw, dict):
        raise ValueError("YAML must be a mapping.")
    if "note" in raw and "basics" not in raw:
        raise ValueError("Editor still has import header only — extract content or paste resume YAML.")
    return load_resume_from_dict(raw)


def main() -> None:
    """Launch the modern web UI (default)."""
    from ppd.gui_web import main as web_main

    web_main()


def main_tk() -> None:
    """Legacy tkinter UI."""
    ensure_runtime_dirs()
    seed_default_files()
    app = PPDApp()
    app.mainloop()


if __name__ == "__main__":
    main()
