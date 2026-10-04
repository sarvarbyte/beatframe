"""The whole run: voice -> timing -> clips -> final video and extras."""

from __future__ import annotations

import math
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from beatframe import assemble
from beatframe.render import ClipJob, render_all
from beatframe.schema import Project
from beatframe.templates import get_template
from beatframe.tts import make_voice

PREVIEW = (854, 480, 15)


@dataclass
class RunResult:
    out_dir: Path
    video: Path
    durations: list[float] = field(default_factory=list)

    @property
    def total(self) -> float:
        return sum(self.durations)


def validate(project: Project) -> list[str]:
    """Return a list of human-readable problems (empty = fine)."""
    problems = []
    for i, b in enumerate(project.beats, 1):
        try:
            cls = get_template(b.scene)
            cls.Params.model_validate(b.params)
        except Exception as e:  # noqa: BLE001
            problems.append(f"beat {i}: {e}")
    return problems


def run(
    project: Project,
    project_file: Path,
    preview: bool = False,
    only: list[int] | None = None,
    workers: int | None = None,
    log: Callable[[str], None] = print,
) -> RunResult:
    root = project_file.parent
    build = root / "build"
    out_dir = root / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    problems = validate(project)
    if problems:
        raise ValueError("project has problems:\n  " + "\n  ".join(problems))

    w, h, fps = PREVIEW if preview else (project.video.width, project.video.height, project.video.fps)

    # 1. voice + exact beat length (rounded up to whole frames)
    voices, durations = [], []
    for i, b in enumerate(project.beats, 1):
        wav, secs = make_voice(i, b, project.voice, build / "audio")
        d = max(b.min_duration, secs + b.pad)
        d = math.ceil(d * fps) / fps
        voices.append(wav)
        durations.append(d)
    log(f"voice ready: {len(voices)} beats, {sum(durations):.1f} s total")

    # 2. clips
    jobs = [
        ClipJob(i, b.scene, b.params, durations[i - 1], w, h, fps)
        for i, b in enumerate(project.beats, 1)
        if not only or i in only
    ]
    clips_dir = build / ("clips_preview" if preview else "clips")

    def done(job: ClipJob, path: Path, cached: bool) -> None:
        log(f"  beat {job.index:03d} {job.template:<20} {job.duration:5.1f}s {'(cached)' if cached else 'rendered'}")

    clips = render_all(jobs, clips_dir, workers=workers, on_done=done)

    # 3. assemble (only beats that were rendered, in order)
    order = sorted(clips)
    sel_durs = [durations[i - 1] for i in order]
    audio = build / ("voice_preview.wav" if preview else "voice.wav")
    assemble.build_audio([voices[i - 1] for i in order], sel_durs, audio)

    name = "preview.mp4" if preview else "final.mp4"
    video = out_dir / name
    assemble.build_video([clips[i] for i in order], audio, video)

    if not preview and not only:
        texts = [b.text for b in project.beats]
        assemble.write_srt(texts, durations, out_dir / "subtitles.srt")
        assemble.write_chapters([b.chapter for b in project.beats], durations, out_dir / "chapters.txt")
        starts = [sum(durations[:i]) for i in range(len(durations))]
        assemble.extract_thumbs(video, starts, durations, out_dir / "thumbs")
    log(f"done: {video}")
    return RunResult(out_dir, video, sel_durs)


def clean(project_file: Path) -> None:
    shutil.rmtree(project_file.parent / "build", ignore_errors=True)
