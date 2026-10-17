"""How we hear: sound is funnelled by the outer ear, the eardrum and three tiny bones (malleus, incus,
stapes) pass the vibration to the fluid-filled cochlea, where hair cells turn it into nerve signals.
An 'uncoiled' cochlea shows where a pitch peaks: high pitches near the base, low near the apex.

Accuracy notes (simplified diagram, not to scale): the travelling wave on the basilar membrane peaks
at a place that depends on frequency (tonotopy; von Bekesy). Hair cells along that place respond most
strongly and the auditory nerve carries the signal to the brainstem and on to the auditory cortex.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
from manim import (
    DOWN, LEFT, RIGHT, UP, Arc, Circle, Ellipse, FadeIn, Line, MoveAlongPath, Polygon, Rectangle, RoundedRectangle,
    ShowPassingFlash, ValueTracker, VGroup, VMobject, rate_functions,
)

from beatframe.templates import sci
from beatframe.templates.sci import SciParams, Stage

PEAK = {"high": 0.12, "middle": 0.5, "low": 0.88}     # where on the cochlea (base 0 -> apex 1) the wave peaks


def spiral(center, r: float, turns: float = 2.5, n: int = 90) -> VMobject:
    ts = np.linspace(0, 1, n)
    pts = [np.array(center) + r * (1 - 0.82 * t) * np.array([np.cos(np.pi - t * turns * 2 * np.pi), np.sin(np.pi - t * turns * 2 * np.pi), 0]) for t in ts]
    return VMobject().set_points_smoothly(pts)


class InnerEar(sci.Template):
    name = "inner_ear"
    description = "Outer, middle and inner ear: sound -> eardrum -> three bones -> cochlea -> nerve; pitch maps to place"
    category = "Human perception"
    theme = "bright"
    vertical_width = 8.0

    class Params(SciParams):
        pitch: Literal["high", "middle", "low"] = "high"
        uncoiled: bool = True             # show the cochlea unrolled, with where this pitch peaks
        caption: str = "High pitches peak near the start of the cochlea, low pitches near its tip"

    def build(self, scene, p, duration):
        st, pal = Stage(), sci.pal_of(p)
        hi = sci.hi_of(p, pal)
        clock = sci.Clock(scene, duration, p.speed)
        sci.guard(scene, duration)
        sci.background(scene, pal, st, seed=41)
        ts = p.text_size
        title = sci.headline(p.title, st, pal, ts)
        top, bottom = st.content(bool(p.title))
        cap = sci.wrapped(p.caption, 0.4 * ts, pal["muted"], 30 if st.v else 66, st.sw * 0.92) if p.caption else VGroup()
        bottom += st.place_caption(cap)

        # ---- the chain, built in a 12 x 4.4 box (x: -6..6)
        aur_out = sci.ear_shape(4.6).flip(UP).move_to([-5.15, 0.1, 0]).set_stroke(pal["ink"], 3).set_fill(pal["panel"], 0.85)
        helix = sci.smooth([(-5.0, 1.05), (-5.5, 0.75), (-5.65, 0.0), (-5.35, -0.65), (-4.95, -0.75)], pal["muted"], 2.2, 0.8)
        aur = VGroup(aur_out, helix)
        canal = VGroup(Line([-4.6, 0.32, 0], [-1.85, 0.25, 0]), Line([-4.6, -0.32, 0], [-1.85, -0.25, 0])).set_stroke(pal["muted"], 3)
        drum = Arc(radius=0.45, start_angle=-np.pi / 2.6, angle=2 * np.pi / 2.6).set_stroke(pal["peach"], 5).move_to([-1.78, 0, 0])
        bone = pal["warm"]
        mal = VGroup(Line([-1.72, -0.1, 0], [-1.35, 0.45, 0]).set_stroke(bone, 9),                       # hammer: handle + head
                     Circle(radius=0.17).set_fill(bone, 1).set_stroke(width=0).move_to([-1.3, 0.55, 0]))
        inc = VGroup(Polygon([-1.18, 0.62, 0], [-0.82, 0.58, 0], [-0.9, 0.2, 0]).set_fill(bone, 1).set_stroke(bone, 3),   # anvil
                     Line([-0.9, 0.25, 0], [-0.72, 0.02, 0]).set_stroke(bone, 7))
        stp = VGroup(Arc(radius=0.2, start_angle=np.pi / 2, angle=np.pi).rotate(np.pi).move_to([-0.5, 0.02, 0]).set_stroke(bone, 6),  # stirrup
                     Line([-0.33, 0.24, 0], [-0.33, -0.2, 0]).set_stroke(bone, 8))
        ossicles = VGroup(mal, inc, stp)
        middle_box = RoundedRectangle(width=2.0, height=2.0, corner_radius=0.5).set_stroke(pal["faint"], 1.5).set_fill(pal["bottom"], 0.35).move_to([-1.0, 0.25, 0])
        coch_c = np.array([1.35, 0.1, 0])
        coch = spiral(coch_c, 1.25).set_stroke(pal["lavender"], 6)
        coch_fill = Circle(radius=1.32).move_to(coch_c).set_fill(pal["lavender"], 0.08).set_stroke(width=0)
        nerve = sci.smooth([coch_c + np.array([0.1, -0.15, 0]), coch_c + np.array([1.4, -0.5, 0]), np.array([4.3, -0.2, 0]), np.array([5.4, 0.7, 0])], pal["mint"], 5)
        brain = sci.glow_dot(pal["mint"], 0.18).move_to([5.55, 0.85, 0])
        chain = VGroup(aur, canal, middle_box, drum, ossicles, coch_fill, coch, nerve, brain)

        brackets = VGroup()
        for x0, x1, lab in ((-6.0, -1.9, "outer"), (-1.95, -0.05, "middle"), (0.0, 2.7, "inner")):
            line = Line([x0, 2.25, 0], [x1, 2.25, 0]).set_stroke(pal["muted"], 2)
            ticks = VGroup(Line([x0, 2.25, 0], [x0, 2.05, 0]), Line([x1, 2.25, 0], [x1, 2.05, 0])).set_stroke(pal["muted"], 2)
            brackets.add(VGroup(line, ticks, sci.text(lab, 0.42, pal["muted"], bold=True).next_to(line, UP, buff=0.1)))
        diagram = VGroup(chain, brackets)

        strip_h = 0.0
        strip = VGroup()
        if p.uncoiled:
            L = 11.0
            base = Line([-L / 2, 0, 0], [L / 2, 0, 0]).set_stroke(pal["lavender"], 3, 0.6)
            ends = VGroup(sci.text("base · high pitch", 0.5, pal["muted"]).next_to(base.get_start(), DOWN, buff=0.22).align_to(base, LEFT),
                          sci.text("apex · low pitch", 0.5, pal["muted"]).next_to(base.get_end(), DOWN, buff=0.22).align_to(base, RIGHT))
            strip = VGroup(base, ends)
            strip_h = 2.4
        # ---- fit: diagram on top, uncoiled strip below
        block = VGroup(diagram, strip)
        avail_h = top - bottom
        dh = avail_h * ((0.56 if st.v else 0.66) if p.uncoiled else 0.95)
        k = min(dh / diagram.height, st.sw / diagram.width)
        diagram.scale(k).move_to([st.cx, top - diagram.height / 2 - 0.05, 0])
        if p.uncoiled:
            strip.scale(min(st.sw / strip.width, k * 1.0))
            strip.move_to([st.cx, bottom + strip.height / 2 + (0.6 if st.v else 0.8), 0])
        amp = (0.32 if st.v else max(0.3, min(0.6, diagram.get_bottom()[1] - strip[0].get_center()[1] - 0.9))) if p.uncoiled else 0

        labels = VGroup()
        if p.labels:
            s = 0.28 * ts
            labels.add(sci.callout(drum.get_center() + DOWN * 0.3 * k, "eardrum", (-0.4, -1), pal["peach"], pal, s, 0.55 * k))
            labels.add(sci.callout(inc.get_center(), "3 tiny bones", (0.2, 1), pal["warm"], pal, s, 0.75 * k))
            labels.add(sci.callout(coch.get_center() + UP * 0.9 * k, "cochlea", (0.6, 1), pal["lavender"], pal, s, 0.35 * k))
            labels.add(sci.callout(nerve.point_from_proportion(0.55), "auditory nerve", (0.3, -1), pal["mint"], pal, s, 0.45 * k))

        scene.add(diagram, strip)
        scene.play(FadeIn(title), FadeIn(cap), FadeIn(labels), run_time=0.3)

        # 1. sound arrives through the canal
        waves = sci.arcs(aur.get_left() + LEFT * 0.4 * k, 0.35 * k, 3, 1.1, 0.0, pal["sky"], 3)
        t = clock.t(0.12, 0.5, 1.0)
        scene.play(FadeIn(waves, lag_ratio=0.3), waves.animate.shift(RIGHT * 2.4 * k).set_opacity(0.2), run_time=t)
        scene.remove(waves)
        # 2. eardrum and bones vibrate
        pivot = mal[0].get_start()
        for j in range(3):
            if clock.left < 3.0:
                break
            scene.play(drum.animate(rate_func=rate_functions.there_and_back).shift(RIGHT * 0.08 * k),
                       ossicles.animate(rate_func=rate_functions.there_and_back).rotate(-0.12, about_point=pivot), run_time=0.22)
        # 3. a wave through the cochlea fluid, then the place of this pitch on the uncoiled strip
        flash = coch.copy().set_stroke(hi, 9)
        scene.play(ShowPassingFlash(flash, time_width=0.4), run_time=clock.t(0.12, 0.5, 1.1))
        if p.uncoiled:
            base = strip[0]
            x0, x1 = base.get_start()[0], base.get_end()[0]
            peak = PEAK[p.pitch]
            env = ValueTracker(0.0)
            wave = VMobject().set_stroke(hi, 4)
            y0 = base.get_center()[1]

            def draw(m):
                xs = np.linspace(0, 1, 140)
                e = env.get_value()
                a = amp * 0.5 * np.exp(-((xs - peak) / 0.13) ** 2) * np.clip((e * 1.3 - xs / (peak + 0.15)), 0, 1)
                y = a * np.sin(xs * 50 - e * 20)
                m.set_points_smoothly([np.array([x0 + (x1 - x0) * x, y0 + yy, 0]) for x, yy in zip(xs, y)])
            wave.add_updater(draw)
            scene.add(wave)
            t = clock.t(0.25, 0.8, 2.0)
            scene.play(env.animate(rate_func=rate_functions.linear).set_value(1.0), run_time=t)
            wave.clear_updaters()
            mark = sci.tag(f"{p.pitch} pitch peaks here", hi, pal, 0.3 * ts).move_to([x0 + (x1 - x0) * peak, strip[1].get_bottom()[1] - 0.35, 0])
            if mark.get_right()[0] > st.right:
                mark.shift(LEFT * (mark.get_right()[0] - st.right))
            if mark.get_left()[0] < st.left:
                mark.shift(RIGHT * (st.left - mark.get_left()[0]))
            scene.play(FadeIn(mark, shift=UP * 0.1), run_time=0.3)
        # 4. nerve signal to the brain
        if clock.left > 0.8:
            spark = sci.glow_dot(pal["mint"], 0.06 * k + 0.02).move_to(nerve.get_start())
            scene.add(spark)
            scene.play(MoveAlongPath(spark, nerve, rate_func=rate_functions.ease_in_sine), run_time=min(0.9, clock.left * 0.5))
            scene.play(brain.animate(rate_func=rate_functions.there_and_back).scale(1.6), spark.animate.set_opacity(0), run_time=0.35)
        sci.finish(scene, clock, p.camera)
