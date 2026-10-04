"""Blow a fingertip up to the size of Earth: a 13 nm wrinkle becomes a house-sized bump."""

import numpy as np
from manim import (
    DOWN, LEFT, RIGHT, UP, Arc, Arrow, Circle, DashedLine, FadeIn, FadeOut, Polygon, Rectangle,
    RoundedRectangle, Text, VGroup, Transform, linear, rate_functions,
)

from beatframe import brand
from beatframe.templates.base import Template, soft_glow


def _house(w=0.5, h=0.38, color=brand.DIM):
    body = Rectangle(width=w, height=h).set_stroke(color, 1.6).set_fill(brand.NIGHT, 1)
    roof = Polygon(body.get_corner(UP + LEFT), body.get_corner(UP + RIGHT), body.get_top() + UP * h * 0.6)
    roof.set_stroke(color, 1.6).set_fill(brand.NIGHT, 1)
    door = Rectangle(width=w * 0.2, height=h * 0.45).set_stroke(color, 1.2).move_to(body.get_bottom() + UP * h * 0.225)
    return VGroup(body, roof, door)


def _car(color=brand.DIM):
    body = RoundedRectangle(width=0.5, height=0.14, corner_radius=0.05).set_stroke(color, 1.4)
    cab = RoundedRectangle(width=0.26, height=0.12, corner_radius=0.04).set_stroke(color, 1.4).next_to(body, UP, buff=0)
    wheels = VGroup(*[Circle(radius=0.05).set_stroke(color, 1.4).move_to(body.get_bottom() + RIGHT * k * 0.15) for k in (-1, 1)])
    return VGroup(body, cab, wheels)


class EarthFinger(Template):
    name = "earth_finger"
    description = "Fingertip scaled up to Earth size; the tiny wrinkle becomes a house"

    class Params(Template.Params):
        finger_label: str = "your fingertip"
        earth_label: str = "blown up to the size of Earth"
        bump_label: str = "13 nm wrinkle → a bump the size of a house"
        caption: str = "and you would still feel it"

    def build(self, scene, p, duration):
        frame = scene.camera.frame
        # phase 1: finger -> Earth
        tip = RoundedRectangle(width=0.7, height=1.6, corner_radius=0.34).set_stroke(brand.PAPER, 2.5)
        tip.move_to([-4.6, -0.4, 0])
        fl = Text(p.finger_label, font=brand.SANS, color=brand.PAPER).scale(0.4).next_to(tip, DOWN, buff=0.3)
        earth = Circle(radius=2.6).set_stroke(brand.GLOW, 3).set_fill(brand.GLOW, 0.06).move_to([2.2, -0.2, 0])
        lines = VGroup(*[Arc(radius=2.6 * np.sqrt(1 - y * y), start_angle=np.pi, angle=np.pi)
                         .stretch(0.25, 1).set_stroke(brand.GLOW, 1, 0.3)
                         .move_to(earth.get_center() + UP * 2.6 * y) for y in (-0.5, 0.0, 0.5)])
        el = Text(p.earth_label, font=brand.SANS, color=brand.GLOW).scale(0.42).next_to(earth, UP, buff=0.3)
        arrow = Arrow(tip.get_right() + RIGHT * 0.2, earth.get_left() + LEFT * 0.2, buff=0).set_color(brand.DIM)
        x_lab = Text("× 1,000,000,000", font=brand.SANS, color=brand.DIM).scale(0.36).next_to(arrow, UP, buff=0.12)

        t1 = min(0.7, duration * 0.08)
        scene.play(FadeIn(tip), FadeIn(fl), run_time=t1)
        scene.play(FadeIn(arrow), FadeIn(x_lab), FadeIn(earth, scale=0.2), FadeIn(lines), run_time=min(1.2, duration * 0.13))
        scene.play(FadeIn(el, shift=DOWN * 0.1), run_time=0.5)
        scene.wait(min(0.8, duration * 0.08))

        # phase 2: dive to the surface (top of the Earth circle)
        surf_pt = earth.get_top()
        ph1 = VGroup(tip, fl, arrow, x_lab, el)
        scene.play(FadeOut(ph1), frame.animate(rate_func=rate_functions.ease_in_sine).scale(0.25).move_to(surf_pt),
                   run_time=min(1.0, duration * 0.1))
        scene.remove(earth, lines)
        frame.move_to([0, 0, 0]).set(width=14.222222)

        R = 60.0
        ground = Arc(radius=R, start_angle=np.pi / 2 - 0.13, angle=0.26, arc_center=[0, -1.6 - R, 0])
        ground.set_stroke(brand.GLOW, 3)
        town = VGroup()
        rng = np.random.default_rng(2)
        xs = [-6.2, -5.4, -4.5, -3.3, -2.4, 2.3, 3.2, 4.4, 5.3, 6.3]
        for x in xs:
            y = -1.6 - R + np.sqrt(R ** 2 - x ** 2)
            obj = _car() if rng.uniform() < 0.3 else _house(w=rng.uniform(0.4, 0.6))
            obj.move_to([x, y + obj.height / 2, 0]).rotate(-x / R, about_point=[x, y, 0])
            town.add(obj)
        hero = _house(w=1.2, h=0.9, color=brand.EMBER)
        hero.move_to([0, -1.6 + hero.height / 2, 0])
        halo = soft_glow(1.6, brand.EMBER, layers=8, strength=0.05).move_to(hero.get_center())
        pointer = DashedLine(hero.get_top() + UP * 0.2, hero.get_top() + UP * 1.4, dash_length=0.08).set_stroke(brand.EMBER, 1.5)
        bl = Text(p.bump_label, font=brand.SANS, color=brand.EMBER).scale(0.44).next_to(pointer, UP, buff=0.12)
        cap = Text(p.caption, font=brand.SERIF, weight="BOLD", color=brand.PAPER).scale(0.75).move_to([0, -3.0, 0])

        scene.play(FadeIn(ground), FadeIn(town, lag_ratio=0.1), run_time=min(1.0, duration * 0.1))
        scene.play(FadeIn(halo), FadeIn(hero, shift=UP * 0.3), run_time=0.7)
        scene.play(FadeIn(pointer), FadeIn(bl, shift=UP * 0.1), run_time=0.6)
        scene.play(FadeIn(cap, shift=UP * 0.1), run_time=0.5)
        rest = duration - scene.renderer.time
        if rest > 0.2:
            scene.play(frame.animate(rate_func=linear).scale(0.9).shift(UP * 0.2), run_time=rest)
