"""One still per scene template (with its default settings) for the Templates page.

    beatframe scene-thumbs     -> beatframe/web/static/scenes/<name>.png  (still)
                                  beatframe/web/static/scenes/<name>.mp4  (short loop for the library)

Real renders of each template's default settings at 640x360, 15 fps; run again after changing a
template's look. `only` limits it to some templates.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Callable

from beatframe.render import ClipJob, render_all
from beatframe.templates import REGISTRY, get_template

OUT_DIR = Path(__file__).parent / "web" / "static" / "scenes"


def make(log: Callable[[str], None] = print, only: list[str] | None = None, seconds: float = 4.5) -> list[Path]:
    get_template(next(iter(REGISTRY), "title_card"))      # import every template module
    names = [n for n in sorted(REGISTRY) if not only or n in only]
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    jobs = [ClipJob(i, name, {}, seconds, 640, 360, 15) for i, name in enumerate(names, 1)]
    with tempfile.TemporaryDirectory(prefix="beatframe_scenes_") as tmp:
        clips = render_all(jobs, Path(tmp), on_done=lambda j, p, c: log(f"  {j.template}"))
        made = []
        for job in jobs:
            clip, png = clips.get(job.index), OUT_DIR / f"{job.template}.png"
            if clip is None:
                continue
            # 70% in: the scene is fully built, before the end-of-beat camera push gets too far
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{seconds * 0.7:.2f}", "-i", str(clip), "-frames:v", "1",
                            str(png)], check=True)
            loop = OUT_DIR / f"{job.template}.mp4"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(clip), "-an", "-c:v", "libx264", "-crf", "30",
                            "-preset", "veryfast", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(loop)], check=True)
            made += [png, loop]
    return made
