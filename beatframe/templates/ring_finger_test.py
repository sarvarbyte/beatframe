"""The ring-finger trick: hand flat on the table, middle finger folded under, now lift each finger.
Thumb, index and little finger rise - the ring finger (for most people) can't. Then why: on the back
of the hand, bands of tissue (juncturae tendinum) tie the ring finger's extensor tendon to its
neighbours, and the ring and middle fingers share muscle from one extensor.

Accuracy notes (conceptual diagram): this is an anatomical constraint of shared extensor tendons and
their cross-connections, not muscle weakness; how much the ring finger can still lift varies between
people. Tendon layout is simplified.
"""

from __future__ import annotations

import numpy as np
from manim import (
    DOWN, LEFT, RIGHT, UP, Circle, Create, FadeIn, FadeOut, Line, RoundedRectangle, VGroup, rate_functions,
)

from beatframe.templates import sci
from beatframe.templates.sci import SciParams, Stage

FINGERS = [("thumb", -2.05, 1.05, 0.62), ("index", -0.95, 1.7, 0.56), ("middle", 0.0, 1.85, 0.56),
           ("ring", 0.95, 1.7, 0.54), ("little", 1.85, 1.35, 0.48)]


class RingFingerTest(sci.Template):
    name = "ring_finger_test"
    description = "Middle finger folded: thumb, index and little finger lift, the ring finger can't - then the tendons why"
    category = "Experiments"
    theme = "bright"
    vertical_width = 8.0

    class Params(SciParams):
        try_it: str = "Fold your middle finger under, then try to lift your ring finger"
        explain: bool = True
        explain_text: str = "Its tendon is tied to its neighbours, so it can't straighten on its own"
        title: str = "Try to lift your ring finger"

    def build(self, scene, p, duration):
        st, pal = Stage(), sci.pal_of(p)
        hi = sci.hi_of(p, pal)
        clock = sci.Clock(scene, duration, p.speed)
        sci.guard(scene, duration)
        sci.background(scene, pal, st, seed=67)
        ts = p.text_size
        title = sci.headline(p.title, st, pal, ts)
        top, bottom = st.content(bool(p.title))
        instr = sci.wrapped(p.try_it, 0.42 * ts, pal["ink"], 26 if st.v else 56, st.sw * 0.95)
        instr.move_to([st.cx, top - instr.height / 2 - 0.05, 0])

        # ---- the hand from the front: knuckles on top, fingertips on the table line
        skin, edge = pal["peach"], pal["ink"] if not pal["dark"] else "#3B355F"
        table = Line([-3.4, 0, 0], [3.4, 0, 0]).set_stroke(pal["muted"], 4)
        back = RoundedRectangle(width=4.9, height=1.1, corner_radius=0.45).set_fill(skin, 1).set_stroke(edge, 2.5).move_to([0.0, 2.35, 0])
        fingers = {}
        for name, x, h, w in FINGERS:
            if name == "middle":       # folded under: only the bent knuckle reaches the table
                f = VGroup(RoundedRectangle(width=w, height=h * 0.62, corner_radius=w / 2).set_fill(skin, 1).set_stroke(edge, 2.5).move_to([x, 2.0 - h * 0.31, 0]),
                           Circle(radius=w * 0.5).set_fill(skin, 0.95).set_stroke(edge, 2.5).move_to([x, 2.0 - h * 0.62 + 0.05, 0]))
                f.shift(DOWN * (f.get_bottom()[1] - 0.0))
            else:
                base_y = 2.0 if name != "thumb" else 1.55
                f = RoundedRectangle(width=w, height=base_y, corner_radius=w / 2).set_fill(skin, 1).set_stroke(edge, 2.5)
                f.move_to([x, base_y / 2, 0])
                if name == "thumb":
                    f.rotate(0.35, about_point=[x, base_y, 0]).shift(DOWN * 0.0)
                    f.shift(DOWN * (f.get_bottom()[1]))
                nail = RoundedRectangle(width=w * 0.6, height=w * 0.5, corner_radius=w * 0.2).set_fill(pal["warm"], 0.55).set_stroke(width=0).move_to(f.get_bottom() + UP * w * 0.38)
                f = VGroup(f, nail)
            fingers[name] = f
        hand = VGroup(table, *[fingers[n] for n, *_ in FINGERS], back)
        names = VGroup(*[sci.text(n, 0.3, pal["muted"]).next_to(fingers[n], DOWN, buff=0.18) for n, *_ in FINGERS])
        fig = VGroup(hand, names)

        area_top = instr.get_bottom()[1] - 0.3
        cap_space = 1.2 if not st.v else 0.0
        fig.scale(min(st.sw * 0.9 / fig.width, (area_top - bottom - cap_space) * 0.85 / fig.height))
        fig.move_to([st.cx, (area_top + bottom + cap_space) / 2, 0])
        k = fig.width / 6.8

        scene.add(fig)
        scene.play(FadeIn(title), FadeIn(instr), run_time=0.3)

        explain = p.explain and duration > 6.5
        budget = clock.left - 0.4 - (2.4 if explain else 0)
        step = max(0.45, budget / 4.6)
        marks = VGroup()
        for n in ("thumb", "index", "little"):
            f = fingers[n]
            up = UP * 0.55 * k
            mark = sci.text("✓", 0.55 * ts, pal["mint"], bold=True).next_to(f, UP, buff=0.12).shift(up)
            if n != "thumb":
                mark.move_to([f.get_x(), back.get_top()[1] + 0.35 * k, 0])
            scene.play(f.animate(rate_func=rate_functions.ease_out_back).shift(up), run_time=step * 0.45)
            scene.play(FadeIn(mark, scale=1.4), run_time=0.2)
            scene.play(f.animate(rate_func=rate_functions.ease_in_out_sine).shift(-up), run_time=max(0.2, step * 0.45 - 0.2))
            marks.add(mark)
        ring = fingers["ring"]
        for _ in range(2):
            scene.play(ring.animate(rate_func=rate_functions.wiggle).shift(UP * 0.05 * k), run_time=step * 0.45)
        cross = sci.text("✕", 0.6 * ts, hi, bold=True).move_to([ring.get_x(), back.get_top()[1] + 0.35 * k, 0])
        stuck = sci.tag("stuck", hi, pal, 0.3 * ts).next_to(cross, RIGHT, buff=0.12)
        scene.play(FadeIn(cross, scale=1.4), FadeIn(stuck), ring.animate.set_stroke(hi, 4), run_time=0.35)

        if explain and clock.left > 1.6:
            # back of the hand from above: extensor tendons and the bands that tie ring to its neighbours
            scene.play(FadeOut(fig), FadeOut(marks), FadeOut(cross), FadeOut(stuck), FadeOut(instr), run_time=0.3)
            palm = RoundedRectangle(width=4.2, height=3.0, corner_radius=0.9).set_fill(skin, 0.35).set_stroke(edge, 2).move_to([0, -0.6, 0])
            tops = {n: np.array([x, 2.6 if n != "thumb" else 0.9, 0]) for n, x, *_ in FINGERS}
            tops["thumb"] = np.array([-2.9, 0.6, 0])
            bases = {n: np.array([x * 0.55, -1.9, 0]) for n, x, *_ in FINGERS}
            bases["thumb"] = np.array([-1.3, -1.8, 0])
            tendons = VGroup(*[Line(bases[n], tops[n]).set_stroke(pal["warm"], 5) for n, *_ in FINGERS])
            outline = VGroup(*[RoundedRectangle(width=w, height=1.8 if n != "thumb" else 1.3, corner_radius=w / 2).set_fill(skin, 0.35).set_stroke(edge, 2)
                               .move_to((tops[n] + (np.array([x, 0.8, 0]) if n != "thumb" else np.array([-2.4, 0.2, 0]))) / 2) for n, x, h, w in FINGERS])
            ties = VGroup(Line(tendons[3].point_from_proportion(0.42), tendons[2].point_from_proportion(0.5)),
                          Line(tendons[3].point_from_proportion(0.42), tendons[4].point_from_proportion(0.36))).set_stroke(hi, 7)
            top_view = VGroup(outline, palm, tendons, ties)
            body = sci.wrapped(p.explain_text, 0.42 * ts, pal["ink"], 28 if st.v else 56, st.sw * 0.92, bold=True)
            t_top, t_bot = st.content(bool(p.title))
            t_bot += st.place_caption(body)
            top_view.scale(min(st.sw * 0.8 / top_view.width, (t_top - t_bot) * 0.85 / top_view.height)).move_to([st.cx, (t_top + t_bot) / 2, 0])
            lab = sci.callout(ties.get_center(), "tendon links", (1, 0.4), hi, pal, 0.28 * ts, 0.6)
            scene.play(FadeIn(top_view[:2]), Create(tendons), FadeIn(body), run_time=0.6)
            scene.play(Create(ties), FadeIn(lab), run_time=0.5)
            scene.play(ties.animate(rate_func=rate_functions.there_and_back).set_stroke(width=11), run_time=min(0.6, max(0.1, clock.left - 0.2)))
        sci.finish(scene, clock, "still")
