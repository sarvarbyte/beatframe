"""AI review #1: an AI watches a rendered video (picture + sound) and lists what to fix, beat by beat.

Runs after a preview, before the final render. The model gets the video, the script with each beat's
time range, and the channel's rules; it answers in a fixed JSON shape so Studio can link every issue
to its beat. The result is saved next to the video (output/review.json or review_short.json).

The AIs are tried as a chain, so one busy service doesn't stop the review:
  1. Gemini flash models, newest first, then Gemini flash-lite   (GEMINI_API_KEY / ~/.beatframe/gemini_key)
  2. free OpenRouter models that take video: Nemotron Omni (hears the sound), then Gemma 4
                                                                 (OPENROUTER_API_KEY / ~/.beatframe/openrouter_key)
Keys are saved once from Studio → Settings; a provider without a key is skipped. A busy model is
retried, then the next one is used. BEATFRAME_GEMINI_MODEL puts one Gemini model first.
"""

from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, Literal

from pydantic import BaseModel, Field, field_validator

from beatframe.formats import get_format
from beatframe.pipeline import output_name
from beatframe.schema import Project

CONFIG_DIR = Path.home() / ".beatframe"
KEY_FILE = CONFIG_DIR / "gemini_key"
FALLBACK_MODEL = "gemini-2.5-flash"


class ReviewError(RuntimeError):
    """A problem the user can fix (no key, no video, quota...): shown as is, without a traceback."""


# ---- answer shape -----------------------------------------------------------------------
class Issue(BaseModel):
    beat: int = Field(description="Beat number (1-based) the problem is in; 0 if it is about the whole video")
    time: str = Field(description="Where in the video, m:ss")
    severity: Literal["high", "medium", "low"]
    category: Literal["hook", "pacing", "visual", "voice", "captions", "text", "fact", "ending", "other"]
    problem: str = Field(description="What is wrong, in Uzbek, concrete and short")
    fix: str = Field(description="What to change in the script, in Uzbek (scene, params, cut, reorder...)")
    new_text: str = Field("", description="Suggested new narration for this beat in English, or empty")

    # weaker models (the free backups) sometimes invent values: keep the review instead of failing it
    @field_validator("category", mode="before")
    @classmethod
    def _known_category(cls, v):
        v = str(v or "").strip().lower()
        return v if v in ("hook", "pacing", "visual", "voice", "captions", "text", "fact", "ending") else "other"

    @field_validator("severity", mode="before")
    @classmethod
    def _known_severity(cls, v):
        v = str(v or "").strip().lower()
        return v if v in ("high", "medium", "low") else "medium"

    @field_validator("beat", mode="before")
    @classmethod
    def _beat_number(cls, v):
        m = re.search(r"\d+", str(v if v is not None else ""))
        return int(m.group()) if m else 0

    @field_validator("new_text", mode="before")
    @classmethod
    def _text_or_empty(cls, v):
        return "" if v is None else str(v)


class Review(BaseModel):
    score: int = Field(description="1-10: how ready this video is to publish")
    verdict: Literal["ready", "fix_first"]
    summary: str = Field(description="2-3 sentences in Uzbek: the main finding")
    first_seconds: str = Field(description="In Uzbek: what a viewer sees and hears in the first 2 seconds")
    issues: list[Issue] = Field(description="Most important first; at most 8")
    strengths: list[str] = Field(description="What works, in Uzbek; at most 3")

    @field_validator("score", mode="before")
    @classmethod
    def _score_1_10(cls, v):
        try:
            return max(1, min(10, round(float(v))))
        except (TypeError, ValueError):
            return 5

    @field_validator("verdict", mode="before")
    @classmethod
    def _known_verdict(cls, v):
        return "ready" if str(v or "").strip().lower() in ("ready", "publish", "ok") else "fix_first"


