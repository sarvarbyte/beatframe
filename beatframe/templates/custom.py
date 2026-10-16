"""custom: a one-off scene whose Manim code is written right into the script.

    - text: "Your brain fills the gap before you notice it."
      scene: custom
      params:
        theme: night            # night (dark brand + dust) | bright (cream background)
        fallback: statement     # used if the code fails, so the video still renders
        code: |
          gap = Rectangle(width=4, height=2).set_stroke(PAPER, 3)
          scene.play(Create(gap), run_time=0.6)
          wait_until("fills")                      # waits for the narrator to say "fills"
          scene.play(gap.animate.set_fill(GLOW, 0.8), run_time=0.5)

Inside `code` you have:
  scene / self        the Manim scene (scene.play, scene.add, scene.camera.frame ...)
  everything from `from manim import *`, plus np, random
  brand colours       NIGHT, DEEP, PAPER, GLOW, EMBER, DIM, SERIF, SANS (and `brand`, `kit`)
  layout              frame_w(), frame_h(), fit(mob, w, h), keep_inside_x(mob), width_ratio()
  light               glow(r, color), soft_glow(r, color)
  style guard         Text(...) defaults to the brand font and colour and never overflows the frame;
                      safe(mob) shrinks a group into the safe area and centres it
  timing              duration (beat length, s), now(), rest(),
                      words  [{"word", "start", "end"}, ...] of this beat's voice,
                      at("word", nth=1) -> second the word starts,
                      wait_until("word" | seconds) -> waits until then (no-op if already past)
Time left after the code runs is filled by a slow camera push, like every other scene.

Scene library: a custom scene that came out well can be saved under its own name
(beatframe save-scene, or the button in Studio). It is stored in scene_library/<name>.yaml and from
then on works like any template: `scene: <name>`, with `params: {vars: {...}}` read in its code as v.
"""

from __future__ import annotations

import random
import re
from pathlib import Path
from typing import Literal

import numpy as np
import yaml
from pydantic import Field

from beatframe import brand
from beatframe.templates import kit
from beatframe.templates.base import (Template, fit, frame_h, frame_w, glow, keep_inside_x, soft_glow,
                                      width_ratio)

DEMO = """\
t = Text("Custom scene", font=SERIF, color=PAPER).scale(1.2)
scene.play(FadeIn(t, shift=UP * 0.2), run_time=0.6)
scene.play(t.animate.set_color(EMBER), run_time=0.6)
"""

BRIGHT_BG = "#FFF6E5"


def norm(word: str) -> str:
    """A word as it is compared: lower case, no punctuation or quotes."""
    return re.sub(r"[^\w']+", "", word.lower()).strip("'")


class WordClock:
    """The beat's word timings, read by the scene code."""

    def __init__(self, words: list[dict], duration: float):
        self.words = words or []
        self.duration = duration

    def at(self, word: str, nth: int = 1) -> float:
        key = norm(word)
        hits = [w for w in self.words if norm(w.get("word", "")) == key]
        if len(hits) < nth:    # a word glued to another by the TTS ("brain's" vs "brain")
            hits = [w for w in self.words if norm(w.get("word", "")).startswith(key)]
        if len(hits) < nth:
            said = " ".join(w.get("word", "") for w in self.words)
            raise KeyError(f'at("{word}"): the narrator does not say it{" that many times" if hits else ""}. '
                           f"This beat says: {said[:200]}")
        return min(float(hits[nth - 1]["start"]), self.duration)


class Custom(Template):
    name = "custom"
    description = "One-off scene: its own Manim code, written into the script (with word-timed cues)"
    vertical_width = 8.0          # the code gets the real frame: use frame_w()/frame_h() for layout
    library_code: str = ""        # set on scene-library templates
    library_source: str = ""      # the library file's text (part of the render cache key)

    class Params(Template.Params):
        code: str = DEMO
        theme: Literal["night", "bright"] = "night"
        fallback: str = "statement"                       # scene used if the code fails
        fallback_params: dict = Field(default_factory=dict)   # empty: statement with the beat's text
        vars: dict = Field(default_factory=dict)          # values the code reads as v["name"]

    def source(self, p) -> str:
        return self.library_code or p.code

    def build(self, scene, p, duration):
        night = p.theme != "bright"
        if not night:                            # BeatScene drew the night look; swap it for cream
            scene.clear()
            scene.camera.background_color = BRIGHT_BG

        clock = WordClock(getattr(scene, "words", []), duration)

        def now() -> float:
            return float(getattr(scene.renderer, "time", 0.0))

        def rest() -> float:
            return max(0.0, duration - now())

        def wait_until(when) -> None:
            t = clock.at(when) if isinstance(when, str) else float(when)
            gap = min(t, duration) - now()
            if gap > 1 / 30:
                scene.wait(gap)

        import manim

        ns = {k: getattr(manim, k) for k in dir(manim) if not k.startswith("_")}
        ns.update(
            np=np, random=random, brand=brand, kit=kit,
            NIGHT=brand.NIGHT, DEEP=brand.DEEP, PAPER=brand.PAPER, GLOW=brand.GLOW, EMBER=brand.EMBER,
            DIM=brand.DIM, SERIF=brand.SERIF, SANS=brand.SANS, INK=kit.INK,
            frame_w=frame_w, frame_h=frame_h, fit=fit, keep_inside_x=keep_inside_x, width_ratio=width_ratio,
            glow=glow, soft_glow=soft_glow, safe=safe,
            Text=guarded_text(manim.Text, brand.PAPER if night else kit.INK),
            MarkupText=guarded_text(manim.MarkupText, brand.PAPER if night else kit.INK),
            scene=scene, self=scene, p=p, duration=duration, words=clock.words, v=dict(p.vars),
            at=clock.at, wait_until=wait_until, now=now, rest=rest,
        )
        exec(compile(self.source(p), "<custom beat>", "exec"), ns)   # noqa: S102 - the user's own script
        if rest() > 0.4:          # keep the frame alive until the beat ends (a slow camera push)
            from manim import linear
            scene.play(scene.camera.frame.animate(rate_func=linear).scale(0.95), run_time=rest())


