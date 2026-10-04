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


def build_video(clips: list[Path], audio: Path, out: Path, loudnorm: bool = True) -> None:
    listing = out.with_suffix(".txt")
    listing.write_text("".join(f"file '{c.resolve()}'\n" for c in clips), encoding="utf-8")
    af = ["-af", "loudnorm=I=-14:TP=-1.5:LRA=11"] if loudnorm else []
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(listing),
         "-i", str(audio), "-map", "0:v", "-map", "1:a", "-c:v", "copy", *af,
         "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", str(out)],
        check=True,
    )
    listing.unlink(missing_ok=True)


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