# ---- rules the model judges against ------------------------------------------------------
SHORT_RULES = """\
This is a YouTube Short (9:16) for "Human Unknowns", a faceless English channel about the viewer's own body,
brain and perception. The channel's numbers so far:
- Shorts made like this one (stick figures, Beatframe) get a fast push from the Shorts feed but lose viewers
  around 11-12 s (31-44% viewed). Shorts that held 61-82% delivered a clear payoff early.
- Winners: a "You/Your" CLAIM about the viewer's own body that they can test right now.
  Losers: question openings, stories about other people, abstract claims.
Judge against these rules:
1. Length 20-25 s. Longer needs a strong reason.
2. First 1-2 s: a 4-5-word claim, voice from the first frame, something already moving. No slow intro,
   no question card, no empty frame. This decides whether people swipe away.
3. The payoff (the surprising answer) lands before ~15 s.
4. A "try it right now" moment, and a clear ending line.
5. Every second has motion or change; flag frames that sit still for more than ~2 s.
6. Picture matches what the voice says at that moment.
7. Text and captions readable on a phone, not covering the key visual, no overlap between them.
8. Facts correct and gentle (nothing medical or scary); flag claims that are doubtful or overstated.
"""

LONG_RULES = """\
This is a long YouTube video (16:9) for "Human Unknowns", a faceless English channel about the viewer's own
body, brain and perception. Long videos so far get very few views and low retention.
Judge against these rules:
1. The first 15 s deliver the title's claim and show the thumbnail moment; no slow intro, no channel intro.
2. A re-hook at the start of every chapter (a question or promise that makes the next part worth watching).
3. No slow stretches: flag parts where the picture barely changes for a long time or the narration repeats.
4. Picture matches what the voice says at that moment.
5. Text readable, not covering the key visual.
6. Facts correct and gentle; flag claims that are doubtful or overstated.
7. A clear ending that points to another video.
"""

INSTRUCTIONS = """\
You are a strict YouTube retention editor. Watch the whole video (picture and sound). The script below
lists every beat with its time range; refer to beats by these numbers. Only report problems you can
actually see or hear in this video or read in this script; be specific (which beat, what exactly).
Do not praise generically. Write problem, fix, summary, first_seconds and strengths in Uzbek
(Latin script); write new_text (replacement narration) in English. verdict is "ready" only if no
high-severity issue is left.
"""


# ---- keys ------------------------------------------------------------------------------
KEYS = {   # provider -> (environment variable, file in ~/.beatframe)
    "gemini": ("GEMINI_API_KEY", "gemini_key"),
    "openrouter": ("OPENROUTER_API_KEY", "openrouter_key"),
}


def key_file(provider: str = "gemini") -> Path:
    return KEY_FILE if provider == "gemini" else CONFIG_DIR / KEYS[provider][1]


def api_key(provider: str = "gemini") -> str:
    key = os.environ.get(KEYS[provider][0], "").strip()
    if not key:
        try:
            key = key_file(provider).read_text(encoding="utf-8").strip()
        except OSError:
            key = ""
    return key


def save_key(key: str, provider: str = "gemini") -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    f = key_file(provider)
    f.write_text(key.strip() + "\n", encoding="utf-8")
    f.chmod(0o600)


def has_key(provider: str | None = None) -> bool:
    """A key for this provider, or (provider None) for any provider in the chain."""
    return any(api_key(p) for p in ([provider] if provider else KEYS))


# ---- Gemini ----------------------------------------------------------------------------
def _client():
    key = api_key("gemini")
    if not key:
        raise ReviewError("Gemini API key is not set. Add it in Studio → Settings (or export GEMINI_API_KEY).")
    try:
        from google import genai
    except ImportError:
        raise ReviewError("The Gemini library is missing. Run once: .venv/bin/pip install -e '.[audit]'") from None
    return genai.Client(api_key=key)


_MODELS: dict[str, list[str]] = {}


