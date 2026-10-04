"""Command line: beatframe make / preview / templates / new / check."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

import typer

from beatframe import pipeline
from beatframe.schema import load_project
from beatframe.templates import REGISTRY, get_template

app = typer.Typer(add_completion=False, help="Narration script in, animated documentary out.")


def _parse_beats(beats: Optional[str]) -> list[int] | None:
    if not beats:
        return None
    out: list[int] = []
    for part in beats.split(","):
        if "-" in part:
            a, b = part.split("-")
            out += list(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out


@app.command()
def make(project: Path, beats: Optional[str] = typer.Option(None, help="e.g. 1-3,7"),
         workers: Optional[int] = None):
    """Render the full-quality video."""
    p = load_project(project)
    pipeline.run(p, project, preview=False, only=_parse_beats(beats), workers=workers)


@app.command()
def preview(project: Path, beats: Optional[str] = typer.Option(None, help="e.g. 2 or 1-4"),
            workers: Optional[int] = None):
    """Fast 480p preview (seconds per beat instead of minutes)."""
    p = load_project(project)
    pipeline.run(p, project, preview=True, only=_parse_beats(beats), workers=workers)


@app.command()
def check(project: Path):
    """Validate the project file without rendering."""
    p = load_project(project)
    problems = pipeline.validate(p)
    if problems:
        for x in problems:
            typer.echo(f"✗ {x}")
        raise typer.Exit(1)
    typer.echo(f"✓ {len(p.beats)} beats look fine")


@app.command()
def templates():
    """List the available scene templates and their params."""
    get_template(next(iter(REGISTRY), "title_card"))  # ensure everything is imported
    for name in sorted(REGISTRY):
        cls = REGISTRY[name]
        typer.echo(f"\n{name} - {cls.description}")
        for field, info in cls.Params.model_fields.items():
            default = info.default if info.default is not None else ""
            typer.echo(f"    {field}: {json.dumps(default) if not isinstance(default, str) else default}")


@app.command()
def clean(project: Path):
    """Delete the build cache of a project."""
    pipeline.clean(project)
    typer.echo("build cache removed")


if __name__ == "__main__":
    app()
