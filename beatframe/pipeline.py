"""The whole run: voice -> timing -> clips -> final video and extras."""

from __future__ import annotations

import json
import math
import shutil
from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from beatframe import assemble
from beatframe.render import ClipJob, render_all
from beatframe.schema import Project
from beatframe.templates import get_template
from beatframe.templates.custom import is_custom
from beatframe import captions as captions_mod
from beatframe.tts import auto_pad, load_words, make_voice

PREVIEW_FPS = 15

Progress = Callable[[dict], None]


def output_name(kind: str, video_format: str | None = None) -> str:
    """Output file for a render kind ("preview", "final", "beat_preview") in a format.

    Long keeps the original names (final.mp4); short gets a suffix (final_short.mp4).
    """
    from beatframe.formats import get_format

    return f"{kind}{get_format(video_format).suffix}.mp4"


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


MEDIA = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg", ".mp4", ".mov", ".webm")


def resolve_media(params: dict, root: Path) -> dict:
    """Relative picture paths in params -> absolute (clips render in a temp folder), plus each file's
    change time, so replacing a picture re-renders its beat."""
    out, stamps = {}, {}
    for k, v in params.items():
        if isinstance(v, str) and v.lower().endswith(MEDIA) and "\n" not in v:
            p = Path(v).expanduser()
            p = p if p.is_absolute() else root / p
            out[k] = str(p)
            if p.exists():
                stamps[k] = int(p.stat().st_mtime)
        else:
            out[k] = v
    if stamps:
        out["_file_stamps"] = stamps
    return out


def default_image(i: int, beat) -> dict:
    """A photo beat without `image` uses images/beat_NNN.png (the name `image-prompts` gives it)."""
    if beat.scene == "photo" and not str(beat.params.get("image") or "").strip():
        return {**beat.params, "image": f"images/beat_{i:03d}.png"}
    return beat.params


def custom_extras(beat, words: list[dict]) -> dict:
    """Word timings and the fallback scene for a custom beat."""
    fb = str(beat.params.get("fallback") or "statement")
    fb_params = dict(beat.params.get("fallback_params") or {})
    if not fb_params and fb == "statement":
        fb_params = {"text": beat.text}
    return {"words": words, "fallback": (fb, fb_params)}