def model_candidates(client) -> list[str]:
    """Gemini models to try, best first: BEATFRAME_GEMINI_MODEL if set, the three newest
    "gemini-<version>-flash", then the newest "-flash-lite" (each model has its own free quota)."""
    if "list" not in _MODELS:
        flash, lite = [], []
        try:
            for m in client.models.list():
                name = (m.name or "").removeprefix("models/")
                actions = getattr(m, "supported_actions", None) or []
                match = re.fullmatch(r"gemini-(\d+(?:\.\d+)?)-flash(-lite)?", name)
                if match and (not actions or "generateContent" in actions):
                    (lite if match.group(2) else flash).append((float(match.group(1)), name))
        except Exception:  # noqa: BLE001  (listing is only a convenience)
            pass
        chosen = [n for _, n in sorted(flash, reverse=True)][:3] or [FALLBACK_MODEL]
        _MODELS["list"] = chosen + [n for _, n in sorted(lite, reverse=True)][:1]
    first = os.environ.get("BEATFRAME_GEMINI_MODEL", "").strip()
    return ([first] if first else []) + [m for m in _MODELS["list"] if m != first]


def pick_model(client) -> str:
    return model_candidates(client)[0]


BUSY = ("503", "UNAVAILABLE", "overloaded", "500", "INTERNAL", "502", "504", "DEADLINE")
QUOTA = ("429", "RESOURCE_EXHAUSTED")
RETRY_WAIT = (10, 30)          # seconds before the 2nd and 3rd try on a busy model


def _generate(client, models: list[str], contents, config, log, status) -> tuple[object, str]:
    """Ask the first model that answers. A busy model is retried twice, then the next one is tried;
    a model whose free quota is used up is skipped. Returns (response, model used)."""
    busy = quota = False
    for model in models:
        for attempt in range(len(RETRY_WAIT) + 1):
            try:
                return client.models.generate_content(model=model, contents=contents, config=config), model
            except Exception as e:  # noqa: BLE001
                msg = str(e)
                if "API key" in msg or "API_KEY" in msg or "401" in msg or "PERMISSION_DENIED" in msg:
                    raise ReviewError("Gemini did not accept the API key. Check it in Studio → Settings.") from e
                if any(k in msg for k in QUOTA):
                    quota = True
                    log(f"{model}: free quota used up, trying the next model")
                    break
                if not any(k in msg for k in BUSY):
                    raise
                busy = True
                if attempt < len(RETRY_WAIT):
                    wait = RETRY_WAIT[attempt]
                    log(f"{model}: busy (try {attempt + 1}), waiting {wait} s")
                    status(f"{model} is busy, trying again in {wait} s")
                    time.sleep(wait)
                else:
                    log(f"{model}: still busy, trying the next model")
        status("Writing the review")
    if busy:
        raise ReviewError("Gemini is overloaded right now (all its models tried).")
    if quota:
        raise ReviewError("Gemini free-tier limit reached.")
    raise ReviewError("No Gemini model answered.")


def _gemini_review(video: Path, prompt: str, duration: float, log, step, status) -> tuple[Review, str]:
    from google.genai import types

    client = _client()
    models = model_candidates(client)
    log(f"Gemini models: {', '.join(models)}")
    step(1)
    uploaded = client.files.upload(file=str(video), config={"mime_type": "video/mp4"})
    try:
        step(2)
        deadline = time.time() + 300
        while uploaded.state and uploaded.state.name == "PROCESSING":
            if time.time() > deadline:
                raise ReviewError("Gemini took too long to process the video.")
            time.sleep(2)
            uploaded = client.files.get(name=uploaded.name)
        if uploaded.state and uploaded.state.name == "FAILED":
            raise ReviewError("Gemini could not read this video file.")
        step(3)
        config = types.GenerateContentConfig(
            response_mime_type="application/json", response_schema=Review, temperature=0.3,
            # long videos: fewer tokens per frame so a 10-14 min video fits the free tier
            media_resolution="MEDIA_RESOLUTION_LOW" if duration > 180 else None,
        )
        resp, model = _generate(client, models, [uploaded, prompt], config, log, status)
        review = resp.parsed if isinstance(resp.parsed, Review) else Review.model_validate_json(resp.text)
        return review, model
    finally:
        try:
            client.files.delete(name=uploaded.name)
        except Exception:  # noqa: BLE001
            pass


