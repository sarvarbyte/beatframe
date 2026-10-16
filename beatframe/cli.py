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


FORMAT_HELP = "long (16:9, 1920x1080) or short (9:16, 1080x1920). Default: the project's video.format"


@app.command()
def make(project: Path, beats: Optional[str] = typer.Option(None, help="e.g. 1-3,7"),
         workers: Optional[int] = None,
         format: Optional[str] = typer.Option(None, "--format", "-f", help=FORMAT_HELP)):
    """Render the full-quality video."""
    p = load_project(project)
    pipeline.run(p, project, preview=False, only=_parse_beats(beats), workers=workers, video_format=format)


@app.command()
def preview(project: Path, beats: Optional[str] = typer.Option(None, help="e.g. 2 or 1-4"),
            workers: Optional[int] = None,
            format: Optional[str] = typer.Option(None, "--format", "-f", help=FORMAT_HELP)):
    """Fast 480p preview (seconds per beat instead of minutes)."""
    p = load_project(project)
    pipeline.run(p, project, preview=True, only=_parse_beats(beats), workers=workers, video_format=format)


@app.command()
def check(project: Path,
          test: bool = typer.Option(False, "--test", help="also test-render every custom scene at 240p")):
    """Pre-render check: scenes, custom code, cue words, missing files, repeated frames."""
    from beatframe.preflight import preflight, test_custom

    p = load_project(project)
    if p.imported:
        typer.echo("✓ imported video (made outside Beatframe): there are no beats to check")
        return
    issues = preflight(p, project.parent)
    if test:
        typer.echo("testing custom scenes...")
        issues += test_custom(p, project, log=typer.echo)
    for x in issues:
        typer.echo(str(x))
    if any(x.level == "error" for x in issues):
        raise typer.Exit(1)
    typer.echo(f"✓ {len(p.beats)} beats look fine")
    from beatframe.advice import script_advice

    for tip in script_advice(p):
        typer.echo(f"! {tip}")


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


STARTER = '''\
title: "{title}"

voice:
  provider: edge             # edge | files | silent
  name: en-US-AndrewNeural
  rate: "-5%"

video: {{format: {format}, fps: 30}}   # format: long (16:9) | short (9:16)

beats:
  - text: "The first sentence the narrator says."
    scene: title_card
    chapter: "Intro"
    params: {{line1: "FIRST LINE", line2: "BIG SECOND LINE"}}

  - text: "A sentence you want to land hard."
    scene: statement
    params: {{text: "A sentence you want to land hard.", highlight: "hard"}}
'''


@app.command()
def new(name: str, title: str = typer.Option("My new video", help="Video title"),
        format: str = typer.Option("long", "--format", "-f", help="long (16:9) or short (9:16)")):
    """Create projects/<name>/<name>.yaml with a starter script."""
    folder = Path("projects") / name
    file = folder / f"{name}.yaml"
    if file.exists():
        typer.echo(f"✗ {file} already exists")
        raise typer.Exit(1)
    folder.mkdir(parents=True, exist_ok=True)
    from beatframe.formats import get_format

    file.write_text(STARTER.format(title=title, format=get_format(format).name), encoding="utf-8")
    typer.echo(f"✓ created {file}\n  next: edit it, then  beatframe preview {file}")


@app.command()
def profile(action: str = typer.Argument("show", help="show | list | use | off"),
            name: str = typer.Argument("", help="profile name for `use` (a file in profiles/)")):
    """Channel look (colours, fonts, music, picture style, voice): show, list, use <name>, off."""
    import shutil

    from beatframe import brand

    folder = brand.APP_DIR / "profiles"
    if action == "list":
        for f in sorted(folder.glob("*.yaml")):
            typer.echo(f"  {f.stem}")
    elif action == "use":
        src = folder / f"{name}.yaml"
        if not src.exists():
            typer.echo(f"✗ no profiles/{name}.yaml")
            raise typer.Exit(1)
        shutil.copy(src, brand.PROFILE_FILE)
        typer.echo(f"✓ active profile: {name} (restart Studio; beats re-render with the new look)")
    elif action == "off":
        brand.PROFILE_FILE.unlink(missing_ok=True)
        typer.echo("✓ profile removed: back to the built-in Human Unknowns look")
    else:
        typer.echo(f"channel: {brand.CHANNEL}\nprofile: {brand.PROFILE_FILE if brand.PROFILE_TEXT else 'built-in'}\n"
                   f"colours: {brand.NIGHT} {brand.PAPER} {brand.GLOW} {brand.EMBER}\nfonts: {brand.SERIF} / {brand.SANS}\n"
                   f"music: {brand.MUSIC_MOOD}")


