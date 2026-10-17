"""The acute stress response, simplified: a threat is noticed, the brain triggers a fast nerve route
(sympathetic nervous system -> adrenal medulla -> adrenaline, within seconds) and a slower hormone route
(hypothalamus -> pituitary -> adrenal cortex -> cortisol, over minutes). The heart speeds up.

Accuracy notes (simplified diagram, front view): organ positions are schematic; the 'fast' and 'slow'
labels follow the textbook SAM / HPA distinction. Heart-rate numbers are illustrative defaults and
editable, not measurements.
"""

from __future__ import annotations

import numpy as np
from manim import (
    DOWN, LEFT, RIGHT, UP, Circle, Ellipse, FadeIn, FadeOut, Line, MoveAlongPath, Polygon, ShowPassingFlash,
    ValueTracker, VGroup, rate_functions,
)
from pydantic import Field

from beatframe.templates import sci
from beatframe.templates.sci import SciParams, Stage


def heart_shape(r: float):
    from manim import VMobject
    t = np.linspace(0, 2 * np.pi, 60)
    x = 16 * np.sin(t) ** 3
    y = 13 * np.cos(t) - 5 * np.cos(2 * t) - 2 * np.cos(3 * t) - np.cos(4 * t)
    pts = np.stack([x, y, np.zeros_like(x)], axis=1) * r / 17
    return VMobject().set_points_smoothly(list(pts))


