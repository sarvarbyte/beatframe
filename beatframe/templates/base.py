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
)
from pydantic import BaseModel

from beatframe import brand

REGISTRY: dict[str, type["Template"]] = {}


def glow(radius: float, color: str, layers: int = 6, strength: float = 0.18) -> VGroup:
    """A soft light: a solid core with fading halos around it."""
    from manim import Circle

    halo = VGroup(*[
        Circle(radius=radius * (1 + 0.55 * k)).set_stroke(width=0).set_fill(color, strength * (1 - k / layers))
        for k in range(1, layers + 1)
    ])
    core = Circle(radius=radius).set_stroke(width=0).set_fill(color, 1)
    return VGroup(halo, core)


class Template:
    name: ClassVar[str] = ""
    description: ClassVar[str] = ""

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
        self.camera.background_color = brand.NIGHT
        self.add(self.dust())

        tpl_cls = get_template(self.template_name)
        tpl = tpl_cls()
        p = tpl_cls.Params.model_validate(self.params)
        tpl.build(self, p, self.beat_duration)

        elapsed = getattr(self.renderer, "time", 0.0)
        if self.beat_duration - elapsed > 1 / config.frame_rate:
            self.wait(self.beat_duration - elapsed)

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
