"""Light enters the eye, the cornea and lens focus an upside-down image on the retina, and a close-up of
the retina shows the signal path: light passes through to the rods and cones at the back, and their
signal travels forward through bipolar cells to ganglion cells, whose fibres form the optic nerve.

Accuracy notes (simplified diagram, side view, light from the left): the vertebrate retina is
'inverted': photoreceptors face away from the light and the ganglion-cell layer is nearest the lens.
The image on the retina is inverted; the brain interprets it. Horizontal and amacrine cells are left out.
"""

from __future__ import annotations

import numpy as np
from manim import (
    DOWN, LEFT, RIGHT, UP, Arc, Arrow, Circle, Create, Ellipse, FadeIn, Line, MoveAlongPath, RoundedRectangle,
    ShowPassingFlash, VGroup, rate_functions,
)

from beatframe.templates import sci
from beatframe.templates.sci import SciParams, Stage


class RetinaProcessing(sci.Template):
    name = "retina_processing"
    description = "Light focused onto the retina (upside down), then the retina close-up: rods/cones -> bipolar -> ganglion -> optic nerve"
    category = "Human perception"
    theme = "bright"
    vertical_width = 8.0

    class Params(SciParams):
        close_up: bool = True            # show the retina layers and the signal path
        caption: str = "Light reaches the rods and cones at the back; the signal travels back out to the optic nerve"

    def build(self, scene, p, duration):
        st, pal = Stage(), sci.pal_of(p)
        hi = sci.hi_of(p, pal)
        clock = sci.Clock(scene, duration, p.speed)
        sci.guard(scene, duration)
        sci.background(scene, pal, st, seed=43)
        ts = p.text_size
        title = sci.headline(p.title, st, pal, ts)
        top, bottom = st.content(bool(p.title))
        cap = sci.wrapped(p.caption, 0.4 * ts, pal["muted"], 30 if st.v else 66, st.sw * 0.92) if p.caption else VGroup()
        bottom += st.place_caption(cap)

        # ---- eye, light from the left (built around (0,0), radius 2)
        R = 2.0
        globe = Circle(radius=R).set_stroke(pal["ink"], 3).set_fill(pal["panel"], 0.55)
        cornea = Arc(radius=1.05, start_angle=np.pi * 0.72, angle=np.pi * 0.56).move_to([-R - 0.12, 0, 0]).set_stroke(pal["ink"], 3)
        iris = VGroup(Line([-1.55, 0.45, 0], [-1.55, 1.25, 0]), Line([-1.55, -0.45, 0], [-1.55, -1.25, 0])).set_stroke(pal["purple"], 6)
        lens = Ellipse(width=0.55, height=1.15).move_to([-1.3, 0, 0]).set_stroke(pal["sky"], 3).set_fill(pal["sky"], 0.25)
        retina = Arc(radius=R - 0.1, start_angle=-np.pi * 0.42, angle=np.pi * 0.84).set_stroke(pal["mint"], 7)
        disc_pt = np.array([np.cos(-0.18), np.sin(-0.18), 0]) * (R - 0.1)
        nerve = sci.smooth([disc_pt, disc_pt + np.array([0.7, -0.15, 0]), disc_pt + np.array([1.5, -0.55, 0])], pal["peach"], 16, 0.9)
        eye = VGroup(nerve, globe, retina, cornea, iris, lens)
        # object: an upright arrow far left; its image lands upside down on the retina
        obj = Arrow([-4.3, -0.55, 0], [-4.3, 0.85, 0], buff=0, stroke_width=8, max_tip_length_to_length_ratio=0.3).set_color(pal["peach"])
        tip_img = np.array([R - 0.12, -0.7, 0])
        base_img = np.array([R - 0.12, 0.3, 0])
        img = Arrow(base_img, tip_img, buff=0, stroke_width=6, max_tip_length_to_length_ratio=0.35).set_color(pal["peach"])
        rays = VGroup(sci.smooth([obj.get_end(), [-1.3, 0.3, 0], tip_img], pal["warm"], 2.4, 0.9),
                      sci.smooth([obj.get_end(), [-1.3, -0.25, 0], tip_img], pal["warm"], 2.4, 0.9),
                      sci.smooth([obj.get_start(), [-1.3, 0.25, 0], base_img], pal["warm"], 2.4, 0.6),
                      sci.smooth([obj.get_start(), [-1.3, -0.3, 0], base_img], pal["warm"], 2.4, 0.6))
        scene_eye = VGroup(eye, obj, img, rays)

        # ---- retina close-up panel (light from the left, back of the eye on the right)
        panel = VGroup()
        if p.close_up:
            W, H = 5.2, 3.4
            box = sci.card(W, H, pal)
            xs = {"gang": -1.5, "bip": 0.1, "photo": 1.55}
            rows = [-1.0, 0.0, 1.0]
            cells = VGroup()
            for y in rows:
                g = Circle(radius=0.2).set_fill(pal["lavender"], 0.95).set_stroke(width=0).move_to([xs["gang"], y, 0])
                b = Ellipse(width=0.42, height=0.24).set_fill(pal["sky"], 0.95).set_stroke(width=0).move_to([xs["bip"], y, 0])
                rod = RoundedRectangle(width=0.6, height=0.16, corner_radius=0.07).set_fill(pal["mint"], 1).set_stroke(width=0).move_to([xs["photo"], y + 0.17, 0])
                cone = VGroup(RoundedRectangle(width=0.32, height=0.2, corner_radius=0.08).set_fill(pal["peach"], 1).set_stroke(width=0),
                              ).move_to([xs["photo"] - 0.12, y - 0.15, 0])
                links = VGroup(Line(g.get_right(), b.get_left()), Line(b.get_right(), rod.get_left()), Line(b.get_right(), cone.get_left())).set_stroke(pal["muted"], 2, 0.8)
                fibre = Line(g.get_left(), [xs["gang"] - 0.55, y, 0]).set_stroke(pal["lavender"], 2.5, 0.9)
                cells.add(VGroup(links, fibre, g, b, rod, cone))
            epi = RoundedRectangle(width=0.32, height=H - 0.5, corner_radius=0.12).set_fill(pal["faint"], 0.9).set_stroke(width=0).move_to([2.25, 0, 0])
            to_nerve = sci.smooth([[xs["gang"] - 0.55, 1.0], [xs["gang"] - 0.75, 0], [xs["gang"] - 0.6, -1.4], [xs["gang"] + 0.4, -1.55]], pal["lavender"], 3)
            heads = VGroup(*[sci.text(t, 0.3, c, bold=True).move_to([x, H / 2 - 0.3, 0])
                             for t, c, x in (("ganglion", pal["lavender"], xs["gang"]), ("bipolar", pal["sky"], xs["bip"]), ("rods & cones", pal["mint"], xs["photo"]))])
            light_lab = sci.text("light →", 0.3, pal["warm"], bold=True).move_to([-W / 2 + 0.55, -H / 2 + 0.3, 0])
            panel = VGroup(box, epi, cells, to_nerve, heads, light_lab)
            panel.cells, panel.xs, panel.to_nerve = cells, xs, to_nerve

        # ---- layout
        area_h = top - bottom
        if st.v:
            scene_eye.scale_to_fit_width(st.sw * 0.98)
            if p.close_up:
                eh = area_h * 0.5
                if scene_eye.height > eh:
                    scene_eye.scale_to_fit_height(eh)
                scene_eye.move_to([st.cx, top - scene_eye.height / 2 - 0.05, 0])
                panel.scale_to_fit_width(st.sw * 0.95)
                if panel.height > area_h - scene_eye.height - 0.4:
                    panel.scale_to_fit_height(area_h - scene_eye.height - 0.4)
                panel.move_to([st.cx, bottom + panel.height / 2, 0])
            else:
                scene_eye.move_to([st.cx, (top + bottom) / 2, 0])
        else:
            if p.close_up:
                scene_eye.scale(min(st.sw * 0.5 / scene_eye.width, area_h * 0.85 / scene_eye.height)).move_to([st.left + st.sw * 0.27, (top + bottom) / 2, 0])
                panel.scale(min(st.sw * 0.42 / panel.width, area_h * 0.85 / panel.height)).move_to([st.right - st.sw * 0.22, (top + bottom) / 2, 0])
            else:
                scene_eye.scale(min(st.sw * 0.9 / scene_eye.width, area_h * 0.9 / scene_eye.height)).move_to([st.cx, (top + bottom) / 2, 0])
        k = scene_eye.height / 4.2

        labels = VGroup()
        if p.labels:
            s = 0.26 * ts
            labels.add(sci.callout(lens.get_top(), "lens", (-0.2, 1), pal["sky"], pal, s, 0.45 * k))
            labels.add(sci.callout(retina.point_from_proportion(0.85), "retina", (0.6, 1), pal["mint"], pal, s, 0.4 * k))
            labels.add(sci.callout(nerve.point_from_proportion(0.5), "optic nerve", (-0.5, -1), pal["peach"], pal, s, 0.3 * k))

        scene.add(eye, obj)
        scene.play(FadeIn(title), FadeIn(cap), FadeIn(labels), FadeIn(panel), run_time=0.3)
        t = clock.t(0.16, 0.6, 1.4)
        scene.play(*[Create(r) for r in rays], run_time=t)
        scene.play(FadeIn(img, scale=0.6), retina.animate(rate_func=rate_functions.there_and_back).set_stroke(hi, 9), run_time=0.45)
        flip = sci.tag("upside down", pal["peach"], pal, 0.26 * ts).next_to(img, LEFT, buff=0.15)
        scene.play(FadeIn(flip), run_time=0.25)

        if p.close_up and clock.left > 1.5:
            cells, xs = panel.cells, panel.xs
            # light crosses the whole retina to the photoreceptors at the back
            beams = VGroup(*[Line(c[2].get_center() + LEFT * 0.9 * cells.height / 2.6, c[4].get_center()).set_stroke(pal["warm"], 5)
                             for c in cells])
            t = clock.t(0.12, 0.5, 1.0)
            scene.play(*[ShowPassingFlash(b, time_width=0.7) for b in beams], run_time=t)
            scene.play(*[c[4].animate(rate_func=rate_functions.there_and_back).set_fill(hi, 1) for c in cells],
                       *[c[5].animate(rate_func=rate_functions.there_and_back).set_fill(hi, 1) for c in cells], run_time=0.35)
            # signal back out: photoreceptor -> bipolar -> ganglion -> optic-nerve fibres
            back = [sci.smooth([c[4].get_center(), c[3].get_center(), c[2].get_center(), c[1].get_end()], hi, 2, 0) for c in cells]
            sparks = [sci.glow_dot(hi, 0.05).move_to(b.get_start()) for b in back]
            scene.add(*sparks)
            t = clock.t(0.16, 0.6, 1.3)
            scene.play(*[MoveAlongPath(s_, b, rate_func=rate_functions.ease_in_out_sine) for s_, b in zip(sparks, back)],
                       *[c[3].animate(rate_func=rate_functions.there_and_back).scale(1.2) for c in cells], run_time=t)
            scene.play(ShowPassingFlash(panel.to_nerve.copy().set_stroke(hi, 6), time_width=0.6), *[s_.animate.set_opacity(0) for s_ in sparks],
                       *[c[2].animate(rate_func=rate_functions.there_and_back).scale(1.25) for c in cells], run_time=min(0.8, clock.left * 0.5))
            if clock.left > 0.6:
                scene.play(ShowPassingFlash(nerve.copy().set_stroke(hi, 10), time_width=0.6), run_time=min(0.6, clock.left - 0.1))
        sci.finish(scene, clock, p.camera)
