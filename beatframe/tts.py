"""Voice for each beat. Returns the audio file and its length in seconds.

Providers:
  edge   - free Microsoft Edge neural voices (needs internet). With style "auto" (default) every
           beat gets its own small change of speed and pitch from what the sentence is (hook,
           question, punchline, chapter start...), so the narration never sounds like one flat line.
  kokoro - Kokoro-82M, a free open-source AI voice that runs on this computer (no internet after the
           first download). Much more natural than edge. It lives in its own Python (~/.kokoro);
           install once with ovoz_ornat.sh.
  files  - your own recordings: <files_dir>/001.mp3, 002.wav, ... one per beat
  silent - no voice, length estimated from word count (for quick layout tests)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import re
import shutil
import subprocess
import wave
from pathlib import Path

from beatframe.schema import Beat, Voice

AUDIO_EXTS = (".wav", ".mp3", ".m4a", ".ogg", ".flac")


def probe_duration(path: Path) -> float:
    path = Path(path)
    if path.suffix.lower() == ".wav":
        try:
            with wave.open(str(path), "rb") as w:
                return w.getnframes() / float(w.getframerate())
        except wave.Error:
            pass
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


# ---- expressive delivery ----------------------------------------------------------------
def _pct(s: str) -> int:
    m = re.match(r"\s*([+-]?\d+)\s*%", s or "")
    return int(m.group(1)) if m else 0


def _hz(s: str) -> int:
    m = re.match(r"\s*([+-]?\d+)\s*Hz", s or "", re.I)
    return int(m.group(1)) if m else 0


def delivery(index: int, beat: Beat, voice: Voice, total: int = 0) -> tuple[str, str]:
    """Speed and pitch for one beat (edge-tts strings like "+4%", "-2Hz").

    style "flat" keeps the project's rate/pitch on every beat (the old behaviour).
    style "auto" reads the sentence like a storyteller would:
      * the hook (beat 1) and exclamations come a little faster and brighter,
      * very short lines ("And then, nothing.") are slowed down so they land,
      * a new chapter starts slower and lower,
      * questions slow down slightly,
      * long explanations speed up a touch so they don't drag,
      * plus a small, repeatable variation per beat so no two beats sound identical.
    """
    rate, pitch = _pct(voice.rate), _hz(voice.pitch)
    if voice.style == "flat":
        return f"{rate:+d}%", f"{pitch:+d}Hz"
    text = beat.text.strip()
    words = len(text.split())
    r, p = 0, 0
    if index == 1:
        r, p = r + 5, p + 2
    if beat.chapter and index > 1:
        r, p = r - 5, p - 2
    if text.endswith("!"):
        r, p = r + 5, p + 3
    elif text.endswith("?"):
        r, p = r - 3, p + 1
    if words <= 6:
        r, p = r - 8, p - 2
    elif words >= 26:
        r += 4
    # repeatable jitter: same beat text -> same delivery (keeps the voice cache valid)
    h = int(hashlib.md5(f"{index}|{text}".encode()).hexdigest()[:6], 16)
    r += (h % 7) - 3            # -3..+3 %
    p += ((h >> 4) % 5) - 2     # -2..+2 Hz
    k = voice.expressiveness
    rate_out = int(round(rate + r * k))
    pitch_out = int(round(pitch + p * k))
    return f"{max(-30, min(30, rate_out)):+d}%", f"{max(-20, min(20, pitch_out)):+d}Hz"


def auto_pad(index: int, beat: Beat, next_beat: Beat | None) -> float:
    """Breathing room after a beat: longer after questions, punchlines and before a new chapter."""
    if beat.pad != Beat.model_fields["pad"].default:
        return beat.pad                       # set by hand in the script: keep it
    text = beat.text.strip()
    pad = 0.3
    if text.endswith("?"):
        pad = 0.6
    elif len(text.split()) <= 6 or text.endswith(("...", "…")):
        pad = 0.55
    if next_beat is not None and next_beat.chapter:
        pad += 0.45
    return pad


async def _edge(text: str, voice: Voice, rate: str, pitch: str, dst: Path, words_dst: Path) -> None:
    import edge_tts

    try:
        comm = edge_tts.Communicate(text, voice.name, rate=rate, pitch=pitch, boundary="WordBoundary")
    except TypeError:       # edge-tts < 7 always sends word boundaries
        comm = edge_tts.Communicate(text, voice.name, rate=rate, pitch=pitch)
    words = []
    with open(dst, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":      # offset and duration in 100 ns ticks
                start = chunk["offset"] / 1e7
                words.append({"word": chunk["text"], "start": round(start, 3),
                              "end": round(start + chunk["duration"] / 1e7, 3)})
    words_dst.write_text(json.dumps(words), encoding="utf-8")


# ---- word timings (for captions) ---------------------------------------------------------
def words_file(index: int, audio_dir: Path) -> Path:
    return audio_dir / f"{index:03d}.words.json"


def estimate_words(text: str, seconds: float) -> list[dict]:
    """Spread the words over the clip by their length (voices without timings: files, silent)."""
    tokens = text.split()
    if not tokens or seconds <= 0:
        return []
    start, end = min(0.1, seconds * 0.05), max(seconds - 0.1, seconds * 0.95)
    weights = [len(t) + 2 for t in tokens]
    per = (end - start) / sum(weights)
    out, t = [], start
    for tok, w in zip(tokens, weights):
        out.append({"word": tok, "start": round(t, 3), "end": round(t + w * per, 3)})
        t += w * per
    return out


def load_words(index: int, beat: Beat, audio_dir: Path, seconds: float) -> list[dict]:
    """Word timings of one beat's voice: from the TTS when it gave them, otherwise estimated."""
    f = words_file(index, audio_dir)
    try:
        words = json.loads(f.read_text(encoding="utf-8"))
        if words:
            return words
    except (OSError, ValueError):
        pass
    return estimate_words(beat.text, seconds)


