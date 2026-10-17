"""The withdrawal reflex arc: a painful stimulus at the fingertip, a sensory neuron to the spinal cord,
an interneuron, a motor neuron back to the arm muscle - the hand pulls away before the brain has
'felt' it; the pain signal also travels up to the brain, a moment later.

Accuracy notes (simplified diagram): the withdrawal reflex is polysynaptic (sensory neuron ->
interneuron(s) in the spinal grey matter -> motor neuron), with the sensory cell body in the dorsal
root ganglion, input via the dorsal root and output via the ventral root. Elbow flexion uses the
biceps (with brachialis). Conscious pain arrives via ascending pathways, slightly after the reflex.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
from manim import (
    DOWN, LEFT, RIGHT, UP, Arrow, Circle, Ellipse, FadeIn, FadeOut, Line, MoveAlongPath, ShowPassingFlash, VGroup,
    VMobject, rate_functions,
)

from beatframe.templates import sci
from beatframe.templates.sci import SciParams, Stage

SHOULDER, ELBOW, HAND = np.array([-4.6, 2.3, 0]), np.array([-4.6, -0.55, 0]), np.array([-1.35, -0.55, 0])


class ReflexArc(sci.Template):
    name = "reflex_arc"
    description = "Withdrawal reflex: stimulus -> sensory neuron -> spinal cord -> motor neuron -> muscle pulls away"
    category = "Human perception"
    theme = "bright"
    vertical_width = 8.0

    class Params(SciParams):
        stimulus: Literal["flame", "pin"] = "flame"
        show_brain_path: bool = True
        caption: str = "The spinal cord answers first; the brain feels it a moment later"

    def build(self, scene, p, duration):
        st, pal = Stage(), sci.pal_of(p)
        hi = sci.hi_of(p, pal)
        sens_c, mot_c, inter_c = pal["sky"], hi, pal["lavender"]
        clock = sci.Clock(scene, duration, p.speed)
        sci.guard(scene, duration)
        sci.background(scene, pal, st, seed=53)
        ts = p.text_size
        title = sci.headline(p.title, st, pal, ts)
        top, bottom = st.content(bool(p.title))
        cap = sci.wrapped(p.caption, 0.4 * ts, pal["muted"], 30 if st.v else 66, st.sw * 0.92) if p.caption else VGroup()
        bottom += st.place_caption(cap)

        # ---- arm (side view): upper arm down, forearm forward
        def limb(a, b, w):
            from manim import RoundedRectangle
            L = float(np.linalg.norm(b - a))
            r = RoundedRectangle(width=L + w, height=w, corner_radius=w / 2).set_fill(pal["panel"], 1).set_stroke(pal["muted"], 3)
            return r.rotate(np.arctan2(*(b - a)[1::-1])).move_to((a + b) / 2)
        upper = limb(SHOULDER, ELBOW, 0.78)
        fore_line = limb(ELBOW, HAND, 0.6)
        hand = Ellipse(width=0.75, height=0.42).set_fill(pal["panel"], 1).set_stroke(pal["muted"], 3).move_to(HAND + RIGHT * 0.25)
        finger = Line(HAND + RIGHT * 0.55, HAND + RIGHT * 0.95 + DOWN * 0.05).set_stroke(pal["muted"], 14)
        biceps = Ellipse(width=0.5, height=1.5).set_fill(mot_c, 0.25).set_stroke(mot_c, 2).move_to([-4.28, 1.0, 0])
        tip = HAND + RIGHT * 0.95 + DOWN * 0.08
        sens_fore = sci.smooth([tip, HAND + RIGHT * 0.1 + UP * 0.08, ELBOW + RIGHT * 0.25 + UP * 0.1], sens_c, 3)
        forearm = VGroup(fore_line, hand, finger, sens_fore)
        if p.stimulus == "pin":
            stim = VGroup(Line(tip + DOWN * 1.1, tip + DOWN * 0.15).set_stroke(pal["warm"], 4),
                          Circle(radius=0.12).set_fill(pal["coral"], 1).set_stroke(width=0).move_to(tip + DOWN * 1.15))
        else:
            stim = VGroup(*[sci.smooth([(0, 0.75), (0.32, 0.1), (0.18, -0.35), (-0.18, -0.35), (-0.32, 0.1), (0, 0.75)], c, 3).set_fill(c, 0.85).scale(sc)
                            for c, sc in ((pal["coral"], 1.0), (pal["peach"], 0.6))])
            stim[1].align_to(stim[0], DOWN)
            stim.move_to(tip + DOWN * 1.0)

        # ---- spinal cord cross-section (dorsal side up)
        cc = np.array([3.4, 0.4, 0]) if not st.v else np.array([-1.2, -3.5, 0])   # 9:16: the cord sits under the arm
        white = Ellipse(width=3.0, height=2.3).set_fill(pal["panel"], 0.9).set_stroke(pal["muted"], 2).move_to(cc)
        horn = lambda dx, dy, w, h: Ellipse(width=w, height=h).set_fill(pal["faint"], 1).set_stroke(width=0).move_to(cc + np.array([dx, dy, 0]))
        grey = VGroup(horn(-0.45, 0.4, 0.4, 0.95).rotate(0.5), horn(0.45, 0.4, 0.4, 0.95).rotate(-0.5),
                      horn(-0.42, -0.42, 0.6, 0.75), horn(0.42, -0.42, 0.6, 0.75), horn(0, 0, 1.0, 0.35))
        drg = Ellipse(width=0.55, height=0.4).set_fill(sens_c, 0.35).set_stroke(sens_c, 2).move_to(cc + np.array([-1.95, 0.95, 0]))
        dorsal_in = cc + np.array([-0.55, 0.75, 0])
        ventral = cc + np.array([-0.5, -0.5, 0])
        cord = VGroup(white, grey, drg)

        if st.v:
            sens_rest = sci.smooth([ELBOW + RIGHT * 0.25 + UP * 0.1, ELBOW + np.array([0.6, -0.9, 0]), drg.get_center() + UP * 0.5, drg.get_center(), dorsal_in], sens_c, 3)
            motor = sci.smooth([ventral, cc + np.array([-1.7, -0.75, 0]), [-5.4, -2.6, 0], [-5.3, 0.2, 0], biceps.get_center() + LEFT * 0.15], mot_c, 3)
            up_path = Arrow(cc + np.array([2.1, -0.6, 0]), cc + np.array([2.1, 0.7, 0]), buff=0, stroke_width=5, max_tip_length_to_length_ratio=0.18).set_color(pal["peach"])
        else:
            sens_rest = sci.smooth([ELBOW + RIGHT * 0.25 + UP * 0.1, [-4.25, 1.9, 0], [-2.6, 2.35, 0], [0.2, 1.75, 0], drg.get_center(), dorsal_in], sens_c, 3)
            motor = sci.smooth([ventral, cc + np.array([-1.7, -0.75, 0]), [-0.5, -0.15, 0], [-2.6, 0.95, 0], biceps.get_center() + RIGHT * 0.2], mot_c, 3)
            up_path = Arrow(cc + UP * 1.2, cc + UP * 2.6, buff=0, stroke_width=5, max_tip_length_to_length_ratio=0.18).set_color(pal["peach"])
        inter = sci.smooth([dorsal_in, cc + np.array([-0.25, 0.1, 0]), ventral], inter_c, 3)
        diagram = VGroup(upper, biceps, forearm, stim, cord, sens_rest, inter, motor)
        if p.show_brain_path:
            diagram.add(up_path)

        area = top - bottom
        w0 = diagram.width
        diagram.scale(min(st.sw * (0.96 if not st.v else 0.8) / diagram.width, area * 0.92 / diagram.height))
        diagram.move_to([st.cx + (0.25 if st.v else 0), (top + bottom) / 2, 0])
        k = diagram.width / w0
        elbow_now = upper[0].get_end()

        s = 0.27 * ts
        names = {
            "stim": sci.callout(stim.get_center(), "1  stimulus", (1, -0.3), pal["coral"], pal, s, 0.4 * k),
            "sens": sci.callout(sens_rest.point_from_proportion(0.45), "2  sensory neuron", (0.2, 1) if not st.v else (-1, -0.2), sens_c, pal, s, 0.35 * k),
            "inter": sci.callout(inter.point_from_proportion(0.5), "3  spinal cord", (1, -0.2) if not st.v else (1, -0.6), inter_c, pal, s, 1.0 * k),
            "motor": sci.callout(motor.point_from_proportion(0.6), "4  motor neuron", (0.4, -1) if not st.v else (1, -0.3), mot_c, pal, s, 0.55 * k),
            "muscle": sci.callout(biceps.get_center(), "5  muscle pulls", (-0.3, -1) if not st.v else (1, 0.5), mot_c, pal, s, 1.2 * k),
        }
        if not p.labels:
            names = {k_: VGroup() for k_ in names}

        scene.add(diagram)
        scene.play(FadeIn(title), FadeIn(cap), FadeIn(names["stim"]), run_time=0.3)
        scene.play(stim.animate(rate_func=rate_functions.wiggle).scale(1.15), run_time=0.4)

        full_sens = VMobject()
        full_sens.set_points(np.concatenate([sens_fore.points, sens_rest.points]))
        def travel(path, color, t):
            spark = sci.glow_dot(color, 0.05 * k + 0.025).move_to(path.get_start())
            scene.add(spark)
            scene.play(MoveAlongPath(spark, path, rate_func=rate_functions.ease_in_out_sine),
                       ShowPassingFlash(path.copy().set_stroke(color, 7), time_width=0.4), run_time=t)
            return spark
        avail = max(2.0, clock.left - 1.6)
        sp = travel(full_sens, sens_c, avail * 0.3)
        def swap(new, old):     # 9:16 has no room for all five labels: only the current step stays
            return [FadeIn(names[new])] + ([FadeOut(names[old])] if st.v and old else [])
        scene.play(*swap("sens", "stim"), FadeOut(sp), drg.animate(rate_func=rate_functions.there_and_back).scale(1.3), run_time=0.25)
        sp = travel(inter, inter_c, avail * 0.12)
        scene.play(*swap("inter", "sens"), FadeOut(sp), run_time=0.2)
        brain_spark = None
        if p.show_brain_path:
            brain_spark = sci.glow_dot(pal["peach"], 0.05 * k + 0.02).move_to(up_path.get_start())
            scene.add(brain_spark)
        sp = sci.glow_dot(mot_c, 0.05 * k + 0.025).move_to(motor.get_start())
        scene.add(sp)
        anims = [MoveAlongPath(sp, motor, rate_func=rate_functions.ease_in_out_sine), ShowPassingFlash(motor.copy().set_stroke(mot_c, 7), time_width=0.4)]
        if brain_spark is not None:
            anims.append(MoveAlongPath(brain_spark, Line(up_path.get_start(), up_path.get_end()), rate_func=rate_functions.ease_in_sine))
        scene.play(*anims, *swap("motor", "inter"), run_time=avail * 0.3)
        # the muscle contracts and the forearm swings up, away from the stimulus
        scene.play(FadeOut(sp), biceps.animate.stretch(1.35, 0).stretch(0.8, 1).set_fill(mot_c, 0.6), *swap("muscle", "motor"),
                   forearm.animate(rate_func=rate_functions.ease_out_back).rotate(0.5, about_point=elbow_now), run_time=0.45)
        if p.show_brain_path and clock.left > 0.8:
            late = sci.tag("to the brain: “ouch!” a moment later", pal["peach"], pal, 0.27 * ts)
            late.next_to(up_path, UP, buff=0.08) if not st.v else late.next_to(white, DOWN, buff=0.12)
            if late.get_right()[0] > st.right:
                late.shift(LEFT * (late.get_right()[0] - st.right))
            scene.play(FadeIn(late, shift=UP * 0.1), FadeOut(brain_spark), run_time=0.35)
        sci.finish(scene, clock, p.camera)
