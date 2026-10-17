"""A night of sleep as a hypnogram: the line steps through Wake, REM and NREM stages N1-N3 while a
brainwave-style trace shows what each stage looks like.

Accuracy notes (educational simplification of a typical healthy adult night): sleep runs in cycles
of roughly 90 minutes (often 70-120); deep N3 sleep is concentrated in the first cycles, REM periods
get longer towards morning; brief awakenings are normal. The traces are stylised EEG patterns:
wake = fast low-amplitude, N1 = slower theta, N2 = sleep spindles and K-complexes, N3 = large slow
delta waves, REM = low-amplitude mixed and 'sawtooth' waves. Not a medical recording.
"""

from __future__ import annotations

import numpy as np
from manim import (
    DOWN, LEFT, RIGHT, UP, Dot, FadeIn, Line, RoundedRectangle, ValueTracker, VGroup, VMobject, linear,
)
from pydantic import Field

from beatframe.templates import sci
from beatframe.templates.sci import SciParams, Stage

ORDER = ["Wake", "REM", "N1", "N2", "N3"]           # hypnogram rows, top to bottom (clinical convention)
DESCRIBE = {"Wake": "awake: fast, small waves", "REM": "REM: dreaming, brain very active",
            "N1": "N1: drifting off", "N2": "N2: spindles and K-complexes", "N3": "N3: deep, slow waves"}


def night(cycles: int, hours: float, seed: int = 1) -> list[tuple[float, str]]:
    """(start hour, stage) steps for a typical night: N3 early, REM growing later."""
    rng = np.random.default_rng(seed)
    cyc = hours / cycles
    steps = [(0.0, "Wake"), (0.15, "N1")]
    t = 0.25
    for k in range(cycles):
        f = k / max(cycles - 1, 1)
        deep = max(0.0, 0.45 - 0.62 * f) * cyc            # N3 shrinks through the night, gone by morning
        rem = (0.10 + 0.28 * f) * cyc                       # REM grows
        n2a = (cyc - deep - rem) * 0.55
        n2b = (cyc - deep - rem) * 0.45
        seq = [("N2", n2a)] + ([("N3", deep)] if deep > 0.05 else []) + [("N2", n2b * 0.6), ("REM", rem)]
        if k in (1, 3) and k < cycles - 1:
            seq += [("Wake", 0.05)]
        seq += [("N1", n2b * 0.4)]
        for stage, d in seq:
            if t >= hours - 0.05:
                break
            steps.append((t, stage))
            t += max(0.04, d * rng.uniform(0.9, 1.1))
    steps.append((min(t, hours - 0.1), "Wake"))
    return steps


def stage_at(steps, h: float) -> str:
    cur = steps[0][1]
    for t, s in steps:
        if t <= h:
            cur = s
    return cur


def trace_points(stage: str, phase: float, w: float, amp: float, n: int = 160) -> np.ndarray:
    x = np.linspace(0, 1, n)
    tt = x * 6 + phase
    if stage == "Wake":
        y = 0.18 * np.sin(tt * 19) + 0.12 * np.sin(tt * 31 + 1)
    elif stage == "N1":
        y = 0.35 * np.sin(tt * 7) + 0.1 * np.sin(tt * 17)
    elif stage == "N2":
        spindle = np.exp(-((tt % 6) - 3.0) ** 2 * 3) * 0.32 * np.sin(tt * 40)
        k = -0.9 * np.exp(-((tt % 6) - 1.2) ** 2 * 25) + 0.45 * np.exp(-((tt % 6) - 1.45) ** 2 * 25)
        y = 0.22 * np.sin(tt * 6) + spindle + k
    elif stage == "N3":
        y = 0.85 * np.sin(tt * 2.2) + 0.08 * np.sin(tt * 13)
    else:   # REM: low amplitude, mixed, with sawtooth bursts
        saw = 0.25 * ((tt * 3.5) % 1 - 0.5) * (np.sin(tt * 0.9) > 0.3)
        y = 0.16 * np.sin(tt * 15) + 0.1 * np.sin(tt * 23 + 2) + saw
    return np.stack([x * w - w / 2, y * amp, np.zeros(n)], axis=1)


