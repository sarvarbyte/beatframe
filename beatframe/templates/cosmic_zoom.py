"""Reverse powers-of-ten: from the gap between your sole and the ground out to a galaxy.

Same trick as scale_zoom, backwards: the next (bigger) world is pre-scaled up so that
its anchor point sits exactly where the current world is; the camera pulls back, the
worlds crossfade, then everything is invisibly rescaled to normal coordinates.
"""

from __future__ import annotations

import numpy as np
from manim import (
    DOWN, LEFT, ORIGIN, RIGHT, UP, Arc, Circle, Dot, FadeIn, FadeOut, Line, RoundedRectangle, Text,
    VGroup, config, linear, rate_functions,
)

from beatframe import brand
from beatframe.templates.base import Template, glow, soft_glow

ZOOM = 0.12


def _lab(text, pos, color=brand.DIM, s=0.42):
    return Text(text, font=brand.SANS, color=color).scale(s).move_to(pos)


def lvl_atoms():
    g = VGroup()
    for row, (color, y) in enumerate(((brand.PAPER, 0.75), (brand.PAPER, 1.45), (brand.GLOW, -0.75), (brand.GLOW, -1.45))):
        for x in np.arange(-7.5, 7.6, 0.75):
            g.add(VGroup(glow(0.06, color, layers=4, strength=0.12),
                         Circle(radius=0.3).set_stroke(color, 1.4, 0.45)).move_to([x + (0.37 if row % 2 else 0), y, 0]))
    gap = VGroup(Line([-7.5, 0, 0], [7.5, 0, 0]).set_stroke(brand.EMBER, 1.5, 0.6))
    return VGroup(g, gap, _lab("your sole", [0, 2.4, 0], brand.PAPER), _lab("the ground", [0, -2.4, 0], brand.GLOW),
                  _lab("never touching", [4.6, 0.25, 0], brand.EMBER, 0.36)), ORIGIN


def lvl_foot():
    ground = Line([-8, -1.0, 0], [8, -1.0, 0]).set_stroke(brand.GLOW, 3)
    sole = RoundedRectangle(width=5.2, height=1.5, corner_radius=0.6).set_stroke(brand.PAPER, 3).set_fill(brand.DEEP, 1)
    sole.move_to([0, -1.0 + 0.75 + 0.04, 0])
    leg = RoundedRectangle(width=1.6, height=4.0, corner_radius=0.5).set_stroke(brand.PAPER, 3).set_fill(brand.DEEP, 1)
    leg.move_to([-1.4, 2.4, 0])
    return VGroup(ground, leg, sole, _lab("your foot", [3.6, 1.6, 0], brand.PAPER)), np.array([0, -1.0, 0])


def lvl_person():
    R = 40
    ground = Arc(radius=R, start_angle=np.pi / 2 - 0.2, angle=0.4, arc_center=[0, -2.0 - R, 0]).set_stroke(brand.GLOW, 3)
    head = Circle(radius=0.28).set_stroke(brand.PAPER, 2.5).move_to([0, 0.15, 0])
    body = VGroup(Line([0, -0.15, 0], [0, -1.15, 0]), Line([0, -1.15, 0], [-0.3, -2.0, 0]), Line([0, -1.15, 0], [0.3, -2.0, 0]),
                  Line([0, -0.4, 0], [-0.45, -1.0, 0]), Line([0, -0.4, 0], [0.45, -1.0, 0])).set_stroke(brand.PAPER, 2.5)
    return VGroup(ground, head, body, _lab("you", [1.2, -0.3, 0], brand.PAPER)), np.array([0.3, -2.0, 0])


def lvl_earth():
    e = Circle(radius=2.4).set_stroke(brand.GLOW, 3).set_fill(brand.GLOW, 0.06)
    lat = VGroup(*[Arc(radius=2.4 * np.sqrt(1 - y * y), start_angle=np.pi, angle=np.pi).stretch(0.25, 1)
                   .set_stroke(brand.GLOW, 1, 0.3).move_to(UP * 2.4 * y) for y in (-0.5, 0.0, 0.5)])
    return VGroup(e, lat, _lab("Earth", [3.4, 1.6, 0], brand.GLOW)), np.array([0, 2.4, 0])


