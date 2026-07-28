# PPD — Personal Resume System

> A subscription-free, local-first resume builder. Import an existing resume (PDF or image), edit it in a structured desktop editor, and export polished, ATS-friendly PDFs — all offline, with your data staying on your machine.

PPD runs as a lightweight desktop app (pywebview) backed by a Python pipeline that ingests documents, parses them into a structured data model, and renders PDFs with [Typst](https://typst.app/). No accounts, no cloud, no monthly fees.

---

## Table of contents

- [Features](#features)
- [How it works](#how-it-works)
- [Tech stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
  - [Desktop app](#desktop-app-recommended)
  - [Command line](#command-line)
- [Resume data model](#resume-data-model)
- [Templates](#templates)
- [Building a standalone executable](#building-a-standalone-executable)
- [Continuous integration](#continuous-integration)
- [Project structure](#project-structure)
- [Troubleshooting](#troubleshooting)
- [License](#license)

---

## Features

- **Import from PDF or image** — extracts text directly from PDFs, or runs OCR (Tesseract) on screenshots/scans.
- **Semantic parsing** — automatically detects sections (summary, experience, projects, skills, education, certifications) and maps them into a structured schema.
- **Structured section editor** — edit each part of your resume in dedicated cards instead of one giant text blob; only the sections found in your document are shown.
- **Raw YAML editor** — power users can edit the underlying `data/resume.yaml` directly.
- **Design forensics** — for PDF imports, PPD analyzes fonts, colors, and layout and can reproduce your original design as a template.
- **12+ templates** — 11 single-column ATS-friendly layouts plus a two-column "Sidebar Pro" visual layout, and a "Your Upload" template that mirrors your original PDF.
- **Live preview** — every edit re-renders the PDF and shows page thumbnails in-app.
- **ATS score & skill match** — real-time scoring and keyword analysis as you edit.
- **Skill gap panel** — highlights missing keywords versus common expectations.
- **Job tracker** — track applications, statuses, follow-up dates, contacts, salary, and notes locally.
- **AI assistant** — local, rule-based suggestions (tense fixes, keyword hints, senior-level optimization).
- **One-click export** — build and save the final PDF anywhere.
- **Portable builds** — ship a self-contained executable (with Typst and Tesseract bundled) for Windows and Linux.

---

## How it works

PPD is a multi-stage document pipeline orchestrated by the backend API and desktop UI:

```
Upload (PDF / image)
  ├─ PDF  → PyMuPDF text extraction ┐
  └─ image → Tesseract OCR          ┘
        → semantic parsing (section detection, skill bucketing)
        → structured data model (data/resume.yaml, v2 schema)
        → edit in section editor / YAML / AI assistant
        → Typst template (+ design spec from original PDF)
        → output/resume.pdf
        → PyMuPDF rasterization → in-app preview
        → export / Save As
```

For PDF uploads, a parallel **design pipeline** (`forensics.py` / `design.py`) writes `design-spec.json` (fonts, colors, layout) so the default preview can match your original resume.

---

## Tech stack

| Area | Technology |
|------|------------|
| Language | Python 3.11+ |
| Desktop shell | [pywebview](https://pywebview.flowrl.com/) + HTML/CSS/JS UI |
| PDF parsing & preview | [PyMuPDF](https://pymupdf.readthedocs.io/) (`fitz`) |
| Image OCR | [Tesseract](https://github.com/tesseract-ocr/tesseract) via `pytesseract` + Pillow |
| PDF rendering | [Typst](https://typst.app/) |
| Data model & validation | [Pydantic](https://docs.pydantic.dev/) v2 |
| Config / storage | YAML + JSON (local files) |
| CLI | [Click](https://click.palletsprojects.com/) |
| Packaging | PyInstaller |
| CI/CD | GitHub Actions (Windows + Linux release builds) |

---

## Prerequisites

- **Python 3.11+**
- **Typst CLI** — required for PDF rendering
  - Windows: `winget install Typst.Typst`
  - macOS: `brew install typst`
  - Linux: download from [Typst releases](https://github.com/typst/typst/releases)
- **Tesseract OCR** — only needed for **image** uploads (PDFs don't require it)
  - Windows: `winget install UB-Mannheim.TesseractOCR`
  - macOS: `brew install tesseract`
  - Linux: `sudo apt install tesseract-ocr`

> When you build the packaged executable with `build-exe.bat` / `build-exe.sh`, Typst and Tesseract are bundled automatically — end users don't need to install anything.

---

## Installation

```bash
git clone https://github.com/AnThoSeph/PPD.git
cd PPD
pip install -e .
```

This installs the `ppd` package and the `ppd` / `ppd-gui` console commands.

---

## Usage

### Desktop app (recommended)

```bash
ppd gui
```

Or double-click **`run-app.bat`** on Windows (runs from source, falls back to a built executable if Python isn't available).

**Typical workflow:**

1. **Upload PDF / Image** — pick your existing resume from the sidebar.
2. **Extract Content** — text is parsed into the structured editor (OCR runs automatically for images).
3. **Edit** — fix any fields in the section editor or the raw YAML panel.
4. **Choose a template** — pick from the ATS gallery, Sidebar Pro, or "Your Upload".
5. **Update Preview** — re-render and review page thumbnails.
6. **Export PDF** — save the final document anywhere.

**Shortcuts:** `Ctrl+S` to save, `Ctrl+Enter` to export.

### Command line

The CLI is handy for scripting and one-off conversions:

```bash
ppd import path/to/resume.pdf     # PDF or image → data/resume.yaml (+ .draft.yaml)
ppd analyze path/to/resume.pdf    # write design-spec.json (fonts/colors/layout)
ppd validate                      # validate resume YAML without building
ppd build                         # render output/resume.pdf with the default template
ppd build --template ats-modern   # render with a specific template
ppd build --resume data/resume.yaml --output output/custom.pdf
```

---

## Resume data model

Content is stored in `data/resume.yaml` using a structured **v2 schema** (validated with Pydantic). Top-level shape:

```yaml
resume:
  personal:      # name, title, location, phone, email, github, linkedin, portfolio
  summary:       # text
  experience:    # list: title, company, location, dates, bullets[]
  projects:      # list: name, technologies[], description, bullets[]
  skills:        # frontend[], backend[], database[], cloud_tools[], other[]
  education:     # list: degree, field, institution, location, graduation, gpa
  certifications: []
  custom_sections:  # list: title, items[]
  visible_sections: []          # only the sections detected on import
  visible_skill_categories: []  # only the skill buckets that have content
```

Legacy single-blob resumes are migrated to this structure automatically on load.

---

## Templates

All templates live in `templates/` as `.typ` files and are listed in `ppd/template_catalog.py`.

**ATS-friendly (single column, parser-safe):**

`ats-standard` · `ats-modern` · `ats-bold` · `ats-tech` · `ats-creative` · `ats-minimal` · `ats-elegant` · `ats-swiss` · `ats-executive` · `ats-professional` · `ats-compact`

**Other:**

- **Sidebar Pro** (`resume-io-clone`) — two-column visual layout with strong impact (best for direct sharing rather than ATS portals).
- **Your Upload** (`source`) — reproduces your uploaded PDF's fonts, colors, and layout using `design-spec.json`.

The default template is **Your Upload** after a PDF import, otherwise **ATS Standard**.

---

## Building a standalone executable

Create a self-contained app that bundles Python, Typst, and Tesseract — no dependencies required on the target machine.

**Windows:**

```powershell
# Double-click build-exe.bat, or:
powershell -File build-exe.ps1
```

Produces `dist\PPD-Resume\` — copy the **entire folder** anywhere and run `PPD-Resume.exe`.

**Linux:**

```bash
chmod +x build-exe.sh
./build-exe.sh
```

Produces `dist/PPD-Resume/PPD-Resume`. On Linux, pywebview also needs system WebKit/GTK libraries:

```bash
sudo apt install libgtk-3-0 libwebkit2gtk-4.1-0 gir1.2-webkit2-4.1
```

> The tool-bundling logic is shared with CI via `scripts/bundle-tools-windows.ps1`.

---

## Continuous integration

`.github/workflows/build-release.yml` builds and publishes cross-platform releases:

- **Triggers:** push a version tag (`v*`) or run the workflow manually.
- **Matrix build:** compiles the app on `windows-latest` and `ubuntu-latest` in parallel.
- **Bundling:** installs and packages Typst + Tesseract into each build.
- **Artifacts:** uploads `PPD-Resume-windows-x64.zip` and `PPD-Resume-linux-x64.tar.gz`.
- **Release:** on tag pushes, attaches both archives to a GitHub Release with install notes.

To cut a release:

```bash
git tag v1.0.0
git push origin v1.0.0
```

---

## Project structure

```
PPD/
├── ppd/                       # Python package
│   ├── api.py                 # backend API exposed to the web UI
│   ├── gui_web.py             # pywebview desktop entry point
│   ├── cli.py                 # Click command-line interface
│   ├── import_file.py         # unified PDF/image import
│   ├── import_pdf.py          # PDF text extraction
│   ├── import_image.py        # image OCR
│   ├── import_semantic.py     # section detection & structured parsing
│   ├── tesseract_util.py      # Tesseract discovery/config
│   ├── resume_v2.py           # structured v2 schema + migration
│   ├── schema.py              # legacy resume schema
│   ├── build.py               # Typst compilation
│   ├── template_catalog.py    # template registry
│   ├── forensics.py / design.py  # PDF design analysis
│   ├── preview_render.py      # PDF → PNG previews
│   ├── ats.py / assistant.py  # scoring & local suggestions
│   ├── paths.py               # dev vs. frozen path resolution
│   └── web/                   # HTML/CSS/JS desktop UI
├── templates/                 # Typst resume templates
├── data/                      # resume.yaml, config.yaml, jobs.json, uploads
├── output/                    # generated PDF + preview images
├── scripts/                   # build helper scripts
├── .github/workflows/         # CI/CD
├── build-exe.ps1 / .bat / .sh # local packaging scripts
├── ppd.spec                   # PyInstaller spec
├── run-app.bat                # launch the app on Windows
└── pyproject.toml
```

---

## Troubleshooting

**"Typst not found"** — install the Typst CLI and restart your terminal, or run from a folder that includes `tools/typst`. Packaged builds include it automatically.

**"Tesseract OCR is not installed or not on PATH"** — only affects **image** uploads. Install Tesseract (`winget install UB-Mannheim.TesseractOCR`) and restart the app, or upload a PDF instead (PDFs don't need OCR and generally parse more accurately).

**Preview stuck / stale after editing** — click **Update Preview**. If the app was frozen into an `.exe`, close it fully and relaunch after rebuilding, since old bundles may lag behind source changes.

**Build fails with "access denied" on `dist/`** — close any running `PPD-Resume.exe` before rebuilding; the running process locks the output folder.

---

## License

No license file is currently included, so all rights are reserved by default. Add a `LICENSE` file (for example MIT) if you intend to open-source or distribute this project.
