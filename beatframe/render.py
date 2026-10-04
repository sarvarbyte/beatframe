"""Render one Manim clip per beat, with caching and parallel workers."""

from __future__ import annotations

import hashlib
import inspect
import json
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from beatframe.templates import base as base_mod
from beatframe.templates import get_template


@dataclass
class ClipJob:
    index: int            # 1-based beat number
    template: str
    params: dict
    duration: float
    width: int
    height: int
    fps: int


def _source_hash(template: str) -> str:
    cls = get_template(template)
    src = inspect.getsource(sys.modules[cls.__module__]) + inspect.getsource(base_mod)
    return hashlib.sha1(src.encode()).hexdigest()[:10]


def clip_key(job: ClipJob) -> str:
    payload = json.dumps(
        [job.template, job.params, round(job.duration, 2), job.width, job.height, job.fps,
         _source_hash(job.template)],
        sort_keys=True,
    )
    return hashlib.sha1(payload.encode()).hexdigest()[:12]


RUNNER = '''\
from beatframe.templates.base import BeatScene

class Beat(BeatScene):
    template_name = {template!r}
    params = {params}
    beat_duration = {duration}
    seed = {seed}
'''


def render_clip(job: ClipJob, clips_dir: Path) -> Path:
    clips_dir.mkdir(parents=True, exist_ok=True)
    key = clip_key(job)
    out = clips_dir / f"{job.index:03d}_{key}.mp4"
    if out.exists():
        return out
    for old in clips_dir.glob(f"{job.index:03d}_*.mp4"):
        old.unlink()

    with tempfile.TemporaryDirectory(prefix="beatframe_") as tmp:
        tmp = Path(tmp)
        runner = tmp / f"beat_{job.index:03d}.py"
        runner.write_text(
            RUNNER.format(template=job.template, params=json.dumps(job.params),
                          duration=job.duration, seed=job.index * 13 + 7),
            encoding="utf-8",
        )
        cmd = [
            sys.executable, "-m", "manim", "render", str(runner), "Beat",
            "-r", f"{job.width},{job.height}", "--fps", str(job.fps),
            "--media_dir", str(tmp / "media"), "-o", "clip",
            "--disable_caching", "--progress_bar", "none", "-v", "WARNING",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"beat {job.index} ({job.template}) failed:\n{res.stderr[-3000:]}")
        found = list((tmp / "media").rglob("clip.mp4"))
        if not found:
            raise RuntimeError(f"beat {job.index}: manim produced no video")
        shutil.move(str(found[0]), out)
    return out


def render_all(
    jobs: list[ClipJob],
    clips_dir: Path,
    workers: int | None = None,
    on_done: Callable[[ClipJob, Path, bool], None] | None = None,
) -> dict[int, Path]:
    workers = workers or max(1, (os.cpu_count() or 2) // 2)
    results: dict[int, Path] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {}
        for job in jobs:
            cached = (clips_dir / f"{job.index:03d}_{clip_key(job)}.mp4").exists()
            futs[pool.submit(render_clip, job, clips_dir)] = (job, cached)
        for fut in as_completed(futs):
            job, cached = futs[fut]
            results[job.index] = fut.result()
            if on_done:
                on_done(job, results[job.index], cached)
    return results
