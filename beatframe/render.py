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
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from beatframe.formats import frame_size
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
    words: list = field(default_factory=list)       # voice word timings (sent only to custom scenes)
    fallback: tuple | None = None                   # (template, params) to use if a custom scene fails
    error: str = ""                                 # set when the fallback had to be used
    stats: dict = field(default_factory=dict)       # measured cost of an uncached render


class RenderCancelled(RuntimeError):
    """The user stopped the render; finished clips stay cached."""


def _source_hash(template: str) -> str:
    cls = get_template(template)
    mod_src = inspect.getsource(sys.modules[cls.__module__])
    src = mod_src + inspect.getsource(base_mod)
    from beatframe import brand
    src += getattr(cls, "library_source", "") + brand.PROFILE_TEXT   # saved code; the channel profile   # scene-library templates: their saved code
    if "templates.kit" in mod_src:          # bright templates share the kit: its edits re-render them
        from beatframe.templates import kit
        src += inspect.getsource(kit)
    if "templates.sci" in mod_src:          # science-library templates share the sci kit
        from beatframe.templates import sci
        src += inspect.getsource(sci)
    return hashlib.sha1(src.encode()).hexdigest()[:10]


def clip_key(job: ClipJob) -> str:
    parts = [job.template, job.params, round(job.duration, 2), job.width, job.height, job.fps,
             _source_hash(job.template)]
    if job.words:           # only custom scenes get words, so other clips keep their old cache keys
        parts.append([[w.get("word"), round(float(w.get("start", 0)), 2)] for w in job.words])
    payload = json.dumps(parts, sort_keys=True)
    return hashlib.sha1(payload.encode()).hexdigest()[:12]


RUNNER = '''\
import json
from manim import config
from beatframe.templates.base import BeatScene

config.frame_width, config.frame_height = {frame_width!r}, {frame_height!r}
# Bounded frame queue: Manim's serial encoder keeps an unbounded queue of raw frames, and a long,
# simple animation renders frames faster than they are encoded (measured: 1.1 GB peak at 1080p).
# Capping it at 12 frames makes the renderer wait for the encoder instead (about 100 MB at 1080p).
try:
    import manim.scene.scene_file_writer as _sfw
    _job_init = _sfw._PartialMovieEncodeJob.__init__
    def _bounded(self, *a, frame_queue_size=0, **k):
        _job_init(self, *a, frame_queue_size=frame_queue_size or {queue}, **k)
    _sfw._PartialMovieEncodeJob.__init__ = _bounded
except (ImportError, AttributeError):   # other Manim versions: keep their default
    pass

class Beat(BeatScene):
    template_name = {template!r}
    params = json.loads({params!r})
    beat_duration = {duration}
    seed = {seed}
    words = json.loads({words!r})
'''


def failed_marker(job: ClipJob, clips_dir: Path) -> Path:
    return clips_dir / f"{job.index:03d}_{clip_key(job)}.failed.txt"


def render_clip(job: ClipJob, clips_dir: Path, cancel: threading.Event | None = None) -> Path:
    """Render one beat. A custom scene that fails falls back to job.fallback (the error is kept in
    job.error and in NNN_<key>.failed.txt, so the same broken code is not re-rendered every time)."""
    if not job.fallback:
        return _render(job, clips_dir, cancel)
    marker = failed_marker(job, clips_dir)
    if marker.exists():
        job.error = marker.read_text(encoding="utf-8")
    else:
        try:
            return _render(job, clips_dir, cancel)
        except RenderCancelled:
            raise
        except RuntimeError as e:
            job.error = str(e)
            clips_dir.mkdir(parents=True, exist_ok=True)
            for old in clips_dir.glob(f"{job.index:03d}_*.failed.txt"):
                old.unlink()
            marker.write_text(job.error, encoding="utf-8")
    template, params = job.fallback
    backup = ClipJob(job.index, template, params, job.duration, job.width, job.height, job.fps)
    out = _render(backup, clips_dir, cancel)
    job.stats = backup.stats
    return out


def _run_manim(cmd: list[str], nice: int, cancel: threading.Event | None) -> tuple[int, str, dict]:
    """Run Manim at low priority; return (exit code, stderr, measured cost). Killed on cancel."""
    def lower():                      # runs in the child before exec
        try:
            os.nice(nice)
        except OSError:
            pass
    t0 = time.monotonic()
    err_file = tempfile.TemporaryFile(mode="w+")
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=err_file, text=True,
                            preexec_fn=lower if nice and os.name == "posix" else None)
    killed = False
    while True:
        if cancel is not None and cancel.is_set() and not killed:
            killed = True
            try:
                os.kill(proc.pid, 9)       # not proc.kill(): it would reap the child before wait4 can measure it
            except OSError:
                pass
        if hasattr(os, "wait4"):
            try:
                pid, status, ru = os.wait4(proc.pid, os.WNOHANG)
            except ChildProcessError:      # already reaped elsewhere
                ru = None
                proc.returncode = proc.returncode if proc.returncode is not None else -9
                break
            if pid:
                proc.returncode = os.waitstatus_to_exitcode(status)
                break
        else:                         # pragma: no cover - Windows
            ru = None
            if proc.poll() is not None:
                break
        time.sleep(0.05)
    wall = time.monotonic() - t0
    err_file.seek(0)
    stderr = err_file.read()
    err_file.close()
    stats = {"seconds": round(wall, 2)}
    if ru is not None:
        cpu = ru.ru_utime + ru.ru_stime
        stats.update(cpu_seconds=round(cpu, 2), cpu_percent=round(100 * cpu / max(wall, 1e-3)),
                     peak_rss_mb=round(ru.ru_maxrss / 1024, 1))   # Linux reports KiB
    if cancel is not None and cancel.is_set():
        raise RenderCancelled("render stopped")
    return proc.returncode, stderr, stats


