"""A press on the skin, seen in cross-section: the skin dents, touch receptors fire, and two spike
trains show the difference between a slowly adapting receptor (keeps firing while the pressure lasts)
and a fast adapting one (fires when the press starts and when it ends).

Accuracy notes (simplified diagram, not to scale): Merkel endings are slowly adapting (SA1) and
Meissner corpuscles fast adapting (RA1) - both sit near the surface; deeper Pacinian corpuscles
respond to vibration. Spikes are illustrative patterns, not recordings. (The scene `skin_receptors`
is the catalogue of all four receptor types; this one is about a stimulus and adaptation.)
"""

from __future__ import annotations

from typing import Literal

import numpy as np
from manim import (
    DOWN, LEFT, RIGHT, UP, Arrow, Circle, Ellipse, FadeIn, Line, MoveAlongPath, RoundedRectangle, ShowPassingFlash,
    ValueTracker, VGroup, VMobject, linear, rate_functions,
)
from pydantic import Field

from beatframe.templates import sci
from beatframe.templates.sci import SciParams, Stage


class TouchReceptors(sci.Template):
    name = "touch_receptors"
    description = "A press dents the skin; receptors fire; spike trains show slow vs fast adapting touch sensors"
    category = "Human perception"
    theme = "bright"
    vertical_width = 8.0

    class Params(SciParams):
        stimulus: Literal["fingertip", "pin", "brush"] = "fingertip"
        press_share: float = Field(0.5, ge=0.25, le=0.7)    # how long the press lasts (share of the beat)
        caption: str = "Some touch sensors keep firing while you press; others only report the change"

    def build(self, scene, p, duration):
        st, pal = Stage(), sci.pal_of(p)
        hi = sci.hi_of(p, pal)
        clock = sci.Clock(scene, duration, p.speed)
        sci.guard(scene, duration)
        sci.background(scene, pal, st, seed=47)
        ts = p.text_size
        title = sci.headline(p.title, st, pal, ts)
        top, bottom = st.content(bool(p.title))
        cap = sci.wrapped(p.caption, 0.4 * ts, pal["muted"], 30 if st.v else 66, st.sw * 0.92) if p.caption else VGroup()
        bottom += st.place_caption(cap)
        sa_c, ra_c = pal["mint"], pal["sky"]

        # ---- skin block, built 8 wide x 3.4 tall around (0, 0); surface at y = 1.2
        W = 8.0
        dent = ValueTracker(0.0)
        def surface_pts(d):
            xs = np.linspace(-W / 2, W / 2, 90)
            ys = 1.2 - d * 0.45 * np.exp(-(xs / 0.7) ** 2)
            return [np.array([x, y, 0]) for x, y in zip(xs, ys)]
        surface = VMobject().set_points_smoothly(surface_pts(0)).set_stroke(pal["peach"], 4)
        place = {"c0": np.zeros(3), "s": 1.0, "c1": np.zeros(3)}     # local -> frame, set after layout
        epi = RoundedRectangle(width=W, height=0.7, corner_radius=0.1).set_fill(pal["peach"], 0.16).set_stroke(width=0).move_to([0, 0.85, 0])
        dermis = RoundedRectangle(width=W, height=1.5, corner_radius=0.1).set_fill(pal["coral"], 0.08).set_stroke(width=0).move_to([0, -0.25, 0])
        hypo = RoundedRectangle(width=W, height=0.9, corner_radius=0.1).set_fill(pal["warm"], 0.05).set_stroke(width=0).move_to([0, -1.45, 0])
        fat = VGroup(*[Circle(radius=0.17).set_fill(pal["warm"], 0.08).set_stroke(pal["faint"], 1).move_to([x, -1.45 + 0.12 * ((i % 2) - 0.5), 0])
                       for i, x in enumerate(np.linspace(-W / 2 + 0.4, W / 2 - 0.4, 18))])
        merkel = VGroup(*[Circle(radius=0.09).set_fill(sa_c, 1).set_stroke(width=0).move_to([-0.35 + 0.22 * i, 0.55, 0]) for i in range(3)])
        meiss = VGroup(*[Ellipse(width=0.42, height=0.12).set_stroke(ra_c, 2.5).move_to([0.75, 0.55 + 0.1 * i, 0]) for i in range(4)])
        pac = VGroup(*[Ellipse(width=0.25 + 0.15 * i, height=0.45 + 0.2 * i).set_stroke(pal["lavender"], 1.5, 0.6).move_to([-2.4, -1.2, 0]) for i in range(4)])
        sa_n = sci.smooth([merkel.get_bottom(), [-0.1, -0.6], [-0.6, -1.6], [-1.0, -1.75]], sa_c, 3, 0.9)
        ra_n = sci.smooth([meiss.get_bottom(), [0.9, -0.6], [0.3, -1.6], [-0.3, -1.75]], ra_c, 3, 0.9)
        skin = VGroup(hypo, fat, dermis, epi, pac, sa_n, ra_n, merkel, meiss)
        layer_labels = VGroup(*[sci.text(t, 0.3, pal["muted"]).move_to([W / 2 - 0.15, y, 0], aligned_edge=RIGHT)
                                for t, y in (("epidermis", 0.85), ("dermis", -0.25), ("fat layer", -1.45))])
        if p.stimulus == "pin":
            tool = VGroup(Line([0, 3.3, 0], [0, 1.45, 0]).set_stroke(pal["warm"], 5), Circle(radius=0.14).set_fill(pal["coral"], 1).set_stroke(width=0).move_to([0, 3.3, 0]))
        elif p.stimulus == "brush":
            tool = VGroup(Line([0.6, 3.3, 0], [0.1, 1.9, 0]).set_stroke("#B98A6A", 9),
                          *[Line([0.1, 1.9, 0], [0.1 + dx, 1.3, 0]).set_stroke(pal["warm"], 2) for dx in np.linspace(-0.3, 0.3, 7)])
        else:
            tool = VGroup(RoundedRectangle(width=1.0, height=2.3, corner_radius=0.48).set_fill(pal["warm"], 0.95).set_stroke(pal["ink"], 2).move_to([0, 2.55, 0]),
                          RoundedRectangle(width=0.62, height=0.4, corner_radius=0.15).set_fill(pal["peach"], 0.6).set_stroke(width=0).move_to([0, 3.35, 0]))
        block = VGroup(skin, surface, layer_labels, tool)
        place["c0"], w0 = block.get_center(), block.width

        # ---- spike trains panel
        tr_w = 6.5
        def train(color, label):
            axis = Line([0, 0, 0], [tr_w, 0, 0]).set_stroke(pal["faint"], 2)
            lab = sci.text(label, 0.42 * ts, color, bold=True).next_to(axis, DOWN, buff=0.12).align_to(axis, LEFT)
            return VGroup(axis, lab)
        sa_t, ra_t = train(sa_c, "Merkel · slow adapting: fires all through the press"), train(ra_c, "Meissner · fast adapting: on and off only")
        press_bar = VGroup(Line([0, 0, 0], [tr_w, 0, 0]).set_stroke(pal["faint"], 2), sci.text("pressure", 0.38 * ts, pal["muted"]).move_to([-0.7, 0, 0]))
        trains = VGroup(press_bar, sa_t, ra_t).arrange(DOWN, buff=0.75, aligned_edge=LEFT)

        area_h = top - bottom
        if st.v:
            block.scale_to_fit_width(st.sw * 0.98)
            if block.height > area_h * 0.58:
                block.scale_to_fit_height(area_h * 0.58)
            block.move_to([st.cx, top - block.height / 2, 0])
            trains.scale_to_fit_width(st.sw * 0.92)
            trains.move_to([st.cx, bottom + trains.height / 2 + 0.05, 0])
        else:
            block.scale(min(st.sw * 0.5 / block.width, area_h * 0.92 / block.height)).move_to([st.left + st.sw * 0.27, (top + bottom) / 2, 0])
            trains.scale(min(st.sw * 0.43 / trains.width, area_h * 0.7 / trains.height)).move_to([st.right - st.sw * 0.22, (top + bottom) / 2, 0])
        k = block.height / 4.9
        place.update(s=block.width / w0, c1=block.get_center())
        surface.add_updater(lambda m: m.set_points_smoothly(
            [(q - place["c0"]) * place["s"] + place["c1"] for q in surface_pts(dent.get_value())]))
        axis_x0 = trains[0][0].get_start()[0]
        axis_x1 = trains[0][0].get_end()[0]
        tw = axis_x1 - axis_x0
        ys = [trains[0][0].get_y(), sa_t[0].get_y(), ra_t[0].get_y()]
        spike_h = (ys[0] - ys[1]) * 0.5

        scene.add(skin, surface, layer_labels, tool, trains)
        scene.play(FadeIn(title), FadeIn(cap), run_time=0.3)

        # time line of the press, drawn while it happens
        total = max(2.0, clock.left - 0.6)
        on, off = 0.18, 0.18 + p.press_share
        now = ValueTracker(0.0)
        cursor = Line([axis_x0, ys[0] + spike_h, 0], [axis_x0, ys[2] - 0.15, 0]).set_stroke(pal["muted"], 1.5, 0.6)
        cursor.add_updater(lambda m: m.set_x(axis_x0 + tw * now.get_value()))
        press_line = VMobject().set_stroke(hi, 4)
        def press_shape(m):
            f = now.get_value()
            xs = np.linspace(0, f, max(2, int(f * 120)))
            yv = [ys[0] + (spike_h * 0.8 if on <= x <= off else 0) for x in xs]
            m.set_points_as_corners([np.array([axis_x0 + tw * x, y, 0]) for x, y in zip(xs, yv)])
        press_line.add_updater(press_shape)
        rng = np.random.default_rng(3)
        sa_times = sorted([on + 0.01 + x for x in np.cumsum(rng.uniform(0.025, 0.05, 40)) if on + x < off] + [on + 0.005])
        ra_times = [on + 0.005, on + 0.03, on + 0.055, off + 0.005, off + 0.03]
        spikes = VGroup()
        fired = set()
        def spike_updater(m):
            f = now.get_value()
            for kind, times, y, col in (("sa", sa_times, ys[1], sa_c), ("ra", ra_times, ys[2], ra_c)):
                for t in times:
                    if t <= f and (kind, t) not in fired:
                        fired.add((kind, t))
                        m.add(Line([axis_x0 + tw * t, y, 0], [axis_x0 + tw * t, y + spike_h, 0]).set_stroke(col, 3))
        spikes.add_updater(spike_updater)
        scene.add(cursor, press_line, spikes)

        sig_sa = sci.glow_dot(sa_c, 0.05 * k + 0.02).move_to(sa_n.get_start())
        sig_ra = sci.glow_dot(ra_c, 0.05 * k + 0.02).move_to(ra_n.get_start())
        def seg(a, b):
            return now.animate(rate_func=linear).set_value(b), (b - a) * total
        a1, t1 = seg(0, on)
        scene.play(a1, tool.animate.shift(DOWN * 0.35 * k), run_time=t1)
        a2, t2 = seg(on, on + 0.08)
        scene.play(a2, dent.animate.set_value(1.0), tool.animate.shift(DOWN * 0.25 * k),
                   merkel.animate.set_fill(hi), meiss.animate.set_stroke(hi), run_time=t2)
        scene.add(sig_sa, sig_ra)
        a3, t3 = seg(on + 0.08, off)
        scene.play(a3, MoveAlongPath(sig_sa, sa_n, rate_func=linear), MoveAlongPath(sig_ra, ra_n, rate_func=linear),
                   meiss.animate.set_stroke(ra_c), run_time=t3)
        a4, t4 = seg(off, min(1.0, off + 0.08))
        scene.play(a4, dent.animate.set_value(0.0), tool.animate.shift(UP * 0.6 * k), meiss.animate(rate_func=rate_functions.there_and_back).set_stroke(hi),
                   merkel.animate.set_fill(sa_c), sig_sa.animate.set_opacity(0), sig_ra.animate.set_opacity(0), run_time=t4)
        a5, t5 = seg(min(1.0, off + 0.08), 1.0)
        if t5 > 0.05:
            scene.play(a5, run_time=t5)
        for m in (cursor, press_line, spikes, surface):
            m.clear_updaters()
        sci.finish(scene, clock, "still" if p.camera == "gentle" else p.camera)
