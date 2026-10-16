"""Music and sound effects under the narration.

Nothing is downloaded: the background music is generated here (soft chords, bass, a few plucked
notes, reverb) in one of several moods, so it is royalty-free and never triggers a Content ID claim.
A project can use its own track instead (audio.music: "music.mp3" in the project folder).

Mixing: the music is "ducked" (pushed down) automatically while the narrator speaks and comes up
in the pauses; a soft whoosh marks each scene change and a low hit marks every new chapter.
"""

from __future__ import annotations

import subprocess
import wave
from pathlib import Path

import numpy as np

SR = 48000

# mood -> (root Hz, chords as semitones from the root, seconds per chord, pluck scale, percussion bpm or 0)
MOODS = {
    "mystery": (110.0, [[0, 3, 7, 10], [-4, 0, 3, 7], [-7, -4, 0, 3], [-5, -1, 2, 7]], 8.0, [0, 3, 5, 7, 10, 12], 0),
    "wonder":  (146.8, [[0, 4, 7, 11], [-3, 0, 4, 7], [-7, -3, 0, 4], [-5, -1, 2, 7]], 8.0, [0, 2, 4, 7, 9, 12], 0),
    "epic":    (73.4,  [[0, 3, 7, 12], [-4, 0, 3, 8], [-9, -5, 0, 3], [-2, 2, 5, 10]], 4.0, [0, 3, 7, 12], 84),
    "tense":   (82.4,  [[0, 3, 7, 10], [0, 3, 6, 10], [1, 5, 8, 13], [0, 3, 7, 10]], 6.0, [0, 1, 3, 7], 100),
    "calm":    (130.8, [[0, 4, 7, 11], [-3, 0, 4, 9], [-7, -3, 0, 4], [-5, -1, 2, 7]], 8.0, [0, 2, 4, 7, 9], 0),
}


def _note(freq: float, dur: float, harmonics: int = 6, detune: float = 0.004) -> np.ndarray:
    """A soft, string-like tone: a few detuned voices with gently falling harmonics."""
    t = np.arange(int(dur * SR)) / SR
    out = np.zeros_like(t)
    for d in (-detune, 0.0, detune):
        f = freq * (1 + d)
        for h in range(1, harmonics + 1):
            out += np.sin(2 * np.pi * f * h * t + h * 0.7) / (h ** 1.6)
    return out / 3.0


def _envelope(n: int, attack: float, release: float) -> np.ndarray:
    a, r = int(attack * SR), int(release * SR)
    env = np.ones(n)
    env[:a] = np.linspace(0, 1, a) ** 2
    env[n - r:] *= np.linspace(1, 0, r) ** 1.5
    return env


def _reverb(x: np.ndarray, seconds: float = 2.8, wet: float = 0.35, seed: int = 3) -> np.ndarray:
    from scipy.signal import oaconvolve

    rng = np.random.default_rng(seed)
    n = int(seconds * SR)
    ir = rng.standard_normal(n) * np.exp(-np.linspace(0, 7, n))
    ir[0] = 0
    ir /= np.sqrt(np.sum(ir ** 2))
    tail = oaconvolve(x, ir)[: len(x)]
    return x * (1 - wet) + tail * wet


def _kick(dur: float = 0.6) -> np.ndarray:
    t = np.arange(int(dur * SR)) / SR
    f = 45 + 80 * np.exp(-t * 18)
    phase = 2 * np.pi * np.cumsum(f) / SR
    return np.sin(phase) * np.exp(-t * 7)


def music_loop(mood: str, seed: int = 1) -> np.ndarray:
    """One seamless loop (4 chords) of generated music, mono float32 at 48 kHz."""
    root, chords, chord_s, scale, bpm = MOODS.get(mood, MOODS["mystery"])
    rng = np.random.default_rng(seed)
    loop_n = int(chord_s * len(chords) * SR)
    # render three loops and keep the middle one, so the reverb tail wraps around seamlessly
    total = np.zeros(loop_n * 3)
    for rep in range(3):
        for ci, chord in enumerate(chords):
            start = rep * loop_n + int(ci * chord_s * SR)
            dur = chord_s + 1.5
            pad = sum(_note(root * 2 ** ((s + 12) / 12), dur, 5) for s in chord) / len(chord)
            pad *= _envelope(len(pad), min(1.8, chord_s * 0.3), 1.6) * 0.55
            bass = _note(root * 2 ** ((chord[0] % 12 - 12 if chord[0] > 0 else chord[0]) / 12), dur, 3) * 0.5
            bass *= _envelope(len(bass), 0.4, 1.4)
            seg = pad + bass
            end = min(len(total), start + len(seg))
            total[start:end] += seg[: end - start]
            # a few plucked notes, quiet, in the scale
            for _ in range(rng.integers(1, 4)):
                pos = start + int(rng.uniform(0.5, chord_s - 0.5) * SR)
                f = root * 4 * 2 ** (rng.choice(scale) / 12)
                n = int(1.6 * SR)
                t = np.arange(n) / SR
                pl = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)) * np.exp(-t * 3.2) * 0.22
                for k, g in ((0, 1.0), (int(0.37 * SR), 0.45), (int(0.74 * SR), 0.2)):   # simple echo
                    a = pos + k
                    b = min(len(total), a + n)
                    if a < len(total):
                        total[a:b] += pl[: b - a] * g
        if bpm:
            step = 60 / bpm
            beats = int(chord_s * len(chords) / step)
            for k in range(beats):
                if k % 4 in (0, 3) or (bpm >= 100 and k % 2 == 0):
                    a = rep * loop_n + int(k * step * SR)
                    kk = _kick() * (0.8 if k % 4 == 0 else 0.45)
                    b = min(len(total), a + len(kk))
                    total[a:b] += kk[: b - a]
    total = _reverb(total)
    loop = total[loop_n: 2 * loop_n]
    loop /= max(1e-6, np.max(np.abs(loop)))
    return (loop * 0.8).astype(np.float32)


