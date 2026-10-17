"""A reaction-time demo the viewer can play along with: instruction, countdown, a sudden signal,
a running timer that stops at a typical response, then what happened in between.

Accuracy notes: simple visual reaction time in healthy young adults is typically about 200-250 ms
(it varies with age, alertness, practice and the device's display lag); responses to a sound are
usually a little faster. The default result is labelled "typical", not the viewer's own time, and
the breakdown names the stages (see, decide, move) without inventing exact milliseconds.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
from manim import (
    DOWN, LEFT, RIGHT, UP, Circle, FadeIn, FadeOut, Line, RoundedRectangle, ValueTracker, VGroup, rate_functions,
)
from pydantic import Field

from beatframe.templates import sci
from beatframe.templates.sci import SciParams, Stage


class ReactionTime(sci.Template):
    name = "reaction_time"
    description = "Reaction-time demo: countdown, sudden signal, running timer, response and what takes the time"
    category = "Experiments"
    theme = "bright"
    vertical_width = 8.0

    class Params(SciParams):
        instruction: str = "Tap the moment the circle turns green"
        countdown: int = Field(3, ge=0, le=5)
        wait_seconds: float = Field(1.2, ge=0.3, le=4.0)     # pause after the countdown before the signal
        reaction_ms: int = Field(250, ge=100, le=900)
        result_label: str = "typical adult: about a quarter of a second"
        breakdown: bool = True
        signal: Literal["green", "highlight"] = "green"

    def build(self, scene, p, duration):
        st, pal = Stage(), sci.pal_of(p)
        hi = sci.hi_of(p, pal)
        go = pal["mint"] if p.signal == "green" else hi
        clock = sci.Clock(scene, duration, 1.0)
        sci.guard(scene, duration)
        sci.background(scene, pal, st, seed=23)
        ts = p.text_size
        title = sci.headline(p.title, st, pal, ts)
        top, bottom = st.content(bool(p.title))

        instr = sci.wrapped(p.instruction, (0.5 if st.v else 0.52) * ts, pal["ink"], 24 if st.v else 50, st.sw * 0.95, bold=True)
        instr.move_to([st.cx, top - instr.height / 2 - 0.05, 0])
        r = min((top - bottom) * (0.2 if st.v else 0.3), st.sw * 0.36)
        cy = (instr.get_bottom()[1] + bottom) / 2 + (0.75 if st.v else 0.1)
        target = Circle(radius=r).set_fill(pal["faint"], 1).set_stroke(pal["lavender"], 5).move_to([st.cx, cy, 0])
        rim = Circle(radius=r * 1.12).set_stroke(pal["lavender"], 1.5, 0.4).move_to(target)
        wait_t = sci.text("wait…", 0.55 * ts, pal["muted"], bold=True).move_to(target)

        # timer under the circle (16:9: to the right of it)
        ms = ValueTracker(0)
        def timer_text():
            return sci.text(f"{int(round(ms.get_value()))} ms", (0.95 if st.v else 0.9) * ts, pal["ink"], bold=True, serif=True)
        timer = timer_text()
        if st.v:
            timer_pos = np.array([st.cx, target.get_bottom()[1] - 0.65, 0])
        else:
            target.shift(LEFT * st.sw * 0.16)
            rim.move_to(target)
            wait_t.move_to(target)
            timer_pos = np.array([st.cx + st.sw * 0.22, cy + 0.35, 0])
        timer.move_to(timer_pos)
        timer_box = RoundedRectangle(width=max(timer.width, 2.6) + 0.6, height=timer.height + 0.5, corner_radius=0.2)
        timer_box.set_fill(pal["panel"], 0.75).set_stroke(pal["faint"], 1.5).move_to(timer_pos)

        scene.add(target, rim)
        scene.play(FadeIn(title), FadeIn(instr), FadeIn(wait_t), FadeIn(timer_box), FadeIn(timer), run_time=0.3)

        # countdown: numbers inside the circle
        reserve = p.reaction_ms / 1000 + 1.2 + (1.4 if p.breakdown else 0)
        step = min(0.7, max(0.35, (clock.left - reserve - p.wait_seconds) / max(p.countdown, 1)))
        if p.countdown:
            scene.play(FadeOut(wait_t), run_time=0.15)
            for n in range(p.countdown, 0, -1):
                if clock.left < reserve + 0.5:
                    break
                num = sci.text(str(n), 1.4 * ts * r / 1.4, pal["ink"], bold=True, serif=True).move_to(target)
                scene.play(FadeIn(num, scale=1.4), run_time=step * 0.4)
                scene.play(FadeOut(num, scale=0.7), run_time=step * 0.6)
            wait_t = sci.text("wait…", 0.55 * ts, pal["muted"], bold=True).move_to(target)
            scene.play(FadeIn(wait_t), run_time=0.15)
        hold = min(p.wait_seconds, max(0.1, clock.left - reserve))
        scene.wait(hold)

        # the signal: instant, no fade (a fade would blur the moment the timer starts)
        burst = VGroup(*[Line(target.get_center() + np.array([np.cos(a), np.sin(a), 0]) * r * 1.2,
                              target.get_center() + np.array([np.cos(a), np.sin(a), 0]) * r * 1.5).set_stroke(go, 6)
                         for a in np.linspace(0, 2 * np.pi, 13)[:-1]])
        scene.remove(wait_t)
        target.set_fill(go, 1).set_stroke(go, 5)
        now_t = sci.text("NOW!", 0.75 * ts * r / 1.4 * 1.4, pal["bottom"] if pal["dark"] else pal["warm"], bold=True).move_to(target)
        scene.add(burst, now_t)

        timer.add_updater(lambda m: m.become(timer_text().move_to(timer_pos)))
        react = p.reaction_ms / 1000
        scene.play(ms.animate(rate_func=rate_functions.linear).set_value(p.reaction_ms), burst.animate.scale(1.25).set_opacity(0),
                   run_time=react)
        timer.clear_updaters()
        timer.become(timer_text().move_to(timer_pos))

        # the response: a tap ripple and the timer locks in
        tap = Circle(radius=r * 0.25).set_stroke(pal["warm"], 6).move_to(target)
        scene.play(tap.animate(rate_func=rate_functions.ease_out_cubic).scale(4).set_stroke(opacity=0),
                   target.animate(rate_func=rate_functions.there_and_back).scale(0.94),
                   timer_box.animate.set_stroke(go, 3), run_time=0.4)
        res = sci.wrapped(p.result_label, 0.4 * ts, pal["muted"], 26 if st.v else 34, st.sw * (0.9 if st.v else 0.4))
        res.next_to(timer_box, DOWN, buff=0.25)
        scene.play(FadeIn(res, shift=UP * 0.1), run_time=0.3)

        if p.breakdown and clock.left > 1.0:
            stages = [("see", pal["sky"]), ("decide", pal["lavender"]), ("move", pal["peach"])]
            w = st.sw * (0.86 if st.v else 0.42)
            segs = VGroup()
            for k, (name, col) in enumerate(stages):
                bar = RoundedRectangle(width=w / 3 - 0.08, height=0.32, corner_radius=0.12).set_fill(col, 0.9).set_stroke(width=0)
                lab = sci.text(name, 0.38 * ts, pal["ink"], bold=True).next_to(bar, DOWN, buff=0.12)
                segs.add(VGroup(bar, lab))
            segs.arrange(RIGHT, buff=0.08, aligned_edge=UP)
            if st.v:                       # below the subtitle band
                segs.move_to([st.cx, st.foot, 0])
            else:
                segs.next_to(res, DOWN, buff=0.45)
            scene.play(*[FadeIn(sg[0], shift=RIGHT * 0.15) for sg in segs], *[FadeIn(sg[1]) for sg in segs],
                       run_time=min(0.8, clock.left * 0.4))
        sci.finish(scene, clock, p.camera, focus=target.get_center())