# ---- style guard -------------------------------------------------------------------------
SAFE = 0.9          # share of the frame that content may fill


def safe(mob, share: float = SAFE):
    """Shrink (never grow) a mobject into the safe area and centre it."""
    fit(mob, frame_w() * share, frame_h() * share)
    return mob.move_to(manim_origin())


def manim_origin():
    from manim import ORIGIN
    return ORIGIN


def guarded_text(cls, color: str):
    """Text with the channel's font and colour by default, shrunk to fit the frame."""
    def make(*args, **kw):
        kw.setdefault("font", brand.SANS)
        kw.setdefault("color", color)
        return fit(cls(*args, **kw), frame_w() * SAFE, frame_h() * SAFE)
    make.__name__ = cls.__name__
    return make


def is_custom(scene: str) -> bool:
    from beatframe.templates.base import get_template
    try:
        return issubclass(get_template(scene), Custom)
    except KeyError:
        return False


# ---- scene library -----------------------------------------------------------------------
LIBRARY = brand.APP_DIR / "scene_library"
NAME_OK = re.compile(r"^[a-z][a-z0-9_]{2,40}$")


def _register(path: Path) -> None:
    from beatframe.templates.base import REGISTRY
    try:
        text = path.read_text(encoding="utf-8")
        data = yaml.safe_load(text) or {}
        name, code = str(data.get("name") or path.stem), str(data.get("code") or "")
    except (OSError, yaml.YAMLError):
        return
    if not NAME_OK.match(name) or not code.strip() or (name in REGISTRY and not
                                                      getattr(REGISTRY[name], "library_code", "")):
        return                                   # never shadow a built-in template
    default_theme = data.get("theme") if data.get("theme") in ("night", "bright") else "night"
    defaults = dict(data.get("vars") or {})

    class Params(Custom.Params):
        code: str = ""
        theme: Literal["night", "bright"] = default_theme
        vars: dict = Field(default_factory=lambda: dict(defaults))

        def model_post_init(self, _ctx) -> None:
            self.vars = {**defaults, **self.vars}

    type(f"Lib_{name}", (Custom,), {
        "name": name, "description": "Library · " + str(data.get("description") or "saved custom scene"),
        "library_code": code, "library_source": text, "Params": Params, "__module__": __name__,
    })


class _BlockDumper(yaml.SafeDumper):
    """Writes multi-line strings (the code) as readable | blocks."""


_BlockDumper.add_representer(str, lambda d, s: d.represent_scalar(
    "tag:yaml.org,2002:str", s, style="|" if "\n" in s else None))


def load_library() -> None:
    for path in sorted(LIBRARY.glob("*.yaml")) if LIBRARY.is_dir() else []:
        _register(path)


def save_to_library(beat, name: str, description: str = "") -> Path:
    """Store a custom beat's code as a reusable scene. Returns the file."""
    from beatframe.templates.base import REGISTRY
    if beat.scene != "custom":
        raise ValueError("only a custom scene can be saved to the library")
    if not NAME_OK.match(name):
        raise ValueError("name: 3-40 characters, lower case letters, digits and _ (e.g. gap_fill)")
    if name in REGISTRY and not getattr(REGISTRY[name], "library_code", ""):
        raise ValueError(f"{name} is already a built-in scene: pick another name")
    p = Custom.Params.model_validate(beat.params)
    LIBRARY.mkdir(parents=True, exist_ok=True)
    data = {"name": name, "description": description or beat.text[:80], "theme": p.theme,
            "vars": p.vars, "made_from": beat.text, "code": p.code}
    path = LIBRARY / f"{name}.yaml"
    path.write_text(yaml.dump(data, Dumper=_BlockDumper, sort_keys=False, allow_unicode=True, width=100),
                    encoding="utf-8")
    _register(path)
    return path


load_library()
