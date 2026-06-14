"""Application paths — works in dev and in a PyInstaller bundle."""

from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)


def app_root() -> Path:
    """Writable folder: project root in dev, folder containing the .exe when frozen."""
    if is_frozen():
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def bundle_root() -> Path:
    """Bundled read-only assets (_MEIPASS for PyInstaller, else project root)."""
    if is_frozen():
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            return Path(meipass)
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


def templates_dir() -> Path:
    for base in (app_root(), bundle_root()):
        path = base / "templates"
        if path.exists():
            return path
    return app_root() / "templates"


def ensure_runtime_dirs() -> None:
    for sub in ("data", "data/source", "output", "tools"):
        (app_root() / sub).mkdir(parents=True, exist_ok=True)


def web_dir() -> Path:
    candidates = [
        bundle_root() / "ppd" / "web",
        bundle_root() / "web",
        Path(__file__).resolve().parent / "web",
    ]
    for path in candidates:
        if path.exists():
            return path
    return Path(__file__).resolve().parent / "web"


def seed_default_files() -> None:
    """Copy default config/resume next to exe on first run."""
    ensure_runtime_dirs()
    config = app_root() / "data" / "config.yaml"
    if config.exists():
        return

    for base in (bundle_root(), app_root()):
        src_data = base / "data"
        if not src_data.exists():
            continue
        for name in ("config.yaml", "resume.yaml"):
            src = src_data / name
            dst = app_root() / "data" / name
            if src.exists() and not dst.exists():
                dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        break
