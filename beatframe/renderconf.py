"""Render settings for a laptop: how many Manim processes at once, their priority, preview quality.

Saved in ~/.beatframe/render.json (per computer, not per project):

    {"workers": 1, "nice": 10, "preview_preset": "eco"}

  workers         Manim processes rendering at the same time. 1 keeps a 16 GB laptop with an
                  integrated GPU responsive; raise it on a desktop. BEATFRAME_WORKERS overrides it.
  nice            OS priority of the Manim processes (0 normal .. 19 lowest). 10 lets the browser
                  and the Studio stay smooth while a render runs.
  preview_preset  eco (480p, 15 fps) | balanced (720p, 30 fps) | quality (1080p, 30 fps).
                  The final video always uses the format's full size (1080p) and its own fps.

Every uncached clip records what it cost (seconds, peak memory, CPU) in build/render_stats.jsonl,
so the numbers in the Studio are measured, not estimated.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path

def config_file() -> Path:
    return Path.home() / ".beatframe" / "render.json"

# short side in pixels, fps
PRESETS: dict[str, dict] = {
    "eco": {"label": "Eco", "short_side": 480, "fps": 15, "hint": "480p · 15 fps — fastest, lowest load"},
    "balanced": {"label": "Balanced", "short_side": 720, "fps": 30, "hint": "720p · 30 fps — smooth motion check"},
    "quality": {"label": "Quality", "short_side": 1080, "fps": 30, "hint": "1080p · 30 fps — what the final looks like"},
}


@dataclass
class RenderSettings:
    workers: int = 1
    nice: int = 10
    preview_preset: str = "eco"

    def clean(self) -> "RenderSettings":
        self.workers = max(1, min(8, int(self.workers)))
        self.nice = max(0, min(19, int(self.nice)))
        if self.preview_preset not in PRESETS:
            self.preview_preset = "eco"
        return self


def load() -> RenderSettings:
    try:
        data = json.loads(config_file().read_text(encoding="utf-8"))
        s = RenderSettings(**{k: data[k] for k in ("workers", "nice", "preview_preset") if k in data})
    except (OSError, ValueError, TypeError):
        s = RenderSettings()
    env = os.environ.get("BEATFRAME_WORKERS", "").strip()
    if env.isdigit():
        s.workers = int(env)
    return s.clean()


def save(s: RenderSettings) -> RenderSettings:
    s.clean()
    config_file().parent.mkdir(parents=True, exist_ok=True)
    config_file().write_text(json.dumps(asdict(s), indent=2), encoding="utf-8")
    return s


def preset_size(preset: str, vertical: bool) -> tuple[int, int, int]:
    """(width, height, fps) of a preset; 480p is the original 854x480 preview size."""
    p = PRESETS.get(preset, PRESETS["eco"])
    short = p["short_side"]
    long_ = {480: 854, 720: 1280, 1080: 1920}[short]
    return (short, long_, p["fps"]) if vertical else (long_, short, p["fps"])