class SleepCycle(sci.Template):
    name = "sleep_cycle"
    description = "A night's hypnogram (Wake, REM, N1-N3) drawn in time, with a live brainwave-style trace"
    category = "Neuroscience"
    theme = "bright"
    vertical_width = 8.0

    class Params(SciParams):
        hours: float = Field(8.0, ge=5.0, le=10.0)
        cycles: int = Field(5, ge=3, le=6)
        focus: str = ""                 # optional: REM | N3 ... - that stage is highlighted on the chart
        caption: str = "About 90-minute cycles: deep sleep early, more REM towards morning"

    def build(self, scene, p, duration):
        st, pal = Stage(), sci.pal_of(p)
        hi = sci.hi_of(p, pal)
        clock = sci.Clock(scene, duration, p.speed)
        sci.guard(scene, duration)
        sci.background(scene, pal, st, seed=29)
        ts = p.text_size
        title = sci.headline(p.title, st, pal, ts)
        top, bottom = st.content(bool(p.title))
        cap = sci.wrapped(p.caption, 0.4 * ts, pal["muted"], 30 if st.v else 66, st.sw * 0.92) if p.caption else VGroup()
        bottom += st.place_caption(cap)
        colors = {"Wake": pal["peach"], "REM": hi if p.highlight != "sky" else pal["coral"], "N1": pal["lavender"], "N2": pal["purple"], "N3": pal["sky"]}

        # ---- layout: chart on top, trace panel below (both formats; widths differ)
        area = top - bottom
        chart_h = area * (0.5 if st.v else 0.58)
        label_w = 1.1 * ts
        W = st.sw - label_w - 0.2
        x0 = st.left + label_w + 0.2
        y_top = top - 0.15
        row = chart_h / (len(ORDER) - 0.5)
        ys = {s: y_top - k * row for k, s in enumerate(ORDER)}
        grid = VGroup()
        for s in ORDER:
            grid.add(Line([x0, ys[s], 0], [x0 + W, ys[s], 0]).set_stroke(pal["faint"], 1.2, 0.8))
            lab = sci.text(s, 0.36 * ts, colors[s], bold=True).move_to([x0 - 0.15, ys[s], 0], aligned_edge=RIGHT)
            grid.add(lab)
        steps = night(p.cycles, p.hours)
        H = p.hours
        hx = lambda h: x0 + W * h / H
        ticks = VGroup()
        for h in range(0, int(H) + 1, 2 if st.v else 1):
            ticks.add(sci.text(f"{h}h", 0.28 * ts, pal["muted"]).move_to([hx(h), ys["N3"] - 0.32, 0]))
        if p.focus in colors:
            for (t, s), (t2, _) in zip(steps, steps[1:] + [(H, "")]):
                if s == p.focus:
                    band = RoundedRectangle(width=max(0.04, hx(t2) - hx(t)), height=row * 0.7, corner_radius=0.04)
                    grid.add(band.set_fill(colors[s], 0.28).set_stroke(width=0).move_to([(hx(t) + hx(t2)) / 2, ys[s], 0]))

        # the line, sampled every few minutes so drawing it evenly also means evenly in time
        samples = np.linspace(0, H, 300)
        pts = [np.array([hx(h), ys[stage_at(steps, h)], 0]) for h in samples]
        full = VMobject().set_points_as_corners(pts).set_stroke(pal["ink"], 3)
        line = full.copy()
        prog = ValueTracker(0.001)
        line.add_updater(lambda m: m.pointwise_become_partial(full, 0, max(0.001, prog.get_value())))
        marker = Dot(radius=0.09, color=hi).move_to(pts[0])
        marker.add_updater(lambda m: m.move_to(full.point_from_proportion(max(0.001, min(0.999, prog.get_value())))))

        # ---- trace panel
        panel_h = area - chart_h - 0.9
        pw = st.sw
        panel = sci.card(pw, panel_h, pal).move_to([st.cx, bottom + panel_h / 2, 0])
        amp = panel_h * 0.28
        stage_name = {"v": "Wake"}
        trace = VMobject().set_points_smoothly(trace_points("Wake", 0, pw * 0.9, amp)).set_stroke(colors["Wake"], 3)
        trace.move_to(panel.get_center() + DOWN * panel_h * 0.08)
        tclock = {"t": 0.0}
        label_box = sci.tag(DESCRIBE["Wake"], colors["Wake"], pal, 0.34 * ts).move_to(panel.get_top() + DOWN * 0.38)

        def upd_trace(m, dt):
            tclock["t"] += dt
            h = prog.get_value() * H
            s = stage_at(steps, h)
            m.set_points_smoothly(trace_points(s, tclock["t"] * 1.6, pw * 0.9, amp)).set_stroke(colors[s])
            m.move_to(panel.get_center() + DOWN * panel_h * 0.08)
            if s != stage_name["v"]:
                stage_name["v"] = s
                label_box.become(sci.tag(DESCRIBE[s], colors[s], pal, 0.34 * ts).move_to(panel.get_top() + DOWN * 0.38))
        trace.add_updater(upd_trace)

        scene.add(grid, ticks, panel, line, marker, trace, label_box)
        scene.play(FadeIn(title), FadeIn(cap), run_time=0.3)
        draw = max(1.0, clock.left - min(1.2, clock.left * 0.18))
        scene.play(prog.animate(rate_func=linear).set_value(1.0), run_time=draw)
        line.clear_updaters()
        marker.clear_updaters()
        trace.clear_updaters()
        sci.finish(scene, clock, "still" if p.camera == "gentle" else p.camera)
