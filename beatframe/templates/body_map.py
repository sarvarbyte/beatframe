"""A friendly body outline with one part lit up and labelled (brain, eyes, heart, stomach...)."""

from __future__ import annotations

from typing import Literal

import numpy as np
from manim import DOWN, LEFT, RIGHT, UP, Circle, Create, FadeIn, GrowFromCenter, Line, RoundedRectangle, VGroup, linear

from beatframe.templates.base import Template
from beatframe.templates.kit import (
    DRIFT, INK, WHITE, PaletteName, Budget, brain_shape, caption_bar, drift_camera, fh, flat_bg, fw, palette, pill, vertical,
    wrap_label,
)

Part = Literal["brain", "eyes", "ears", "mouth", "heart", "lungs", "stomach", "hands", "skin", "spine", "legs", "feet"]


def body(scale: float) -> tuple[VGroup, dict]:
    s = scale
    head = Circle(radius=0.62 * s).move_to([0, 2.55 * s, 0])
    neck = RoundedRectangle(width=0.36 * s, height=0.35 * s, corner_radius=0.1 * s).move_to([0, 1.85 * s, 0])
    torso = RoundedRectangle(width=1.7 * s, height=2.3 * s, corner_radius=0.5 * s).move_to([0, 0.6 * s, 0])
    arms = VGroup(*[RoundedRectangle(width=0.42 * s, height=2.2 * s, corner_radius=0.2 * s).rotate(sd * 0.18).move_to([sd * 1.15 * s, 0.45 * s, 0])
                    for sd in (-1, 1)])
    legs = VGroup(*[RoundedRectangle(width=0.55 * s, height=2.4 * s, corner_radius=0.25 * s).move_to([sd * 0.42 * s, -1.75 * s, 0])
                    for sd in (-1, 1)])
    g = VGroup(legs, arms, torso, neck, head).set_stroke(INK, 6).set_fill(WHITE, 1)
    spots = {
        "brain": np.array([0, 2.75 * s, 0]), "eyes": np.array([0.22 * s, 2.6 * s, 0]), "ears": np.array([0.6 * s, 2.5 * s, 0]),
        "mouth": np.array([0.15 * s, 2.25 * s, 0]), "heart": np.array([-0.3 * s, 1.05 * s, 0]), "lungs": np.array([0.35 * s, 1.0 * s, 0]),
        "stomach": np.array([0.1 * s, 0.2 * s, 0]), "hands": np.array([1.35 * s, -0.6 * s, 0]), "skin": np.array([-1.2 * s, 0.6 * s, 0]),
        "spine": np.array([0, 0.9 * s, 0]), "legs": np.array([0.42 * s, -1.6 * s, 0]), "feet": np.array([0.42 * s, -2.85 * s, 0]),
    }
    return g, spots


class BodyMap(Template):
    name = "body_map"
    description = "Body outline with one part glowing and labelled (brain, eyes, heart, stomach, hands...)"
    theme = "bright"
    vertical_width = 8.0

    class Params(Template.Params):
        part: Part = "brain"
        label: str = "your brain"
        caption: str = ""
        palette: PaletteName = "auto"

    def build(self, scene, p, duration):
        pal = palette(p.palette, scene.seed)
        flat_bg(scene, pal)
        W, H = fw(), fh()
        b = Budget(duration)
        tall = vertical()
        s = (H * 0.52 if tall else H * 0.78) / 6.4
        fig, spots = body(s)
        cx = 0 if tall else -W * 0.16
        before = fig.get_center()
        fig.move_to([cx, -0.3 if tall else -0.2, 0])
        spot = spots[p.part] + (fig.get_center() - before)
        col = pal["a"]
        glowc = VGroup(*[Circle(radius=0.22 * s * k).set_stroke(width=0).set_fill(col, 0.18) for k in (3.2, 2.2, 1.4)],
                       Circle(radius=0.2 * s).set_stroke(WHITE, 4).set_fill(col, 1)).move_to(spot)
        if p.part == "brain":
            glowc.add(brain_shape(0.9 * s).move_to(spot))
        tag = pill(p.label, col, 0.5)
        if tall:
            tag.move_to([0, fig.get_top()[1] + 0.8, 0])
        else:
            tag.move_to([W * 0.2, spot[1] + 0.4, 0])
        lead = Line(spot, tag.get_center()).set_stroke(col, 5)
        lead.put_start_and_end_on(spot, tag.get_bottom() if tall else tag.get_left())
        items = []
        if p.caption:
            cap = wrap_label(p.caption, 0.5, INK, chars=20 if tall else 26, max_width=W * (0.8 if tall else 0.36))
            cap.move_to([0, fig.get_bottom()[1] - 0.7 - cap.height / 2, 0] if tall else [W * 0.2, spot[1] - 1.0 - cap.height / 2, 0])
            items.append(cap)
        scene.play(FadeIn(fig, shift=UP * 0.3), run_time=b.t(0.12, 0.6))
        scene.play(GrowFromCenter(glowc), run_time=b.t(0.1, 0.5))
        scene.play(Create(lead), FadeIn(tag, shift=UP * 0.1), run_time=b.t(0.1, 0.5))
        if items:
            scene.play(FadeIn(items[0], shift=UP * 0.1), run_time=b.t(0.08, 0.4))
        pulse = glowc[0]
        rest = duration - getattr(scene.renderer, "time", 0)
        if rest > 0.3:
            from manim import rate_functions
            scene.play(pulse.animate(rate_func=rate_functions.there_and_back).scale(1.35),
                       scene.camera.frame.animate(rate_func=linear).scale(DRIFT), run_time=rest)
