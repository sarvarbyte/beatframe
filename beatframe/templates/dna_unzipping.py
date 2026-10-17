"""DNA unzipping and copying: a double helix with A-T and G-C base pairs; an enzyme unzips it, and new
matching bases pair with each exposed strand, giving two copies that are each half old, half new.

Accuracy notes (stylised 2D diagram of a 3D helix): base pairing A-T and G-C; the enzyme helicase
separates the strands; DNA polymerase builds each new strand by pairing (semi-conservative
replication, Meselson & Stahl 1958). Leading/lagging strand details and other proteins are left out.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
from manim import (
    DOWN, LEFT, ORIGIN, RIGHT, UP, FadeIn, Line, RoundedRectangle, Text, ValueTracker, VGroup, VMobject, linear,
    rate_functions,
)
from pydantic import Field

from beatframe.templates import sci
from beatframe.templates.sci import SciParams, Stage

PAIR = {"A": "T", "T": "A", "G": "C", "C": "G"}


class DnaUnzipping(sci.Template):
    name = "dna_unzipping"
    description = "DNA double helix unzips; new bases pair with each strand (A-T, G-C) to make two copies"
    category = "Biology"
    theme = "bright"
    vertical_width = 8.0

    class Params(SciParams):
        pairs: int = Field(12, ge=8, le=18)
        sequence: str = "ATGCGTACCATG"          # top strand, A/T/G/C; repeated or cut to `pairs`
        mode: Literal["replicate", "unzip"] = "replicate"
        letters: bool = True
        caption: str = "Each strand is a template: A pairs with T, G pairs with C"

    def build(self, scene, p, duration):
        st, pal = Stage(), sci.pal_of(p)
        hi = sci.hi_of(p, pal)
        clock = sci.Clock(scene, duration, p.speed)
        sci.guard(scene, duration)
        sci.background(scene, pal, st, seed=79)
        ts = p.text_size
        title = sci.headline(p.title, st, pal, ts)
        top, bottom = st.content(bool(p.title))
        cap = sci.wrapped(p.caption, 0.4 * ts, pal["muted"], 30 if st.v else 66, st.sw * 0.92) if p.caption else VGroup()
        bottom += st.place_caption(cap)
        col = {"A": pal["mint"], "T": pal["peach"], "G": pal["sky"], "C": pal["lavender"]}
        seq = "".join(c for c in p.sequence.upper() if c in PAIR) or "ATGC"
        seq = (seq * (p.pairs // len(seq) + 1))[: p.pairs]

        # local frame: helix along x from -L/2..L/2 (rotated to vertical for 9:16)
        L = 11.0
        A = 1.0
        n = p.pairs
        xs = np.linspace(-L / 2 + 0.4, L / 2 - 0.4, n)
        kx = 2 * np.pi / 4.2
        fork = ValueTracker(-L / 2 - 0.6)       # left of this x the strands are apart
        rot = np.pi / 2 if st.v else 0.0
        area = top - bottom
        scale = min((st.sw * 0.95 if not st.v else area * 0.95) / L, (area * 0.9 if not st.v else st.sw * 0.95) / 5.2)
        center = np.array([st.cx, (top + bottom) / 2, 0])
        Rm = np.array([[np.cos(rot), -np.sin(rot), 0], [np.sin(rot), np.cos(rot), 0], [0, 0, 1]])

        def to_scene(x, y):
            return center + Rm @ np.array([x, y, 0]) * scale

        def sep_at(x):
            d = fork.get_value() - x
            return 0 if d <= 0 else min(1.0, d / 1.4)

        def strand_y(x, top_side: bool):
            s = sep_at(x)
            helix = A * np.sin(kx * x) * (1 if top_side else -1)
            apart = 1.55 * (1 if top_side else -1)
            return helix * (1 - s) + apart * s

        back_top, back_bot = VMobject().set_stroke(pal["purple"], 6), VMobject().set_stroke(pal["purple"], 6)
        rungs = VGroup(*[VGroup(Line(), Line()) for _ in range(n)])
        letters = VGroup(*[VGroup(Text(b, font=sci.brand.SANS, weight="BOLD", color=pal["bottom"] if pal["dark"] else pal["warm"]).scale(0.34 * scale),
                                  Text(PAIR[b], font=sci.brand.SANS, weight="BOLD", color=pal["bottom"] if pal["dark"] else pal["warm"]).scale(0.34 * scale))
                           for b in seq]) if p.letters else VGroup()

        def draw(_m=None):
            fine = np.linspace(-L / 2, L / 2, 140)
            back_top.set_points_smoothly([to_scene(x, strand_y(x, True)) for x in fine])
            back_bot.set_points_smoothly([to_scene(x, strand_y(x, False)) for x in fine])
            for i, x in enumerate(xs):
                yt, yb = strand_y(x, True), strand_y(x, False)
                s = sep_at(x)
                depth = 0.45 + 0.55 * abs(np.cos(kx * x)) if s < 1 else 1.0
                half = 0.55 if s >= 1 else abs(yt - yb) / 2 * (1 - s) + 0.55 * s
                mid_t = yt - np.sign(yt - yb or 1) * half
                mid_b = yb + np.sign(yt - yb or 1) * half
                top_l, bot_l = rungs[i]
                b = seq[i]
                top_l.put_start_and_end_on(to_scene(x, yt), to_scene(x, mid_t + 1e-3)).set_stroke(col[b], 9 * scale / 0.9, depth)
                bot_l.put_start_and_end_on(to_scene(x, yb), to_scene(x, mid_b - 1e-3)).set_stroke(col[PAIR[b]], 9 * scale / 0.9, depth)
                if p.letters:
                    lt, lb = letters[i]
                    lt.move_to(to_scene(x, (yt + mid_t) / 2)).set_opacity(depth if abs(yt - mid_t) > 0.25 else 0)
                    lb.move_to(to_scene(x, (yb + mid_b) / 2)).set_opacity(depth if abs(yb - mid_b) > 0.25 else 0)
        draw()
        helicase = RoundedRectangle(width=0.9 * scale, height=1.3 * scale, corner_radius=0.4 * scale).set_fill(hi, 0.85).set_stroke(pal["ink"], 2)
        helicase.move_to(to_scene(fork.get_value(), 0))
        hel_tag = sci.tag("helicase unzips", hi, pal, 0.27 * ts)

        updater_group = VGroup(back_top, back_bot, rungs, letters)
        updater_group.add_updater(lambda m: draw())
        helicase.add_updater(lambda m: m.move_to(to_scene(fork.get_value() + 0.35, 0)))
        hel_tag.add_updater(lambda m: m.next_to(helicase, UP if not st.v else RIGHT, buff=0.12))
        legend = VGroup(*[VGroup(VGroup(Line(LEFT * 0.2, ORIGIN).set_stroke(col[a], 8), Line(ORIGIN, RIGHT * 0.2).set_stroke(col[PAIR[a]], 8)), sci.text(f"{a}–{PAIR[a]}", 0.3 * ts, pal["ink"], bold=True)).arrange(RIGHT, buff=0.1)
                          for a in ("A", "G")]).arrange(RIGHT, buff=0.4)
        legend.move_to([st.right - legend.width / 2, top - legend.height / 2, 0]) if not st.v else legend.move_to([st.cx, top - legend.height / 2, 0])

        scene.add(updater_group, helicase, hel_tag)
        scene.play(FadeIn(title), FadeIn(cap), FadeIn(legend), run_time=0.3)
        unzip_t = clock.left * (0.5 if p.mode == "replicate" else 0.85)
        scene.play(fork.animate(rate_func=rate_functions.ease_in_out_sine).set_value(L / 2 + 1.8), run_time=unzip_t)
        updater_group.clear_updaters()
        helicase.clear_updaters()
        hel_tag.clear_updaters()
        scene.play(helicase.animate.set_opacity(0), hel_tag.animate.set_opacity(0), run_time=0.3)

        if p.mode == "replicate" and clock.left > 1.2:
            # new bases (lighter outline) fly in and pair with each exposed strand
            new = VGroup()
            moves = []
            for i, x in enumerate(xs):
                b = seq[i]
                for side, base in ((True, PAIR[b]), (False, b)):
                    y_strand = 1.55 if side else -1.55
                    y_end = y_strand - 1.1 if side else y_strand + 1.1
                    end_mid = (y_strand - 0.55) if side else (y_strand + 0.55)
                    piece = Line(to_scene(x, end_mid), to_scene(x, end_mid - 0.5 if side else end_mid + 0.5)).set_stroke(col[base], 9 * scale / 0.9)
                    start = piece.copy().shift(Rm @ np.array([np.random.uniform(-0.8, 0.8), -2.0 if side else 2.0, 0]) * scale).set_opacity(0)
                    new.add(piece)
                    moves.append((start, piece))
            new_back = VGroup(sci.smooth([to_scene(x, 1.55 - 1.1) for x in np.linspace(-L / 2, L / 2, 6)], pal["warm"], 5, 0.9),
                              sci.smooth([to_scene(x, -1.55 + 1.1) for x in np.linspace(-L / 2, L / 2, 6)], pal["warm"], 5, 0.9))
            starts = VGroup(*[s_ for s_, _ in moves])
            scene.add(starts)
            t = min(1.6, clock.left * 0.5)
            from manim import Transform, LaggedStart
            scene.play(LaggedStart(*[Transform(s_, e) for s_, e in moves], lag_ratio=0.03), run_time=t)
            two = VGroup(sci.tag("copy 1: old + new", pal["purple"], pal, 0.27 * ts), sci.tag("copy 2: old + new", pal["purple"], pal, 0.27 * ts))
            two[0].next_to(back_top, UP if not st.v else LEFT, buff=0.12)
            two[1].next_to(back_bot, DOWN if not st.v else RIGHT, buff=0.12)
            if st.v:
                for g in two:
                    g.rotate(0)
            scene.play(FadeIn(new_back), FadeIn(two), run_time=min(0.5, clock.left * 0.5))
        sci.finish(scene, clock, "still" if p.camera == "gentle" else p.camera)
