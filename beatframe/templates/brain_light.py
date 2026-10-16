"""A big friendly brain; one region lights up, sparks fly, a label points at it."""

from __future__ import annotations

from typing import Literal

import numpy as np
from manim import DOWN, UP, Circle, Create, Dot, FadeIn, GrowFromCenter, Line, VGroup, linear, rate_functions

from beatframe.templates.base import Template
from beatframe.templates.kit import (
    DRIFT, INK, WHITE, PaletteName, Budget, brain_shape, caption_bar, fh, flat_bg, fw, palette, pill, vertical, wrap_label,
)

Region = Literal["front", "back", "top", "bottom", "left", "right", "center", "whole"]
OFFSETS = {"front": (0.55, 0.05), "back": (-0.55, 0.0), "top": (0.0, 0.42), "bottom": (0.1, -0.35),
           "left": (-0.4, 0.25), "right": (0.4, 0.25), "center": (0.0, 0.0), "whole": (0.0, 0.05)}


class BrainLight(Template):
    name = "brain_light"
    description = "Big brain with one region lighting up (front, back, top...), sparks and a label"
    theme = "bright"
    vertical_width = 8.0

    class Params(Template.Params):
        region: Region = "front"
        label: str = "planning & decisions"
        caption: str = ""
        palette: PaletteName = "auto"

    def build(self, scene, p, duration):
        pal = palette(p.palette, scene.seed)
        flat_bg(scene, pal)
        W, H = fw(), fh()
        b = Budget(duration)
        tall = vertical()
        size = min(W * 0.62, H * 0.42) if tall else min(W * 0.34, H * 0.62)
        cx = 0 if tall else -W * 0.16
        brain = brain_shape(size).move_to([cx, 0.3 if tall else 0.0, 0])
        r = size / 2
        ox, oy = OFFSETS[p.region]
        spot = brain.get_center() + np.array([ox * r, oy * r, 0])
        col = pal["a"]
        rad = r * (1.05 if p.region == "whole" else 0.42)
        glowc = VGroup(*[Circle(radius=rad * k).set_stroke(width=0).set_fill(col, 0.16) for k in (1.6, 1.15, 0.75)]).move_to(spot)
        rng = np.random.default_rng(scene.seed)
        sparks = VGroup()
        for _ in range(14):
            a = rng.uniform(0, 2 * np.pi)
            d0, d1 = rad * 0.6, rad * rng.uniform(1.4, 2.0)
            sparks.add(Line(spot + d0 * np.array([np.cos(a), np.sin(a), 0]), spot + d1 * np.array([np.cos(a), np.sin(a), 0]))
                       .set_stroke("#FFD166", 5))
        tag = pill(p.label, INK, 0.5)
        if tall:
            tag.next_to(brain, UP, buff=0.7)
        else:
            tag.move_to([W * 0.22, spot[1] + 0.6, 0])
        lead = Line(spot, tag.get_bottom() if tall else tag.get_left()).set_stroke(INK, 4)
        if p.caption:
            cap = wrap_label(p.caption, 0.5, INK, chars=20 if tall else 24, max_width=W * (0.8 if tall else 0.36))
            cap.next_to(brain, DOWN, buff=0.7) if tall else cap.move_to([W * 0.22, spot[1] - 0.8 - cap.height / 2, 0])
        scene.play(FadeIn(brain, scale=0.85), run_time=b.t(0.12, 0.6))
        scene.play(GrowFromCenter(glowc), run_time=b.t(0.1, 0.5))
        scene.play(Create(sparks, lag_ratio=0.05), Create(lead), FadeIn(tag, shift=UP * 0.1), run_time=b.t(0.12, 0.6))
        if p.caption:
            scene.play(FadeIn(cap, shift=UP * 0.1), run_time=b.t(0.08, 0.4))
        rest = duration - getattr(scene.renderer, "time", 0)
        if rest > 0.3:
            scene.play(glowc.animate(rate_func=rate_functions.there_and_back).scale(1.18), sparks.animate.set_opacity(0.3),
                       scene.camera.frame.animate(rate_func=linear).scale(DRIFT), run_time=rest)
