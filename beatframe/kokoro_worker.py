"""Kokoro voice worker. Runs in its own Python 3.12 environment (~/.kokoro), because Kokoro's
libraries don't install on newer Pythons yet. Beatframe starts it once and sends one JSON line per
beat: {"text": ..., "voice": "am_michael", "speed": 1.0, "out": "/path/001_k.wav"} -> replies "ok" or "error: ...".
With an optional "words": "/path/001.words.json" it also writes the word timings there.
"""
import json
import sys

import numpy as np
import soundfile as sf
from kokoro import KPipeline

OUT = sys.stdout          # answers go here; anything the libraries print goes to stderr
sys.stdout = sys.stderr


def say(msg: str) -> None:
    OUT.write(msg + "\n")
    OUT.flush()


pipes = {}
say("ready")
for line in sys.stdin:
    try:
        job = json.loads(line)
        lang = "b" if job["voice"].startswith("b") else "a"
        if lang not in pipes:
            pipes[lang] = KPipeline(lang_code=lang, repo_id="hexgrad/Kokoro-82M")
        parts, words, offset = [], [], 0.0
        for result in pipes[lang](job["text"], voice=job["voice"], speed=job["speed"]):
            audio = result.audio.numpy() if hasattr(result.audio, "numpy") else result.audio
            for t in result.tokens or []:     # word timings, relative to this chunk's audio
                if t.start_ts is not None and t.end_ts is not None:
                    words.append({"word": t.text, "start": round(offset + t.start_ts, 3),
                                  "end": round(offset + t.end_ts, 3)})
            parts.append(audio)
            offset += len(audio) / 24000
        sf.write(job["out"], np.concatenate(parts), 24000)
        if job.get("words"):
            with open(job["words"], "w", encoding="utf-8") as f:
                json.dump(words, f)
        say("ok")
    except Exception as e:  # noqa: BLE001
        say("error: " + str(e).replace("\n", " "))
