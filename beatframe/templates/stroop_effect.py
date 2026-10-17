"""The Stroop test, playable: name the INK colour, not the word. Round 1 matches word and ink, round 2
makes them clash; a moving marker sets the pace. Then why it is harder.

Accuracy notes: Stroop (1935). Reading is highly practised and automatic, so the written word
interferes with naming the ink colour; people are typically slower and make more errors on
incongruent items. Timing differs between people; the scene states no numbers.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
from manim import DOWN, LEFT, RIGHT, UP, FadeIn, FadeOut, Line, RoundedRectangle, VGroup, rate_functions
from pydantic import Field

from beatframe.templates import sci
from beatframe.templates.sci import SciParams, Stage

INKS_DARK = {"RED": "#FF6B6B", "BLUE": "#5AA9FF", "GREEN": "#4CD38A", "YELLOW": "#FFD45C", "PURPLE": "#B98CFF"}
INKS_LIGHT = {"RED": "#D7263D", "BLUE": "#1F6FD1", "GREEN": "#138A4A", "YELLOW": "#C99700", "PURPLE": "#7B3FD6"}


class StroopEffect(sci.Template):
    name = "stroop_effect"
    description = "Playable Stroop test: name the ink colour; matching round, then a clashing round, then why"
    category = "Experiments"
    theme = "bright"
    vertical_width = 8.0

    class Params(SciParams):
        words: int = Field(6, ge=4, le=9)
        rounds: Literal["both", "clash_only"] = "both"
        instruction: str = "Say the COLOUR of the ink out loud, not the word"
        explain: bool = True
        explain_text: str = "Reading is automatic: the word jumps in before the colour, and the two answers clash"
        title: str = "The Stroop test"

    def build(self, scene, p, duration):
        st, pal = Stage(), sci.pal_of(p)
        hi = sci.hi_of(p, pal)
        clock = sci.Clock(scene, duration, 1.0)
        sci.guard(scene, duration)
        sci.background(scene, pal, st, seed=61)
        ts = p.text_size
        inks = INKS_DARK if pal["dark"] else INKS_LIGHT
        names = list(inks)
        rng = np.random.default_rng(p.words * 3 + 1)
        title = sci.headline(p.title, st, pal, ts)
        top, bottom = st.content(bool(p.title))

        instr = sci.wrapped(p.instruction, (0.5 if st.v else 0.48) * ts, pal["ink"], 22 if st.v else 46, st.sw * 0.95, bold=True)
        instr.move_to([st.cx, top - instr.height / 2 - 0.05, 0])
        ex_word = sci.text("RED", 1.1 * ts, inks["BLUE"], bold=True)
        ex_ans = sci.tag("say: “blue”", inks["BLUE"], pal, 0.36 * ts)
        example = VGroup(ex_word, ex_ans).arrange(DOWN if st.v else RIGHT, buff=0.4).move_to([st.cx, (instr.get_bottom()[1] + bottom) / 2, 0])

        def card(congruent: bool):
            g = VGroup()
            for j in range(p.words):
                w = names[rng.integers(len(names))]
                ink = w if congruent else names[(names.index(w) + 1 + rng.integers(len(names) - 1)) % len(names)]
                g.add(sci.text(w, 0.9 * ts, inks[ink], bold=True))
            cols = 2 if st.v else 3
            g.arrange_in_grid(cols=cols, buff=(0.7, 0.55) if not st.v else (0.6, 0.6))
            area_top = instr.get_bottom()[1] - 0.6
            g.scale(min(1.0, st.sw * 0.9 / g.width, (area_top - bottom - 0.3) / g.height))
            g.move_to([st.cx, (area_top + bottom) / 2, 0])
            return g

        rounds = [("Round 1 · words and ink match", True), ("Round 2 · they clash", False)]
        if p.rounds == "clash_only":
            rounds = rounds[1:]
        explain = p.explain and duration > 7
        budget = clock.left - 0.6 - (2.2 if explain else 0) - 1.2
        per_round = max(1.2, budget / len(rounds))

        scene.add(instr, example)
        scene.play(FadeIn(title), run_time=0.3)
        scene.wait(min(1.0, max(0.2, budget * 0.08)))
        scene.play(FadeOut(example), run_time=0.25)
        prev = VGroup()
        for label, congruent in rounds:
            words = card(congruent)
            tag = sci.tag(label, pal["mint"] if congruent else hi, pal, 0.32 * ts).next_to(instr, DOWN, buff=0.22)
            scene.play(FadeOut(prev), FadeIn(words, lag_ratio=0.05), FadeIn(tag), run_time=0.35)
            step = max(0.25, (per_round - 0.35) / p.words)
            marker = Line(LEFT, RIGHT).set_stroke(pal["ink"], 5)
            for j, w in enumerate(words):
                marker_target = Line(w.get_corner(DOWN + LEFT) + DOWN * 0.12, w.get_corner(DOWN + RIGHT) + DOWN * 0.12).set_stroke(pal["warm"], 5)
                if j == 0:
                    marker.become(marker_target)
                    scene.play(FadeIn(marker), run_time=min(0.15, step))
                    scene.wait(max(0.01, step - 0.15))
                else:
                    scene.play(marker.animate(rate_func=rate_functions.ease_in_out_sine).become(marker_target), run_time=step)
            prev = VGroup(words, tag, marker)
        if explain and clock.left > 1.0:
            scene.play(FadeOut(prev), FadeOut(instr), run_time=0.3)
            word = sci.text("GREEN", 1.3 * ts, inks["PURPLE"], bold=True)
            read = sci.tag("reading says: green", pal["muted"], pal, 0.32 * ts)
            see = sci.tag("colour says: purple", inks["PURPLE"], pal, 0.32 * ts)
            pair = VGroup(read, see).arrange(DOWN if st.v else RIGHT, buff=0.3)
            body = sci.wrapped(p.explain_text, 0.42 * ts, pal["ink"], 26 if st.v else 52, st.sw * 0.92)
            grp = VGroup(word, pair, body).arrange(DOWN, buff=0.45).move_to([st.cx, (top + bottom) / 2, 0])
            clash = RoundedRectangle(width=pair.width + 0.3, height=pair.height + 0.25, corner_radius=0.2).set_stroke(hi, 2.5).move_to(pair)
            scene.play(FadeIn(word, scale=1.2), run_time=0.3)
            scene.play(FadeIn(read, shift=UP * 0.1), FadeIn(see, shift=UP * 0.1), run_time=0.35)
            scene.play(FadeIn(clash), FadeIn(body), run_time=0.4)
        sci.finish(scene, clock, "still")
