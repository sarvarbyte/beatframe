"""3-5 steps of a process ('icon|text'), lit one after another; optional loop back to the start.
A row in 16:9, a column in 9:16."""

from __future__ import annotations

import numpy as np
from manim import DOWN, LEFT, RIGHT, UP, Arrow, CurvedArrow, FadeIn, GrowArrow, GrowFromCenter, VGroup

from beatframe.templates.base import Template
from beatframe.templates.kit import (
    ICONS, INK, PaletteName, Budget, caption_bar, card, drift_camera, fh, flat_bg, fw, icon, palette, parse_pair,
    vertical, wrap_label,
)


class ProcessCycle(Template):
    name = "process_cycle"
    description = "3-5 process steps ('icon|text') lighting up in order, optionally looping back"
    theme = "bright"
    vertical_width = 8.0

    class Params(Template.Params):
        title: str = ""
        steps: list[str] = ["sun|Daylight", "clock|Body clock", "moon|Melatonin", "zzz|Sleep"]
        loop: bool = True
        palette: PaletteName = "auto"

    def build(self, scene, p, duration):
        pal = palette(p.palette, scene.seed)
        flat_bg(scene, pal)
        W, H = fw(), fh()
        b = Budget(duration)
        steps = [parse_pair(x, "star") for x in p.steps[:5]] or [("star", "…")]
        n = len(steps)
        tall = vertical()
        colors = [pal["a"], pal["b"], pal["c"], pal["d"]]
        top_room = 1.6 if p.title else 0.4
        if tall:
            ch = min(1.5, (H - top_room - 1.2 - 0.6 * (n - 1)) / n)
            cw = W * 0.7
        else:
            cw = min(2.6, (W * 0.88 - 0.7 * (n - 1)) / n)
            ch = cw * 1.1
        nodes = VGroup()
        for i, (ic, text) in enumerate(steps):
            box = card(cw, ch)
            if tall:
                ico = icon(ic if ic in ICONS else "star", ch * 0.6, pal).move_to(box[-1].get_left() + RIGHT * ch * 0.55)
                t = wrap_label(text, 0.48, INK, chars=16, max_width=cw - ch * 1.2).next_to(ico, RIGHT, buff=0.35)
            else:
                ico = icon(ic if ic in ICONS else "star", cw * 0.42, pal).move_to(box[-1].get_center() + UP * ch * 0.14)
                t = wrap_label(text, 0.38, INK, chars=12, max_width=cw * 0.86).next_to(ico, DOWN, buff=0.25)
            nodes.add(VGroup(box, ico, t))
        nodes.arrange(DOWN if tall else RIGHT, buff=0.6 if tall else 0.7).move_to([0, -top_room / 2 + 0.2, 0])
        arrows = VGroup(*[Arrow(nodes[i].get_bottom() if tall else nodes[i].get_right(),
                                nodes[i + 1].get_top() if tall else nodes[i + 1].get_left(), buff=0.08, stroke_width=7,
                                max_tip_length_to_length_ratio=0.45).set_color(INK) for i in range(n - 1)])
        if p.title:
            scene.play(FadeIn(caption_bar(p.title, pal), shift=UP * 0.2), run_time=b.t(0.08, 0.5))
        each = b.t(0.62 / n, 0.7)
        for i in range(n):
            anims = [FadeIn(nodes[i], shift=(DOWN if tall else LEFT) * -0.3, scale=0.9)]
            if i:
                anims.append(GrowArrow(arrows[i - 1]))
            scene.play(*anims, run_time=each)
            scene.play(nodes[i][0][-1].animate.set_stroke(colors[i % 4], 8), run_time=min(0.2, each / 2))
        if p.loop and n > 2:
            if tall:
                start, end = nodes[-1].get_left() + LEFT * 0.1, nodes[0].get_left() + LEFT * 0.1
                back = CurvedArrow(start, end, angle=-1.2, stroke_width=6).set_color(pal["a"])
            else:
                start, end = nodes[-1].get_bottom() + DOWN * 0.1, nodes[0].get_bottom() + DOWN * 0.1
                back = CurvedArrow(start, end, angle=-0.9, stroke_width=6).set_color(pal["a"])
            scene.play(FadeIn(back), run_time=b.t(0.08, 0.5))
        drift_camera(scene, duration)
