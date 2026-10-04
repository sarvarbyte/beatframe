"""Voice for each beat. Returns the audio file and its length in seconds.

Providers:
  edge   - free Microsoft Edge neural voices (needs internet)
  files  - your own recordings: <files_dir>/001.mp3, 002.wav, ... one per beat
  silent - no voice, length estimated from word count (for quick layout tests)
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
from pathlib import Path

from beatframe.schema import Beat, Voice

AUDIO_EXTS = (".wav", ".mp3", ".m4a", ".ogg", ".flac")


def probe_duration(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out)


def _to_wav(src: Path, dst: Path) -> None:
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-ac", "1", "-ar", "48000", str(dst)],
        check=True,
    )


def _silence(dst: Path, seconds: float) -> None:
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=48000:cl=mono",
         "-t", f"{seconds:.3f}", str(dst)],
        check=True,
    )


async def _edge(text: str, voice: Voice, dst: Path) -> None:
    import edge_tts

    await edge_tts.Communicate(text, voice.name, rate=voice.rate).save(str(dst))


def make_voice(index: int, beat: Beat, voice: Voice, audio_dir: Path) -> tuple[Path, float]:
    """Create (or reuse) the voice clip for one beat. index is 1-based."""
    audio_dir.mkdir(parents=True, exist_ok=True)
    wav = audio_dir / f"{index:03d}.wav"
    stamp = audio_dir / f"{index:03d}.txt"
    key = f"{voice.provider}|{voice.name}|{voice.rate}|{beat.text}"

    if wav.exists() and stamp.exists() and stamp.read_text(encoding="utf-8") == key:
        return wav, probe_duration(wav)

    if voice.provider == "silent":
        words = len(beat.text.split())
        _silence(wav, max(beat.min_duration, words / voice.words_per_second))
    elif voice.provider == "files":
        if not voice.files_dir:
            raise ValueError("voice.provider=files needs voice.files_dir")
        folder = Path(voice.files_dir)
        found = [folder / f"{index:03d}{ext}" for ext in AUDIO_EXTS if (folder / f"{index:03d}{ext}").exists()]
        if not found:
            raise FileNotFoundError(f"no audio for beat {index} in {folder} (expected {index:03d}.mp3 or .wav)")
        _to_wav(found[0], wav)
    elif voice.provider == "edge":
        mp3 = audio_dir / f"{index:03d}.mp3"
        asyncio.run(_edge(beat.text, voice, mp3))
        _to_wav(mp3, wav)
        mp3.unlink(missing_ok=True)
    else:  # pragma: no cover
        raise ValueError(f"unknown voice provider {voice.provider}")

    stamp.write_text(key, encoding="utf-8")
    return wav, probe_duration(wav)


def has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
