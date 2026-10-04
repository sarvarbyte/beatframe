"""A pressure-gated ion channel (Piezo2): a push bends the membrane, the gate opens,
ions rush in and the nerve fires."""

import numpy as np
from manim import (
    DOWN, LEFT, RIGHT, UP, Arrow, Circle, Dot, FadeIn, Line, RoundedRectangle, Text, ValueTracker,
    VGroup, VMobject, Create, linear, rate_functions, smooth,
)

from beatframe import brand
from beatframe.templates.base import Template, glow

MEM_Y = 0.4          # membrane centre line
GAP = 0.22           # half-thickness of the bilayer


def _bend(x, b):
    return -b * np.exp(-(x ** 2) / 3.0)


class IonChannel(Template):
    name = "ion_channel"
    description = "Membrane with a pressure-gated channel; push -> gate opens -> ions in -> spike"

    class Params(Template.Params):
        channel_label: str = "Piezo2"
        top_label: str = "outside"
        bottom_label: str = "inside the nerve"
        caption: str = "pressure pulls the gate open"
        show_spike: bool = True

    def build(self, scene, p, duration):
        bend = ValueTracker(0.0)
        opn = ValueTracker(0.0)

        # lipid heads: two rows of small circles, leaving a hole for the channel
        xs = [x for x in np.arange(-7.4, 7.5, 0.34) if abs(x) > 1.15]
        heads = VGroup()
        for row in (1, -1):
            for x in xs:
                c = Circle(radius=0.11).set_stroke(brand.PAPER, 1.5, 0.8).set_fill(brand.PAPER, 0.15)
                c.x0, c.row = x, row
                heads.add(c)

        def place_heads(g):
            b = bend.get_value()
            for c in g:
                c.move_to([c.x0, MEM_Y + c.row * GAP + _bend(c.x0, b), 0])
        place_heads(heads)
        heads.add_updater(place_heads)

        # the channel: two halves that slide apart as it opens
        def half(side):
            r = RoundedRectangle(width=0.55, height=1.0, corner_radius=0.2)
            r.set_stroke(brand.GLOW, 3).set_fill(brand.GLOW, 0.25)
            r.side = side
            return r
        halves = VGroup(half(-1), half(1))

        def place_halves(g):
            b, o = bend.get_value(), opn.get_value()
            for h in g:
                h.move_to([h.side * (0.3 + 0.36 * o), MEM_Y + _bend(0, b), 0])
        place_halves(halves)
        halves.add_updater(place_halves)

        # tethers ("springs") linking the channel to the membrane - Piezo's blades
        blades = VGroup(*[Line().set_stroke(brand.GLOW, 2, 0.7) for _ in range(2)])

        def place_blades(g):
            b = bend.get_value()
            for k, l in zip((-1, 1), g):
                h = halves[0 if k < 0 else 1]
                end = np.array([k * 1.7, MEM_Y + GAP + 0.35 + _bend(k * 1.7, b), 0])
                l.put_start_and_end_on(h.get_top() + k * RIGHT * 0.1, end)
        place_blades(blades)
        blades.add_updater(place_blades)

        chan_label = Text(p.channel_label, font=brand.SERIF, weight="BOLD", color=brand.GLOW).scale(0.55)
        chan_label.add_updater(lambda m: m.move_to(halves.get_center() + np.array([-2.0, -0.95, 0])))
        top = Text(p.top_label, font=brand.SANS, color=brand.DIM).scale(0.38).move_to([-6.0, 2.3, 0])
        bot = Text(p.bottom_label, font=brand.SANS, color=brand.DIM).scale(0.38).move_to([-5.6, -1.4, 0])
        cap = Text(p.caption, font=brand.SERIF, weight="BOLD", color=brand.PAPER).scale(0.7).move_to([0, 3.35, 0])

        # ions waiting outside; each gets a path in through the pore
        rng = np.random.default_rng(5)
        ions = VGroup()
        for i in range(22):
            start = np.array([rng.uniform(-1.6, 3.8), rng.uniform(1.4, 2.6), 0])
            end = np.array([rng.uniform(-0.6, 3.4), rng.uniform(-2.0, -0.9), 0])
            d = VGroup(glow(0.07, brand.EMBER, layers=3, strength=0.2),
                       Text("+", font=brand.SANS, weight="BOLD", color=brand.NIGHT).scale(0.22))
            d.start, d.end, d.delay, d.ph = start, end, rng.uniform(0, 0.6), rng.uniform(0, 6.28)
            d.move_to(start)
            ions.add(d)
        flow = ValueTracker(0.0)
        clock = {"t": 0.0}

        def move_ions(g, dt):
            clock["t"] += dt
            f = flow.get_value()
            for d in g:
                jit = 0.06 * np.array([np.sin(3 * clock["t"] + d.ph), np.cos(2.5 * clock["t"] + d.ph), 0])
                a = np.clip((f - d.delay) / 0.4, 0, 1)
                if a <= 0:
                    d.move_to(d.start + jit)
                    continue
                pore = np.array([0, MEM_Y + _bend(0, bend.get_value()), 0])
                if a < 0.5:   # drift to the pore
                    s = smooth(a * 2)
                    pos = d.start * (1 - s) + (pore + UP * 0.5) * s
                else:         # drop through and spread out inside
                    s = smooth((a - 0.5) * 2)
                    mid = pore + UP * 0.5
                    pos = mid * (1 - s) + d.end * s
                d.move_to(pos + jit * 0.5)
        ions.add_updater(move_ions)

        # the finger pressing from above
        press = Arrow(UP * 3.0, UP * 1.6, buff=0, stroke_width=6, max_tip_length_to_length_ratio=0.3)
        press.set_color(brand.PAPER)
        push_lab = Text("push", font=brand.SANS, color=brand.PAPER).scale(0.4).next_to(press, RIGHT, buff=0.15)
        pusher = VGroup(press, push_lab).shift(LEFT * 3.4)

        # voltage trace bottom-right
        box_o = np.array([2.4, -3.0, 0])
        def spike(t):
            y = 0.0
            if 0.45 < t < 0.75:
                y = 1.1 * np.sin((t - 0.45) / 0.3 * np.pi) ** 2 * (1 if t < 0.62 else 1)
            if 0.62 < t < 0.85:
                y = 1.1 * np.sin((t - 0.45) / 0.3 * np.pi) ** 2 if t < 0.75 else -0.2 * np.sin((t - 0.75) / 0.1 * np.pi)
            return y
        pts = [box_o + np.array([3.6 * t, spike(t), 0]) for t in np.linspace(0, 1, 140)]
        trace = VMobject().set_points_smoothly(pts).set_stroke(brand.EMBER, 3)
        base_line = Line(box_o, box_o + RIGHT * 3.6).set_stroke(brand.DIM, 1, 0.5)
        sig_lab = Text("signal", font=brand.SANS, color=brand.EMBER).scale(0.36).next_to(base_line, LEFT, buff=0.2)

        t0 = min(1.0, duration * 0.12)
        scene.play(FadeIn(heads), FadeIn(halves), FadeIn(blades), FadeIn(top), FadeIn(bot), run_time=t0)
        scene.play(FadeIn(ions), FadeIn(chan_label), FadeIn(cap, shift=DOWN * 0.1), run_time=min(0.8, duration * 0.1))
        scene.wait(min(0.6, duration * 0.06))

        # push: membrane bends, tethers pull, the gate opens
        scene.play(FadeIn(pusher, shift=DOWN * 0.3), run_time=0.5)
        t_press = min(1.6, duration * 0.18)
        scene.play(bend.animate.set_value(0.55), opn.animate(rate_func=rate_functions.ease_in_quad).set_value(1.0),
                   pusher.animate.shift(DOWN * 0.45), run_time=t_press)
        halves.set_stroke(brand.EMBER)
        rest = duration - scene.renderer.time
        t_flow = max(1.2, min(2.6, rest * 0.55))
        if p.show_spike:
            scene.add(base_line, sig_lab)
            scene.play(flow.animate(rate_func=linear).set_value(1.0),
                       Create(trace, rate_func=rate_functions.ease_in_out_sine), run_time=t_flow)
        else:
            scene.play(flow.animate(rate_func=linear).set_value(1.0), run_time=t_flow)
        rest = duration - scene.renderer.time
        if rest > 0.2:
            scene.play(scene.camera.frame.animate(rate_func=linear).scale(0.94), run_time=rest)
