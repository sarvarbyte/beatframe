"""A working blind-spot test the viewer can do on their screen, then why it works.

Correct method (right eye version): close the LEFT eye, stare at the cross with the RIGHT eye, and
slowly move closer to / further from the screen. At some distance the dot to the RIGHT of the cross
vanishes: its image lands on the optic disc, where the optic nerve leaves the eye and there are no
light-sensitive cells. For the left eye everything is mirrored (dot on the left of the cross).
The brain fills the hole with the surrounding background, which is why you never notice it.
The test only works if the marks stay still, so nothing moves during the test phase.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
from manim import (
    DOWN, LEFT, RIGHT, UP, Arc, Circle, Create, Ellipse, FadeIn, FadeOut, Line, Rectangle, Star, VGroup, rate_functions,
)
from pydantic import Field

from beatframe.templates import sci
from beatframe.templates.sci import SciParams, Stage


class BlindSpotTest(sci.Template):
    name = "blind_spot_test"
    description = "Interactive blind-spot test: instructions, a still test card, then the optic-disc explanation"
    category = "Experiments"
    theme = "bright"
    vertical_width = 8.0

    class Params(SciParams):
        open_eye: Literal["right", "left"] = "right"
        spacing: float = Field(0.62, ge=0.35, le=0.8)    # distance between the marks, share of the frame width
        marker: Literal["dot", "star"] = "dot"
        phases: Literal["full", "instructions", "test", "explain"] = "full"
        title: str = "Find your blind spot"
        explain_text: str = "No light receptors where the optic nerve leaves the eye"

    def build(self, scene, p, duration):
        st, pal = Stage(), sci.pal_of(p)
        hi = sci.hi_of(p, pal)
        clock = sci.Clock(scene, duration, 1.0)
        sci.guard(scene, duration)
        sci.background(scene, pal, st, seed=11)
        ts = p.text_size
        shut = "left" if p.open_eye == "right" else "right"
        side = 1 if p.open_eye == "right" else -1          # the dot is on the open eye's side

        plan = {"full": (0.3, 0.45, 0.25), "instructions": (1, 0, 0), "test": (0, 1, 0), "explain": (0, 0, 1)}[p.phases]
        if p.phases == "full" and duration < 6:
            plan = (0.35, 0.65, 0)          # too short to explain: instructions + test only

        # ---- phase 1: instructions
        if plan[0]:
            title = sci.headline(p.title, st, pal, ts)
            steps = [(self._eye(pal, closed=True, s=0.42), f"Close your {shut} eye"),
                     (self._cross(pal, 0.4), f"Stare at the + with your {p.open_eye} eye"),
                     (self._arrows(pal), "Slowly move closer to the screen"),
                     (self._marker(p, hi, 0.2), f"Watch the {'dot' if p.marker == 'dot' else 'star'} vanish")]
            rows = VGroup()
            for k, (ico, label) in enumerate(steps):
                num = sci.text(str(k + 1), 0.5 * ts, pal["lavender"], bold=True, serif=True)
                t = sci.text(label, (0.48 if st.v else 0.44) * ts, pal["ink"], bold=k == 1, max_w=st.sw * 0.66)
                ico_box = ico.scale_to_fit_width(min(ico.width, 0.75)) if ico.width > 0.75 else ico
                rows.add(VGroup(num, ico_box, t).arrange(RIGHT, buff=0.32))
            rows.arrange(DOWN, buff=0.5 if st.v else 0.36, aligned_edge=LEFT)
            top, bottom = st.content(True)
            rows.scale(min(1.6, (top - bottom) * 0.8 / rows.height, st.sw * 0.9 / rows.width))
            rows.move_to([st.cx, (top + bottom) / 2, 0])
            scene.add(title, rows)
            scene.play(FadeIn(rows[0], shift=RIGHT * 0.1), run_time=0.3)
            dur = duration * plan[0] - clock.now
            scene.play(*[r.animate(rate_func=rate_functions.there_and_back).scale(1.04) for r in rows[1:]], run_time=max(0.3, dur * 0.6))
            scene.wait(max(0.05, duration * plan[0] - clock.now - 0.35))
            scene.play(FadeOut(rows), FadeOut(title), run_time=0.3)

        # ---- phase 2: the test card (nothing moves: motion would spoil the effect)
        if plan[1]:
            gap = st.w * p.spacing
            cross = self._cross(pal, 0.75 if st.v else 0.62).move_to([-side * gap / 2, st.cy * 0.3, 0])
            mark = self._marker(p, hi, 0.34 if st.v else 0.3).move_to([side * gap / 2, st.cy * 0.3, 0])
            hint = sci.text(f"{shut} eye closed  ·  stare at the +  ·  move closer", 0.42 * ts, pal["muted"], max_w=st.sw * 0.95)
            hint.move_to([0, st.top - hint.height / 2, 0])
            scene.play(FadeIn(cross), FadeIn(mark), FadeIn(hint), run_time=0.3)
            hold = duration * (plan[0] + plan[1]) - clock.now
            if hold > 0.05:
                scene.wait(hold)
            if plan[2]:
                scene.play(FadeOut(VGroup(cross, mark, hint)), run_time=0.3)

        # ---- phase 3: why (eye seen from above, the dot's image falls on the optic disc)
        if plan[2] and clock.left > 0.8:
            pre = VGroup()
            if plan[0] == 0 and plan[1] == 0:
                pre = sci.headline(p.title, st, pal, ts)
                scene.add(pre)
            top, bottom = st.content(bool(len(pre)))
            eye, disc, ray_end, lens_c = self._eye_section(pal, hi, side)
            cap = sci.wrapped(p.explain_text, 0.42 * ts, pal["ink"], 30 if st.v else 60, st.sw * 0.92, bold=True)
            bottom += st.place_caption(cap)
            size = min((top - bottom) * 0.8, st.sw * 0.85)
            eye.scale_to_fit_height(size).move_to([st.cx, (top + bottom) / 2, 0])
            k = eye.height / 4.0
            disc_pt, lens_pt = eye.disc.get_center(), eye.lens.get_center()
            # light from the dot enters through the lens and crosses to the far side of the retina
            src = lens_pt + np.array([0, 1, 0]) * 2.6 * k + np.array([side * 1.2 * k, 0, 0])
            ray = Line(src, lens_pt).set_stroke(hi, 4)
            ray2 = Line(lens_pt, disc_pt).set_stroke(hi, 4)
            labels = VGroup()
            if p.labels:
                labels.add(sci.callout(disc_pt, "optic disc: the blind spot", (side * 1, -0.6), hi, pal, 0.3 * ts, 0.5 * k))
                labels.add(sci.callout(eye.nerve.get_end(), "optic nerve", (-side * 1, -0.4), pal["muted"], pal, 0.28 * ts, 0.35 * k))
            scene.play(FadeIn(eye), FadeIn(cap), FadeIn(labels), run_time=0.3)
            t = max(0.4, min(1.6, clock.left * 0.45))
            scene.play(Create(ray), run_time=t * 0.5)
            scene.play(Create(ray2), run_time=t * 0.5)
            if clock.left > 0.5:
                scene.play(eye.disc.animate(rate_func=rate_functions.there_and_back).scale(1.6), run_time=min(0.6, clock.left - 0.1))
            sci.finish(scene, clock, p.camera, focus=disc_pt)
        elif clock.left > 0.05:
            scene.wait(clock.left)

    # ---- drawings
    @staticmethod
    def _cross(pal, s):
        return VGroup(Line(LEFT * s / 2, RIGHT * s / 2), Line(UP * s / 2, DOWN * s / 2)).set_stroke(pal["ink"], 9 * s / 0.62)

    @staticmethod
    def _marker(p, color, r):
        if p.marker == "star":
            return Star(5, outer_radius=r * 1.2, inner_radius=r * 0.5).set_fill(color, 1).set_stroke(width=0)
        return Circle(radius=r).set_fill(color, 1).set_stroke(width=0)

    @staticmethod
    def _eye(pal, closed: bool, s: float):
        if closed:
            lid = Arc(radius=s, start_angle=np.pi * 1.15, angle=np.pi * 0.7).set_stroke(pal["ink"], 4)
            lashes = VGroup(*[Line(lid.point_from_proportion(f), lid.point_from_proportion(f) + DOWN * 0.12 + RIGHT * (f - 0.5) * 0.12)
                              for f in (0.2, 0.4, 0.6, 0.8)]).set_stroke(pal["ink"], 3)
            return VGroup(lid, lashes)
        return VGroup(Circle(radius=s).set_stroke(pal["ink"], 3), Circle(radius=s * 0.4).set_fill(pal["ink"], 1))

    @staticmethod
    def _arrows(pal):
        a = VGroup(Line(LEFT * 0.35, RIGHT * 0.35), Line(RIGHT * 0.35, RIGHT * 0.2 + UP * 0.13), Line(RIGHT * 0.35, RIGHT * 0.2 + DOWN * 0.13))
        screen = Rectangle(width=0.08, height=0.6).set_fill(pal["sky"], 1).set_stroke(width=0).next_to(a, RIGHT, buff=0.1)
        return VGroup(a.set_stroke(pal["ink"], 4), screen)

    @staticmethod
    def _eye_section(pal, hi, side):
        """Right eye seen from above (front of the eye at the top). The optic nerve leaves on the nose side,
        so the blind spot sits on the temporal side of the visual field."""
        globe = Circle(radius=2.0).set_stroke(pal["ink"], 3).set_fill(pal["panel"], 0.6)
        retina = Arc(radius=1.88, start_angle=np.pi * 0.08 + np.pi, angle=np.pi * 0.84 + np.pi * 0.0).set_stroke(pal["mint"], 6)
        retina.rotate(0)                               # back half of the eye
        cornea = Arc(radius=0.9, start_angle=np.pi * 0.17, angle=np.pi * 0.66).shift(UP * 1.32).set_stroke(pal["ink"], 3)
        lens = Ellipse(width=1.05, height=0.42).move_to(UP * 1.2).set_stroke(pal["sky"], 3).set_fill(pal["sky"], 0.25)
        lens_c = Circle(radius=0.05).set_stroke(width=0).set_fill(pal["sky"], 0).move_to(UP * 1.2)
        # nose side: towards the other eye. For the right eye seen from above, the nose is on the left (-x).
        ang = np.pi * 1.5 - side * 0.27
        disc_pt = np.array([np.cos(ang), np.sin(ang), 0]) * 1.88
        disc = Circle(radius=0.17).move_to(disc_pt).set_fill(hi, 1).set_stroke(pal["ink"], 2)
        nerve = sci.smooth([disc_pt, disc_pt + np.array([-side * 0.2, -0.8, 0]), disc_pt + np.array([-side * 0.6, -1.7, 0])], pal["peach"], 14, 0.9)
        g = VGroup(nerve, globe, retina, cornea, lens, disc, lens_c)
        g.disc, g.lens, g.nerve = disc, lens_c, nerve
        return g, disc, None, lens_c