# ---- OpenRouter (free models, a different company: works when Google is overloaded) -----
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
# free models that accept video; hears_audio = the model also gets the soundtrack
OPENROUTER_MODELS = [
    ("nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free", True),
    ("google/gemma-4-31b-it:free", False),
    ("google/gemma-4-26b-a4b-it:free", False),
]
NO_AUDIO_NOTE = ("You cannot hear this video's sound. Judge the narration only from the script's voice lines "
                 "and their timing; do not report audio problems.\n")


def _small_video(video: Path, duration: float, out: Path) -> Path:
    """A light copy for sending inline: longest side 640 px, few frames per second, mono sound."""
    fps, crf = ("2", "34") if duration > 180 else ("8", "30")
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(video),
         "-vf", "scale='if(gt(iw,ih),640,-2)':'if(gt(iw,ih),-2,640)'", "-r", fps,
         "-c:v", "libx264", "-preset", "veryfast", "-crf", crf, "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-ac", "1", "-b:a", "48k", "-movflags", "+faststart", str(out)],
        check=True,
    )
    return out


def _openrouter_post(payload: dict, key: str) -> tuple[int, dict]:
    import httpx

    r = httpx.post(OPENROUTER_URL, json=payload, timeout=300,
                   headers={"Authorization": f"Bearer {key}", "X-Title": "Beatframe Studio"})
    try:
        return r.status_code, r.json()
    except ValueError:
        return r.status_code, {"error": {"message": r.text[:300]}}


