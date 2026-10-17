"""Balance uses three senses at once: vision, the vestibular system in the inner ear, and
proprioception (stretch and pressure sensors in the ankles and feet). Take one away and the body
sways more, and the brain keeps correcting. A sway trace records it live.

Accuracy notes (conceptual demo, like the clinical Romberg / foam-surface tests): standing still is a
constant series of small corrections; closing the eyes or standing on foam typically increases sway
because the brain must rely more on the remaining inputs. Sway sizes here are illustrative, not data.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
from manim import (
    DOWN, LEFT, RIGHT, UP, Arc, Circle, Ellipse, FadeIn, FadeOut, Line, RoundedRectangle, ShowPassingFlash,
    ValueTracker, VGroup, VMobject, linear, rate_functions,
)

from beatframe.templates import sci
from beatframe.templates.sci import SciParams, Stage


class BalanceExperiment(sci.Template):
    name = "balance_experiment"
    description = "Balance from vision + inner ear + feet: close the eyes (and stand on foam) and the sway grows"
    category = "Experiments"
    theme = "bright"
    vertical_width = 8.0

    class Params(SciParams):
        steps: Literal["eyes", "eyes_and_foam"] = "eyes"
        try_it: str = "Try it: stand on one leg, then close your eyes"
        caption: str = "Your brain balances you with three senses at once"

    def build(self, scene, p, duration):
        st, pal = Stage(), sci.pal_of(p)
        hi = sci.hi_of(p, pal)
        clock = sci.Clock(scene, duration, p.speed)
        sci.guard(scene, duration)
        sci.background(scene, pal, st, seed=59)
        ts = p.text_size
        title = sci.headline(p.title, st, pal, ts)
        top, bottom = st.content(bool(p.title))
        cap = sci.wrapped(p.caption, 0.4 * ts, pal["muted"], 30 if st.v else 66, st.sw * 0.92) if p.caption else VGroup()
        bottom += st.place_caption(cap)
        vis_c, ves_c, pro_c = pal["sky"], pal["lavender"], pal["mint"]

        H = 6.0
        hd = H / 7.5
        body = sci.body_front(H).set_fill(pal["panel"], 0.75).set_stroke(pal["muted"], 2.2)
        head_c = np.array([0, H / 2 - hd * 0.5, 0])
        brain = Ellipse(width=hd * 0.7, height=hd * 0.42).set_fill(pal["purple"], 0.4).set_stroke(pal["purple"], 1.5).move_to(head_c + UP * hd * 0.12)
        eyes_open = VGroup(*[Circle(radius=hd * 0.06).set_fill(vis_c, 1).set_stroke(width=0).move_to(head_c + np.array([s * hd * 0.17, -hd * 0.05, 0])) for s in (-1, 1)])
        eyes_shut = VGroup(*[Arc(radius=hd * 0.08, start_angle=np.pi * 1.15, angle=np.pi * 0.7).set_stroke(vis_c, 3).move_to(head_c + np.array([s * hd * 0.17, -hd * 0.07, 0])) for s in (-1, 1)])
        ear = sci.ear_shape(hd * 0.5).set_stroke(ves_c, 3).move_to(head_c + RIGHT * hd * 0.52)
        feet_y = -H / 2
        nerves = VGroup(*[sci.smooth([[s * hd * 0.42, feet_y + hd * 0.2], [s * hd * 0.35, -hd * 0.5], [s * hd * 0.1, H / 2 - hd * 1.4], head_c], pro_c, 2.2, 0.5)
                          for s in (-1, 1)])
        sensors = VGroup(*[Circle(radius=hd * 0.1).set_fill(pro_c, 1).set_stroke(width=0).move_to([s * hd * 0.42, feet_y + hd * 0.3, 0]) for s in (-1, 1)])
        person = VGroup(body, nerves, brain, eyes_open, ear, sensors)
        ground = Line([-2.5, feet_y, 0], [2.5, feet_y, 0]).set_stroke(pal["muted"], 3)
        foam = RoundedRectangle(width=2.6, height=0.45, corner_radius=0.18).set_fill(pal["peach"], 0.55).set_stroke(pal["peach"], 2).move_to([0, feet_y - 0.22, 0])

        # sway trace panel
        PW, PH = (7.0, 2.6) if st.v else (5.6, 2.2)
        panel = sci.card(PW, PH, pal)
        mid = Line([-PW / 2 + 0.3, 0, 0], [PW / 2 - 0.3, 0, 0]).set_stroke(pal["faint"], 1.5)
        plabel = sci.text("body sway", 0.32, pal["muted"], bold=True).move_to([-PW / 2 + 0.95, PH / 2 - 0.28, 0])
        trace_box = VGroup(panel, mid, plabel)

        # inputs legend
        def row(c, t):
            return VGroup(Circle(radius=0.1).set_fill(c, 1).set_stroke(width=0), sci.text(t, 0.34, pal["ink"], bold=True)).arrange(RIGHT, buff=0.15)
        legend = VGroup(row(vis_c, "eyes · vision"), row(ves_c, "inner ear · balance organs"), row(pro_c, "feet & ankles · body sense")).arrange(DOWN, buff=0.22, aligned_edge=LEFT)

        stage_group = VGroup(person, ground, foam)
        area = top - bottom
        if st.v:
            trace_box.scale_to_fit_width(st.sw * 0.95)
            if trace_box.height > area * 0.3:
                trace_box.scale_to_fit_height(area * 0.3)
            trace_box.move_to([st.cx, bottom + trace_box.height / 2 + 0.05, 0])
            stage_group.scale_to_fit_height(area * 0.52)
            stage_group.move_to([st.left + stage_group.width / 2 + 0.2, top - stage_group.height / 2, 0])
            legend.scale_to_fit_width(min(legend.width, st.right - stage_group.get_right()[0] - 0.2)).next_to(stage_group, RIGHT, buff=0.2).align_to(stage_group, UP)
        else:
            stage_group.scale_to_fit_height(area * 0.92).move_to([st.left + st.sw * 0.25, (top + bottom) / 2, 0])
            col_w = st.sw * 0.46
            legend.scale(min(1.2, col_w / legend.width)).move_to([st.right - col_w / 2, top - legend.height / 2 - 0.1, 0]).align_to([st.right - col_w, 0, 0], LEFT)
            trace_box.scale_to_fit_width(col_w).next_to(legend, DOWN, buff=0.95).align_to(legend, LEFT)
        k = stage_group.height / (H + 0.5)
        pivot = ground.get_center()
        eyes_shut.scale(k).move_to(eyes_open)
        foam.set_opacity(0)

        x0, x1 = mid.get_start()[0], mid.get_end()[0]
        y_mid = mid.get_y()
        amp_y = trace_box.height * 0.32
        phase_t = ValueTracker(0.0)
        sway = ValueTracker(0.012)          # radians
        base = person.copy()
        pts: list[np.ndarray] = []
        trace = VMobject().set_stroke(hi, 3)
        total = max(2.5, clock.left - 0.6)

        def angle():
            t = phase_t.get_value()
            return sway.get_value() * (np.sin(t * 2 * np.pi / 1.7) + 0.35 * np.sin(t * 2 * np.pi / 0.63 + 1))

        def upd_person(m):
            m.become(base.copy().rotate(angle(), about_point=pivot))
            if eyes_closed["v"]:
                m[3].set_opacity(0)
        eyes_closed = {"v": False}
        person.add_updater(upd_person)

        def upd_trace(m):
            f = phase_t.get_value() / total
            pts.append(np.array([x0 + (x1 - x0) * min(1, f), y_mid + np.clip(angle() / 0.08, -1, 1) * amp_y, 0]))
            if len(pts) > 1:
                m.set_points_as_corners(pts)
        trace.add_updater(upd_trace)

        scene.add(stage_group, legend, trace_box, trace)
        scene.play(FadeIn(title), FadeIn(cap), run_time=0.3)

        tag_y = trace_box.get_top()[1] + 0.3
        def note(text, color):
            t = sci.tag(text, color, pal, 0.32 * ts)
            if t.width > trace_box.width:
                t.scale_to_fit_width(trace_box.width)
            if st.v:
                return t.next_to(trace_box, UP, buff=0.15)
            return t.next_to(trace_box, UP, buff=0.15).align_to(trace_box, LEFT)

        phases = [("all three senses: tiny corrections", pro_c, 0.012)]
        phases.append(("eyes closed: more sway", vis_c, 0.035))
        if p.steps == "eyes_and_foam":
            phases.append(("eyes closed + soft foam: much more sway", pal["peach"], 0.06))
        per = total / len(phases)
        cur = None
        for j, (text, color, amp) in enumerate(phases):
            t = note(text, color)
            pre = [FadeIn(t)] + ([FadeOut(cur)] if cur is not None else [])
            if j == 1:
                eyes_closed["v"] = True
                base[3].set_opacity(0)
                eye_shut_live = eyes_shut
                scene.add(eye_shut_live)
                eye_shut_live.add_updater(lambda m: m.move_to(person[3].get_center()))
                pre += [legend[0].animate.set_opacity(0.35)]
            if j == 2:
                base[5].set_fill(opacity=0.35)
                pre += [foam.animate.set_opacity(1), legend[2].animate.set_opacity(0.35)]
            rt = 0.35 if per > 1 else per * 0.3
            scene.play(*pre, phase_t.animate(rate_func=linear).set_value(phase_t.get_value() + rt), run_time=rt)
            rest = per * (j + 1) - phase_t.get_value()
            if rest > 0.05:
                scene.play(phase_t.animate(rate_func=linear).set_value(per * (j + 1)),
                           sway.animate(rate_func=rate_functions.smooth).set_value(amp), run_time=rest)
            cur = t
        for m in (person, trace, eyes_shut):
            m.clear_updaters()
        if clock.left > 0.5 and p.try_it:
            tip = sci.tag(p.try_it, pal["warm"], pal, 0.3 * ts)
            if tip.width > st.sw:
                tip.scale_to_fit_width(st.sw)
            tip.move_to(cur)
            scene.play(FadeOut(cur), FadeIn(tip), run_time=0.3)
        sci.finish(scene, clock, "still")
