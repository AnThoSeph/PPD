# PPD — Personal Resume System

Subscription-free resume editor. Upload a PDF or image, edit your content, and rebuild a polished PDF that closely matches Resume.io sidebar layouts.

## Prerequisites

- Python 3.11+
- Typst CLI: `winget install Typst.Typst` (restart terminal after install)
- Tesseract OCR (for image uploads): `winget install UB-Mannheim.TesseractOCR`

## Setup

```powershell
cd C:\Users\anshu\Documents\PPD
pip install -e .
```

## Desktop app (recommended)

Launch the **Advanced Resume Dashboard** UI:

```powershell
ppd gui
```

Or double-click `run-app.bat` / `dist\PPD-Resume\PPD-Resume.exe`

### Dashboard features

- **3-column layout** — YAML IDE, AI Assistant, live preview (matches PPD Editor design)
- **Upload PDF/Image** — sidebar or attach button
- **Extract Content** — OCR for images, text extract for PDFs
- **AI Assistant** — local suggestions (ATS score, keywords, tense fixes, senior optimization)
- **ATS Score & Skill Match** — real-time scoring as you edit
- **Theme switcher** — Modern / Executive / Creative templates
- **Skill Gap panel** — missing keywords analysis
- **Job Tracker** — track applications locally
- **Export PDF** — builds and shows preview thumbnail

Keyboard: `Ctrl+S` save, `Ctrl+Enter` export PDF

> Note: UI loads Tailwind/Google Fonts from CDN — internet required for first launch styling.

### Build the standalone .exe (one-time)

```powershell
# Double-click build-exe.bat, or:
powershell -File build-exe.ps1
```

This creates `dist\PPD-Resume\` — copy that **entire folder** anywhere and run `PPD-Resume.exe`. No Python install needed on that machine.

Bundled inside: app + Typst (for PDF export). For **image OCR**, Tesseract must still be installed: `winget install UB-Mannheim.TesseractOCR`

## Desktop app workflow

1. **Upload PDF / Image** — pick your Resume.io PDF or a screenshot/scan
2. **Extract Content** — pulls text into the YAML editor (OCR for images)
3. **Analyze Design** (PDF only) — saves font/color hints to `design-spec.json`
4. **Edit YAML** — fix any mis-parsed sections in the editor
5. **Save YAML** — writes to `data/resume.yaml`
6. **Build PDF** — generates `output/resume.pdf` (option to open immediately)

Choose **Template** in the toolbar:

- `resume-io-clone` — sidebar layout (Resume.io-like, default)
- `compact` — single-column ATS-friendly

## CLI (optional)

```powershell
ppd import path/to/resume.pdf      # PDF or image → draft YAML
ppd analyze path/to/resume.pdf     # design forensics
ppd validate
ppd build
ppd build --template compact
```

## Project layout

```
PPD/
├── run-app.bat               # double-click to open desktop app
├── data/resume.yaml          # your content
├── data/source/              # uploaded files
├── templates/                # visual design
├── output/resume.pdf         # generated PDF
├── design-spec.json          # from Analyze Design
└── ppd/                      # Python package
```

## Tuning design to match your PDF

After **Analyze Design**, open `design-spec.json` and adjust `templates/resume-io-clone.typ`:

- `sidebar-bg` — left panel background color
- `accent` — section titles and highlights
- Column ratio in `#grid(columns: (32%, 1fr))`

Compare `output/resume.pdf` side-by-side with your original and iterate.

## Daily use

1. Open app (`ppd gui` or `run-app.bat`)
2. Edit YAML → Save → Build PDF

Or edit `data/resume.yaml` directly and run `ppd build`.
