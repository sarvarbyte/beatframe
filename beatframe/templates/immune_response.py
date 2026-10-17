"""A simplified immune response: bacteria get in, a macrophage engulfs one and shows a piece of it
(an antigen) to a helper T cell, which activates a B cell; the B cell releases antibodies that latch
onto the remaining bacteria and mark them for destruction.

Accuracy notes (conceptual diagram, not to scale): innate response (phagocytosis by macrophages)
and adaptive response (antigen presentation, helper T cells, B cells and antibodies). In reality
antigen presentation mostly happens in lymph nodes and antibody production takes days; the scene
compresses time and space, and says so in its caption.
"""

from __future__ import annotations

import numpy as np
from manim import (
    DOWN, LEFT, RIGHT, UP, Circle, FadeIn, FadeOut, Line, Polygon, RoundedRectangle, VGroup, rate_functions,
)
from pydantic import Field

from beatframe.templates import sci
from beatframe.templates.sci import SciParams, Stage


def blob(r: float, seed: int, bumps: int = 7, amp: float = 0.12):
    rng = np.random.default_rng(seed)
    ph = rng.uniform(0, 2 * np.pi, 3)
    a = np.linspace(0, 2 * np.pi, 48, endpoint=False)
    rr = r * (1 + amp * np.sin(bumps * a + ph[0]) + amp * 0.6 * np.sin((bumps - 3) * a + ph[1]))
    pts = [np.array([np.cos(t) * q, np.sin(t) * q, 0]) for t, q in zip(a, rr)] + [np.array([rr[0], 0, 0])]
    return sci.VMobject().set_points_smoothly(pts)


def bacterium(pal, s=1.0):
    body = RoundedRectangle(width=0.9 * s, height=0.42 * s, corner_radius=0.21 * s).set_fill(pal["mint"], 0.9).set_stroke(pal["ink"], 1.5)
    pili = VGroup(*[Line(body.get_center() + np.array([x, 0.2 * s * sgn, 0]), body.get_center() + np.array([x * 1.2, 0.36 * s * sgn, 0]))
                    for x in (-0.3 * s, 0, 0.3 * s) for sgn in (-1, 1)]).set_stroke(pal["mint"], 2)
    return VGroup(pili, body)


def antibody(color, s=0.35):
    return VGroup(Line(DOWN * s, ORIGIN), Line(ORIGIN, np.array([-0.6, 0.7, 0]) * s), Line(ORIGIN, np.array([0.6, 0.7, 0]) * s)).set_stroke(color, 4)


ORIGIN = np.zeros(3)


