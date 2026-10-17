"""Gas exchange in the lungs: in each air sac (alveolus) oxygen diffuses across a very thin wall into
the red blood cells passing through the capillary, while carbon dioxide diffuses out of the blood
into the air to be breathed out.

Accuracy notes (schematic, not to scale): exchange is passive diffusion down partial-pressure
gradients across the alveolar-capillary barrier (thinner than a cell); oxygen binds haemoglobin in
red blood cells; most CO2 travels dissolved / as bicarbonate in plasma before leaving. Colours are
codes: mint = O2, peach = CO2.
"""

from __future__ import annotations

import numpy as np
from manim import (
    DOWN, LEFT, RIGHT, UP, Circle, Ellipse, FadeIn, RoundedRectangle, UpdateFromAlphaFunc, VGroup, interpolate_color,
    ManimColor, linear,
)
from pydantic import Field

from beatframe.templates import sci
from beatframe.templates.sci import SciParams, Stage


class OxygenExchange(sci.Template):
    name = "oxygen_exchange"
    description = "Alveolus and capillary: oxygen diffuses into red blood cells, carbon dioxide out into the air"
    category = "Biology"
    theme = "bright"
    vertical_width = 8.0

    class Params(SciParams):
        molecules: int = Field(14, ge=6, le=30)       # O2 and CO2 dots on screen at once (each)
        breathing: bool = True
        caption: str = "Oxygen moves into the blood; carbon dioxide moves out"

    def build(self, scene, p, duration):
        st, pal = Stage(), sci.pal_of(p)
        clock = sci.Clock(scene, duration, p.speed)
        sci.guard(scene, duration)
        sci.background(scene, pal, st, seed=73)
        ts = p.text_size
        o2_c, co2_c = pal["mint"], pal["peach"]
        title = sci.headline(p.title, st, pal, ts)
        top, bottom = st.content(bool(p.title))
        cap = sci.wrapped(p.caption, 0.4 * ts, pal["muted"], 30 if st.v else 66, st.sw * 0.92) if p.caption else VGroup()
        bottom += st.place_caption(cap)

        # geometry in a local frame: alveolus centred at (0, 0), capillary along +x side (rotated for 9:16)
        R = 2.2
        alv = Circle(radius=R).set_fill(pal["sky"], 0.1).set_stroke(pal["sky"], 4)
        cap_w, cap_h = 1.5, 6.4
        vessel = RoundedRectangle(width=cap_w, height=cap_h, corner_radius=0.7).set_fill(pal["coral"], 0.12).set_stroke(pal["coral"], 4)
        vessel.move_to([R + cap_w / 2 + 0.08, 0, 0])
        wall = RoundedRectangle(width=0.12, height=2.6, corner_radius=0.05).set_fill(pal["warm"], 0.6).set_stroke(width=0).move_to([R + 0.04, 0, 0])
        rbc_x = vessel.get_x()
        n_rbc = 5
        rbcs = VGroup(*[VGroup(Ellipse(width=0.95, height=0.55).set_fill(pal["coral"], 0.85).set_stroke(width=0),
                               Ellipse(width=0.45, height=0.2).set_fill(pal["bottom"], 0.35).set_stroke(width=0)) for _ in range(n_rbc)])
        txt = VGroup(sci.text("air sac", 0.62, pal["sky"], bold=True).move_to([0, R * 0.62, 0]),
                     sci.text("blood", 0.62, pal["coral"], bold=True).next_to(vessel, RIGHT, buff=0.2))
        local = VGroup(alv, vessel, wall, rbcs, txt)
        rot = -np.pi / 2 if st.v else 0.0          # 9:16: capillary under the air sac
        if rot:
            for m in (alv, vessel, wall):
                m.rotate(rot, about_point=np.zeros(3))
            txt[1].next_to(vessel, DOWN, buff=0.2)
            for r in rbcs:
                r.rotate(rot)
        area = top - bottom
        fitted = VGroup(alv, vessel, wall, txt)
        s = min(st.sw * 0.95 / fitted.width, area * 0.95 / fitted.height)
        center = np.array([st.cx, (top + bottom) / 2, 0])
        origin_shift = center - fitted.get_center() * s
        for m in local:
            m.scale(s, about_point=np.zeros(3)).shift(origin_shift)
        A = alv.get_center()
        axis = (vessel.get_center() - A) / np.linalg.norm(vessel.get_center() - A)   # alveolus -> capillary
        along = np.array([-axis[1], axis[0], 0])                                      # direction of blood flow
        Vc = vessel.get_center()
        L = cap_h * s

        rng = np.random.default_rng(5)
        o2 = VGroup(*[Circle(radius=0.11 * s).set_fill(o2_c, 1).set_stroke(width=0) for _ in range(p.molecules)])
        co2 = VGroup(*[Circle(radius=0.11 * s).set_fill(co2_c, 1).set_stroke(width=0) for _ in range(p.molecules)])
        o2_start = [A + (rng.uniform(0.15, 0.85) * R * s) * np.array([np.cos(a), np.sin(a), 0]) for a in rng.uniform(0, 2 * np.pi, p.molecules)]
        co2_start = [Vc + along * rng.uniform(-0.35, 0.35) * L + axis * rng.uniform(-0.25, 0.25) * cap_w * s for _ in range(p.molecules)]
        offs = rng.uniform(0, 1, p.molecules)
        for d, q in zip(o2, o2_start):
            d.move_to(q)
        for d, q in zip(co2, co2_start):
            d.move_to(q)

        labels = VGroup()
        if p.labels:
            k = 0.3 * ts
            labels.add(sci.callout(wall.get_center() + along * 0.9 * s, "thin wall", -along + axis * 0.3, pal["warm"], pal, k, 0.5 * s))
        key = VGroup(*[VGroup(Circle(radius=0.09).set_fill(c, 1).set_stroke(width=0), sci.text(t, 0.34 * ts, pal["ink"], bold=True)).arrange(RIGHT, buff=0.12)
                       for c, t in ((o2_c, "O₂ in"), (co2_c, "CO₂ out"))]).arrange(RIGHT, buff=0.4)
        key.move_to([st.cx, top - key.height / 2, 0]) if not st.v else key.next_to(alv, UP, buff=0.12)
        if not st.v:
            key.move_to([st.right - key.width / 2, top - key.height / 2, 0])

        scene.add(alv, vessel, wall, rbcs, txt, o2, co2)
        scene.play(FadeIn(title), FadeIn(cap), FadeIn(labels), FadeIn(key), run_time=0.3)
        total = max(1.0, clock.left - 0.05)
        speed = 0.22 * p.speed
        rbc_off = np.linspace(0, 1, n_rbc, endpoint=False)

        def rbc_pos(f):
            return Vc + along * (f - 0.5) * L * 0.9

        def update(group, alpha):
            t = alpha * total
            breathe = 1 + (0.05 * np.sin(t * 2 * np.pi / 3.2) if p.breathing else 0)
            alv.set(width=2 * R * s * breathe)
            alv.move_to(A)
            for j, r in enumerate(rbcs):
                f = (rbc_off[j] + t * speed) % 1.0
                r.move_to(rbc_pos(f))
                r[0].set_fill(interpolate_color(ManimColor(pal["purple"]), ManimColor(pal["coral"]), min(1, max(0, f * 1.6 - 0.3))))
            for j, d in enumerate(o2):
                ph = (offs[j] + t * speed * 1.3) % 1.0
                rbc_j = j % n_rbc
                target = rbcs[rbc_j].get_center()
                start = o2_start[j]
                a = min(1, ph * 1.25)
                pos = start + (target - start) * (a ** 1.4)
                d.move_to(pos)
                d.set_opacity(1 if ph < 0.85 else max(0, (1 - ph) / 0.15))
            for j, d in enumerate(co2):
                ph = (offs[::-1][j] + t * speed * 1.1) % 1.0
                start = co2_start[j] + along * ph * L * 0.3
                end = A + (co2_start[j] - Vc) * 0.4 - axis * R * s * 0.45
                pos = start + (end - start) * min(1, ph * 1.2) ** 1.2
                d.move_to(pos)
                d.set_opacity(1 if ph < 0.85 else max(0, (1 - ph) / 0.15))
        scene.play(UpdateFromAlphaFunc(VGroup(rbcs, o2, co2, alv), update, rate_func=linear), run_time=total)
        if clock.left > 0.02:
            scene.wait(clock.left)
