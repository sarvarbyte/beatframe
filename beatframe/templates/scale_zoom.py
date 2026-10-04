"""'Powers of ten' dive: the camera keeps falling into smaller and smaller worlds.

Each level is drawn at normal size. While the camera dives into the level's target
point, the next level fades in, already shrunk into that point. When the dive ends,
everything is rescaled back (invisibly), so the numbers never get tiny; on screen it
is one continuous zoom.
"""

from __future__ import annotations

import numpy as np
from manim import (
    DOWN, LEFT, ORIGIN, RIGHT, UP, Arc, Circle, Dot, FadeIn, FadeOut, Line, ParametricFunction,
    Rectangle, RoundedRectangle, Text, VGroup, config, linear, rate_functions,
)

from beatframe import brand
from beatframe.templates.base import Template, glow

ZOOM = 0.12  # each dive shrinks the view to this fraction


def _surface(y: float = -2.2) -> VGroup:
    top = Line([-9, y, 0], [9, y, 0]).set_stroke(brand.GLOW, 3)
    body = Rectangle(width=18, height=3).set_stroke(width=0).set_fill(brand.GLOW, 0.06)
    body.next_to(top, DOWN, buff=0)
    return VGroup(body, top)


def _label(text: str, pos, color=brand.DIM) -> Text:
    return Text(text, font=brand.SANS, color=color).scale(0.42).move_to(pos)


def level_fingertip():
    finger = RoundedRectangle(width=3.0, height=7.0, corner_radius=1.45)
    finger.set_stroke(brand.PAPER, 3).set_fill(brand.DEEP, 1).move_to([0, 1.31, 0])
    ridges = VGroup(*[
        Arc(radius=0.45 + 0.17 * k, start_angle=np.pi * 1.12, angle=np.pi * 0.76)
        .set_stroke(brand.PAPER, 1.4, opacity=0.35)
        .move_to([0, -1.3 + 0.07 * k, 0])
        for k in range(7)
    ])
    g = VGroup(_surface(), finger, ridges, _label("your fingertip", [3.4, 0.4, 0]))
    return g, np.array([0.0, -2.2, 0]), "1 cm"


def level_skin():
    waves = VGroup()
    for k in range(5):
        y0 = -1.85 + 0.55 * k
        waves.add(
            ParametricFunction(lambda t, y0=y0: np.array([t, y0 + 0.26 * np.sin(2.2 * t + 1.57), 0]),
                               t_range=[-8.5, 8.5]).set_stroke(brand.PAPER, 2.5, opacity=0.9 - 0.15 * k)
        )
    g = VGroup(_surface(), waves, _label("fingerprint ridges", [3.8, 2.4, 0]))
    return g, np.array([0.0, -2.2, 0]), "1 mm"


def level_cells():
    rng = np.random.default_rng(3)
    cells = VGroup()
    for row in range(5):
        for col in range(-9, 10):
            r = 0.42 + rng.uniform(-0.05, 0.05)
            c = Circle(radius=r).set_stroke(brand.PAPER, 2, opacity=0.7).set_fill(brand.PAPER, 0.04)
            c.move_to([col * 0.9 + (0.45 if row % 2 else 0), -1.72 + row * 0.82, 0])
            cells.add(VGroup(c, Dot(c.get_center(), radius=0.08, color=brand.PAPER).set_opacity(0.5)))
    g = VGroup(_surface(), cells, _label("skin cells", [3.8, 2.6, 0]))
    return g, np.array([0.45, -2.2, 0]), "10 µm"


def _atom_row(color, y0, dy, xoff):
    atoms = VGroup()
    for row in range(3):
        for x in np.arange(-8.25, 8.3, 0.75):
            a = VGroup(glow(0.07, color, layers=4, strength=0.12),
                       Circle(radius=0.32).set_stroke(color, 1.5, 0.5))
            a.move_to([x + xoff, y0 + dy * row, 0])
            a.phase = np.random.uniform(0, 2 * np.pi)
            a.off = np.zeros(3)
            atoms.add(a)
    atoms.amp = 0.03
    atoms.t = 0.0

    def jiggle(group, dt):
        group.t += dt
        for a in group:
            new = group.amp * np.array([np.sin(9 * group.t + a.phase), np.cos(7 * group.t + a.phase), 0])
            a.shift(new - a.off)
            a.off = new

    atoms.add_updater(jiggle)
    return atoms