def _render(job: ClipJob, clips_dir: Path, cancel: threading.Event | None = None) -> Path:
    clips_dir.mkdir(parents=True, exist_ok=True)
    key = clip_key(job)
    out = clips_dir / f"{job.index:03d}_{key}.mp4"
    if out.exists():
        return out
    for old in clips_dir.glob(f"{job.index:03d}_*.mp4"):
        old.unlink()

    fw, fh = frame_size(job.width, job.height, get_template(job.template).vertical_width)
    with tempfile.TemporaryDirectory(prefix="beatframe_") as tmp:
        tmp = Path(tmp)
        runner = tmp / f"beat_{job.index:03d}.py"
        runner.write_text(
            RUNNER.format(template=job.template, params=json.dumps(job.params),
                          duration=job.duration, seed=job.index * 13 + 7,
                          words=json.dumps(job.words),
                          frame_width=fw, frame_height=fh, queue=12),
            encoding="utf-8",
        )
        cmd = [
            sys.executable, "-m", "manim", "render", str(runner), "Beat",
            "-r", f"{job.width},{job.height}", "--fps", str(job.fps),
            "--media_dir", str(tmp / "media"), "-o", "clip",
            "--disable_caching", "--progress_bar", "none", "-v", "WARNING",
        ]
        from beatframe import renderconf
        code, stderr, stats = _run_manim(cmd, renderconf.load().nice, cancel)
        if code != 0:
            raise RuntimeError(f"beat {job.index} ({job.template}) failed:\n{_short_error(stderr)}")
        found = list((tmp / "media").rglob("clip.mp4"))
        if not found:
            raise RuntimeError(f"beat {job.index}: manim produced no video")
        shutil.move(str(found[0]), out)
    stats.update(template=job.template, beat=job.index, width=job.width, height=job.height, fps=job.fps,
                 duration=round(job.duration, 2), mb=round(out.stat().st_size / 1e6, 2),
                 when=time.strftime("%Y-%m-%d %H:%M:%S"))
    job.stats = stats
    try:
        with (clips_dir.parent / "render_stats.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(stats) + "\n")
    except OSError:
        pass
    return out


def reuse_moved_clips(jobs: list[ClipJob], clips_dir: Path) -> int:
    """A beat that only moved (storyboard reorder) keeps its clip: the cache key does not depend on
    the beat's position, so a clip rendered under another number is copied instead of re-rendered.
    Done for all jobs before any rendering starts, so no worker deletes a clip another one needs."""
    if not clips_dir.exists():
        return 0
    by_key: dict[str, Path] = {}
    for f in clips_dir.glob("*.mp4"):
        by_key.setdefault(f.stem.split("_", 1)[-1], f)
    copied = 0
    for job in jobs:
        key = clip_key(job)
        out = clips_dir / f"{job.index:03d}_{key}.mp4"
        src = by_key.get(key)
        if not out.exists() and src is not None and src != out:
            tmp = out.with_suffix(".tmp")
            shutil.copyfile(src, tmp)
            tmp.replace(out)
            copied += 1
    return copied


def _short_error(stderr: str) -> str:
    """The useful end of a Manim traceback; for custom code, from its own line onwards."""
    i = stderr.find('File "<custom beat>"')
    return (stderr[i:] if i >= 0 else stderr)[-3000:].strip()


def _run_one(job: ClipJob, clips_dir: Path, on_start: Callable[[ClipJob], None] | None,
             cancel: threading.Event | None = None) -> Path:
    if cancel is not None and cancel.is_set():
        raise RenderCancelled("render stopped")
    if on_start:
        on_start(job)
    return render_clip(job, clips_dir, cancel)


def render_all(
    jobs: list[ClipJob],
    clips_dir: Path,
    workers: int | None = None,
    on_done: Callable[[ClipJob, Path, bool], None] | None = None,
    on_start: Callable[[ClipJob], None] | None = None,
    cancel: threading.Event | None = None,
) -> dict[int, Path]:
    """Render every job (cached clips are reused). `workers` defaults to the laptop setting
    (renderconf: 1 Manim process at a time); `cancel` stops after killing the running clip."""
    from beatframe import renderconf
    workers = workers or renderconf.load().workers
    reuse_moved_clips(jobs, clips_dir)
    results: dict[int, Path] = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {}
        for job in jobs:
            cached = (clips_dir / f"{job.index:03d}_{clip_key(job)}.mp4").exists() and not (
                job.fallback and failed_marker(job, clips_dir).exists())
            futs[pool.submit(_run_one, job, clips_dir, on_start, cancel)] = (job, cached)
        for fut in as_completed(futs):
            job, cached = futs[fut]
            try:
                results[job.index] = fut.result()
            except RenderCancelled:
                for f in futs:
                    f.cancel()
                raise
            if on_done:
                on_done(job, results[job.index], cached)
    return results
