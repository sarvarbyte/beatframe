"""A big number that counts up on a bright card, with an icon, caption and source."""

from __future__ import annotations

import re

import numpy as np
from manim import BOLD, DOWN, UP, FadeIn, GrowFromCenter, Text, ValueTracker, VGroup, always_redraw, smooth

from beatframe import brand
from beatframe.templates.base import Template
from beatframe.templates.kit import (
    INK, IconName, PaletteName, Budget, card, drift_camera, fh, flat_bg, fw, icon, label, palette, vertical, wrap_label,
)


class StatPop(Template):
    name = "stat_pop"
    description = "Bright stat card: a number counts up, with icon, caption and source"
    theme = "bright"
    vertical_width = 8.0

    class Params(Template.Params):
        number: str = "70%"          # a leading number counts up; the rest is kept as written
        caption: str = "of what you feel is predicted"
        source: str = ""
        icon: IconName = "brain"
        count: bool = True
        palette: PaletteName = "auto"

    def build(self, scene, p, duration):
        pal = palette(p.palette, scene.seed)
        flat_bg(scene, pal)
        W, H = fw(), fh()
        b = Budget(duration)
        cw = W * (0.82 if vertical() else 0.5)
        chh = min(H * 0.62, cw * (1.25 if vertical() else 0.85))
        box = card(cw, chh).move_to([0, -0.1, 0])
        top = box[-1].get_top()
        ico = icon(p.icon, min(1.4, chh * 0.24), pal).move_to(top + DOWN * chh * 0.2) if p.icon != "none" else None

        m = re.match(r"\s*([\d][\d.,]*)(.*)", p.number)
        target = float(m.group(1).replace(",", "")) if m and p.count else None
        tail = m.group(2) if m and p.count else ""
        decimals = len(m.group(1).split(".")[1]) if m and "." in m.group(1) else 0
        sep = "," in (m.group(1) if m else "")
        tracker = ValueTracker(0)
        ny = top[1] - chh * (0.47 if ico else 0.36)

        def num():
            if target is None:
                s = p.number
            else:
                v = tracker.get_value()
                s = (f"{v:,.{decimals}f}" if sep else f"{v:.{decimals}f}") + tail
            t = Text(s, font=brand.SANS, weight=BOLD, color=pal["a"]).scale(1.9 if vertical() else 1.7)
            if t.width > cw * 0.86:
                t.scale_to_fit_width(cw * 0.86)
            return t.move_to([0, ny, 0])
        n = always_redraw(num)
        cap = wrap_label(p.caption, 0.5, INK, chars=20 if vertical() else 30, max_width=cw * 0.86)
        cap.move_to([0, ny - 1.0 - cap.height / 2 + 0.2, 0])
        src = label(p.source, 0.3, "#6B7280", bold=False, max_width=cw * 0.86).next_to(box[-1].get_bottom(), UP, buff=0.3) if p.source else None

        scene.play(FadeIn(box, shift=UP * 0.4, scale=0.9), run_time=b.t(0.1, 0.5))
        if ico:
            scene.play(GrowFromCenter(ico), run_time=b.t(0.07, 0.35))
        scene.add(n)
        scene.play(tracker.animate.set_value(target or 0), run_time=b.t(0.28, 1.4), rate_func=smooth)
        n.clear_updaters()
        scene.play(FadeIn(cap, shift=UP * 0.15), *([FadeIn(src)] if src else []), run_time=b.t(0.1, 0.5))
        drift_camera(scene, duration)
