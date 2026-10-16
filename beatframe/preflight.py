"""Pre-render check: what would make a render fail or look repetitive, found before anything renders.

    beatframe check project.yaml           # quick checks (a second)
    beatframe check project.yaml --test    # also test-renders every custom scene at 240p

Errors stop a render (or make a custom scene fall back); warnings are things to improve.
"""

from __future__ import annotations

import ast
import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from beatframe.captions import TEXT_SCENES
from beatframe.schema import Project
from beatframe.templates import get_template
from beatframe.templates.custom import is_custom

MEDIA_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".svg", ".gif", ".mp4", ".mov", ".webm",
              ".mp3", ".wav", ".m4a", ".ogg", ".flac")
WORDS_PER_SECOND = 2.4
HEX = re.compile(r"#[0-9A-Fa-f]{6}\b")


def brand_colours() -> set[str]:
    from beatframe import brand
    from beatframe.templates import kit
    found = {v for v in vars(brand).values() if isinstance(v, str) and v.startswith("#")}
    found |= {v for v in vars(kit).values() if isinstance(v, str) and v.startswith("#")}
    found |= {c for pal in kit.PALETTES.values() for c in pal.values()}
    return {c.upper() for c in found} | {"#FFF6E5", "#000000", "#FFFFFF"}


CUE_CALL = re.compile(r"""\b(?:at|wait_until)\(\s*(['"])(.+?)\1""")


@dataclass
class Issue:
    level: str          # "error" | "warn"
    beat: int | None    # 1-based, None = whole video
    msg: str

    def __str__(self) -> str:
        where = f"beat {self.beat}: " if self.beat else ""
        return f"{'✗' if self.level == 'error' else '!'} {where}{self.msg}"


def _norm(w: str) -> str:
    return re.sub(r"[^\w']+", "", w.lower()).strip("'")


def _strings(value):
    """Every string inside a params value (nested dicts and lists included)."""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            yield from _strings(v)
    elif isinstance(value, (list, tuple)):
        for v in value:
            yield from _strings(v)


def _fingerprint(beat) -> str:
    params = {k: v for k, v in beat.params.items() if k not in ("fallback", "fallback_params")}
    return json.dumps([beat.scene, params], sort_keys=True)


def check_custom(i: int, beat) -> list[Issue]:
    """Static checks of one custom scene's code: it parses, its cue words are really spoken."""
    out: list[Issue] = []
    code = str(beat.params.get("code") or "")
    if not code.strip():
        return [Issue("error", i, "custom scene has no `code`")]
    try:
        ast.parse(code)
    except SyntaxError as e:
        line = (e.text or "").strip()
        return [Issue("error", i, f"custom code line {e.lineno}: {e.msg}" + (f" → {line}" if line else ""))]
    spoken = [_norm(w) for w in beat.text.split()]
    for _, word in CUE_CALL.findall(code):
        key = _norm(word)
        if key and not any(s == key or s.startswith(key) for s in spoken):
            out.append(Issue("error", i, f'cue "{word}" is not in this beat\'s text, so the timing can\'t be found'))
    fb = str(beat.params.get("fallback") or "statement")
    try:
        cls = get_template(fb)
        if fb == "custom":
            out.append(Issue("error", i, "fallback can't be custom itself"))
        elif beat.params.get("fallback_params"):
            cls.Params.model_validate(beat.params["fallback_params"])
    except Exception as e:  # noqa: BLE001
        out.append(Issue("error", i, f"fallback: {e}"))
    off = sorted({h.upper() for h in HEX.findall(code)} - brand_colours())
    if off:
        out.append(Issue("warn", i, f"colours outside the channel palette: {', '.join(off[:5])} — use PAPER, GLOW, "
                                    "EMBER, DIM, NIGHT (or kit palettes on bright)"))
    if not CUE_CALL.search(code) and len(beat.text.split()) >= 10:
        out.append(Issue("warn", i, 'custom scene ignores the voice: add wait_until("word") so the visual '
                                    "lands on the spoken word"))
    if "self.wait(" in code or "scene.wait(" in code:
        waits = re.findall(r"(?:self|scene)\.wait\(\s*([\d.]+)", code)
        total = sum(float(x) for x in waits)
        est = len(beat.text.split()) / WORDS_PER_SECOND + 0.5
        if total > est + 1:
            out.append(Issue("warn", i, f"the code waits {total:.1f} s but the line lasts about {est:.1f} s: "
                                        "use wait_until(...) or rest() instead of fixed waits"))
    return out


