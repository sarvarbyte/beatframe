"""Cross-section of skin with the four touch sensors; one can be put in focus."""

import numpy as np
from manim import (
    DOWN, LEFT, RIGHT, UP, Circle, Dot, Ellipse, FadeIn, FadeOut, Line, ParametricFunction, Polygon,
    Rectangle, Text, VGroup, Indicate, linear, rate_functions, MoveAlongPath, ShowPassingFlash,
)

from beatframe import brand
from beatframe.templates.base import Template

INFO = {
    "meissner": ("Meissner", "light flutter, slip"),
    "merkel": ("Merkel", "pressure and edges"),
    "pacinian": ("Pacinian", "fast vibration"),
    "ruffini": ("Ruffini", "skin stretch"),
}
X = {"meissner": -4.2, "merkel": -1.4, "pacinian": 1.4, "ruffini": 4.2}


def _sensor(kind: str):
    if kind == "meissner":      # stacked coil just under the ridges
        g = VGroup(*[Ellipse(width=0.42, height=0.13).shift(UP * 0.1 * k) for k in range(5)])
        g.set_stroke(brand.PAPER, 2).move_to([X[kind], 0.65, 0])
    elif kind == "merkel":      # small discs at the base of the epidermis
        g = VGroup(*[Circle(radius=0.08).shift(RIGHT * 0.22 * k) for k in range(-1, 2)])
        g.set_stroke(brand.PAPER, 2).set_fill(brand.PAPER, 0.25).move_to([X[kind], 0.95, 0])
    elif kind == "pacinian":    # onion: concentric ovals deep down
        g = VGroup(*[Ellipse(width=0.25 + 0.16 * k, height=0.5 + 0.22 * k) for k in range(5)])
        g.set_stroke(brand.PAPER, 1.6).move_to([X[kind], -1.55, 0])
    else:                       # Ruffini: spindle with branching endings
        body = Ellipse(width=1.0, height=0.28).set_stroke(brand.PAPER, 2)
        twigs = VGroup(*[Line(LEFT * 0.35 + RIGHT * 0.17 * k, LEFT * 0.25 + RIGHT * 0.17 * k + UP * 0.18 * (-1) ** k)
                         for k in range(5)]).set_stroke(brand.PAPER, 1.5)
        g = VGroup(body, twigs).move_to([X[kind], -0.55, 0])
    return g.scale(1.45)


class SkinReceptors(Template):
    name = "skin_receptors"
    description = "Skin cross-section with four touch sensors; focus one of them"

    class Params(Template.Params):
        focus: str = "all"          # all | meissner | merkel | pacinian | ruffini
        title: str = "four sensors under your skin"

    def build(self, scene, p, duration):
        ridges = ParametricFunction(lambda t: np.array([t, 2.1 + 0.18 * np.sin(3.2 * t), 0]), t_range=[-7.5, 7.5])
        ridges.set_stroke(brand.GLOW, 3)
        base = ParametricFunction(lambda t: np.array([t, 1.15 + 0.22 * np.sin(3.2 * t + 0.6), 0]), t_range=[-7.5, 7.5])
        base.set_stroke(brand.PAPER, 1.5, 0.5)
        epi_label = Text("epidermis", font=brand.SANS, color=brand.DIM).scale(0.32).move_to([-6.2, 1.65, 0])
        der_label = Text("dermis", font=brand.SANS, color=brand.DIM).scale(0.32).move_to([-6.4, -0.2, 0])
        skin = VGroup(ridges, base, epi_label, der_label)

        sensors, nerves, labels = {}, VGroup(), VGroup()
        for kind in X:
            s = _sensor(kind)
            sensors[kind] = s
            n = Line(s.get_bottom(), [X[kind] * 0.6, -3.3, 0]).set_stroke(brand.DIM, 2, 0.8)
            n.kind = kind
            nerves.add(n)
            name, what = INFO[kind]
            lab = VGroup(Text(name, font=brand.SERIF, weight="BOLD", color=brand.PAPER).scale(0.42),
                         Text(what, font=brand.SANS, color=brand.GLOW).scale(0.32)).arrange(DOWN, buff=0.06)
            lab.move_to([X[kind], 2.95, 0])
            lab.kind = kind
            labels.add(lab)
        title = Text(p.title, font=brand.SANS, color=brand.DIM).scale(0.4).move_to([0, -3.65, 0])

        quick = p.focus in X  # focus beats follow an overview beat: skip the slow build
        scene.play(FadeIn(skin), FadeIn(nerves), FadeIn(title), run_time=0.3 if quick else min(0.9, duration * 0.12))
        scene.play(*[FadeIn(sensors[k], scale=0.6) for k in X], FadeIn(labels, lag_ratio=0.2),
                   run_time=0.3 if quick else min(1.4, duration * 0.18))

        frame = scene.camera.frame
        focus = p.focus if p.focus in X else None
        if focus:
            others = [k for k in X if k != focus]
            s = sensors[focus]
            name, what = INFO[focus]
            side = LEFT if X[focus] > 0 else RIGHT
            big = VGroup(Text(name, font=brand.SERIF, weight="BOLD", color=brand.PAPER).scale(0.5),
                         Text(what, font=brand.SANS, color=brand.GLOW).scale(0.34)).arrange(DOWN, buff=0.08)
            big.next_to(s, side, buff=0.55)
            center = VGroup(s, big).get_center()
            scene.play(
                *[sensors[k].animate.fade(0.82) for k in others],
                FadeOut(labels), FadeOut(title),
                *[n.animate.fade(0.7) for n in nerves if n.kind != focus],
                frame.animate.scale(0.55).move_to(center),
                run_time=min(1.2, duration * 0.15),
            )
            scene.play(FadeIn(big, shift=-side * 0.15), run_time=0.5)
            scene.play(Indicate(sensors[focus], color=brand.GLOW, scale_factor=1.25), run_time=0.8)

        # signals keep firing up the nerves until the beat ends
        targets = [n for n in nerves if not focus or n.kind == focus]
        while duration - getattr(scene.renderer, "time", 0) > 0.9:
            flashes = [ShowPassingFlash(Line(n.get_start(), n.get_end()).set_stroke(brand.EMBER, 5),
                                        time_width=0.4) for n in targets]
            pulse = [Indicate(sensors[n.kind], color=brand.EMBER, scale_factor=1.12) for n in targets]
            scene.play(*flashes, *pulse, run_time=0.8)
            gap = min(0.4, duration - getattr(scene.renderer, "time", 0) - 0.05)
            if gap > 0.05:
                scene.wait(gap)