class StressResponse(sci.Template):
    name = "stress_response"
    description = "Stress response: threat -> brain -> fast adrenaline route and slow cortisol route -> heart speeds up"
    category = "Neuroscience"
    theme = "bright"
    vertical_width = 8.0

    class Params(SciParams):
        stimulus: str = "sudden threat"
        slow_route: bool = True              # also show hypothalamus -> pituitary -> cortisol
        bpm_from: int = Field(70, ge=40, le=120)
        bpm_to: int = Field(115, ge=60, le=190)
        effects: list[str] = ["heart beats faster", "breathing speeds up", "pupils widen", "stored energy released"]
        caption: str = "Fast route: nerves and adrenaline. Slow route: hormones and cortisol."

    def build(self, scene, p, duration):
        st, pal = Stage(), sci.pal_of(p)
        hi = sci.hi_of(p, pal)
        fast_c, slow_c = hi, pal["sky"] if p.highlight != "sky" else pal["lavender"]
        clock = sci.Clock(scene, duration, p.speed)
        sci.guard(scene, duration)
        sci.background(scene, pal, st, seed=31)
        ts = p.text_size
        title = sci.headline(p.title, st, pal, ts)
        top, bottom = st.content(bool(p.title))
        cap = sci.wrapped(p.caption, 0.4 * ts, pal["muted"], 30 if st.v else 66, st.sw * 0.92) if p.caption else VGroup()
        bottom += st.place_caption(cap)

        H = 6.0
        hd = H / 7.5
        body = sci.body_front(H).set_fill(pal["panel"], 0.7).set_stroke(pal["muted"], 2.2)
        top_y = H / 2
        brain = Ellipse(width=hd * 0.78, height=hd * 0.52).set_fill(pal["lavender"], 0.35).set_stroke(pal["lavender"], 2).move_to([0, top_y - hd * 0.36, 0])
        hypo = Circle(radius=hd * 0.07).set_fill(pal["lavender"], 1).set_stroke(width=0).move_to(brain.get_center() + DOWN * hd * 0.1)
        pit = Circle(radius=hd * 0.05).set_fill(slow_c, 1).set_stroke(width=0).move_to(hypo.get_center() + DOWN * hd * 0.16)
        eyes = VGroup(*[Circle(radius=hd * 0.055).set_fill(pal["ink"], 1).set_stroke(width=0).move_to([s * hd * 0.17, top_y - hd * 0.5, 0]) for s in (-1, 1)])
        cord = Line([0, top_y - hd * 1.0, 0], [0, top_y - hd * 3.9, 0]).set_stroke(pal["lavender"], 3, 0.7)
        heart = heart_shape(hd * 0.28).set_fill(pal["coral"], 0.9).set_stroke(width=0).move_to([hd * 0.22, top_y - hd * 2.0, 0])
        kid_y = top_y - hd * 3.25
        kidneys = VGroup(*[Ellipse(width=hd * 0.26, height=hd * 0.42).set_fill(pal["peach"], 0.45).set_stroke(pal["peach"], 1.5).move_to([s * hd * 0.42, kid_y, 0]) for s in (-1, 1)])
        adrenals = VGroup(*[Polygon([-hd * 0.11, 0, 0], [hd * 0.11, 0, 0], [0, hd * 0.14, 0]).set_fill(fast_c, 1).set_stroke(width=0)
                            .move_to([s * hd * 0.42, kid_y + hd * 0.27, 0]) for s in (-1, 1)])
        lungs = VGroup(*[Ellipse(width=hd * 0.5, height=hd * 0.95).set_fill(pal["sky"], 0.12).set_stroke(pal["sky"], 1.2, 0.5).move_to([s * hd * 0.38, top_y - hd * 1.95, 0]) for s in (-1, 1)])
        figure = VGroup(body, lungs, cord, kidneys, adrenals, heart, brain, hypo, pit, eyes)

        if st.v:
            figure.scale_to_fit_height((top - bottom) * 0.9).move_to([st.cx - st.sw * 0.22, (top + bottom) / 2 + 0.2, 0])
        else:
            figure.scale_to_fit_height((top - bottom) * 0.98).move_to([st.left + st.sw * 0.27, (top + bottom) / 2, 0])
        k = figure.height / H

        # right column: stimulus, heart-rate readout, effects list
        col_x = st.cx + st.sw * (0.25 if st.v else 0.2)
        col_w = st.sw * (0.46 if st.v else 0.42)
        stim = sci.tag(p.stimulus, pal["coral"], pal, (0.36 if st.v else 0.42) * ts)
        if stim.width > col_w:
            stim.scale_to_fit_width(col_w)
        stim.move_to([col_x, top - stim.height / 2 - 0.1, 0])
        bpm = ValueTracker(p.bpm_from)
        def readout():
            n = sci.text(f"{int(round(bpm.get_value()))}", 1.25 * ts, pal["ink"], bold=True, serif=True)
            u = sci.text("beats / min", 0.34 * ts, pal["muted"])
            return VGroup(n, u).arrange(DOWN, buff=0.08)
        hr = readout().move_to([col_x, stim.get_bottom()[1] - 1.1, 0])
        hr_heart = heart_shape(0.3).set_fill(pal["coral"], 1).set_stroke(width=0).next_to(hr, LEFT, buff=0.25)
        es = (0.36 if st.v else 0.42) * ts
        effects = VGroup(*[VGroup(sci.text("↑" if j < 2 else "•", es, pal["mint"], bold=True),
                                  sci.wrapped(e, es, pal["ink"], 16 if st.v else 30, col_w * 0.88, align="left")).arrange(RIGHT, buff=0.15, aligned_edge=UP)
                           for j, e in enumerate(p.effects[:5])]).arrange(DOWN, buff=0.2, aligned_edge=LEFT)
        if effects.width > col_w:
            effects.scale_to_fit_width(col_w)
        effects.next_to(hr, DOWN, buff=0.45)
        if st.v:
            effects.move_to([col_x, effects.get_center()[1], 0])
        else:
            effects.align_to(hr_heart, LEFT)
            need = (1.1 if p.slow_route else 0.6) * ts + 0.3       # room for the fast / slow route tags
            avail = effects.get_bottom()[1] - bottom
            if avail < need:
                col = VGroup(stim, hr, hr_heart, effects)
                col.scale(max(0.6, (col.height - (need - avail)) / col.height), about_edge=UP)

        labels = VGroup()
        if p.labels:
            s = 0.26 * ts
            labels.add(sci.callout(adrenals[0].get_center(), "adrenal glands", (-1, -0.5), fast_c, pal, s, 0.5 * k))
            labels.add(sci.callout(hypo.get_center(), "hypothalamus", (-1, 0.5), pal["lavender"], pal, s, 0.45 * k))

        scene.add(figure)
        scene.play(FadeIn(title), FadeIn(cap), FadeIn(stim, shift=LEFT * 0.2), FadeIn(hr), FadeIn(hr_heart), FadeIn(labels), run_time=0.3)

        # 1. the threat is noticed: eyes -> brain
        seen = Line(stim.get_left(), eyes[1].get_center()).set_stroke(pal["coral"], 3)
        scene.play(ShowPassingFlash(seen.copy().set_stroke(pal["coral"], 5), time_width=0.6),
                   brain.animate.set_fill(pal["lavender"], 0.8), run_time=clock.t(0.1, 0.4, 0.8))
        # 2. fast route: down the spinal cord to the adrenal glands, adrenaline into the blood
        fast = sci.smooth([hypo.get_center(), cord.get_start(), cord.get_end() + UP * 0.6 * k, adrenals[1].get_center()], fast_c, 3, 0.0)
        t = clock.t(0.16, 0.6, 1.4)
        spark = sci.glow_dot(fast_c, 0.06 * k + 0.02).move_to(fast.get_start())
        tag_fast = sci.tag("fast · seconds: adrenaline", fast_c, pal, (0.27 if st.v else 0.32) * ts)
        if st.v:
            tag_fast.next_to(figure, DOWN, buff=-0.1)
        else:
            tag_fast.next_to(effects, DOWN, buff=0.3).align_to(effects, LEFT)
        scene.add(spark)
        scene.play(MoveAlongPath(spark, fast, rate_func=rate_functions.ease_in_out_sine),
                   ShowPassingFlash(fast.copy().set_stroke(fast_c, 6, 1), time_width=0.5), run_time=t)
        drops = VGroup(*[Circle(radius=0.035 * k + 0.012).set_fill(fast_c, 1).set_stroke(width=0).move_to(adrenals[1].get_center()) for _ in range(6)])
        targets = [heart.get_center() + np.array([np.cos(a), np.sin(a), 0]) * 0.3 * k for a in np.linspace(0, 2 * np.pi, 7)[:-1]]
        scene.play(FadeOut(spark), FadeIn(drops), FadeIn(tag_fast), adrenals.animate.set_fill(fast_c, 1).scale(1.15), run_time=0.3)
        beat_t = clock.t(0.2, 0.8, 1.8)
        scene.play(*[d.animate(rate_func=rate_functions.ease_out_sine).move_to(tg) for d, tg in zip(drops, targets)],
                   bpm.animate.set_value((p.bpm_from + p.bpm_to) / 2), UpdateFromReadout(hr, readout),
                   heart.animate(rate_func=rate_functions.there_and_back).scale(1.18),
                   hr_heart.animate(rate_func=rate_functions.there_and_back).scale(1.3), run_time=beat_t)
        scene.play(FadeOut(drops), FadeIn(effects[: max(1, len(effects) // 2)], lag_ratio=0.3), run_time=0.4)

        # 3. slow route: hypothalamus -> pituitary -> blood -> adrenal cortex
        if p.slow_route and clock.left > 2.0:
            slow = sci.smooth([pit.get_center(), pit.get_center() + RIGHT * 0.35 * k + DOWN * 0.5 * k,
                               heart.get_center() + RIGHT * 0.55 * k, adrenals[1].get_center() + RIGHT * 0.15 * k], slow_c, 2, 0.35)
            dots = VGroup(*[Circle(radius=0.03 * k + 0.01).set_fill(slow_c, 1).set_stroke(width=0).move_to(pit) for _ in range(4)])
            tag_slow = sci.tag("slow · minutes: cortisol", slow_c, pal, (0.27 if st.v else 0.32) * ts)
            tag_slow.next_to(tag_fast, DOWN, buff=0.12).align_to(tag_fast, LEFT)
            t = clock.t(0.2, 0.8, 1.8)
            scene.play(FadeIn(slow), pit.animate.scale(1.5), FadeIn(dots), run_time=0.3)
            scene.play(*[MoveAlongPath(d, slow, rate_func=rate_functions.ease_in_out_sine, run_time=t * (1 - 0.12 * j)) for j, d in enumerate(dots)],
                       bpm.animate.set_value(p.bpm_to), UpdateFromReadout(hr, readout),
                       *[heart.animate(rate_func=rate_functions.there_and_back).scale(1.15)], run_time=t)
            scene.play(FadeOut(dots), FadeIn(tag_slow), FadeIn(effects[max(1, len(effects) // 2):], lag_ratio=0.3), run_time=0.4)
        else:
            scene.play(bpm.animate.set_value(p.bpm_to), UpdateFromReadout(hr, readout), FadeIn(effects[max(1, len(effects) // 2):]), run_time=0.6)

        # the heart keeps racing for the rest of the beat
        while clock.left > 0.5:
            beat = max(0.25, min(0.6, 60 / max(p.bpm_to, 1)))
            scene.play(heart.animate(rate_func=rate_functions.there_and_back).scale(1.15),
                       hr_heart.animate(rate_func=rate_functions.there_and_back).scale(1.25), run_time=min(beat, clock.left - 0.05))
        if clock.left > 0.02:
            scene.wait(clock.left)


def UpdateFromReadout(group, make):
    """Rebuild the heart-rate number as its tracker changes (only during this animation)."""
    from manim import UpdateFromFunc
    centre = group.get_center()
    return UpdateFromFunc(group, lambda m: m.become(make().move_to(centre)))
