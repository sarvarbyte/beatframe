"""Efference copy: the brain predicts the touch and subtracts it. Self-touch cancels; someone else's doesn't."""

import numpy as np
from manim import (
    DOWN, LEFT, RIGHT, UP, Arrow, FadeIn, FunctionGraph, Line, Text, ValueTracker, VGroup, linear,
    rate_functions, always_redraw,
)

from beatframe import brand
from beatframe.templates.base import Template, glow


def _wave(x0, x1, y, amp, color, phase_t, width=3, opacity=1.0):
    return FunctionGraph(lambda x: y + amp * np.sin(4.2 * x - phase_t) * np.exp(-((x - (x0 + x1) / 2) ** 2) / 2.2),
                         x_range=[x0, x1, 0.02]).set_stroke(color, width, opacity)


class Prediction(Template):
    name = "prediction"
    description = "Prediction wave minus touch wave: self-touch cancels out, someone else's does not"

    class Params(Template.Params):
        mode: str = "self"                         # self | other
        predicted_label: str = "what your brain predicts"
        felt_label: str = "what your skin reports"
        result_label: str = "what you feel"
        verdict: str = ""                          # default: "almost nothing" / "the full tickle"

    def build(self, scene, p, duration):
        self_touch = p.mode != "other"
        verdict = p.verdict or ("almost nothing" if self_touch else "the full tickle")
        t = ValueTracker(0.0)
        pred_amp = ValueTracker(0.0)
        res_amp = ValueTracker(0.9)

        L0, L1, R0, R1 = -6.6, -1.4, 1.2, 6.4
        pred = always_redraw(lambda: _wave(L0, L1, 1.35, pred_amp.get_value(), brand.GLOW, t.get_value()))
        felt = always_redraw(lambda: _wave(L0, L1, -1.25, 0.9, brand.EMBER, t.get_value()))
        res = always_redraw(lambda: _wave(R0, R1, 0.05, res_amp.get_value(), brand.PAPER, t.get_value(), width=4))
        guides = VGroup(*[Line([a, y, 0], [b, y, 0]).set_stroke(brand.DIM, 1, 0.4)
                          for a, b, y in ((L0, L1, 1.35), (L0, L1, -1.25), (R0, R1, 0.05))])

        pl = Text(p.predicted_label, font=brand.SANS, color=brand.GLOW).scale(0.4).move_to([(L0 + L1) / 2, 2.45, 0])
        fl = Text(p.felt_label, font=brand.SANS, color=brand.EMBER).scale(0.4).move_to([(L0 + L1) / 2, -2.35, 0])
        rl = Text(p.result_label, font=brand.SANS, color=brand.PAPER).scale(0.42).move_to([(R0 + R1) / 2, 1.25, 0])
        minus = Text("−", font=brand.SERIF, weight="BOLD", color=brand.DIM).scale(1.2).move_to([(L0 + L1) / 2, 0.05, 0])
        arrow = Arrow([L1 + 0.15, 0.05, 0], [R0 - 0.15, 0.05, 0], buff=0, stroke_width=4).set_color(brand.DIM)
        vd = Text(verdict, font=brand.SERIF, weight="BOLD", color=brand.EMBER if not self_touch else brand.PAPER).scale(0.75)
        vd.move_to([(R0 + R1) / 2, -1.25, 0])
        if not self_touch:
            pl_note = Text("(no prediction: it's not your move)", font=brand.SANS, color=brand.DIM).scale(0.32)
            pl_note.next_to(pl, DOWN, buff=0.12)
        else:
            pl_note = VGroup()

        def tick(m, dt):
            m.increment_value(dt * 4.0)
        t.add_updater(tick)
        scene.add(t)

        scene.play(FadeIn(guides), FadeIn(felt), FadeIn(fl), run_time=min(1.0, duration * 0.12))
        scene.play(FadeIn(pred), FadeIn(pl), FadeIn(pl_note), FadeIn(minus), run_time=0.6)
        if self_touch:
            scene.play(pred_amp.animate.set_value(0.9), run_time=min(1.0, duration * 0.12))
        scene.play(FadeIn(arrow), FadeIn(res), FadeIn(rl), run_time=0.6)
        if self_touch:
            scene.play(res_amp.animate(rate_func=rate_functions.ease_out_cubic).set_value(0.08),
                       run_time=min(1.4, duration * 0.15))
        else:
            scene.play(res_amp.animate.set_value(1.1), run_time=0.6)
        scene.play(FadeIn(vd, shift=UP * 0.1), run_time=0.5)
        rest = duration - scene.renderer.time
        if rest > 0.05:
            scene.wait(rest)
