"""An opening hook: a big question, a puzzled stick figure, question marks floating around."""

from __future__ import annotations

import numpy as np
from manim import UP, FadeIn, GrowFromCenter, VGroup, rate_functions

from beatframe.templates.base import Template
from beatframe.templates.kit import (
    INK, PaletteName, Budget, Stick, add_stick, background, bubble, drift_camera, fh, floor_y, fw, label, palette,
    vertical, wrap_label,
)


class QuestionHook(Template):
    name = "question_hook"
    description = "Hook opener: big question text, a puzzled stick figure and floating question marks"
    theme = "bright"
    vertical_width = 8.0

    class Params(Template.Params):
        question: str = "Why do you forget why you walked into a room?"
        highlight: str = "forget"
        palette: PaletteName = "auto"

    def build(self, scene, p, duration):
        pal = palette(p.palette, scene.seed)
        scene.add(background(pal))
        W, H = fw(), fh()
        b = Budget(duration)
        tall = vertical()
        hot = p.highlight.strip()
        q = wrap_label(p.question, 0.95 if tall else 0.85, INK, chars=14 if tall else 26, max_width=W * 0.86,
                       t2c={hot: pal["a"]} if hot else None)
        q.move_to([0, H / 2 - H * 0.2 - q.height / 2 + 0.6, 0])
        st = add_stick(scene, Stick(x=0, accent=pal["a"], face="thinking"))
        rng = np.random.default_rng(scene.seed)
        marks = VGroup(*[label("?", rng.uniform(0.6, 1.1), [pal["a"], pal["b"], pal["c"], pal["d"]][i % 4])
                         .move_to([rng.uniform(-W * 0.42, W * 0.42), rng.uniform(floor_y() + 0.8, q.get_bottom()[1] - 0.5), 0])
                         for i in range(7)])
        marks = VGroup(*[m for m in marks if abs(m.get_x()) > 1.2])
        scene.play(FadeIn(q, shift=UP * 0.3), run_time=b.t(0.15, 0.7))
        scene.play(st.arm_r.animate.set_value(2.6), st.tilt.animate.set_value(-0.2),
                   *[GrowFromCenter(m) for m in marks], run_time=b.t(0.15, 0.6))
        bub = bubble(label("?", 0.9, pal["b"]), "thought")
        head = st.head_top()
        y = min(head[1] + 0.75, q.get_bottom()[1] - bub.height / 2 - 0.2)   # never over the question
        bub.move_to([head[0] + 1.05 + max(0, head[1] + 0.75 - y) * 0.35, y, 0])
        scene.play(GrowFromCenter(bub), run_time=b.t(0.07, 0.35))
        rest = duration - getattr(scene.renderer, "time", 0)
        if rest > 0.3:
            scene.play(*[m.animate(rate_func=rate_functions.there_and_back).shift(UP * 0.3) for m in marks],
                       st.tilt.animate(rate_func=rate_functions.there_and_back).set_value(0.1), run_time=rest)
