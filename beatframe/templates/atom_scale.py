"""How empty an atom is: a grain-sized nucleus in a stadium-sized cloud."""

import numpy as np
from manim import (
    DOWN, UP, Circle, DashedLine, Dot, Ellipse, FadeIn, GrowFromCenter, Text, VGroup, linear, rate_functions,
)

from beatframe import brand
from beatframe.templates.base import Template, glow


class AtomScale(Template):
    name = "atom_scale"
    description = "A stadium-sized electron cloud around a grain-sized nucleus"

    class Params(Template.Params):
        nucleus_label: str = "nucleus: a grain of sand"
        atom_label: str = "the whole atom: a football stadium"
        caption: str = "almost entirely empty"

    def build(self, scene, p, duration):
        # stadium: running track + pitch, seen at an angle
        track = VGroup(*[Ellipse(width=11 - k * 0.5, height=4.6 - k * 0.22).set_stroke(brand.DIM, 1.5, 0.6 - k * 0.08)
                         for k in range(5)])
        pitch = Ellipse(width=8.6, height=3.4).set_stroke(brand.PAPER, 1, 0.25).set_fill(brand.PAPER, 0.03)
        stadium = VGroup(track, pitch).shift(DOWN * 0.3)

        # the electron cloud: a soft haze of moving dots filling the stadium
        rng = np.random.default_rng(4)
        cloud = VGroup()
        for _ in range(420):
            r = np.sqrt(rng.uniform(0, 1))
            a = rng.uniform(0, 2 * np.pi)
            d = Dot([5.2 * r * np.cos(a), 2.2 * r * np.sin(a) - 0.3, 0], radius=0.032, color=brand.GLOW)
            d.set_opacity(rng.uniform(0.15, 0.55))
            d.a, d.r, d.w = a, r, rng.uniform(0.3, 0.9) * rng.choice([-1, 1])
            cloud.add(d)

        def swirl(g, dt):
            for d in g:
                d.a += d.w * dt
                d.move_to([5.2 * d.r * np.cos(d.a), 2.2 * d.r * np.sin(d.a) - 0.3, 0])

        cloud.add_updater(swirl)

        nucleus = glow(0.035, brand.EMBER, layers=5, strength=0.3).move_to([0, -0.3, 0])
        pointer = DashedLine([0, -0.25, 0], [2.6, 1.8, 0], dash_length=0.08).set_stroke(brand.EMBER, 1.5)
        nl = Text(p.nucleus_label, font=brand.SANS, color=brand.EMBER).scale(0.42).next_to(pointer.get_end(), UP, buff=0.1)
        al = Text(p.atom_label, font=brand.SANS, color=brand.PAPER).scale(0.42).move_to([0, -3.1, 0])
        cap = Text(p.caption, font=brand.SERIF, weight="BOLD", color=brand.PAPER).scale(0.8).move_to([0, 3.0, 0])

        scene.play(FadeIn(stadium), FadeIn(al), run_time=min(1.0, duration * 0.15))
        scene.play(GrowFromCenter(nucleus), run_time=min(0.6, duration * 0.08))
        scene.play(FadeIn(pointer), FadeIn(nl, shift=UP * 0.1), run_time=min(0.8, duration * 0.12))
        scene.play(FadeIn(cloud, lag_ratio=0.02), run_time=min(1.4, duration * 0.18))
        scene.play(FadeIn(cap, shift=DOWN * 0.1), run_time=min(0.7, duration * 0.1))
        rest = duration - getattr(scene.renderer, "time", 0)
        if rest > 0.2:
            scene.play(scene.camera.frame.animate(rate_func=linear).scale(0.9), run_time=rest)
