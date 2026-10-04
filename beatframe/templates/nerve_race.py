"""A touch signal racing from the fingertip up the arm and spine to the brain, with a stopwatch."""

import numpy as np
from manim import (
    DOWN, LEFT, RIGHT, UP, Circle, FadeIn, Line, MoveAlongPath, Text, ValueTracker, VGroup, VMobject,
    Create, linear, rate_functions, TracedPath,
)

from beatframe import brand
from beatframe.templates.base import Template, glow, soft_glow

HEAD = np.array([3.6, 2.15, 0])
NECK = np.array([3.6, 1.25, 0])
SHOULDER = np.array([2.7, 0.75, 0])
ELBOW = np.array([0.2, -0.35, 0])
WRIST = np.array([-3.0, -1.05, 0])
TIP = np.array([-4.9, -1.25, 0])


class NerveRace(Template):
    name = "nerve_race"
    description = "Signal travels fingertip -> arm -> spine -> brain with a millisecond counter"

    class Params(Template.Params):
        total_ms: int = 20
        speed_label: str = "up to ~70 m/s"
        caption: str = "fingertip to brain"

    def build(self, scene, p, duration):
        body = VGroup(
            Circle(radius=0.62).move_to(HEAD + UP * 0.15),
            Line(NECK, NECK + DOWN * 3.6),                         # spine
            VMobject().set_points_smoothly([NECK + DOWN * 0.35, SHOULDER, ELBOW, WRIST]),   # upper edge of arm
        ).set_stroke(brand.DIM, 2.2, 0.7)
        hand = VGroup(*[Line(WRIST, WRIST + np.array([-1.0 - 0.7 * (k == 1), 0.25 - 0.18 * k, 0]))
                        for k in range(4)]).set_stroke(brand.DIM, 2.2, 0.7)
        brain = soft_glow(1.1, brand.GLOW, layers=9, strength=0.08).move_to(HEAD + UP * 0.15)

        path = VMobject().set_points_smoothly([TIP, WRIST, ELBOW, SHOULDER, NECK + DOWN * 0.1])
        path.append_points(Line(NECK + DOWN * 0.1, HEAD + UP * 0.1).points)
        nerve = path.copy().set_stroke(brand.GLOW, 2, 0.35)

        labels = VGroup(
            Text("fingertip", font=brand.SANS, color=brand.DIM).scale(0.34).next_to(TIP, DOWN, buff=0.25),
            Text("spinal cord", font=brand.SANS, color=brand.DIM).scale(0.34).next_to(NECK + DOWN * 2.2, RIGHT, buff=0.2),
            Text("brain", font=brand.SANS, color=brand.DIM).scale(0.34).next_to(HEAD, RIGHT, buff=0.9),
        )
        ms = ValueTracker(0)
        timer = Text("0 ms", font=brand.SERIF, weight="BOLD", color=brand.PAPER).scale(1.0).move_to([-4.6, 2.5, 0])

        def upd_timer(m):
            m.become(Text(f"{int(round(ms.get_value()))} ms", font=brand.SERIF, weight="BOLD",
                          color=brand.PAPER).scale(1.0).move_to([-4.6, 2.5, 0]))
        timer.add_updater(upd_timer)
        speed = Text(p.speed_label, font=brand.SANS, color=brand.GLOW).scale(0.4).next_to(timer, DOWN, buff=0.2).align_to(timer, LEFT)
        cap = Text(p.caption, font=brand.SERIF, weight="BOLD", color=brand.PAPER).scale(0.6).move_to([-0.3, -3.2, 0])

        spark = glow(0.09, brand.EMBER, layers=5, strength=0.25).move_to(TIP)
        trail = TracedPath(spark.get_center, stroke_color=brand.EMBER, stroke_width=4, dissipating_time=0.35)

        scene.play(FadeIn(body), FadeIn(hand), FadeIn(nerve), FadeIn(labels), FadeIn(cap), run_time=min(1.0, duration * 0.14))
        scene.play(FadeIn(timer), FadeIn(speed), FadeIn(spark, scale=0.3), run_time=0.5)
        scene.add(trail)
        rest = duration - scene.renderer.time
        travel = max(1.4, min(3.2, rest - 1.4))
        scene.play(MoveAlongPath(spark, path, rate_func=rate_functions.ease_in_out_sine),
                   ms.animate(rate_func=rate_functions.ease_in_out_sine).set_value(p.total_ms), run_time=travel)
        timer.clear_updaters()
        scene.play(FadeIn(brain, scale=0.4), spark.animate.scale(2.2).set_opacity(0), body[0].animate.set_stroke(brand.GLOW, opacity=1), run_time=0.6)
        rest = duration - scene.renderer.time
        if rest > 0.2:
            scene.play(scene.camera.frame.animate(rate_func=linear).scale(0.95), run_time=rest)
