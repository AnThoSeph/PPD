"""PPD command-line interface."""

from __future__ import annotations

from pathlib import Path

import click

from ppd.build import build_pdf, validate_only
from ppd.forensics import write_design_spec
from ppd.import_file import import_file

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@click.group()
@click.version_option(package_name="ppd")
def main() -> None:
    """PPD - Personal resume build system."""


@main.command()
@click.option("--resume", "resume_path", type=click.Path(path_type=Path), default=None)
@click.option("--template", "template_name", default=None, help="resume-io-clone or compact")
@click.option("--output", "output_path", type=click.Path(path_type=Path), default=None)
def build(resume_path: Path | None, template_name: str | None, output_path: Path | None) -> None:
    """Validate YAML and compile PDF."""
    out = build_pdf(resume_path=resume_path, template_name=template_name, output_path=output_path)
    click.echo(f"Built: {out}")


@main.command()
@click.argument("file_path", type=click.Path(exists=True, path_type=Path))
@click.option("--output", "output_yaml", type=click.Path(path_type=Path), default=PROJECT_ROOT / "data" / "resume.yaml")
def import_cmd(file_path: Path, output_yaml: Path) -> None:
    """Import PDF or image text into draft YAML (one-time bootstrap)."""
    raw_txt = PROJECT_ROOT / "data" / "raw-extract.txt"
    resume = import_file(file_path, output_yaml, raw_txt)
    click.echo(f"Draft YAML: {output_yaml.with_suffix('.draft.yaml')}")
    click.echo(f"Raw text:   {raw_txt}")
    click.echo(f"Extracted:  {resume.basics.name!r}, {len(resume.experience)} jobs, {len(resume.skills)} skill groups")
    click.echo("Review the draft, fix sections, then save as data/resume.yaml")


@main.command()
def gui() -> None:
    """Launch the desktop app."""
    from ppd.gui_web import main as gui_main

    gui_main()


@main.command()
@click.option("--host", default="0.0.0.0", show_default=True)
@click.option("--port", default=8765, show_default=True, type=int)
@click.option("--reload", is_flag=True, help="Auto-reload on code changes (dev only).")
def serve(host: str, port: int, reload: bool) -> None:
    """Start the REST API server for mobile clients."""
    import uvicorn

    uvicorn.run("ppd.http_server:app", host=host, port=port, reload=reload)


@main.command()
@click.argument("pdf_path", type=click.Path(exists=True, path_type=Path))
@click.option("--output", "spec_path", type=click.Path(path_type=Path), default=PROJECT_ROOT / "design-spec.json")
def analyze(pdf_path: Path, spec_path: Path) -> None:
    """Extract fonts, colors, and layout hints from your PDF."""
    spec = write_design_spec(pdf_path, spec_path)
    click.echo(f"Design spec: {spec_path}")
    click.echo(f"Layout hint: {spec['layout_hint']}")
    if spec.get("fonts"):
        click.echo(f"Top font:    {spec['fonts'][0]['name']}")
    if spec.get("colors"):
        click.echo(f"Top colors:  {', '.join(c['hex'] for c in spec['colors'][:3])}")


@main.command()
@click.option("--resume", "resume_path", type=click.Path(path_type=Path), default=None)
def validate(resume_path: Path | None) -> None:
    """Validate resume YAML without building."""
    resume = validate_only(resume_path)
    click.echo(f"Valid: {resume.basics.name!r} - {len(resume.experience)} experience entries")


main.add_command(import_cmd, name="import")

if __name__ == "__main__":
    main()