def _parse_json(text: str) -> Review:
    """The model's answer as a Review; tolerates code fences or words around the JSON."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("no JSON in the answer")
    return Review.model_validate_json(text[start:end + 1])


MAX_FRAMES = 48
SHEET = (3, 2)          # stills per contact sheet: columns x rows (some models take at most 12 images)


def _ts(t: float) -> str:
    return f"{int(t) // 60}:{int(t) % 60:02d}"


def _frames(video: Path, duration: float, out_dir: Path) -> list[tuple[str, str]]:
    """Stills for models that may not get the video itself: one a second (at most MAX_FRAMES),
    laid out 6 to a contact sheet with each still's time written on it.
    Returns (caption, base64 JPEG) per sheet."""
    from PIL import Image, ImageDraw, ImageFont

    from beatframe import brand

    fps = 1.0 if duration <= MAX_FRAMES else MAX_FRAMES / max(duration, 1)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-y", "-i", str(video),
         "-vf", f"fps={fps:.4f},scale='if(gt(iw,ih),384,-2)':'if(gt(iw,ih),-2,384)'",
         "-q:v", "4", str(out_dir / "f_%03d.jpg")],
        check=True,
    )
    stills = [(k / fps, Image.open(f).convert("RGB")) for k, f in enumerate(sorted(out_dir.glob("f_*.jpg")))]
    try:
        font = ImageFont.truetype(str(brand.FONT_DIR / "Figtree.ttf"), 22)
    except OSError:
        font = ImageFont.load_default()
    cols, rows = SHEET
    sheets = []
    for i in range(0, len(stills), cols * rows):
        group = stills[i:i + cols * rows]
        w, h = group[0][1].size
        sheet = Image.new("RGB", (cols * w + (cols - 1) * 6, rows * h + (rows - 1) * 6), (255, 255, 255))
        draw = ImageDraw.Draw(sheet)
        for k, (t, img) in enumerate(group):
            x, y = (k % cols) * (w + 6), (k // cols) * (h + 6)
            sheet.paste(img, (x, y))
            draw.rectangle([x, y, x + 62, y + 30], fill=(0, 0, 0))
            draw.text((x + 6, y + 3), _ts(t), fill=(255, 255, 0), font=font)
        buf = out_dir / f"sheet_{i:03d}.jpg"
        sheet.save(buf, quality=80)
        caption = (f"Stills {_ts(group[0][0])}-{_ts(group[-1][0])}, one every {1 / fps:.0f} s, "
                   f"left to right then top to bottom; the time is in each still's corner")
        sheets.append((caption, base64.b64encode(buf.read_bytes()).decode("ascii")))
    return sheets


_OR_STATE = {"video": True}    # False once OpenRouter said video needs a paid balance (402)


def _openrouter_review(video: Path, prompt: str, duration: float, log, step, status) -> tuple[Review, str]:
    """Free OpenRouter models. They get the video when the account allows it; free accounts
    (no balance) get it as stills one second apart, and judge the voice from the script."""
    key = api_key("openrouter")
    if not key:
        raise ReviewError("OpenRouter key is not set.")
    step(1)
    status("Preparing the video")
    with tempfile.TemporaryDirectory(prefix="beatframe_review_") as tmp:
        small = _small_video(video, duration, Path(tmp) / "review.mp4")
        video_part = [{"type": "video_url", "video_url": {
            "url": "data:video/mp4;base64," + base64.b64encode(small.read_bytes()).decode("ascii")}}]
        stills = _frames(small, duration, Path(tmp))
    frame_parts = []
    for caption, data in stills:
        frame_parts += [{"type": "text", "text": caption},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{data}"}}]
    log(f"OpenRouter: video {len(video_part[0]['video_url']['url']) // 1024} KB, {len(stills)} contact sheets")
    schema = json.dumps(Review.model_json_schema(), ensure_ascii=False)
    step(3)
    problems = []
    for model, hears in OPENROUTER_MODELS:
        attempt = 0
        while attempt < 2:
            as_video = _OR_STATE["video"]
            note = "" if (hears and as_video) else NO_AUDIO_NOTE
            if not as_video:
                note += ("You get the video as contact sheets of stills taken one second apart, each with its "
                         "time in the corner; judge motion and pacing from how much changes between stills.\n")
            text = note + prompt + \
                "\nReturn ONLY one JSON object (no code fences, no other text) matching this JSON schema:\n" + schema
            payload = {"model": model, "temperature": 0.3, "max_tokens": 6000, "reasoning": {"exclude": True},
                       "messages": [{"role": "user", "content":
                                     [{"type": "text", "text": text}] + (video_part if as_video else frame_parts)}]}
            status(f"Asking {model.split('/')[-1]}" + ("" if as_video else " (stills)"))
            try:
                code, body = _openrouter_post(payload, key)
            except Exception as e:  # noqa: BLE001  (network)
                code, body = 0, {"error": {"message": str(e)}}
            err = body.get("error") if isinstance(body, dict) else None
            if code == 200 and err:            # an upstream failure wrapped in a 200: treat as busy
                code = int(err.get("code") or 503) if isinstance(err, dict) and str(err.get("code", "")).isdigit() else 503
            if code == 401:
                raise ReviewError("OpenRouter did not accept the API key. Check it in Studio → Settings.")
            if code == 402 and as_video:
                _OR_STATE["video"] = False      # free account: video needs a balance, stills don't
                log("OpenRouter: video needs a paid balance on this account, sending stills instead")
                continue
            if code == 200 and not err:
                try:
                    mode = "" if as_video else " (stills)"
                    return _parse_json(body["choices"][0]["message"]["content"] or ""), f"openrouter:{model}{mode}"
                except (KeyError, IndexError, TypeError, ValueError) as e:
                    problems.append(f"{model}: unreadable answer ({e})")
                    log(problems[-1])
                    break
            msg = (err or {}).get("message", "") if isinstance(err, dict) else str(err)
            problems.append(f"{model}: {code} {msg[:120]}")
            log(problems[-1])
            attempt += 1
            if (code == 429 or code >= 500 or code == 0) and attempt < 2:
                status(f"{model.split('/')[-1]} is busy, trying again in 20 s")
                time.sleep(20)
                continue
            break
    raise ReviewError("No free OpenRouter model answered: " + "; ".join(problems[-3:]))


# ---- the review ------------------------------------------------------------------------
def review_file(out_dir: Path, video_format: str) -> Path:
    return out_dir / f"review{get_format(video_format).suffix}.json"


def latest(out_dir: Path, video_format: str) -> dict | None:
    try:
        return json.loads(review_file(out_dir, video_format).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def pick_video(out_dir: Path, video_format: str, final: bool | None = None) -> Path:
    """The video to review: the final or the preview, by default whichever is newer."""
    kinds = ["final"] if final else ["preview"] if final is False else ["preview", "final"]
    found = [out_dir / output_name(k, video_format) for k in kinds]
    found = [f for f in found if f.exists()]
    if not found:
        raise ReviewError("No video to review yet. Render a preview first.")
    return max(found, key=lambda f: f.stat().st_mtime)


def script_text(project: Project, timeline: list[dict] | None) -> str:
    if project.imported:
        made = f" (made with {project.made_with})" if project.made_with else ""
        return (f"Title: {project.title}\nThis video was made outside Beatframe{made}: there are no beats, "
                f"refer to problems with beat 0 and the time.\nVoiceover:\n{project.script.strip() or '(not given)'}")
    spans = {t["beat"]: t for t in timeline or []}
    rows = [f"Title: {project.title}"]
    for i, b in enumerate(project.beats, 1):
        t = spans.get(i)
        when = f"{t['start']:.1f}-{t['end']:.1f}s" if t else "time unknown"
        params = json.dumps(b.params, ensure_ascii=False) if b.params else "{}"
        chapter = f" [chapter: {b.chapter}]" if b.chapter else ""
        rows.append(f"Beat {i} ({when}) scene={b.scene}{chapter}\n  voice: {b.text}\n  params: {params}")
    return "\n".join(rows)


def run_review(project: Project, project_file: Path, video_format: str | None = None,
               final: bool | None = None, log: Callable[[str], None] = print,
               step: Callable[[int], None] | None = None,
               status: Callable[[str], None] | None = None) -> dict:
    """Ask the chain for a review, save and return it: Gemini (flash models, then flash-lite),
    then free OpenRouter models. A provider without a key is skipped.

    step(n) is called as the work advances: 1 uploading, 2 the AI processing the video, 3 reviewing;
    status(text) gets short notes while waiting (e.g. a busy model being retried).
    """
    step, status = step or (lambda n: None), status or (lambda m: None)
    fmt = get_format(video_format or project.video.format)
    out_dir = project_file.parent / "output"
    video = pick_video(out_dir, fmt.name, final)
    try:
        manifest = json.loads(video.with_suffix(".json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        manifest = {}
    duration = manifest.get("duration") or 0
    rules = SHORT_RULES if fmt.vertical else LONG_RULES
    prompt = f"{INSTRUCTIONS}\n{rules}\nSCRIPT\n{script_text(project, manifest.get('timeline'))}"
    log(f"video: {video.name}")

    chain = [(p, fn) for p, fn in (("gemini", _gemini_review), ("openrouter", _openrouter_review)) if has_key(p)]
    if not chain:
        raise ReviewError("No AI key is set. Add a Gemini or OpenRouter key in Studio → Settings.")
    failures = []
    for provider, fn in chain:
        try:
            review, model = fn(video, prompt, duration, log, step, status)
            break
        except ReviewError as e:
            failures.append(f"{provider}: {e}")
            log(f"{provider} failed: {e}" + (" → trying the next provider" if provider != chain[-1][0] else ""))
    else:
        raise ReviewError("Every AI in the chain failed. " + " | ".join(failures) + " Try again in a few minutes.")

    review.issues.sort(key=lambda x: ("high", "medium", "low").index(x.severity))
    result = {
        "video": video.name, "video_mtime": int(video.stat().st_mtime), "model": model,
        "created": datetime.now().isoformat(timespec="seconds"), "review": review.model_dump(),
        "fallbacks": failures,
    }
    review_file(out_dir, fmt.name).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    log(f"{model}: score {review.score}/10 · {len(review.issues)} issues · {review.verdict}")
    return result
