"""Why touch is never contact: two rows of atoms approach, their electron clouds push
back harder and harder, and the gap never closes."""

from __future__ import annotations

import numpy as np
from manim import (
    DOWN, UP, Arrow, BackgroundRectangle, Circle, DashedLine, FadeIn, Text, ValueTracker, VGroup, linear, rate_functions,
)

from beatframe import brand
from beatframe.templates.base import Template, glow


def _atom(color):
    cloud = VGroup(*[
        Circle(radius=0.55 * (1 - k * 0.15)).set_stroke(width=0).set_fill(color, 0.05 + 0.03 * k)
        for k in range(5)
    ])
    ring = Circle(radius=0.55).set_stroke(color, 1.5, 0.45)
    core = glow(0.08, color, layers=3, strength=0.2)
    a = VGroup(cloud, ring, core)
    a.cloud, a.ring = cloud, ring
    return a


class ElectronRepulsion(Template):
    name = "electron_repulsion"
    description = "Two rows of atoms approach; electron clouds repel; the gap never closes"

    class Params(Template.Params):
        top_label: str = "your finger"
        bottom_label: str = "the table"
        gap_label: str = "never zero"
        show_forces: bool = True

    def build(self, scene, p, duration):
        xs = np.arange(-6.0, 6.01, 1.2)
        top = VGroup(*[_atom(brand.PAPER).move_to([x, 0, 0]) for x in xs])
        bot = VGroup(*[_atom(brand.GLOW).move_to([x + 0.6, 0, 0]) for x in xs])

        gap = ValueTracker(3.0)       # distance between the two rows' centres
        base_y = -1.5
        rng = np.random.default_rng(5)
        phases = rng.uniform(0, 2 * np.pi, (2, len(xs)))
        clock = {"t": 0.0}

        def place(group, dt):
            clock["t"] += dt / 2      # two updaters share the clock
            g = gap.get_value()
            closeness = np.clip((2.0 - g) / 0.7, 0, 1)   # 0 far ... 1 at the closest point
            for row, (grp, y) in enumerate(((top, base_y + g), (bot, base_y))):
                for k, a in enumerate(grp):
                    j = 0.04 * np.array([np.sin(8 * clock["t"] + phases[row, k]),
                                         np.cos(6 * clock["t"] + phases[row, k]), 0])
                    a.move_to([xs[k] + (0.6 if row else 0), y, 0] + j)
                    a.ring.set_stroke(brand.EMBER if closeness > 0.05 else (brand.GLOW if row else brand.PAPER),
                                      1.5 + 2.5 * closeness, 0.45 + 0.5 * closeness)

        top.add_updater(place)
        bot.add_updater(place)

        lt = Text(p.top_label, font=brand.SANS, color=brand.PAPER).scale(0.42)
        lb = Text(p.bottom_label, font=brand.SANS, color=brand.GLOW).scale(0.42)
        lt.add_updater(lambda m: m.move_to([0, base_y + gap.get_value() + 0.95, 0]))
        lb.add_updater(lambda m: m.move_to([0, base_y - 0.95, 0]))

        scene.play(FadeIn(bot), FadeIn(top), FadeIn(lt), FadeIn(lb), run_time=min(0.8, duration * 0.12))

        approach = duration * 0.38
        scene.play(gap.animate.set_value(1.32), run_time=approach, rate_func=rate_functions.ease_in_quad)

        extras = VGroup()
        if p.show_forces:
            ups = VGroup(*[Arrow([x, base_y + 1.32 + 0.15, 0], [x, base_y + 1.32 + 0.95, 0], buff=0,
                                 color=brand.EMBER, stroke_width=4, max_tip_length_to_length_ratio=0.3)
                           for x in xs[2:-2:2]])
            downs = VGroup(*[Arrow([x + 0.6, base_y - 0.15, 0], [x + 0.6, base_y - 0.95, 0], buff=0,
                                   color=brand.EMBER, stroke_width=4, max_tip_length_to_length_ratio=0.3)
                             for x in xs[2:-2:2]])
            extras.add(ups, downs)

        seam = DashedLine([-6.8, 0, 0], [6.8, 0, 0], dash_length=0.12).set_stroke(brand.EMBER, 2, 0.7)
        seam.add_updater(lambda m: m.set_y(base_y + gap.get_value() / 2))
        gl = Text(p.gap_label, font=brand.SANS, weight="BOLD", color=brand.EMBER).scale(0.42)
        gl_bg = BackgroundRectangle(gl, color=brand.NIGHT, fill_opacity=0.85, buff=0.12)
        tag = VGroup(gl_bg, gl)
        tag.add_updater(lambda m: m.move_to([3.6, base_y + gap.get_value() / 2, 0]))
        extras.add(seam, tag)

        # push back: bounce to a slightly larger gap and keep trembling there
        scene.play(
            gap.animate(rate_func=rate_functions.there_and_back_with_pause).set_value(1.2),
            FadeIn(extras),
            run_time=min(1.2, duration * 0.18),
        )
        scene.play(gap.animate.set_value(1.36), run_time=min(0.6, duration * 0.08), rate_func=rate_functions.ease_out_sine)

        rest = duration - getattr(scene.renderer, "time", 0)
        if rest > 0.2:
            scene.play(
                scene.camera.frame.animate(rate_func=linear).scale(0.82).move_to([0, base_y + 0.6, 0]),
                gap.animate(rate_func=rate_functions.wiggle).set_value(1.3),
                run_time=rest,
            )