@app.command("image-prompts")
def image_prompts(project: Path, all: bool = typer.Option(False, "--all", help="also list pictures already made")):
    """Pictures to generate for photo scenes, with file names and prompts (copyable)."""
    from beatframe import images

    p = load_project(project)
    text = images.report(p, project.parent, only_missing=not all)
    typer.echo(text)
    (project.parent / "images").mkdir(exist_ok=True)
    (project.parent / "images" / "PROMPTS.txt").write_text(text + "\n", encoding="utf-8")


@app.command()
def history(projects: Path = typer.Option(Path("projects"), help="Folder with your video projects")):
    """Made topics and recently used scenes, as text to paste into Claude."""
    from beatframe import history as hist

    typer.echo(hist.report(projects) or "no projects yet")


@app.command("save-scene")
def save_scene(project: Path, beat: int = typer.Option(..., help="number of the custom beat to save"),
               name: str = typer.Option(..., help="new scene name, e.g. gap_fill"),
               description: str = typer.Option("", help="one line: what the scene shows")):
    """Save a custom beat's code to the scene library; then use it as `scene: <name>`."""
    from beatframe.templates.custom import save_to_library

    p = load_project(project)
    if not 1 <= beat <= len(p.beats):
        typer.echo(f"✗ beat {beat} does not exist (1-{len(p.beats)})")
        raise typer.Exit(1)
    try:
        path = save_to_library(p.beats[beat - 1], name, description)
    except ValueError as e:
        typer.echo(f"✗ {e}")
        raise typer.Exit(1)
    typer.echo(f"✓ saved: {path}\n  use it as  scene: {name}   (params: {{vars: {{...}}}} if the code reads v)")


@app.command()
def clean(project: Path):
    """Delete the build cache of a project."""
    pipeline.clean(project)
    typer.echo("build cache removed")


@app.command()
def web(projects: Path = typer.Option(Path("projects"), help="Folder with your video projects"),
        port: int = 8000, no_browser: bool = False):
    """Start Beatframe Studio in your browser (http://127.0.0.1:8000)."""
    from beatframe.web.app import serve

    typer.echo(f"Beatframe Studio → http://127.0.0.1:{port}   (Ctrl+C to stop)")
    serve(projects, port=port, open_browser=not no_browser)


@app.command("scene-thumbs")
def scene_thumbs():
    """Render one still per scene template for the Templates page (takes a few minutes)."""
    from beatframe import scene_thumbs as st

    made = st.make(log=typer.echo)
    typer.echo(f"✓ {len(made)} stills in {st.OUT_DIR}")


@app.command("import")
def import_(video: Path, card: Path = typer.Argument(..., help="the import card (YAML text file)"),
            projects: Path = typer.Option(Path("projects"), help="Folder with your video projects")):
    """Import a finished video (Gemini, CapCut...) with its import card, ready to review and publish."""
    from beatframe.web.store import Store

    slug, err, notes = Store(projects).create_import(card.read_text(encoding="utf-8"), video)
    if not slug:
        typer.echo(f"✗ {err}")
        raise typer.Exit(1)
    for n in notes:
        typer.echo(f"! {n}")
    typer.echo(f"✓ imported: {projects / slug}")


@app.command()
def review(project: Path,
           format: Optional[str] = typer.Option(None, "--format", help="long | short (default: the project's)"),
           final: bool = typer.Option(False, "--final", help="review the final video, not the newest one")):
    """AI review #1: Gemini watches the video and lists what to fix, beat by beat."""
    from beatframe import review as rv

    p = load_project(project)
    try:
        res = rv.run_review(p, project, format, final=True if final else None, log=typer.echo)
    except rv.ReviewError as e:
        typer.echo(f"✗ {e}")
        raise typer.Exit(1)
    r = res["review"]
    typer.echo(f"\n{r['score']}/10 · {'tayyor' if r['verdict'] == 'ready' else 'avval tuzating'}\n{r['summary']}\n")
    typer.echo(f"Birinchi 2 soniya: {r['first_seconds']}\n")
    for it in r["issues"]:
        where = f"beat {it['beat']}" if it["beat"] else "butun video"
        typer.echo(f"[{it['severity']}] {where} · {it['time']} · {it['category']}\n  {it['problem']}\n  → {it['fix']}")
        if it["new_text"]:
            typer.echo(f'  "{it["new_text"]}"')
    typer.echo(f"\n✓ saqlandi: {rv.review_file(project.parent / 'output', format or p.video.format)}")


@app.command()
def audit(project: Path):
    """AI orqali ssenariy va videoning YouTube statistikasini tahlil qilish."""
    from beatframe import audit as ai_audit
    ai_audit.run_audit(project)


if __name__ == "__main__":
    app()