def lvl_solar():
    sun = soft_glow(1.4, brand.GLOW, layers=9, strength=0.1).move_to([-3.0, 0, 0])
    core = Circle(radius=0.35).set_stroke(width=0).set_fill(brand.GLOW, 1).move_to([-3.0, 0, 0])
    orbits = VGroup(*[Circle(radius=r).set_stroke(brand.DIM, 1.2, 0.5).move_to([-3.0, 0, 0]) for r in (1.6, 2.6, 3.7, 5.6, 7.8)])
    a = 0.55
    earth_pt = np.array([-3.0 + 3.7 * np.cos(a), 3.7 * np.sin(a), 0])
    planets = VGroup(*[Dot([-3.0 + r * np.cos(t), r * np.sin(t), 0], radius=0.07, color=brand.PAPER)
                       for r, t in ((1.6, 2.4), (2.6, -1.0), (5.6, 3.6), (7.8, -0.4))])
    return VGroup(orbits, sun, core, planets, _lab("the Solar System", [-3.0, -3.0, 0], brand.GLOW)), earth_pt


def lvl_galaxy():
    rng = np.random.default_rng(9)
    stars = VGroup()
    for arm in range(2):
        for t in np.linspace(0.3, 3.3, 260):
            r = 0.9 * np.exp(0.42 * t)
            th = t + arm * np.pi + rng.normal(0, 0.18)
            rr = r + rng.normal(0, 0.25)
            stars.add(Dot([rr * np.cos(th) * 1.25, rr * np.sin(th) * 0.75, 0], radius=rng.uniform(0.01, 0.028),
                          color=brand.PAPER).set_opacity(rng.uniform(0.25, 0.85)))
    bulge = soft_glow(2.0, brand.GLOW, layers=9, strength=0.06).stretch(0.7, 1)
    # anchor: a quiet spot out on one arm
    t = 2.5
    r = 0.9 * np.exp(0.42 * t)
    anchor = np.array([r * np.cos(t) * 1.25, r * np.sin(t) * 0.75, 0])
    return VGroup(bulge, stars, _lab("the Milky Way", [0, -3.2, 0], brand.PAPER)), anchor


LEVELS = {"atoms": lvl_atoms, "foot": lvl_foot, "person": lvl_person, "earth": lvl_earth,
          "solar": lvl_solar, "galaxy": lvl_galaxy}


class CosmicZoom(Template):
    name = "cosmic_zoom"
    description = "Pull back from atoms under your foot to the whole galaxy"

    class Params(Template.Params):
        levels: list[str] = ["atoms", "foot", "person", "earth", "solar", "galaxy"]

    def build(self, scene, p, duration):
        frame = scene.camera.frame
        W = config.frame_width
        names = [n for n in p.levels if n in LEVELS] or ["atoms", "foot"]
        cur, _ = LEVELS[names[0]]()
        intro = min(0.8, duration * 0.1)
        scene.play(FadeIn(cur), run_time=intro)
        hold_first = min(1.0, duration * 0.1)
        scene.wait(hold_first)
        hold_end = min(1.6, duration * 0.15)
        n = len(names) - 1
        seg = max(1.0, (duration - intro - hold_first - hold_end) / max(n, 1))

        for name in names[1:]:
            nxt, anchor = LEVELS[name]()
            nxt.shift(-anchor).scale(1 / ZOOM, about_point=ORIGIN)
            scene.play(
                frame.animate(rate_func=rate_functions.ease_in_out_sine).scale(1 / ZOOM).move_to(-anchor / ZOOM),
                FadeIn(nxt, rate_func=rate_functions.squish_rate_func(rate_functions.smooth, 0.05, 0.4)),
                FadeOut(cur, rate_func=rate_functions.squish_rate_func(rate_functions.smooth, 0.55, 0.85)),
                run_time=seg,
            )
            nxt.scale(ZOOM, about_point=ORIGIN).shift(anchor)
            frame.move_to(ORIGIN).set(width=W)
            cur = nxt

        rest = duration - scene.renderer.time
        if rest > 0.2:
            scene.play(frame.animate(rate_func=linear).scale(1.06), run_time=rest)
