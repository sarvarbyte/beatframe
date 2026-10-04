"""The rubber hand illusion: hidden real hand, visible rubber hand, brushed in sync."""

import numpy as np
from manim import (
    DOWN, LEFT, RIGHT, UP, FadeIn, Line, Rectangle, RoundedRectangle, Text, ValueTracker, VGroup,
    linear, rate_functions,
)

from beatframe import brand
from beatframe.templates.base import Template, soft_glow


def _hand(color, fill=0.05):
    palm = RoundedRectangle(width=1.5, height=1.7, corner_radius=0.4)
    fingers = VGroup(*[RoundedRectangle(width=0.32, height=h, corner_radius=0.15)
                       .next_to(palm, UP, buff=-0.15).shift(RIGHT * x)
                       for x, h in ((-0.54, 1.0), (-0.18, 1.25), (0.18, 1.2), (0.54, 0.95))])
    thumb = RoundedRectangle(width=0.34, height=0.95, corner_radius=0.16).rotate(0.8)
    thumb.move_to(palm.get_left() + np.array([-0.2, 0.15, 0]))
    h = VGroup(palm, fingers, thumb)
    h.set_stroke(color, 2.4).set_fill(color, fill)
    return h


def _brush():
    handle = RoundedRectangle(width=0.16, height=1.3, corner_radius=0.06).set_stroke(brand.PAPER, 2).set_fill(brand.NIGHT, 1)
    tuft = VGroup(*[Line(UP * 0, DOWN * 0.38).shift(RIGHT * dx) for dx in np.linspace(-0.12, 0.12, 6)])
    tuft.set_stroke(brand.GLOW, 2).next_to(handle, DOWN, buff=0)
    b = VGroup(handle, tuft).rotate(-0.5)
    return b


class RubberHand(Template):
    name = "rubber_hand"
    description = "Rubber hand illusion: synced brushing; phase 'transfer' moves the feeling to the fake hand"

    class Params(Template.Params):
        phase: str = "sync"            # sync | transfer
        real_label: str = "your real hand (hidden)"
        fake_label: str = "rubber hand"
        caption: str = ""

    def build(self, scene, p, duration):
        real = _hand(brand.PAPER, 0.04).move_to([-3.4, -0.4, 0])
        fake = _hand(brand.GLOW, 0.08).move_to([0.6, -0.4, 0])
        wall = Rectangle(width=0.18, height=4.8).set_stroke(brand.DIM, 2).set_fill(brand.DIM, 0.5).move_to([-1.45, 0, 0])
        cover = Rectangle(width=3.0, height=4.8).set_stroke(width=0).set_fill(brand.NIGHT, 0.55).move_to([-3.0, 0, 0])
        rl = Text(p.real_label, font=brand.SANS, color=brand.DIM).scale(0.36).move_to([-3.4, -2.75, 0])
        fl = Text(p.fake_label, font=brand.SANS, color=brand.GLOW).scale(0.36).move_to([0.6, -2.75, 0])
        eye = VGroup(Text("you look here", font=brand.SANS, color=brand.PAPER).scale(0.34)).move_to([4.4, 2.6, 0])
        gaze = Line([4.0, 2.35, 0], fake.get_top() + RIGHT * 0.4, ).set_stroke(brand.PAPER, 1.5, 0.4)
        cap = Text(p.caption or ("same strokes, same moment" if p.phase != "transfer" else "it starts to feel like yours"),
                   font=brand.SERIF, weight="BOLD", color=brand.PAPER).scale(0.65).move_to([0, 3.3, 0])

        b1, b2 = _brush(), _brush()
        k = ValueTracker(0.0)

        def place(b, hand):
            def f(m):
                s = np.sin(k.get_value() * 2 * np.pi)
                m.move_to(hand.get_center() + np.array([0.15 + 0.12 * s, 0.75 + 0.45 * s, 0]))
            return f
        b1.add_updater(place(b1, real))
        b2.add_updater(place(b2, fake))

        feel_real = soft_glow(1.0, brand.EMBER, layers=8, strength=0.08).move_to(real.get_center() + UP * 0.3)
        feel_fake = soft_glow(1.0, brand.EMBER, layers=8, strength=0.08).move_to(fake.get_center() + UP * 0.3)

        scene.play(FadeIn(real), FadeIn(fake), FadeIn(wall), FadeIn(rl), FadeIn(fl), run_time=min(0.9, duration * 0.12))
        scene.play(FadeIn(cover), FadeIn(eye), FadeIn(gaze), FadeIn(b1), FadeIn(b2), FadeIn(cap), run_time=0.6)
        rest = duration - scene.renderer.time
        if p.phase == "transfer":
            scene.add(feel_real)
            stroke_t = max(1.0, rest - 0.3)
            scene.play(k.animate(rate_func=linear).set_value(stroke_t / 1.1),
                       feel_real.animate(rate_func=rate_functions.ease_in_out_sine).move_to(feel_fake.get_center()),
                       run_time=stroke_t)
        else:
            scene.play(FadeIn(feel_real), run_time=0.4)
            rest = duration - scene.renderer.time
            scene.play(k.animate(rate_func=linear).set_value(max(0.5, rest - 0.1) / 1.1), run_time=max(0.5, rest - 0.1))
        rest = duration - scene.renderer.time
        if rest > 0.05:
            scene.wait(rest)
