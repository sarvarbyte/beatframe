"""Events on a timeline ('1904|Olympic marathon'): horizontal in 16:9, vertical in 9:16."""

from __future__ import annotations

import numpy as np
from manim import DOWN, LEFT, RIGHT, UP, Circle, Create, FadeIn, GrowFromCenter, Line, VGroup, linear

from beatframe.templates.base import Template
from beatframe.templates.kit import (
    INK, WHITE, PaletteName, Budget, caption_bar, card, drift_camera, fh, flat_bg, fw, label, palette, parse_pair,
    vertical, wrap_label,
)


class Timeline(Template):
    name = "timeline"
    description = "2-5 dated events ('year|what happened') appearing along a timeline"
    theme = "bright"
    vertical_width = 8.0

    class Params(Template.Params):
        title: str = ""
        events: list[str] = ["300,000 BC|First humans", "10,000 BC|First farms", "1879|Light bulb"]
        palette: PaletteName = "auto"

    def build(self, scene, p, duration):
        pal = palette(p.palette, scene.seed)
        flat_bg(scene, pal)
        W, H = fw(), fh()
        b = Budget(duration)
        ev = [parse_pair(x, "") for x in p.events[:5]] or [("", "…")]
        n = len(ev)
        tall = vertical()
        top_room = 1.6 if p.title else 0.3
        colors = [pal["a"], pal["b"], pal["c"], pal["d"]]
        if p.title:
            scene.play(FadeIn(caption_bar(p.title, pal), shift=UP * 0.2), run_time=b.t(0.08, 0.5))
        if tall:
            y0, y1 = H / 2 - top_room - 1.0, -H / 2 + 1.2
            x = -W * 0.3
            pts = [np.array([x, y0 + (y1 - y0) * (i / max(n - 1, 1)), 0]) for i in range(n)]
            axis = Line([x, y0 + 0.4, 0], [x, y1 - 0.4, 0])
        else:
            x0, x1 = -W * 0.38, W * 0.38
            y = -0.2 - top_room / 3
            pts = [np.array([x0 + (x1 - x0) * (i / max(n - 1, 1)), y, 0]) for i in range(n)]
            axis = Line([x0 - 0.5, y, 0], [x1 + 0.5, y, 0])
        axis.set_stroke(INK, 7, 0.75)
        scene.play(Create(axis), run_time=b.t(0.1, 0.6), rate_func=linear)
        each = b.t(0.62 / n, 0.7)
        for i, ((when, what), pt) in enumerate(zip(ev, pts)):
            col = colors[i % 4]
            dot = VGroup(Circle(radius=0.26).set_stroke(WHITE, 6).set_fill(col, 1)).move_to(pt)
            year = label(when, 0.5 if tall else 0.46, col)
            text = wrap_label(what, 0.42 if tall else 0.36, INK, chars=18 if tall else 14, max_width=W * (0.5 if tall else 0.2))
            if tall:
                year.next_to(dot, RIGHT, buff=0.4).shift(UP * 0.2)
                text.next_to(year, DOWN, buff=0.12).align_to(year, LEFT)
            else:
                side = UP if i % 2 == 0 else DOWN
                year.next_to(dot, side, buff=0.35)
                text.next_to(year, side, buff=0.15)
            scene.play(GrowFromCenter(dot), FadeIn(year, shift=-0.2 * (RIGHT if tall else (UP if i % 2 == 0 else DOWN))),
                       FadeIn(text), run_time=each)
        drift_camera(scene, duration)
