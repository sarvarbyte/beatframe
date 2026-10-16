"""One still per scene template (with its default settings) for the Templates page.

    beatframe scene-thumbs     -> beatframe/web/static/scenes/<name>.png

Rendered once at 640x360; run again after changing a template's look.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path
from typing import Callable

from beatframe.render import ClipJob, render_all
from beatframe.templates import REGISTRY, get_template

OUT_DIR = Path(__file__).parent / "web" / "static" / "scenes"


def make(log: Callable[[str], None] = print) -> list[Path]:
    get_template(next(iter(REGISTRY), "title_card"))      # import every template module
    names = sorted(REGISTRY)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    jobs = [ClipJob(i, name, {}, 3.0, 640, 360, 15) for i, name in enumerate(names, 1)]
    with tempfile.TemporaryDirectory(prefix="beatframe_scenes_") as tmp:
        clips = render_all(jobs, Path(tmp), on_done=lambda j, p, c: log(f"  {j.template}"))
        made = []
        for job in jobs:
            clip, png = clips.get(job.index), OUT_DIR / f"{job.template}.png"
            if clip is None:
                continue
            # 85% in: the scene is fully built, before the end-of-beat camera push gets too far
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "2.5", "-i", str(clip), "-frames:v", "1",
                            str(png)], check=True)
            made.append(png)
    return made
