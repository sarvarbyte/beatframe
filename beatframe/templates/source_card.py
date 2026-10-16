"""A key number from a study: it counts up, the citation sits underneath."""

import re

from manim import BOLD, DOWN, UP, FadeIn, Line, Text, ValueTracker, VGroup, always_redraw, linear, smooth

from beatframe import brand
from beatframe.templates.kit import DRIFT
from beatframe.templates.base import Template, fit, frame_w, glow


class SourceCard(Template):
    name = "source_card"
    description = "Counting number + caption + study citation"
    vertical_width = 8.0

    class Params(Template.Params):
        number: str = "13 nm"            # leading number counts up; the rest is the unit
        caption: str = "the smallest wrinkle a fingertip could feel"
        study: str = "Skedung et al., Scientific Reports (2013)"
        count: bool = True               # false: show the number as written (years, "#1"...)

    def build(self, scene, p, duration):
        m = re.match(r"\s*([\d.,]+)\s*(.*)", p.number)
        target = float(m.group(1).replace(",", "")) if m and p.count else None
        unit = m.group(2) if m and p.count else p.number
        decimals = len(m.group(1).split(".")[1]) if m and "." in m.group(1) else 0

        tracker = ValueTracker(0)

        def number_mob():
            val = tracker.get_value()
            txt = f"{val:,.{decimals}f}" if target is not None else ""
            full = f"{txt} {unit}".strip()
            num = Text(full, font=brand.SERIF, weight=BOLD, color=brand.GLOW).scale(2.0)
            return fit(num, max_width=frame_w() * 0.88).move_to(UP * 0.6)

        num = always_redraw(number_mob)
        rule = Line([-3.2, 0, 0], [3.2, 0, 0]).set_stroke(brand.DIM, 2).shift(DOWN * 0.75)
        cap = fit(Text(p.caption, font=brand.SANS, color=brand.PAPER).scale(0.5), max_width=frame_w() * 0.88)
        cap.next_to(rule, DOWN, buff=0.35)
        src = fit(Text(p.study, font=brand.SANS, color=brand.DIM).scale(0.36), max_width=frame_w() * 0.88)
        src.next_to(cap, DOWN, buff=0.3)
        light = glow(0.06, brand.EMBER).move_to(rule.get_start())

        scene.add(num)
        count = min(1.6, duration * 0.35)
        scene.play(
            tracker.animate.set_value(target or 0),
            rule.animate.set_stroke(brand.GLOW, 2),
            light.animate.move_to(rule.get_end()),
            run_time=count, rate_func=smooth,
        )
        scene.play(FadeIn(cap, shift=UP * 0.1), run_time=min(0.6, duration * 0.12))
        scene.play(FadeIn(src), run_time=min(0.5, duration * 0.1))
        num.clear_updaters()
        rest = duration - getattr(scene.renderer, "time", 0)
        if rest > 0.2:
            scene.play(
                scene.camera.frame.animate.scale(DRIFT),
                light.animate.move_to(rule.get_start()),
                run_time=rest, rate_func=linear,
            )