def run(
    project: Project,
    project_file: Path,
    preview: bool = False,
    only: list[int] | None = None,
    workers: int | None = None,
    log: Callable[[str], None] = print,
    out_name: str | None = None,
    video_format: str | None = None,
    progress: Progress | None = None,
) -> RunResult:
    """Render a project.

    video_format  "long" / "short"; overrides project.video.format for this run.
    out_name      output kind ("preview", "final", "beat_preview"); the format suffix is added.
    progress      receives {"stage": "voice"|"render"|"assemble"|"extras"|"done", "done": n,
                  "total": n, "beat": i, "template": name} as the run advances.
    """
    root = project_file.parent
    build = root / "build"
    out_dir = root / "output"
    out_dir.mkdir(parents=True, exist_ok=True)

    def report(stage: str, **kw) -> None:
        if progress:
            progress({"stage": stage, **kw})

    if project.imported:
        raise ValueError("this is an imported video: there is nothing to render (it is already output/final)")
    problems = validate(project)
    if problems:
        raise ValueError("project has problems:\n  " + "\n  ".join(problems))

    video = project.video.with_format(video_format) if video_format else project.video
    fmt = video.spec
    w, h = video.size(preview)
    fps = PREVIEW_FPS if preview else video.fps
    log(f"format: {fmt.name} ({fmt.aspect}, {w}x{h} @ {fps} fps)")

    # 1. voice + exact beat length (rounded up to whole frames)
    voices, durations, timings = [], [], []
    n_beats = len(project.beats)
    for i, b in enumerate(project.beats, 1):
        report("voice", done=i - 1, total=n_beats, beat=i)
        wav, secs = make_voice(i, b, project.voice, build / "audio", n_beats)
        nxt = project.beats[i] if i < n_beats else None
        d = max(b.min_duration, secs + auto_pad(i, b, nxt))
        d = math.ceil(d * fps) / fps
        voices.append(wav)
        durations.append(d)
        timings.append(load_words(i, b, build / "audio", secs))
    report("voice", done=n_beats, total=n_beats)
    log(f"voice ready: {len(voices)} beats, {sum(durations):.1f} s total")

    # 2. clips (custom scenes also get the voice's word timings and a fallback scene)
    jobs = [
        ClipJob(i, b.scene, resolve_media(default_image(i, b), root), durations[i - 1], w, h, fps,
                **(custom_extras(b, timings[i - 1]) if is_custom(b.scene) else {}))
        for i, b in enumerate(project.beats, 1)
        if not only or i in only
    ]
    clips_dir = build / (("clips_preview" if preview else "clips") + fmt.suffix)
    finished = {"n": 0}

    def started(job: ClipJob) -> None:
        report("render", done=finished["n"], total=len(jobs), beat=job.index, template=job.template)

    def done(job: ClipJob, path: Path, cached: bool) -> None:
        finished["n"] += 1
        report("render", done=finished["n"], total=len(jobs), beat=job.index, template=job.template, cached=cached)
        log(f"  beat {job.index:03d} {job.template:<20} {job.duration:5.1f}s {'(cached)' if cached else 'rendered'}"
            + (f"  ✗ custom code failed, used {job.fallback[0]}" if job.error else ""))

    report("render", done=0, total=len(jobs))
    clips = render_all(jobs, clips_dir, workers=workers, on_done=done, on_start=started)

    failed = {j.index: j.error for j in jobs if j.error}
    errors_file = build / "custom_errors.txt"
    if failed:
        errors_file.write_text("\n\n".join(f"=== beat {i} ===\n{e}" for i, e in sorted(failed.items())),
                               encoding="utf-8")
        log(f"! custom scenes fell back in beats {', '.join(map(str, sorted(failed)))} — errors: {errors_file}")
    elif errors_file.exists() and not only:
        errors_file.unlink()

    # 3. assemble (only beats that were rendered, in order)
    report("assemble")
    order = sorted(clips)
    sel_durs = [durations[i - 1] for i in order]
    voice_track = build / (("voice_preview" if preview else "voice") + fmt.suffix + ".wav")
    assemble.build_audio([voices[i - 1] for i in order], sel_durs, voice_track)
    audio = build / (("mix_preview" if preview else "mix") + fmt.suffix + ".wav")
    from beatframe import audio as audio_mod, brand
    starts_sel = [sum(sel_durs[:k]) for k in range(len(sel_durs))]
    audio_mod.mix(voice_track, audio, length=sum(sel_durs), starts=starts_sel,
                  chapters=[bool(project.beats[i - 1].chapter) for i in order], settings=project.audio,
                  project_dir=root, default_mood=getattr(brand, "MUSIC_MOOD", "mystery"), build_dir=build)

    kind = (out_name or ("preview" if preview else "final")).removesuffix(".mp4")
    out_video = out_dir / output_name(kind, fmt.name)
    ass = None
    if project.captions.enabled(fmt.name):
        beats_tl = [(starts_sel[k], starts_sel[k] + sel_durs[k],
                     captions_mod.align(project.beats[i - 1].text, timings[i - 1])
                     if captions_mod.beat_wants_captions(project.beats[i - 1]) else [])
                    for k, i in enumerate(order)]
        ass = build / (("captions_preview" if preview else "captions") + fmt.suffix + ".ass")
        if not captions_mod.write_ass(ass, beats_tl, project.captions, w, h):
            ass = None
    picture = [clips[i] for i in order]
    if video.transitions == "auto" and len(order) > 1:
        report("assemble", step="transitions")
        kinds_all = assemble.pick_transitions(len(project.beats), [bool(b.chapter) for b in project.beats],
                                              fmt.vertical)
        # transitions for the selected beats (a partial render uses the cuts between its own beats)
        kinds = ["fadeblack" if project.beats[i - 1].chapter else kinds_all[i - 2] for i in order[1:]]
        joined = assemble.join_with_transitions(
            picture, sel_durs, [""] + kinds, build / (("joined_preview" if preview else "joined") + fmt.suffix + ".mp4"),
            fps, d=video.transition_seconds * (0.7 if fmt.vertical else 1.0), fast=preview)
        picture = [joined]
    # build next to the old video first; only a finished render replaces it (the old one is kept for Compare)
    fresh = out_video.with_name(out_video.stem + ".new.mp4")
    assemble.build_video(picture, audio, fresh, captions=ass, fonts_dir=brand.FONT_DIR, fast=preview)
    from beatframe import versions
    versions.archive(out_video)
    fresh.replace(out_video)

    if not preview and not only:
        report("extras")
        texts = [b.text for b in project.beats]
        assemble.write_srt(texts, durations, out_dir / "subtitles.srt")
        assemble.write_chapters([b.chapter for b in project.beats], durations, out_dir / "chapters.txt")
        starts = [sum(durations[:i]) for i in range(len(durations))]
        assemble.extract_thumbs(out_video, starts, durations, out_dir / ("thumbs" + fmt.suffix))

    manifest = {
        "video": out_video.name, "format": fmt.name, "aspect": fmt.aspect, "width": w, "height": h,
        "fps": fps, "preview": preview, "beats": order, "duration": round(sum(sel_durs), 2),
        "captions": project.captions.style if ass else "off",
        "custom_fallbacks": {str(i): e.splitlines()[-1][:300] if e else "" for i, e in sorted(failed.items())},
        "timeline": [{"beat": i, "start": round(starts_sel[k], 2), "end": round(starts_sel[k] + sel_durs[k], 2)}
                     for k, i in enumerate(order)],
        "rendered_at": datetime.now().isoformat(timespec="seconds"),
    }
    (out_dir / (out_video.stem + ".json")).write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    report("done", video=out_video.name)
    log(f"done: {out_video}")
    return RunResult(out_dir, out_video, sel_durs)


def clean(project_file: Path) -> None:
    shutil.rmtree(project_file.parent / "build", ignore_errors=True)