def level_atoms():
    top = _atom_row(brand.PAPER, 0.35, 0.7, 0.0)
    bottom = _atom_row(brand.GLOW, -0.75, -0.7, 0.375)
    g = VGroup(bottom, top,
               _label("your skin's atoms", [0, 2.55, 0], brand.PAPER),
               _label("the table's atoms", [0, -3.15, 0], brand.GLOW))
    g.jigglers = [top, bottom]
    return g, np.array([0.0, -0.2, 0]), "1 nm"


LEVELS = {
    "fingertip": level_fingertip,
    "skin": level_skin,
    "cells": level_cells,
    "atoms": level_atoms,
}


class ScaleZoom(Template):
    name = "scale_zoom"
    description = "Continuous dive through scales: fingertip -> skin -> cells -> atoms"

    class Params(Template.Params):
        levels: list[str] = ["fingertip", "skin", "cells", "atoms"]
        show_scale_bar: bool = True

    def build(self, scene, p, duration):
        frame = scene.camera.frame
        W = config.frame_width
        levels = [LEVELS[name]() for name in p.levels]

        # scale bar glued to the screen corner, whatever the camera does
        state = {"label": levels[0][2]}

        def make_bar():
            line = Line(LEFT * 0.8, RIGHT * 0.8).set_stroke(brand.PAPER, 3)
            lab = Text(state["label"], font=brand.SANS, color=brand.PAPER).scale(0.4)
            bar = VGroup(line, lab.next_to(line, UP, buff=0.12))
            s = frame.width / W
            return bar.scale(s).move_to(frame.get_center() + np.array([-W / 2 + 1.5, -3.2, 0]) * s)

        bar = make_bar()
        bar.add_updater(lambda m: m.become(make_bar()))

        cur, target, _ = levels[0]
        intro = min(0.8, duration * 0.12)
        scene.play(FadeIn(cur), FadeIn(bar) if p.show_scale_bar else FadeIn(VGroup()), run_time=intro)
        if not p.show_scale_bar:
            bar.clear_updaters()

        n = len(levels) - 1
        hold_end = min(1.5, duration * 0.2)
        seg = max(0.9, (duration - intro - hold_end) / max(n, 1))

        for i in range(n):
            nxt, nxt_target, nxt_label = levels[i + 1]
            # pre-shrink the next world into the point we are diving toward
            nxt.scale(ZOOM, about_point=ORIGIN).shift(target)
            for j in getattr(nxt, "jigglers", []):
                j.amp *= ZOOM

            def switch_label(_m, alpha, lbl=nxt_label):
                if alpha > 0.8:
                    state["label"] = lbl

            from manim import UpdateFromAlphaFunc

            scene.play(
                frame.animate(rate_func=rate_functions.ease_in_out_sine).scale(ZOOM).move_to(target),
                FadeIn(nxt, rate_func=rate_functions.squish_rate_func(rate_functions.smooth, 0.72, 0.98)),
                FadeOut(cur, rate_func=rate_functions.squish_rate_func(rate_functions.smooth, 0.82, 1.0)),
                UpdateFromAlphaFunc(VGroup(), switch_label),
                run_time=seg,
            )
            # invisible reset back to normal coordinates
            nxt.shift(-target).scale(1 / ZOOM, about_point=ORIGIN)
            for j in getattr(nxt, "jigglers", []):
                j.amp /= ZOOM
            frame.move_to(ORIGIN).set(width=W)
            cur, target = nxt, nxt_target

        rest = duration - getattr(scene.renderer, "time", 0)
        if rest > 0.2:
            scene.play(frame.animate.scale(0.92).move_to(target * 0.3), run_time=rest, rate_func=linear)
