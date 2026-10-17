"""Selective attention as a moving spotlight: one thing at a time is sharp and processed, the rest fade.
Optionally something unattended changes, and the scene asks whether you noticed.

Accuracy notes (conceptual): the 'spotlight' is a classic metaphor for spatial attention (Posner,
1980); attention can also follow objects and features. Missing a change outside attention is
change blindness (Simons & Levin; Rensink). The scene shows that unattended things are processed
less, not that they are invisible.
"""

from __future__ import annotations

import numpy as np
from manim import (
    DOWN, UP, Circle, Create, FadeIn, FadeOut, RoundedRectangle, Square, Star, Triangle, VGroup, rate_functions,
)
from pydantic import Field

from beatframe.templates import sci
from beatframe.templates.sci import SciParams, Stage


class AttentionSpotlight(sci.Template):
    name = "attention_spotlight"
    description = "A spotlight of attention moves between objects; the rest fades (optional unnoticed change)"
    category = "Neuroscience"
    theme = "bright"
    vertical_width = 8.0

    class Params(SciParams):
        items: int = Field(18, ge=8, le=30)
        stops: int = Field(3, ge=1, le=5)               # how many things the spotlight visits
        stop_labels: list[str] = []                     # optional words shown at each stop
        missed_change: bool = True                      # an unattended item changes; revealed at the end
        reveal_text: str = "Did you notice this change?"
        caption: str = "Attention picks one thing; the rest gets far less processing"

    def build(self, scene, p, duration):
        st, pal = Stage(), sci.pal_of(p)
        hi = sci.hi_of(p, pal)
        clock = sci.Clock(scene, duration, p.speed)
        sci.guard(scene, duration)
        sci.background(scene, pal, st, seed=37)
        ts = p.text_size
        title = sci.headline(p.title, st, pal, ts)
        top, bottom = st.content(bool(p.title))
        cap = sci.wrapped(p.caption, 0.4 * ts, pal["muted"], 30 if st.v else 66, st.sw * 0.92) if p.caption else VGroup()
        bottom += st.place_caption(cap)

        rng = np.random.default_rng(p.items * 7 + p.stops)
        cols_n = 4 if st.v else 6
        rows_n = int(np.ceil(p.items / cols_n))
        cw, chh = st.sw / cols_n, (top - bottom - 0.2) / rows_n
        size = min(cw, chh) * 0.42
        palette = [pal["lavender"], pal["mint"], pal["sky"], pal["peach"], pal["coral"], pal["purple"]]
        makers = [lambda c, s: Circle(radius=s / 2).set_fill(c, 1).set_stroke(width=0),
                  lambda c, s: Square(s * 0.85).set_fill(c, 1).set_stroke(width=0).rotate(0.12),
                  lambda c, s: Triangle().scale_to_fit_width(s).set_fill(c, 1).set_stroke(width=0),
                  lambda c, s: Star(5, outer_radius=s * 0.55, inner_radius=s * 0.25).set_fill(c, 1).set_stroke(width=0),
                  lambda c, s: RoundedRectangle(width=s, height=s * 0.55, corner_radius=s * 0.2).set_fill(c, 1).set_stroke(width=0)]
        items = VGroup()
        for k in range(p.items):
            r, c = divmod(k, cols_n)
            x = st.left + cw * (c + 0.5) + rng.uniform(-0.18, 0.18) * cw
            y = top - 0.1 - chh * (r + 0.5) + rng.uniform(-0.15, 0.15) * chh
            m = makers[k % len(makers)](palette[(k * 5 + r) % len(palette)], size * rng.uniform(0.8, 1.1))
            items.add(m.move_to([x, y, 0]).rotate(rng.uniform(-0.3, 0.3)))
        order = list(rng.permutation(p.items))
        stops = order[: p.stops]
        changed = order[p.stops] if p.missed_change and p.items > p.stops else None

        light = VGroup(*[Circle(radius=size * (1.6 - 0.12 * j)).set_stroke(width=0).set_fill(pal["warm"], 0.045) for j in range(6)])
        ring = Circle(radius=size * 1.05).set_stroke(hi, 4)
        spot = VGroup(light, ring).move_to(items[stops[0]])
        spot_tag = sci.tag("attention", hi, pal, 0.3 * ts)

        scene.add(items)
        scene.play(FadeIn(title), FadeIn(cap), run_time=0.3)
        t_in = clock.t(0.08, 0.4, 0.8)
        scene.play(*[m.animate.set_opacity(0.22) for j, m in enumerate(items) if j != stops[0]],
                   items[stops[0]].animate.scale(1.25), FadeIn(spot, scale=1.6), run_time=t_in)
        spot_tag.next_to(spot, UP, buff=0.08)
        scene.play(FadeIn(spot_tag), run_time=0.2)

        reserve = 2.0 if changed is not None else 0.6
        per = max(0.6, (clock.left - reserve) / max(len(stops), 1))
        prev = stops[0]
        for n, s in enumerate(stops):
            lab = p.stop_labels[n] if n < len(p.stop_labels) else ""
            word = sci.tag(lab, pal["ink"], pal, 0.3 * ts).next_to(items[s], DOWN, buff=0.18) if lab else VGroup()
            if n > 0:
                anims = [spot.animate(rate_func=rate_functions.ease_in_out_cubic).move_to(items[s]),
                         items[prev].animate.scale(1 / 1.25).set_opacity(0.22), items[s].animate.scale(1.25).set_opacity(1)]
                if changed is not None and n == 1:          # the unattended change happens mid-move
                    m = items[changed]
                    anims.append(m.animate.set_fill(hi if m.get_fill_color().to_hex() != hi else pal["mint"], 0.22).rotate(0.6))
                scene.play(*anims, spot_tag.animate.next_to(items[s], UP, buff=size * 1.2), run_time=min(per * 0.45, 1.0))
            scene.play(FadeIn(word), run_time=0.2)
            hold = per - (min(per * 0.45, 1.0) if n else 0) - 0.4
            if hold > 0.05:
                scene.wait(hold)
            if len(word):
                scene.play(FadeOut(word), run_time=0.2)
            prev = s

        if changed is not None and clock.left > 0.9:
            m = items[changed]
            mark = Circle(radius=size * 0.95).set_stroke(pal["mint"], 4).move_to(m)
            q = sci.tag(p.reveal_text, pal["mint"], pal, 0.32 * ts)
            q.move_to([st.cx, bottom + q.height / 2 + 0.05, 0]) if st.v else q.next_to(mark, DOWN, buff=0.15)
            if q.get_right()[0] > st.right:
                q.shift((st.right - q.get_right()[0]) * np.array([1, 0, 0]))
            if q.get_left()[0] < st.left:
                q.shift((st.left - q.get_left()[0]) * np.array([1, 0, 0]))
            scene.play(m.animate.set_opacity(1), Create(mark), FadeIn(q), FadeOut(spot), FadeOut(spot_tag), run_time=0.6)
        sci.finish(scene, clock, p.camera)