class ImmuneResponse(sci.Template):
    name = "immune_response"
    description = "Bacteria invade; a macrophage engulfs one, a T cell recognises it, a B cell's antibodies tag the rest"
    category = "Biology"
    theme = "bright"
    vertical_width = 8.0

    class Params(SciParams):
        bacteria: int = Field(4, ge=2, le=7)
        antibodies: int = Field(10, ge=4, le=20)
        caption: str = "Simplified and sped up: the real response takes days"

    def build(self, scene, p, duration):
        st, pal = Stage(), sci.pal_of(p)
        hi = sci.hi_of(p, pal)
        clock = sci.Clock(scene, duration, p.speed)
        sci.guard(scene, duration)
        sci.background(scene, pal, st, seed=83)
        ts = p.text_size
        title = sci.headline(p.title, st, pal, ts)
        top, bottom = st.content(bool(p.title))
        cap = sci.wrapped(p.caption, 0.38 * ts, pal["muted"], 30 if st.v else 66, st.sw * 0.92) if p.caption else VGroup()
        bottom += st.place_caption(cap)
        area = top - bottom
        u = min(st.sw / 12.0, area / 7.0) if not st.v else min(st.sw / 7.0, area / 10.0)

        def at(x, y):              # layout units around the content centre
            return np.array([st.cx + x * u, (top + bottom) / 2 + y * u, 0])
        if st.v:                   # 9:16: cells on top, bacteria below
            P = dict(macro=(1.3, 1.0), meet=(1.0, 2.7), tcell=(-2.3, 3.5), bcell=(-2.1, 0.4), bx=(-2.4, 2.4), by=(-4.3, -1.2))
        else:
            P = dict(macro=(-1.0, 1.4), meet=(-2.5, 1.5), tcell=(-4.6, 1.9), bcell=(-3.8, -1.8), bx=(1.5, 5.0), by=(-2.6, 2.6))

        rng = np.random.default_rng(7)
        bugs = VGroup(*[bacterium(pal, u * 1.05).rotate(rng.uniform(0, np.pi)).move_to(at(rng.uniform(*P['bx']), rng.uniform(*P['by'])))
                        for _ in range(p.bacteria)])
        macro = VGroup(blob(1.05 * u, 3).set_fill(pal["lavender"], 0.55).set_stroke(pal["lavender"], 3),
                       Circle(radius=0.32 * u).set_fill(pal["purple"], 0.8).set_stroke(width=0))
        macro.move_to(at(*P['macro']))
        tcell = VGroup(Circle(radius=0.55 * u).set_fill(pal["sky"], 0.6).set_stroke(pal["sky"], 3),
                       *[Line(np.array([np.cos(a), np.sin(a), 0]) * 0.55 * u, np.array([np.cos(a), np.sin(a), 0]) * 0.72 * u).set_stroke(pal["sky"], 3)
                         for a in np.linspace(0, 2 * np.pi, 10, endpoint=False)]).move_to(at(*P['tcell']))
        bcell = VGroup(Circle(radius=0.6 * u).set_fill(pal["peach"], 0.55).set_stroke(pal["peach"], 3),
                       *[antibody(pal["peach"], 0.18 * u).rotate(a - np.pi / 2).move_to(np.array([np.cos(a), np.sin(a), 0]) * 0.72 * u)
                         for a in np.linspace(0, 2 * np.pi, 8, endpoint=False)]).move_to(at(*P['bcell']))
        names = VGroup()
        if p.labels:
            sz = 0.26 * ts
            names.add(sci.tag("bacteria", pal["mint"], pal, sz).next_to(bugs, UP if not st.v else RIGHT, buff=0.1),
                      sci.tag("macrophage", pal["lavender"], pal, sz).next_to(macro, UP, buff=0.08),
                      sci.tag("helper T cell", pal["sky"], pal, sz).next_to(tcell, UP if not st.v else LEFT, buff=0.08),
                      sci.tag("B cell", pal["peach"], pal, sz).next_to(bcell, DOWN, buff=0.08))
            def keep(n):
                if n.get_right()[0] > st.right:
                    n.shift(LEFT * (n.get_right()[0] - st.right))
                if n.get_left()[0] < st.left:
                    n.shift(RIGHT * (st.left - n.get_left()[0]))
            for n in names:
                keep(n)
            names[1].add_updater(lambda n: keep(n.next_to(macro, UP, buff=0.08)))       # labels travel with their cells
            names[2].add_updater(lambda n: keep(n.next_to(tcell, UP, buff=0.08)))
        step_y = top - 0.3
        def step(text, color):
            t = sci.tag(text, color, pal, 0.3 * ts)
            if st.v:
                return t.move_to([st.cx, bottom + 0.25, 0])
            return t.move_to([st.right - t.width / 2, bottom + 0.25, 0])     # clear of the B cell on the left

        scene.add(bugs, macro, tcell, bcell)
        scene.play(FadeIn(title), FadeIn(cap), FadeIn(names), run_time=0.3)
        # drifting bacteria
        avail = clock.left
        s1 = step("1 · a macrophage engulfs a bacterium", pal["lavender"])
        target = bugs[0]
        scene.play(FadeIn(s1), macro.animate(rate_func=rate_functions.ease_in_out_sine).move_to(target.get_center() + LEFT * 0.35 * u),
                   *[b.animate.shift(np.array([rng.uniform(-0.2, 0.2), rng.uniform(-0.2, 0.2), 0]) * u) for b in bugs[1:]], run_time=avail * 0.2)
        scene.play(target.animate.move_to(macro[0].get_center()).scale(0.6).set_opacity(0.5),
                   macro[0].animate(rate_func=rate_functions.there_and_back).scale(1.12), run_time=avail * 0.1)
        scene.play(FadeOut(target), run_time=0.2)
        # 2: antigen shown to the helper T cell
        antigen = Polygon([0, 0.16 * u, 0], [-0.14 * u, -0.1 * u, 0], [0.14 * u, -0.1 * u, 0]).set_fill(pal["mint"], 1).set_stroke(width=0)
        s2 = step("2 · it shows a piece to a helper T cell", pal["sky"])
        shift = at(*P['meet']) - macro.get_center()
        scene.play(FadeOut(s1), FadeIn(s2), macro.animate.shift(shift),
                   run_time=avail * 0.12)
        antigen.move_to(macro[0].get_left() + LEFT * 0.05 * u)
        scene.play(FadeIn(antigen, scale=0.5), tcell.animate.move_to(macro[0].get_left() + LEFT * 0.75 * u),
                   run_time=avail * 0.1)
        glow = Circle(radius=0.8 * u).move_to(tcell).set_stroke(hi, 5)
        scene.play(glow.animate(rate_func=rate_functions.ease_out_cubic).scale(1.6).set_stroke(opacity=0), tcell[0].animate.set_fill(hi, 0.6), run_time=0.45)
        # 3: T cell signals the B cell, antibodies tag the rest
        link = Line(tcell.get_center(), bcell.get_center()).set_stroke(hi, 3)
        s3 = step("3 · a B cell releases antibodies that tag the rest", pal["peach"])
        from manim import ShowPassingFlash
        scene.play(FadeOut(s2), FadeIn(s3), ShowPassingFlash(link, time_width=0.6), bcell[0].animate.set_fill(pal["peach"], 0.9), run_time=0.5)
        abs_ = VGroup()
        moves = []
        rest = list(bugs[1:])
        for j in range(p.antibodies):
            bug = rest[j % len(rest)] if rest else None
            ab = antibody(pal["peach"], 0.2 * u).move_to(bcell.get_center())
            abs_.add(ab)
            if bug is None:
                continue
            ang = (j // max(len(rest), 1)) * 1.3 + 0.4
            tgt = bug.get_center() + np.array([np.cos(ang), np.sin(ang), 0]) * 0.5 * u
            moves.append(ab.animate(rate_func=rate_functions.ease_out_sine).move_to(tgt).rotate(ang - np.pi / 2))
        scene.add(abs_)
        t = max(0.6, min(1.8, clock.left - 0.8))
        from manim import LaggedStart
        scene.play(LaggedStart(*moves, lag_ratio=0.08), run_time=t)
        if clock.left > 0.5:
            marks = VGroup(*[Circle(radius=0.62 * u).move_to(b).set_stroke(pal["peach"], 2.5, 0.8) for b in rest])
            scene.play(FadeIn(marks), *[b.animate.set_opacity(0.55) for b in rest], run_time=min(0.5, clock.left - 0.1))
        sci.finish(scene, clock, p.camera)