def preflight(project: Project, project_dir: Path | None = None) -> list[Issue]:
    issues: list[Issue] = []
    beats = project.beats
    if project.imported or not beats:
        return issues

    # 1. scenes and params
    for i, b in enumerate(beats, 1):
        try:
            get_template(b.scene).Params.model_validate(b.params)
        except Exception as e:  # noqa: BLE001
            issues.append(Issue("error", i, str(e).splitlines()[0]))
            continue
        if b.scene == "custom":
            issues += check_custom(i, b)
        elif is_custom(b.scene):            # a scene-library template: check its saved code's cues
            lib = get_template(b.scene)
            issues += [x for x in check_custom(i, b.model_copy(update={"params": {**b.params, "code": lib.library_code}}))
                       if x.level == "error"]
        if not b.text.strip():
            issues.append(Issue("error", i, "empty text: the narrator has nothing to say"))

    # 2. files the script points to
    if project_dir is not None:
        for i, b in enumerate(beats, 1):
            params = {k: v for k, v in b.params.items() if k != "code"}
            if b.scene == "photo" and not str(params.get("image") or "").strip():
                params["image"] = f"images/beat_{i:03d}.png"
            for s in _strings(params):
                if s.lower().endswith(MEDIA_EXTS) and "\n" not in s:
                    p = Path(s).expanduser()
                    if not (p if p.is_absolute() else project_dir / p).exists():
                        hint = " — beatframe image-prompts gives its prompt" if b.scene == "photo" else ""
                        issues.append(Issue("error", i, f"file not found: {s} (put it in the project folder){hint}"))
        music = project.audio.music
        if music not in ("auto", "none") and not (project_dir / music).exists():
            issues.append(Issue("error", None, f"music file not found: {music}"))
        if project.voice.provider == "files":
            folder = Path(project.voice.files_dir or "").expanduser()
            folder = folder if folder.is_absolute() else project_dir / folder
            missing = [i for i in range(1, len(beats) + 1)
                       if not any((folder / f"{i:03d}{ext}").exists() for ext in (".wav", ".mp3", ".m4a", ".ogg", ".flac"))]
            if missing:
                issues.append(Issue("error", None, f"voice recordings missing for beats {_list(missing)} in {folder}"))

    n_custom = sum(is_custom(b.scene) for b in beats)
    if len(beats) >= 8 and n_custom / len(beats) > 0.4:
        issues.append(Issue("warn", None, f"{n_custom} of {len(beats)} beats are custom scenes: keep them for the "
                                          "moments templates can't show (renders stay fast, the look stays the channel's)"))

    # 3. repeated frames
    seen: dict[str, int] = {}
    for i, b in enumerate(beats, 1):
        fp = _fingerprint(b)
        if fp in seen:
            issues.append(Issue("warn", i, f"exactly the same picture as beat {seen[fp]} ({b.scene}): change it"))
        else:
            seen[fp] = i
    run = 1
    for i in range(2, len(beats) + 2):
        same = i <= len(beats) and beats[i - 1].scene == beats[i - 2].scene and beats[i - 1].scene != "custom"
        if same:
            run += 1
            continue
        if run >= 3 and beats[i - 2].scene not in TEXT_SCENES:     # text runs are covered by the advice
            issues.append(Issue("warn", i - run, f"{run} {beats[i - 2].scene} scenes in a row "
                                                 f"(beats {i - run}-{i - 1}): vary them"))
        run = 1
    if project_dir is not None:
        issues += variety(project, project_dir)
    if len(beats) >= 12:
        for scene, n in Counter(b.scene for b in beats).most_common(3):
            if scene != "custom" and n / len(beats) > 0.3:
                issues.append(Issue("warn", None, f"{scene} is {n} of {len(beats)} beats ({n * 100 // len(beats)}%): "
                                                  "the video will feel repetitive"))
    return issues


def variety(project: Project, project_dir: Path) -> list[Issue]:
    """Compared with the last videos: the same custom code again, the same favourite scenes again."""
    from beatframe import history

    rec = history.recent(project_dir.parent, exclude=project_dir.name, n=3)
    if not rec:
        return []
    out: list[Issue] = []
    earlier = {}
    for m in rec:
        for h in m.custom_codes:
            earlier.setdefault(h, m.title)
    for i, b in enumerate(project.beats, 1):
        if b.scene == "custom":
            h = history.code_hash(str(b.params.get("code", "")))
            if h in earlier:
                out.append(Issue("warn", i, f'the same custom scene was in "{earlier[h]}": save it to the '
                                            "library and change it, or draw something new"))
    mine = Counter(b.scene for b in project.beats if b.scene != "custom")
    theirs = Counter(s for m in rec for s in m.scenes if s != "custom")
    if mine and theirs:
        top_mine = {s for s, _ in mine.most_common(3)}
        top_theirs = {s for s, _ in theirs.most_common(3)}
        same = sorted(top_mine & top_theirs)
        if len(same) >= 2:
            out.append(Issue("warn", None, f"the most used scenes ({', '.join(same)}) are the same as in the last "
                                           f"{len(rec)} videos: swap some for others or custom scenes"))
    return out


def _list(nums: list[int]) -> str:
    return ", ".join(map(str, nums[:10])) + (f" and {len(nums) - 10} more" if len(nums) > 10 else "")


def test_custom(project: Project, project_file: Path, log=print) -> list[Issue]:
    """Render every custom scene at 240p with estimated word timings. Failures are errors."""
    from beatframe.render import ClipJob, render_all
    from beatframe.tts import estimate_words

    jobs = []
    for i, b in enumerate(project.beats, 1):
        if b.scene != "custom":
            continue
        secs = max(b.min_duration, len(b.text.split()) / WORDS_PER_SECOND + 0.4)
        w, h = (240, 426) if project.video.spec.vertical else (426, 240)
        jobs.append(ClipJob(i, "custom", b.params, round(secs, 2), w, h, 10,
                            words=estimate_words(b.text, secs), fallback=None))
    if not jobs:
        return []
    out_dir = project_file.parent / "build" / "custom_test"
    issues: list[Issue] = []

    def done(job, path, cached):
        log(f"  beat {job.index:03d} custom ✓{' (cached)' if cached else ''}")

    for job in jobs:          # one by one, so one broken scene doesn't hide the others
        try:
            render_all([job], out_dir, workers=1, on_done=done)
        except RuntimeError as e:
            msg = str(e).split("\n", 1)[-1].strip().splitlines()
            issues.append(Issue("error", job.index, "test render failed: " + (msg[-1] if msg else str(e))))
            log(f"  beat {job.index:03d} custom ✗\n{e}")
    return issues
