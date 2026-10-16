"""Import a finished video made elsewhere (Gemini, CapCut...) so Beatframe can review and publish it.

You give two things: the video file and an import card, a short YAML text with everything about it:

    source: import
    title: "You Can't Tickle Yourself"
    video: {format: short}          # short | long (the video's own shape wins if they differ)
    made_with: gemini
    description: |
      One or two sentences for YouTube.
    tags: [brain, body]
    script: |
      The full voiceover, so the AI review knows what is said.
    chapters: |                     # long videos only, optional
      00:00 Intro
      01:30 The trick

The project then looks like any rendered one: output/final.mp4 (final_short.mp4 for Shorts) with a
manifest, thumbnail candidates and chapters.txt, so AI review and Publish work unchanged.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import yaml

from beatframe.formats import get_format
from beatframe.pipeline import output_name
from beatframe.schema import Project

CARD_EXAMPLE = '''source: import
title: "You Can't Tickle Yourself"
video: {format: short}        # short (9:16) | long (16:9)
made_with: gemini
description: |
  Your brain cancels the touch it predicts. Try it right now.
tags: [brain, body, perception]
script: |
  You can't tickle yourself. Try it right now.
  Your brain predicts every move your own hand makes...
chapters: ""                  # long videos: "00:00 Intro" lines
synthetic: false              # true if it shows realistic AI people or events
'''


class ImportError_(ValueError):
    """Something wrong with the card or the video, said in plain words."""


def parse_card(text: str) -> Project:
    """The import card as a Project (source: import is added if it was left out)."""
    try:
        data = yaml.safe_load(text or "")
    except yaml.YAMLError as e:
        raise ImportError_(f"The card is not valid YAML: {e}") from None
    if not isinstance(data, dict) or not str(data.get("title") or "").strip():
        raise ImportError_("The card needs at least a title (title: \"...\").")
    data.setdefault("source", "import")
    if data["source"] != "import":
        raise ImportError_("This is a Beatframe script, not an import card. Use Create instead.")
    return Project.model_validate(data)


def probe(video: Path) -> dict:
    """Width, height, duration and codecs of a video file."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height:format=duration",
             "-of", "json", str(video)], capture_output=True, text=True, check=True).stdout
        info = json.loads(out)
    except (subprocess.CalledProcessError, ValueError):
        raise ImportError_("This file is not a video ffmpeg can read.") from None
    v = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), None)
    if not v:
        raise ImportError_("This file has no video track.")
    a = next((s for s in info.get("streams", []) if s.get("codec_type") == "audio"), None)
    return {"width": int(v["width"]), "height": int(v["height"]), "vcodec": v.get("codec_name"),
            "acodec": a.get("codec_name") if a else None,
            "duration": round(float(info.get("format", {}).get("duration") or 0), 2)}


def _place_video(src: Path, dst: Path, info: dict) -> None:
    """Copy as is when YouTube-friendly (H.264/AAC MP4), otherwise convert once."""
    if src.suffix.lower() == ".mp4" and info["vcodec"] == "h264" and info["acodec"] in ("aac", None):
        shutil.copyfile(src, dst)
        return
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-c:v", "libx264", "-preset", "medium", "-crf", "18",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(dst)],
        check=True,
    )


def _thumbs(video: Path, duration: float, out_dir: Path, n: int = 5) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for k in range(n):
        t = duration * (0.1 + 0.8 * k / max(n - 1, 1))
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1",
                        str(out_dir / f"thumb_{k + 1}.png")], check=True)


def import_video(project: Project, card_text: str, video_src: Path, folder: Path, slug: str) -> dict:
    """Write projects/<slug>/<slug>.yaml and output/final*.mp4 (+ manifest, thumbs, chapters).
    Returns what was done, including a note when the card's format was corrected from the video."""
    info = probe(video_src)
    fmt = get_format("short" if info["height"] > info["width"] else "long")
    notes = []
    if project.video.format != fmt.name:
        notes.append(f"The card said {project.video.format}, but the video is {fmt.aspect}: saved as {fmt.label}.")
        project.video = project.video.with_format(fmt.name)
    if fmt.name == "short" and info["duration"] > 180:
        notes.append("A vertical video over 3 minutes is not a Short on YouTube.")

    out = folder / "output"
    out.mkdir(parents=True, exist_ok=True)
    final = out / output_name("final", fmt.name)
    _place_video(video_src, final, info)

    text = card_text.strip() + "\n"
    if "source:" not in text:
        text = "source: import\n" + text
    if notes and "video:" in text:              # keep the user's text, but fix the format line
        text = "\n".join(f"video: {{format: {fmt.name}}}" if line.strip().startswith("video:") else line
                         for line in text.splitlines()) + "\n"
    elif notes:
        text += f"video: {{format: {fmt.name}}}\n"
    (folder / f"{slug}.yaml").write_text(text, encoding="utf-8")

    manifest = {"video": final.name, "format": fmt.name, "aspect": fmt.aspect, "width": info["width"],
                "height": info["height"], "duration": info["duration"], "source": "import",
                "made_with": project.made_with, "rendered_at": datetime.now().isoformat(timespec="seconds")}
    final.with_suffix(".json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    _thumbs(final, info["duration"], out / ("thumbs" + fmt.suffix))
    if project.chapters.strip():
        (out / "chapters.txt").write_text(project.chapters.strip() + "\n", encoding="utf-8")
    return {"format": fmt.name, "duration": info["duration"], "notes": notes}
