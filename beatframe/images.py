"""Pictures to generate for photo scenes: one copyable list with file names and prompts.

    beatframe image-prompts project.yaml

Generate each picture (Google Flow, Gemini, ...), save it under the given name in the project
folder, render. A beat without its own prompt gets one built from its narration.
"""

from __future__ import annotations

from pathlib import Path

from beatframe.schema import Project

DEFAULT_STYLE = ("cinematic documentary still, soft volumetric light, deep navy and warm amber tones, "
                 "shallow depth of field, no text, no watermark")


def style() -> str:
    from beatframe import brand
    return getattr(brand, "IMAGE_STYLE", "") or DEFAULT_STYLE


def wanted(project: Project, project_dir: Path) -> list[dict]:
    """Every photo beat: its file, prompt and whether the file is already there."""
    out = []
    ratio = "9:16" if project.video.spec.vertical else "16:9"
    for i, b in enumerate(project.beats, 1):
        if b.scene != "photo":
            continue
        image = str(b.params.get("image") or f"images/beat_{i:03d}.png")
        path = Path(image).expanduser()
        path = path if path.is_absolute() else project_dir / path
        prompt = str(b.params.get("prompt") or "").strip() or f"A scene showing: {b.text.strip()}"
        out.append({"beat": i, "image": image, "exists": path.exists(),
                    "prompt": f"{prompt.rstrip('. ')}. {style()}. Aspect ratio {ratio}."})
    return out


def report(project: Project, project_dir: Path, only_missing: bool = True) -> str:
    items = [x for x in wanted(project, project_dir) if not (only_missing and x["exists"])]
    if not items:
        return "all pictures are in place" if wanted(project, project_dir) else "no photo scenes in this script"
    lines = [f"{len(items)} picture(s) to make for: {project.title}", ""]
    for x in items:
        lines += [f"[beat {x['beat']}] save as: {x['image']}", x["prompt"], ""]
    return "\n".join(lines).rstrip()
