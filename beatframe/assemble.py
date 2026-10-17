"""Join beat clips and voice into the final video, plus subtitles and chapters."""

from __future__ import annotations

import subprocess
import textwrap
from pathlib import Path


def _ts_srt(t: float) -> str:
    ms = int(round(t * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _ts_chapter(t: float) -> str:
    t = int(t)
    h, rem = divmod(t, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def build_audio(voice_files: list[Path], durations: list[float], out: Path) -> None:
    """Each voice clip is padded with silence to its beat length, then all are joined."""
    inputs, chains = [], []
    for i, (f, d) in enumerate(zip(voice_files, durations)):
        inputs += ["-i", str(f)]
        chains.append(f"[{i}:a]aresample=48000,apad,atrim=0:{d:.3f},asetpts=PTS-STARTPTS[a{i}]")
    joined = "".join(f"[a{i}]" for i in range(len(voice_files)))
    graph = ";".join(chains) + f";{joined}concat=n={len(voice_files)}:v=0:a=1[out]"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", graph, "-map", "[out]",
         "-ac", "2", str(out)],
        check=True,
    )


def _filter_path(p: Path) -> str:
    """A file path as an ffmpeg filter option value (quoted, so spaces and colons are safe)."""
    path = str(Path(p).resolve())
    if "'" in path:
        raise ValueError(f"captions can't be burned in from a folder whose name has a ' in it: {path}")
    return f"'{path}'"


def build_video(clips: list[Path], audio: Path, out: Path, loudnorm: bool = True,
                captions: Path | None = None, fonts_dir: Path | None = None, fast: bool = False) -> None:
    """Join the clips under the audio. With captions (.ass) the picture is re-encoded once to burn them in;
    without, the clips are copied as they are."""
    listing = out.with_suffix(".txt")
    listing.write_text("".join(f"file '{c.resolve()}'\n" for c in clips), encoding="utf-8")
    af = ["-af", "loudnorm=I=-14:TP=-1.5:LRA=11"] if loudnorm else []
    if captions:
        vf = f"ass=filename={_filter_path(captions)}"
        if fonts_dir:
            vf += f":fontsdir={_filter_path(fonts_dir)}"
        video = ["-vf", vf, "-c:v", "libx264", "-preset", "veryfast" if fast else "medium",
                 "-crf", "18", "-pix_fmt", "yuv420p"]
    else:
        video = ["-c:v", "copy"]
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
         "-i", str(audio), "-map", "0:v", "-map", "1:a", *video, *af,
         "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out)],
        check=True,
    )
    listing.unlink(missing_ok=True)


# ---- transitions between beats ----------------------------------------------------------
LONG_KINDS = ["fade", "smoothleft", "dissolve", "wipeleft", "smoothup", "circleopen", "slideleft", "radial"]
SHORT_KINDS = ["slideleft", "slideup", "smoothleft", "fade", "wipeup", "smoothup"]
CHUNK = 24          # clips per ffmpeg run (keeps memory low on long videos; chunks meet with a cut)


def pick_transitions(n: int, chapters: list[bool], vertical: bool, seed: int = 7) -> list[str]:
    """One transition for each of the n-1 cuts: chapter starts dip to black, the rest vary and never
    repeat twice in a row."""
    import random

    rnd = random.Random(seed)
    kinds = SHORT_KINDS if vertical else LONG_KINDS
    out, last = [], ""
    for k in range(1, n):
        if chapters[k]:
            kind = "fadeblack"
        else:
            kind = rnd.choice([x for x in kinds if x != last])
        out.append(kind)
        last = kind
    return out


def join_with_transitions(clips: list[Path], durations: list[float], kinds: list[str], out: Path,  # kinds[k]: into clip k
                          fps: int, d: float = 0.3, fast: bool = False) -> Path:
    """Join clips with xfade transitions while every beat still starts at its exact time (so the
    voice stays in sync): each clip but the last is held on its last frame for d seconds, and the
    next one fades in over that tail. The result is exactly sum(durations) long."""
    if len(clips) == 1:
        return clips[0]
    parts = []
    for c0 in range(0, len(clips), CHUNK):
        idx = list(range(c0, min(c0 + CHUNK, len(clips))))
        part = out if len(clips) <= CHUNK else out.with_name(f"{out.stem}_part{c0 // CHUNK:02d}.mp4")
        inputs, chains = [], []
        for j, k in enumerate(idx):
            inputs += ["-i", str(clips[k])]
            hold = f",tpad=stop_mode=clone:stop_duration={d:.3f}" if j < len(idx) - 1 else ""
            chains.append(f"[{j}:v]fps={fps},settb=AVTB,format=yuv420p,"
                          f"trim=duration={durations[k]:.3f},setpts=PTS-STARTPTS{hold}[v{j}]")
        prev, t = "v0", 0.0
        for j in range(1, len(idx)):
            t += durations[idx[j - 1]]
            tag = f"x{j}"
            kind = kinds[idx[j]] or "fade"
            dur = d if kind != "cut" else 1 / fps          # a hard cut: a one-frame fade
            chains.append(f"[{prev}][v{j}]xfade=transition={'fade' if kind == 'cut' else kind}:duration={dur:.3f}:offset={t:.3f}[{tag}]")
            prev = tag
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(chains), "-map", f"[{prev}]",
             "-c:v", "libx264", "-preset", "veryfast" if fast else "medium", "-crf", "18", "-pix_fmt", "yuv420p",
             "-r", str(fps), str(part)],
            check=True,
        )
        parts.append(part)
    if len(parts) == 1:
        return parts[0]
    listing = out.with_suffix(".parts.txt")
    listing.write_text("".join(f"file '{p.resolve()}'\n" for p in parts), encoding="utf-8")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
                    "-c", "copy", str(out)], check=True)
    for p in parts:
        p.unlink(missing_ok=True)
    listing.unlink(missing_ok=True)
    return out


def write_srt(texts: list[str], durations: list[float], out: Path) -> None:
    t, blocks = 0.0, []
    for i, (txt, d) in enumerate(zip(texts, durations), 1):
        lines = textwrap.wrap(txt, 42)
        blocks.append(f"{i}\n{_ts_srt(t)} --> {_ts_srt(t + d - 0.05)}\n" + "\n".join(lines) + "\n")
        t += d
    out.write_text("\n".join(blocks), encoding="utf-8")


def write_chapters(chapters: list[str | None], durations: list[float], out: Path) -> None:
    t, rows = 0.0, []
    for name, d in zip(chapters, durations):
        if name:
            rows.append(f"{_ts_chapter(t)} {name}")
        t += d
    if rows and not rows[0].startswith("00:00"):
        rows.insert(0, "00:00 Intro")
    out.write_text("\n".join(rows) + ("\n" if rows else ""), encoding="utf-8")


def extract_thumbs(video: Path, starts: list[float], durations: list[float], out_dir: Path, n: int = 5) -> None:
    """Grab one frame from the middle of the n longest beats as thumbnail candidates."""
    out_dir.mkdir(parents=True, exist_ok=True)
    order = sorted(range(len(durations)), key=lambda i: -durations[i])[:n]
    for rank, i in enumerate(sorted(order), 1):
        t = starts[i] + durations[i] * 0.6
        subprocess.run(
            ["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1",
             str(out_dir / f"thumb_{rank}_beat{i + 1:03d}.png")],
            check=True,
        )