def _whoosh(rng) -> np.ndarray:
    n = int(0.55 * SR)
    noise = rng.standard_normal(n)
    k = 24
    smooth = np.convolve(noise, np.ones(k) / k, mode="same")          # take the hiss off
    env = np.concatenate([np.linspace(0, 1, int(n * 0.55)) ** 2, np.linspace(1, 0, n - int(n * 0.55)) ** 1.5])
    return smooth * env * 1.6


def _hit() -> np.ndarray:
    n = int(1.6 * SR)
    t = np.arange(n) / SR
    f = 38 + 40 * np.exp(-t * 6)
    body = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 2.6)
    return body * 0.9


def sfx_track(starts: list[float], chapters: list[bool], length: float, seed: int = 5) -> np.ndarray:
    """Whoosh just before each scene change, a low hit on every chapter start (not the first beat)."""
    rng = np.random.default_rng(seed)
    out = np.zeros(int(length * SR) + SR, dtype=np.float32)
    for i, (t0, chap) in enumerate(zip(starts, chapters)):
        if i == 0:
            continue
        w = _whoosh(rng) * 0.35
        a = max(0, int((t0 - 0.35) * SR))
        out[a:a + len(w)] += w[: len(out) - a]
        if chap:
            h = _hit() * 0.6
            a = int(t0 * SR)
            out[a:a + len(h)] += h[: len(out) - a]
    return out[: int(length * SR)]


def write_wav(path: Path, x: np.ndarray) -> None:
    x = np.clip(x, -1, 1)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype("<i2").tobytes())


def mix(voice: Path, out: Path, *, length: float, starts: list[float], chapters: list[bool],
        settings, project_dir: Path, default_mood: str = "mystery", build_dir: Path | None = None) -> None:
    """voice.wav + (ducked) music + sfx -> out.wav. With music none and sfx off, just copies the voice."""
    build_dir = build_dir or out.parent
    inputs = ["-i", str(voice)]
    chains = ["[0:a]aformat=sample_rates=48000:channel_layouts=stereo,asplit=2[v][key]"]
    mixes = ["[v]"]
    music_src = None
    if settings.music not in ("none", "off", ""):
        if settings.music == "auto":
            mood = default_mood if settings.mood == "auto" else settings.mood
            music_src = build_dir / f"music_{mood}.wav"
            if not music_src.exists():
                write_wav(music_src, music_loop(mood))
        else:
            music_src = (project_dir / settings.music)
            if not music_src.exists():
                raise FileNotFoundError(f"music file not found: {music_src} (put it in the project folder)")
    if music_src is not None:
        gain = max(0.0, settings.music_volume) * 0.55
        inputs += ["-stream_loop", "-1", "-i", str(music_src)]
        chains.append(f"[1:a]aformat=sample_rates=48000:channel_layouts=stereo,volume={gain:.3f},"
                      f"atrim=0:{length:.3f},afade=t=in:d=1.5,afade=t=out:st={max(0, length - 3):.3f}:d=3[mus]")
        chains.append("[mus][key]sidechaincompress=threshold=0.05:ratio=3:attack=80:release=800:makeup=1[duck]")
        mixes.append("[duck]")
    else:
        chains[0] = "[0:a]aformat=sample_rates=48000:channel_layouts=stereo[v]"
    if settings.sfx:
        sfx = build_dir / "sfx.wav"
        write_wav(sfx, sfx_track(starts, chapters, length) * max(0.0, settings.sfx_volume))
        idx = len([x for x in inputs if x == "-i"])
        inputs += ["-i", str(sfx)]
        chains.append(f"[{idx}:a]aformat=sample_rates=48000:channel_layouts=stereo[fx]")
        mixes.append("[fx]")
    if len(mixes) == 1:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(voice), "-ac", "2", str(out)], check=True)
        return
    graph = ";".join(chains) + ";" + "".join(mixes) + f"amix=inputs={len(mixes)}:normalize=0:duration=first[out]"
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", graph, "-map", "[out]",
                    "-t", f"{length:.3f}", str(out)], check=True)
