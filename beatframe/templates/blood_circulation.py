"""Double circulation: the right side of the heart pumps oxygen-poor blood to the lungs, the left side
pumps oxygen-rich blood to the body, and it all comes back. Blood keeps flowing around both loops
while the heart beats.

Accuracy notes (stylised diagram, front view, so the heart's right side is on the viewer's left):
right ventricle -> pulmonary artery -> lungs -> pulmonary veins -> left atrium; left ventricle ->
aorta -> body -> veins (venae cavae) -> right atrium. Blue for oxygen-poor blood is a diagram
convention: real deoxygenated blood is dark red. The legend says so.
"""

from __future__ import annotations

import numpy as np
from manim import (
    DOWN, LEFT, RIGHT, UP, Circle, Ellipse, FadeIn, RoundedRectangle, UpdateFromAlphaFunc, VGroup, linear,
    rate_functions,
)
from pydantic import Field

from beatframe.templates import sci
from beatframe.templates.sci import SciParams, Stage


class BloodCirculation(sci.Template):
    name = "blood_circulation"
    description = "Heart, lungs and body: two loops of blood flow (to the lungs and to the body) with a beating heart"
    category = "Biology"
    theme = "bright"
    vertical_width = 8.0

    class Params(SciParams):
        cells: int = Field(9, ge=4, le=16)            # moving blood cells per vessel
        bpm: int = Field(70, ge=40, le=160)
        caption: str = "Right side to the lungs, left side to the body, then back again"

    def build(self, scene, p, duration):
        st, pal = Stage(), sci.pal_of(p)
        clock = sci.Clock(scene, duration, p.speed)
        sci.guard(scene, duration)
        sci.background(scene, pal, st, seed=71)
        ts = p.text_size
        rich, poor = pal["coral"], pal["sky"]
        title = sci.headline(p.title, st, pal, ts)
        top, bottom = st.content(bool(p.title))
        cap = sci.wrapped(p.caption, 0.4 * ts, pal["muted"], 30 if st.v else 66, st.sw * 0.92) if p.caption else VGroup()
        bottom += st.place_caption(cap)

        # ---- built in a 7 x 9 box: lungs on top, heart in the middle, body at the bottom
        def chamber(x, y, c, w=0.95, h=0.85):
            return RoundedRectangle(width=w, height=h, corner_radius=0.3).set_fill(c, 0.85).set_stroke(pal["ink"], 2).move_to([x, y, 0])
        RA, LA = chamber(-0.55, 0.45, poor), chamber(0.55, 0.45, rich)
        RV, LV = chamber(-0.55, -0.5, poor, h=1.0), chamber(0.55, -0.55, rich, h=1.1)
        heart = VGroup(RA, LA, RV, LV)
        lungs = VGroup(*[Ellipse(width=1.9, height=2.5).set_fill(pal["lavender"], 0.22).set_stroke(pal["lavender"], 2.5).move_to([s * 1.35, 3.5, 0]) for s in (-1, 1)])
        body = RoundedRectangle(width=4.6, height=1.5, corner_radius=0.6).set_fill(pal["peach"], 0.18).set_stroke(pal["peach"], 2.5).move_to([0, -3.7, 0])
        beds = VGroup(*[sci.smooth([[x, 3.0], [x + 0.25, 3.5], [x - 0.15, 4.0]], pal["lavender"], 1.5, 0.6) for x in (-1.6, -1.2, 1.2, 1.6)],
                      *[sci.smooth([[x, -3.4], [x + 0.2, -3.7], [x - 0.15, -4.0]], pal["peach"], 1.5, 0.6) for x in (-1.2, -0.4, 0.4, 1.2)])
        # vessels (each one direction of flow)
        v_pa = sci.smooth([RV.get_left() + UP * 0.1, [-1.4, 0.1], [-1.9, 1.6], [-1.5, 2.6]], poor, 7, 0.55)            # to lungs
        v_pv = sci.smooth([[1.5, 2.6], [1.9, 1.7], [1.45, 0.9], LA.get_right()], rich, 7, 0.55)                          # from lungs
        v_ao = sci.smooth([LV.get_right() + DOWN * 0.1, [1.7, -1.0], [2.6, -2.2], [2.0, -3.2]], rich, 7, 0.55)            # to body
        v_vc = sci.smooth([[-2.0, -3.2], [-2.6, -2.0], [-2.0, 0.6], RA.get_left()], poor, 7, 0.55)                          # from body
        cross_l = sci.smooth([[-1.5, 2.6], [-0.4, 3.2], [0.4, 3.2], [1.5, 2.6]], pal["lavender"], 3, 0.0)                 # through lungs
        cross_b = sci.smooth([[2.0, -3.2], [0.8, -3.95], [-0.8, -3.95], [-2.0, -3.2]], pal["peach"], 3, 0.0)              # through body
        vessels = VGroup(v_pa, v_pv, v_ao, v_vc)
        diagram = VGroup(lungs, body, beds, vessels, cross_l, cross_b, heart)

        lab = VGroup(sci.text("lungs", 0.7, pal["lavender"], bold=True).move_to([0, 5.1, 0]),
                     sci.text("body", 0.7, pal["peach"], bold=True).move_to(body.get_center() + UP * 0.05))
        diagram.add(lab)
        legend = VGroup(*[VGroup(Circle(radius=0.1).set_fill(c, 1).set_stroke(width=0), sci.text(t, 0.32 * ts, pal["ink"])).arrange(RIGHT, buff=0.15)
                          for c, t in ((rich, "oxygen-rich"), (poor, "oxygen-poor (drawn blue; really dark red)"))]).arrange(DOWN, buff=0.15, aligned_edge=LEFT)

        area = top - bottom
        if st.v:
            diagram.scale(min(st.sw * 0.95 / diagram.width, (area - legend.height - 0.3) / diagram.height)).move_to([st.cx, top - diagram.height / 2 + 0.05, 0])
            legend.scale_to_fit_width(min(legend.width, st.sw * 0.95)).next_to(diagram, DOWN, buff=0.2)
        else:
            diagram.scale(area * 0.98 / diagram.height).move_to([st.cx - st.sw * 0.12, (top + bottom) / 2, 0])
            legend.next_to(diagram, RIGHT, buff=0.6).align_to(diagram, DOWN).shift(UP * 0.3)
        k = diagram.height / 9.9

        labels = VGroup()
        if p.labels:
            s = 0.25 * ts
            labels.add(sci.callout(RA.get_center(), "right side", (-1, 0.15), poor, pal, s, 1.3 * k),
                       sci.callout(LA.get_center(), "left side", (1, 0.15), rich, pal, s, 1.3 * k))
            if not st.v:
                labels.add(sci.callout(v_ao.point_from_proportion(0.55), "aorta", (1, -0.3), rich, pal, s, 0.5 * k),
                           sci.callout(v_vc.point_from_proportion(0.35), "back from the body", (-1, -0.3), poor, pal, s, 0.5 * k))

        scene.add(diagram)
        scene.play(FadeIn(title), FadeIn(cap), FadeIn(legend), FadeIn(labels), run_time=0.3)

        # flowing cells: one moving loop of dots per vessel, colour by oxygen content
        segs = [(v_pa, poor), (cross_l, None), (v_pv, rich), (v_ao, rich), (cross_b, None), (v_vc, poor)]
        flows = []
        for path, col in segs:
            for j in range(p.cells if col else max(3, p.cells // 2)):
                off = j / (p.cells if col else max(3, p.cells // 2))
                if col is None:       # through the capillary bed the colour changes
                    to_rich = path is cross_l
                    d = sci.glow_dot(poor if to_rich else rich, 0.045 * k + 0.012, 2)
                    d.path, d.off, d.change = path, off, (poor, rich) if to_rich else (rich, poor)
                else:
                    d = sci.glow_dot(col, 0.045 * k + 0.012, 2)
                    d.path, d.off, d.change = path, off, None
                d.move_to(path.point_from_proportion(off))
                flows.append(d)
        dots = VGroup(*flows)
        samples = {id(pth): np.array([pth.point_from_proportion(f) for f in np.linspace(0, 1, 240)]) for pth, _ in segs}   # cheap lookups per frame
        speed = 0.38 * p.speed

        def move(group, alpha):
            t = alpha * total * speed
            for d in group:
                f = (d.off + t) % 1.0
                d.move_to(samples[id(d.path)][int(f * 239)])
                if d.change:
                    from manim import interpolate_color, ManimColor
                    c = interpolate_color(ManimColor(d.change[0]), ManimColor(d.change[1]), min(1, max(0, (f - 0.25) / 0.5)))
                    d[-1].set_fill(c)
        total = max(1.0, clock.left - 0.05)
        beat = 60 / p.bpm

        def beat_heart(m, a):
            ph = (a * total) % beat / beat
            s_ = 1 + 0.07 * np.exp(-((ph - 0.15) / 0.08) ** 2) + 0.04 * np.exp(-((ph - 0.42) / 0.08) ** 2)
            m.become(heart_base.copy().scale(s_))
        heart_base = heart.copy()
        scene.add(dots)
        scene.play(UpdateFromAlphaFunc(dots, move, rate_func=linear), UpdateFromAlphaFunc(heart, beat_heart, rate_func=linear), run_time=total)
        if clock.left > 0.02:
            scene.wait(clock.left)
