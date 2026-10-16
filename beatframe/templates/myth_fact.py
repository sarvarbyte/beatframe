"""Myth vs fact: the myth card is struck out, then the fact card lands with a check."""

from __future__ import annotations

from manim import DOWN, UP, Create, FadeIn, GrowFromCenter, Line, VGroup

from beatframe.templates.base import Template
from beatframe.templates.kit import (
    INK, PaletteName, Budget, card, drift_camera, fh, flat_bg, fw, icon, palette, pill, vertical, wrap_label,
)


class MythFact(Template):
    name = "myth_fact"
    description = "MYTH card gets crossed out, then the FACT card appears with a check"
    theme = "bright"
    vertical_width = 8.0

    class Params(Template.Params):
        myth: str = "You only use 10% of your brain"
        fact: str = "You use almost all of it, just not all at once"
        myth_label: str = "MYTH"
        fact_label: str = "FACT"
        palette: PaletteName = "auto"

    def build(self, scene, p, duration):
        pal = palette(p.palette, scene.seed)
        flat_bg(scene, pal)
        W, H = fw(), fh()
        b = Budget(duration)
        tall = vertical()
        cw = W * (0.84 if tall else 0.42)
        chars = 18 if tall else 22

        def make(tag, text, col):
            t = wrap_label(text, 0.52 if tall else 0.48, INK, chars=chars, max_width=cw * 0.84)
            ch = t.height + 1.6
            box = card(cw, ch)
            tg = pill(tag, col, 0.42).next_to(box[-1].get_top(), DOWN, buff=0.3)
            t.next_to(tg, DOWN, buff=0.3)
            return VGroup(box, tg, t)
        myth = make(p.myth_label, p.myth, "#EF476F")
        fact = make(p.fact_label, p.fact, "#06A77D")
        if tall:
            VGroup(myth, fact).arrange(DOWN, buff=0.8).move_to([0, -0.2, 0])
        else:
            VGroup(myth, fact).arrange(buff=0.7).move_to([0, -0.1, 0])
        t_text = myth[2]
        strike = VGroup(*[Line(line.get_left() + [-0.1, 0, 0], line.get_right() + [0.1, 0, 0]).set_stroke("#EF476F", 7)
                          for line in t_text])
        bad = icon("cross", 0.8).move_to(myth[0][-1].get_corner(UP + [1, 0, 0]) + [-0.45, -0.45, 0])
        good = icon("check", 0.8).move_to(fact[0][-1].get_corner(UP + [1, 0, 0]) + [-0.45, -0.45, 0])

        scene.play(FadeIn(myth, shift=UP * 0.4), run_time=b.t(0.12, 0.6))
        scene.wait(b.t(0.12, 0.8))
        scene.play(Create(strike), GrowFromCenter(bad), myth.animate.set_opacity(0.85), run_time=b.t(0.12, 0.6))
        scene.play(FadeIn(fact, shift=UP * 0.4, scale=0.92), run_time=b.t(0.12, 0.6))
        scene.play(GrowFromCenter(good), run_time=b.t(0.06, 0.35))
        drift_camera(scene, duration)
