"""Template base class, the shared scene, and the template registry.

A template is a class with:
  * name            - the value used in `scene:` in the project YAML
  * Params          - a pydantic model; it validates YAML params (and later drives the web form)
  * build(scene, p, duration) - draws the animation into `scene`, using about `duration` seconds

The runtime pads every beat to exactly its voice length, so a template only has to
spread its animations over `duration`; it never has to be exact.
"""

from __future__ import annotations

import random
from typing import ClassVar

import numpy as np
from manim import (
    Dot,
    MovingCameraScene,
    VGroup,
    config,
    linear,
)
from pydantic import BaseModel

from beatframe import brand

REGISTRY: dict[str, type["Template"]] = {}

# Entrances that start in a beat's first FAST_START seconds are squeezed to SNAP seconds, so the frame
# is never empty at a cut (Shorts viewers swipe within the first second). Moves that are not entrances
# (a walk, a camera zoom, a transform) keep their time.
FAST_START = 0.5
SNAP = 0.3


def _introduces(anim) -> bool:
    """True for animations that bring something on screen (FadeIn, Write, Create, GrowFromCenter...)."""
    if hasattr(anim, "animations"):                 # AnimationGroup / LaggedStart / Succession
        if getattr(anim, "lag_ratio", 0) > 0:
            return False    # a word-by-word reveal: it starts at once and is meant to follow the voice
        return bool(anim.animations) and all(_introduces(a) for a in anim.animations)
    check = getattr(anim, "is_introducer", None)
    return bool(check and check())


def glow(radius: float, color: str, layers: int = 6, strength: float = 0.18) -> VGroup:
    """A soft light: a solid core with fading halos around it."""
    from manim import Circle

    halo = VGroup(*[
        Circle(radius=radius * (1 + 0.55 * k)).set_stroke(width=0).set_fill(color, strength * (1 - k / layers))
        for k in range(1, layers + 1)
    ])
    core = Circle(radius=radius).set_stroke(width=0).set_fill(color, 1)
    return VGroup(halo, core)


def soft_glow(radius: float, color: str, layers: int = 8, strength: float = 0.07) -> VGroup:
    """A glow with no hard core: stacked transparent discs, brightest in the middle."""
    from manim import Circle

    return VGroup(*[
        Circle(radius=radius * k / layers).set_stroke(width=0).set_fill(color, strength)
        for k in range(layers, 0, -1)
    ])


# ---- layout helpers: templates use these instead of fixed numbers --------------
# Long (16:9) frames are 14.2 x 8 units. In short (9:16) mode a responsive template gets an
# 8 x 14.2 frame; a template drawn for 16:9 gets a portrait frame `vertical_width` units wide.
LONG_FRAME_WIDTH = 8.0 * 16 / 9


def frame_w() -> float:
    return config.frame_width


def frame_h() -> float:
    return config.frame_height


def width_ratio() -> float:
    """Frame width relative to the 16:9 frame: 1.0 in long mode, 0.56 for a responsive short."""
    return config.frame_width / LONG_FRAME_WIDTH


def fit(mob, max_width: float | None = None, max_height: float | None = None):
    """Shrink (never grow) a mobject so it fits inside the given size."""
    if max_width and mob.width > max_width:
        mob.scale_to_fit_width(max_width)
    if max_height and mob.height > max_height:
        mob.scale_to_fit_height(max_height)
    return mob


def keep_inside_x(mob, margin: float = 0.3) -> bool:
    """Slide a mobject left/right so it stays inside the frame. Returns False if it is too wide."""
    half = config.frame_width / 2 - margin
    if mob.width > 2 * half:
        return False
    x = mob.get_x()
    if x + mob.width / 2 > half:
        mob.set_x(half - mob.width / 2)
    elif x - mob.width / 2 < -half:
        mob.set_x(-half + mob.width / 2)
    return True


class Template:
    name: ClassVar[str] = ""
    description: ClassVar[str] = ""
    # Short (9:16) mode: how many units of width the frame shows. 8 = the template lays itself
    # out for a narrow frame (uses frame_w()/frame_h()/fit()). A template drawn for 16:9 keeps
    # the full 14.2 by default, or a narrower value if its important content fits in it.
    vertical_width: ClassVar[float] = LONG_FRAME_WIDTH
    # "night": dark brand background with drifting dust (the original look).
    # "bright": the template draws a colourful background itself (templates/kit.py).
    theme: ClassVar[str] = "night"

    class Params(BaseModel):
        pass

    def __init_subclass__(cls, **kw):
        super().__init_subclass__(**kw)
        if cls.name:
            REGISTRY[cls.name] = cls

    def build(self, scene: "BeatScene", p: BaseModel, duration: float) -> None:  # pragma: no cover
        raise NotImplementedError


def get_template(name: str) -> type[Template]:
    from beatframe import templates  # noqa: F401  (imports all template modules)

    if name not in REGISTRY:
        known = ", ".join(sorted(REGISTRY))
        raise KeyError(f"unknown scene '{name}'. Available: {known}")
    return REGISTRY[name]


class BeatScene(MovingCameraScene):
    """Scene used for every beat. Subclassed at render time with the beat's data."""

    template_name: str = ""
    params: dict = {}
    beat_duration: float = 3.0
    seed: int = 7

    def construct(self):
        brand.register_fonts()
        random.seed(self.seed)
        np.random.seed(self.seed)
        tpl_cls = get_template(self.template_name)
        if tpl_cls.theme == "bright":      # the template paints its own coloured background
            self.camera.background_color = "#FFF6E5"
        else:
            self.camera.background_color = brand.NIGHT
            self.add(self.dust())

        tpl = tpl_cls()
        p = tpl_cls.Params.model_validate(self.params)
        tpl.build(self, p, self.beat_duration)

        # whatever time is left: keep the camera moving rather than holding a frozen frame
        rest = self.beat_duration - getattr(self.renderer, "time", 0.0)
        if rest > 0.4:
            self.play(self.camera.frame.animate(rate_func=linear).scale(0.95), run_time=rest)
        elif rest > 1 / config.frame_rate:
            self.wait(rest)

    def play(self, *animations, **kwargs):
        if animations and getattr(self.renderer, "time", 0.0) < FAST_START and all(map(_introduces, animations)):
            run_time = kwargs.get("run_time", max(getattr(a, "run_time", 1.0) for a in animations))
            if run_time > SNAP:
                kwargs["run_time"] = SNAP
        super().play(*animations, **kwargs)

    # ---- shared helpers -------------------------------------------------
    def dust(self, n: int = 70) -> VGroup:
        """Slowly drifting specks of light, so no frame is ever fully still."""
        w, h = config.frame_width, config.frame_height
        specks = VGroup()
        for _ in range(n):
            d = Dot(
                point=[random.uniform(-w / 2, w / 2), random.uniform(-h / 2, h / 2), 0],
                radius=random.uniform(0.008, 0.028),
                color=brand.PAPER,
            ).set_opacity(random.uniform(0.08, 0.35))
            d.vel = np.array([random.uniform(-0.05, 0.05), random.uniform(0.02, 0.09), 0])
            specks.add(d)

        def drift(group, dt):
            for d in group:
                d.shift(d.vel * dt)
                x, y, _ = d.get_center()
                if y > h / 2 + 0.2:
                    d.move_to([x, -h / 2 - 0.2, 0])
                if abs(x) > w / 2 + 0.2:
                    d.move_to([-np.sign(x) * w / 2, y, 0])

        specks.add_updater(drift)
        specks.set_z_index(-10)
        return specks
