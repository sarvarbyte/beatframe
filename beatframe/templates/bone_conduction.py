"""Two ways sound reaches the inner ear: through the air (ear canal, eardrum, middle-ear bones) and
through the bones of the skull. Classic use: why your recorded voice sounds strange.

Accuracy notes (conceptual diagram, side view): most everyday hearing is air conduction; bone
conduction adds to it, most noticeably for your own voice (part of it reaches the cochlea through the
skull, which mainly strengthens its lower frequencies). Both paths end in the same cochlea. The
scene says "also", never "instead". A recording only captures the air path.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
from manim import (
    DOWN, LEFT, RIGHT, UP, Arc, Circle, FadeIn, FadeOut, Line, MoveAlongPath, Polygon, RoundedRectangle,
    ShowPassingFlash, VGroup, VMobject, rate_functions,
)

from beatframe.templates import sci
from beatframe.templates.sci import SciParams, Stage

# head-local landmarks (head_profile units, facing right)
MOUTH = np.array([1.24, -0.62, 0])
EAR = np.array([-0.18, 0.12, 0])          # auricle centre
CANAL = np.array([0.02, 0.06, 0])         # opening of the ear canal (seen through the cutaway)
COCHLEA = np.array([0.30, -0.02, 0])      # inner ear, just in front of / under the auricle in a cutaway
JAW = np.array([0.72, -1.02, 0])          # voice box / jaw vibration
MASTOID = np.array([-0.62, -0.38, 0])     # bone behind the ear (tuning fork, bone-conduction test)
CHEEK = np.array([0.42, 0.18, 0])         # cheekbone, where bone-conduction headphones sit


def spiral(center, r: float, turns: float = 2.6) -> VMobject:
    ts = np.linspace(0, 1, 70)
    pts = [np.array(center) + r * (0.18 + 0.82 * (1 - t)) * np.array([np.cos(t * turns * 2 * np.pi), np.sin(t * turns * 2 * np.pi), 0])
           for t in ts]
    return VMobject().set_points_smoothly(pts)


class BoneConduction(sci.Template):
    name = "bone_conduction"
    description = "Sound reaches the inner ear through the air and through the skull: compare the two paths"
    category = "Human perception"
    theme = "bright"
    vertical_width = 8.0

    class Params(SciParams):
        source: Literal["own_voice", "tuning_fork", "headphones"] = "own_voice"
        mode: Literal["compare", "air", "bone"] = "compare"
        air_label: str = "through the air"
        bone_label: str = "through the skull"
        caption: str = "Your own voice reaches your inner ear both ways at once"

    def build(self, scene, p, duration):
        st, pal = Stage(), sci.pal_of(p)
        hi = sci.hi_of(p, pal)
        air_c, bone_c = pal["sky"], hi if p.highlight != "sky" else pal["coral"]
        clock = sci.Clock(scene, duration, p.speed)
        sci.guard(scene, duration)
        sci.background(scene, pal, st, seed=5)
        title = sci.headline(p.title, st, pal, p.text_size)
        top, bottom = st.content(bool(p.title))
        cap = sci.wrapped(p.caption, 0.42 * p.text_size, pal["muted"], 30 if st.v else 64, st.sw * 0.92) if p.caption else VGroup()
        bottom += st.place_caption(cap)

        # ---- the head (built at scale 1, placed afterwards)
        head = sci.head_profile(1.0).set_stroke(pal["ink"], 3.2).set_fill(pal["panel"], 0.55)
        skull = sci.head_profile(0.86).shift(UP * 0.12 + LEFT * 0.06).set_stroke(pal["muted"], 1.6, 0.5)
        ear = sci.ear_shape(1.25).move_to(EAR).set_stroke(pal["ink"], 2.6).set_fill(pal["panel"], 0.9)
        cut = Circle(radius=0.42).move_to(COCHLEA + LEFT * 0.08).set_stroke(pal["muted"], 1.2, 0.7)
        cut.set_fill(pal["bottom"], 0.55)
        canal = Line(CANAL + LEFT * 0.28, COCHLEA + LEFT * 0.17).set_stroke(pal["muted"], 3, 0.8)
        drum = Line(COCHLEA + LEFT * 0.2 + UP * 0.1, COCHLEA + LEFT * 0.2 + DOWN * 0.1).set_stroke(pal["ink"], 2.4)
        coch = spiral(COCHLEA + RIGHT * 0.05, 0.16).set_stroke(pal["lavender"], 3)
        parts = VGroup(head, skull, cut, canal, drum, coch, ear)

        if p.source == "tuning_fork":
            fork = VGroup(Line(np.zeros(3), DOWN * 0.55), Line(LEFT * 0.12, LEFT * 0.12 + UP * 0.7),
                          Line(RIGHT * 0.12, RIGHT * 0.12 + UP * 0.7), Arc(radius=0.12, start_angle=np.pi, angle=np.pi))
            fork.set_stroke(pal["warm"], 4).rotate(0.7).move_to(MASTOID + LEFT * 0.42 + DOWN * 0.5)
            bone_from, air_from = MASTOID, MOUTH + RIGHT * 1.6 + UP * 0.6
            speaker = self._speaker(pal).move_to(air_from + RIGHT * 0.35)
            props = VGroup(fork, speaker)
        elif p.source == "headphones":
            pad = RoundedRectangle(width=0.32, height=0.5, corner_radius=0.12).set_fill(pal["purple"], 1).set_stroke(pal["ink"], 2)
            pad.move_to(CHEEK)
            band = sci.smooth([CHEEK + UP * 0.25, CHEEK + UP * 1.1 + LEFT * 0.3, np.array([-0.2, 1.85, 0])], pal["purple"], 6)
            bone_from, air_from = CHEEK, MOUTH + RIGHT * 1.6 + UP * 0.6
            speaker = self._speaker(pal).move_to(air_from + RIGHT * 0.35)
            props = VGroup(band, pad, speaker)
        else:
            bone_from, air_from = JAW, MOUTH + RIGHT * 0.12
            props = VGroup()
        figure = VGroup(parts, props)

        # air path: out of the mouth (or a speaker), around the face, into the ear canal
        out = MOUTH + RIGHT * 1.0 + UP * 0.25 if p.source == "own_voice" else air_from
        # through the air, around the outside of the head, into the ear from behind
        air_path = sci.smooth([air_from, out, np.array([1.55, 1.75, 0]), np.array([0.2, 2.35, 0]), np.array([-1.35, 1.5, 0]),
                               np.array([-1.55, 0.3, 0]), EAR + LEFT * 0.35, CANAL, COCHLEA + LEFT * 0.15], air_c, 2, 0.3)
        bone_path = sci.smooth([bone_from, (bone_from + COCHLEA) / 2 + np.array([0.12, -0.12, 0]), COCHLEA], bone_c, 2, 0.28)
        figure.add(air_path, bone_path)

        # ---- size and place: head left + legend right (16:9) or head above legend (9:16)
        area_h = top - bottom
        if st.v:
            figure.scale_to_fit_height(min(area_h * 0.7, st.sw * 1.05))
            figure.move_to([st.cx - 0.2, top - figure.height / 2 - 0.1, 0])
        else:
            figure.scale_to_fit_height(area_h * 0.9)
            figure.move_to([st.left + st.sw * 0.3, (top + bottom) / 2, 0])
        s = figure.height / 3.6

        ts = 0.3 * p.text_size
        legend_rows = []
        if p.mode in ("compare", "air"):
            legend_rows.append(self._row(p.air_label, "ear canal, eardrum, tiny bones", air_c, pal, ts))
        if p.mode in ("compare", "bone"):
            legend_rows.append(self._row(p.bone_label, "the skull itself vibrates", bone_c, pal, ts))
        legend = VGroup(*legend_rows).arrange(DOWN, buff=0.28, aligned_edge=LEFT)
        if st.v:
            legend.scale_to_fit_width(min(legend.width, st.sw * 0.95))
            legend.move_to([st.cx, bottom + legend.height / 2 + 0.1, 0])
        else:
            legend.move_to([st.left + st.sw * 0.78, (top + bottom) / 2 + 0.4, 0])
            if legend.width > st.sw * 0.42:
                legend.scale_to_fit_width(st.sw * 0.42)
        labels = VGroup()
        if p.labels:
            c = coch.get_center()
            labels.add(sci.callout(c, "inner ear (cochlea)", (0.8, -1) if not st.v else (1, -0.55), pal["lavender"], pal,
                                   ts * 0.95, 0.9 * s))

        scene.add(figure)
        scene.play(FadeIn(title), FadeIn(cap), FadeIn(legend), FadeIn(labels), run_time=0.3)

        def air_wave(t):
            dots = VGroup(*[sci.glow_dot(air_c, 0.05 * s / 1.6 + 0.02, 3) for _ in range(3)])
            arcs_ = sci.arcs(air_path.get_start(), 0.22 * s, 3, 1.3, 0.35, air_c, 2.6)
            anims = [MoveAlongPath(d, air_path, rate_func=rate_functions.linear, run_time=t * (1 - 0.18 * k)) for k, d in enumerate(dots)]
            for d in dots:
                d.move_to(air_path.get_start())
            return dots, arcs_, anims

        def bone_wave(t):
            rings = VGroup(*[Circle(radius=0.1 * s).move_to(bone_path.get_start()).set_stroke(bone_c, 3, 0.9) for _ in range(3)])
            flash = bone_path.copy().set_stroke(bone_c, 8, 1)
            anims = [ShowPassingFlash(flash, time_width=0.6, run_time=t)]
            anims += [r.animate(rate_func=rate_functions.ease_out_sine, run_time=t * (0.6 + 0.2 * k)).scale(3.5 + 2 * k).set_stroke(opacity=0)
                      for k, r in enumerate(rings)]
            shake = skull.animate(rate_func=rate_functions.wiggle, run_time=t).set_stroke(bone_c, 2.4, 0.9)
            return rings, anims + [shake]

        def arrive(color):
            ring = Circle(radius=0.2 * s).move_to(coch).set_stroke(color, 4)
            return [coch.animate(rate_func=rate_functions.there_and_back).set_stroke(color, 5),
                    ring.animate(rate_func=rate_functions.ease_out_cubic).scale(2.4).set_stroke(opacity=0)]

        t = clock.t(0.22, 0.9, 2.2)
        if p.mode in ("compare", "air") and clock.fits(t):
            dots, arcs_, anims = air_wave(t)
            scene.add(dots)
            scene.play(*anims, FadeIn(arcs_, lag_ratio=0.3), legend_rows[0].animate.set_opacity(1), run_time=t)
            scene.play(*arrive(air_c), FadeOut(dots), FadeOut(arcs_), run_time=0.45)
        if p.mode in ("compare", "bone") and clock.fits(t):
            rings, anims = bone_wave(t)
            scene.play(*anims, run_time=t)
            scene.play(*arrive(bone_c), FadeOut(rings), skull.animate.set_stroke(pal["muted"], 1.6, 0.5), run_time=0.45)
        if p.mode == "compare" and clock.fits(1.6):
            t2 = clock.t(0.2, 0.9, 1.8)
            dots, arcs_, a1 = air_wave(t2)
            rings, a2 = bone_wave(t2)
            scene.add(dots)
            scene.play(*a1, *a2, FadeIn(arcs_), run_time=t2)
            both = sci.tag("both reach the same cochlea", pal["lavender"], pal, ts)
            both.next_to(legend, DOWN, buff=0.3) if not st.v else both.next_to(legend, UP, buff=0.22)
            scene.play(*arrive(pal["lavender"]), FadeOut(dots), FadeOut(arcs_), FadeOut(rings), FadeIn(both, shift=UP * 0.1),
                       skull.animate.set_stroke(pal["muted"], 1.6, 0.5), run_time=0.5)
        sci.finish(scene, clock, p.camera, focus=coch.get_center())

    @staticmethod
    def _speaker(pal) -> VGroup:
        box = RoundedRectangle(width=0.32, height=0.5, corner_radius=0.06).set_fill(pal["panel"], 1).set_stroke(pal["ink"], 2)
        cone = Polygon([-0.06, 0.14, 0], [-0.06, -0.14, 0], [-0.3, -0.3, 0], [-0.3, 0.3, 0]).set_fill(pal["sky"], 0.8).set_stroke(pal["ink"], 2)
        return VGroup(box, cone.next_to(box, LEFT, buff=0))

    @staticmethod
    def _row(head_s: str, sub: str, color: str, pal, size) -> VGroup:
        dot = Circle(radius=0.11).set_stroke(width=0).set_fill(color, 1)
        t = VGroup(sci.text(head_s, size * 1.25, pal["ink"], bold=True), sci.text(sub, size, pal["muted"])).arrange(DOWN, buff=0.08, aligned_edge=LEFT)
        return VGroup(dot, t).arrange(RIGHT, buff=0.22)