def transcribe_words(wav: Path, dst: Path) -> bool:
    """Word timings of a recording with faster-whisper (optional: pip install faster-whisper).
    Returns False (and leaves timings to be estimated) when it is not installed or fails."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        return False
    try:
        model = _KOKORO.get("whisper") or WhisperModel("base.en", device="cpu", compute_type="int8")
        _KOKORO["whisper"] = model
        segments, _ = model.transcribe(str(wav), word_timestamps=True, language="en")
        words = [{"word": w.word.strip(), "start": round(w.start, 3), "end": round(w.end, 3)}
                 for seg in segments for w in (seg.words or [])]
    except Exception:  # noqa: BLE001
        return False
    if words:
        dst.write_text(json.dumps(words), encoding="utf-8")
    return bool(words)


# ---- kokoro (local AI voice) ------------------------------------------------------------
_KOKORO: dict = {}
KOKORO_ENV = Path.home() / ".kokoro" / "bin" / "python"      # separate Python 3.12 made by ovoz_ornat.sh

KOKORO_HELP = ("Kokoro is not installed. Run once in a terminal:\n"
               "  bash ~/Desktop/\"YouTube content\"/beatframe2.0/ovoz_ornat.sh")


def _kokoro_worker():
    """Start (once) the Kokoro worker in its own Python and return the process."""
    proc = _KOKORO.get("proc")
    if proc is not None and proc.poll() is None:
        return proc
    if not KOKORO_ENV.exists():
        raise RuntimeError(KOKORO_HELP)
    worker = Path(__file__).with_name("kokoro_worker.py")
    proc = subprocess.Popen([str(KOKORO_ENV), str(worker)], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            text=True, bufsize=1)
    first = proc.stdout.readline().strip()
    if first != "ready":
        raise RuntimeError(f"Kokoro did not start: {first or 'no answer'}\n{KOKORO_HELP}")
    _KOKORO["proc"] = proc
    return proc


def _kokoro(text: str, voice: Voice, speed: float, dst: Path, words_dst: Path, retry: bool = True) -> None:
    proc = _kokoro_worker()
    job = {"text": text, "voice": voice.name, "speed": speed, "out": str(dst), "words": str(words_dst)}
    proc.stdin.write(json.dumps(job) + "\n")
    proc.stdin.flush()
    answer = proc.stdout.readline().strip()
    if answer != "ok":
        raise RuntimeError(f"Kokoro failed on: {text[:60]}… ({answer or 'worker stopped'})")
    if not words_dst.exists() and retry:     # a worker started before word timings existed: restart it
        proc.terminate()
        _KOKORO.pop("proc", None)
        _kokoro(text, voice, speed, dst, words_dst, retry=False)


# Older, flatter edge voices are swapped for their more natural "Multilingual" versions.
UPGRADE = {
    "en-US-ChristopherNeural": "en-US-BrianMultilingualNeural",
    "en-US-AndrewNeural": "en-US-AndrewMultilingualNeural",
    "en-US-BrianNeural": "en-US-BrianMultilingualNeural",
    "en-US-AvaNeural": "en-US-AvaMultilingualNeural",
    "en-US-EmmaNeural": "en-US-EmmaMultilingualNeural",
}


def effective_voice(voice: Voice) -> Voice:
    """The voice actually used: ovoz.txt in the app folder can switch every project at once
    (e.g. "kokoro am_michael" or "edge en-US-AndrewMultilingualNeural"); old flat edge voices are upgraded."""
    from beatframe import brand

    f = Path(getattr(brand, "APP_DIR", Path(__file__).resolve().parent.parent)) / "ovoz.txt"
    try:
        words = f.read_text(encoding="utf-8").split()
    except OSError:
        words = str(getattr(brand, "VOICE", "") or "").split()     # the channel profile's voice
    if words and words[0] in ("edge", "kokoro") and voice.provider in ("edge", "kokoro"):
        voice = voice.model_copy(update={"provider": words[0], "name": words[1] if len(words) > 1 else
                                         ("am_michael" if words[0] == "kokoro" else voice.name)})
    if voice.provider == "edge" and voice.upgrade and voice.name in UPGRADE:
        voice = voice.model_copy(update={"name": UPGRADE[voice.name]})
    return voice


def make_voice(index: int, beat: Beat, voice: Voice, audio_dir: Path, total: int = 0) -> tuple[Path, float]:
    """Create (or reuse) the voice clip for one beat. index is 1-based."""
    audio_dir.mkdir(parents=True, exist_ok=True)
    voice = effective_voice(voice)
    wav = audio_dir / f"{index:03d}.wav"
    stamp = audio_dir / f"{index:03d}.txt"
    rate, pitch = delivery(index, beat, voice, total)
    key = f"{voice.provider}|{voice.name}|{rate}|{pitch}|{beat.text}"

    words_json = words_file(index, audio_dir)
    timed = voice.provider in ("edge", "kokoro")      # these voices report their word timings
    if (wav.exists() and stamp.exists() and stamp.read_text(encoding="utf-8") == key
            and (words_json.exists() or not timed)):
        return wav, probe_duration(wav)
    words_json.unlink(missing_ok=True)

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
        transcribe_words(wav, words_json)       # own recordings: real word timings if Whisper is installed
    elif voice.provider == "edge":
        mp3 = audio_dir / f"{index:03d}.mp3"
        asyncio.run(_edge(beat.text, voice, rate, pitch, mp3, words_json))
        _to_wav(mp3, wav)
        mp3.unlink(missing_ok=True)
    elif voice.provider == "kokoro":
        raw = audio_dir / f"{index:03d}_k.wav"
        speed = max(0.6, min(1.5, 1.0 + _pct(rate) / 100))
        _kokoro(beat.text, voice, speed, raw, words_json)
        _to_wav(raw, wav)
        raw.unlink(missing_ok=True)
    else:  # pragma: no cover
        raise ValueError(f"unknown voice provider {voice.provider}")

    stamp.write_text(key, encoding="utf-8")
    return wav, probe_duration(wav)


def has_ffmpeg() -> bool:
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None
