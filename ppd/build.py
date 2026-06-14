"""Build PDF from validated resume YAML."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import yaml

from ppd.paths import app_root, ensure_runtime_dirs, templates_dir
from ppd.template_catalog import (
    uses_design_vars,
    uses_v2_yaml,
)
from ppd.resume_v2 import dump_structured, load_structured, structured_to_legacy
from ppd.schema import Resume, dump_resume, load_resume

PROJECT_ROOT = app_root()
DEFAULT_CONFIG = PROJECT_ROOT / "data" / "config.yaml"
DEFAULT_RESUME = PROJECT_ROOT / "data" / "resume.yaml"
DEFAULT_OUTPUT = PROJECT_ROOT / "output" / "resume.pdf"


def _template_paths() -> dict[str, Path]:
    tdir = templates_dir()
    return {
        "ats-standard": tdir / "ats-standard.typ",
        "ats-modern": tdir / "ats-modern.typ",
        "ats-bold": tdir / "ats-bold.typ",
        "ats-tech": tdir / "ats-tech.typ",
        "ats-creative": tdir / "ats-creative.typ",
        "ats-minimal": tdir / "ats-minimal.typ",
        "ats-elegant": tdir / "ats-elegant.typ",
        "ats-swiss": tdir / "ats-swiss.typ",
        "ats-executive": tdir / "ats-executive.typ",
        "ats-professional": tdir / "ats-professional.typ",
        "ats-compact": tdir / "ats-compact.typ",
        "anshual-frontend": tdir / "anshual-frontend.typ",
        "resume-io-clone": tdir / "resume-io-clone.typ",
        "compact": tdir / "compact.typ",
    }


def load_config(config_path: Path | None = None) -> dict:
    path = config_path or DEFAULT_CONFIG
    if not path.exists():
        return {"template": "resume-io-clone", "resume": "data/resume.yaml", "output": "output/resume.pdf"}
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def resolve_path(path: str | Path, base: Path | None = None) -> Path:
    root = base or PROJECT_ROOT
    p = Path(path)
    return p if p.is_absolute() else root / p


def find_typst() -> str:
    tools_dir = PROJECT_ROOT / "tools"
    for name in ("typst.exe", "typst"):
        bundled = tools_dir / name
        if bundled.exists():
            return str(bundled)
    typst = shutil.which("typst")
    if typst:
        return typst
    raise RuntimeError(
        "Typst not found. Either:\n"
        "  • Run from the full PPD folder (includes tools/typst), or\n"
        "  • Install Typst and add it to PATH"
    )


def _typst_resume_file(resume_file: Path, template_key: str) -> Path:
    """Normalize resume YAML to the format each Typst template expects."""
    structured = load_structured(resume_file)
    if uses_v2_yaml(template_key):
        compile_path = resume_file.parent / "_typst_compile_v2.yaml"
        dump_structured(structured, compile_path)
        return compile_path
    legacy = structured_to_legacy(structured)
    compile_path = resume_file.parent / "_typst_compile.yaml"
    dump_resume(legacy, compile_path)
    return compile_path


def build_pdf(
    resume_path: Path | None = None,
    template_name: str | None = None,
    output_path: Path | None = None,
    config_path: Path | None = None,
    design_spec_path: Path | None = None,
) -> Path:
    ensure_runtime_dirs()
    config = load_config(config_path)
    resume_file = resolve_path(resume_path or config.get("resume", DEFAULT_RESUME))
    template_key = template_name or config.get("template", "resume-io-clone")
    output_file = resolve_path(output_path or config.get("output", DEFAULT_OUTPUT))

    templates = _template_paths()
    if template_key not in templates:
        raise ValueError(f"Unknown template '{template_key}'. Choose from: {', '.join(templates)}")

    template_file = templates[template_key]
    if not template_file.exists():
        raise FileNotFoundError(f"Template not found: {template_file}")
    if not resume_file.exists():
        raise FileNotFoundError(
            f"Resume YAML not found: {resume_file}\n"
            "Upload a file and extract content first."
        )

    try:
        structured = load_structured(resume_file)
        resume: Resume = structured_to_legacy(structured)
    except ValueError:
        resume = load_resume(resume_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    typst_resume = _typst_resume_file(resume_file, template_key)
    rel_resume = Path(os.path.relpath(typst_resume, template_file.parent)).as_posix()
    typst = find_typst()
    cmd = [
        typst,
        "compile",
        str(template_file),
        str(output_file),
        "--root",
        str(PROJECT_ROOT),
        "--input",
        f"resume={rel_resume}",
    ]

    if design_spec_path and design_spec_path.exists() and uses_design_vars(template_key):
        from ppd.design import write_design_vars

        vars_file = PROJECT_ROOT / "output" / "design-vars.json"
        write_design_vars(design_spec_path, vars_file)
        rel_design = Path(os.path.relpath(vars_file, template_file.parent)).as_posix()
        cmd.extend(["--input", f"design={rel_design}"])

    result = subprocess.run(cmd, capture_output=True, text=True, cwd=PROJECT_ROOT)
    if result.returncode != 0:
        raise RuntimeError(
            f"Typst compile failed:\n{result.stderr or result.stdout}\n"
            f"Resume: name={resume.basics.name!r}, exp={len(resume.experience)}"
        )
    return output_file


def validate_only(resume_path: Path | None = None) -> Resume:
    path = resolve_path(resume_path or DEFAULT_RESUME)
    return load_resume(path)
