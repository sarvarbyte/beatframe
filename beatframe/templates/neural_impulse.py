"""Neurons passing a signal: an electrical impulse runs down each axon, neurotransmitter crosses
the synapse, the next cell fires. Optionally the camera dives into the first synapse.

Accuracy notes (simplified diagram): the impulse along the axon is electrical (an action potential);
at a chemical synapse it is carried across the gap by neurotransmitter molecules. Most synapses in
the human brain work this way; electrical synapses exist too but are not shown.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
from manim import (
    Circle, Dot, FadeIn, FadeOut, LaggedStart, MoveAlongPath, ShowPassingFlash, VGroup, Create, rate_functions,
)
from pydantic import Field

from beatframe.templates import sci
from beatframe.templates.sci import SciParams, Stage


class NeuralImpulse(sci.Template):
    name = "neural_impulse"
    description = "Neurons fire in sequence: impulse down the axon, neurotransmitter across the synapse"
    category = "Neuroscience"
    theme = "bright"
    vertical_width = 8.0

    class Params(SciParams):
        neurons: int = Field(5, ge=3, le=7)
        layout: Literal["chain", "branching"] = "chain"
        synapse_zoom: bool = True          # the camera dives into the first synapse
        caption: str = "Electrical along the axon, chemical across the gap"
        title: str = ""

    def build(self, scene, p, duration):
        st, pal = Stage(), sci.pal_of(p)
        hi, cold = sci.hi_of(p, pal), pal["lavender"]
        clock = sci.Clock(scene, duration, p.speed)
        sci.guard(scene, duration)
        sci.background(scene, pal, st, seed=3)
        title = sci.headline(p.title, st, pal, p.text_size)
        top, bottom = st.content(bool(p.title))
        cap = sci.wrapped(p.caption, 0.42 * p.text_size, pal["muted"], 30 if st.v else 60, st.sw * 0.9) if p.caption else VGroup()
        cap_h = st.place_caption(cap)

        # ---- positions: zig-zag along the long axis of the frame
        n = p.neurons
        area_top, area_bot = top - 0.2, bottom + cap_h
        pos = []
        for k in range(n):
            f = k / (n - 1)
            if st.v:
                y = area_top - 0.6 - f * (area_top - area_bot - 1.2)
                x = st.cx + st.sw * (0.27 if k % 2 else -0.27) * (1 if k not in (0, n - 1) else 0.4)
            else:
                x = st.left + 1.2 + f * (st.sw - 2.4)
                y = (area_top + area_bot) / 2 + (0.95 if k % 2 else -0.95)
            pos.append(np.array([x, y, 0.0]))
        links = [(k, k + 1) for k in range(n - 1)]
        if p.layout == "branching" and n >= 4:      # the last step forks: one cell feeds two
            last = pos[-1].copy()
            off = np.array([st.sw * 0.26, 0, 0]) if st.v else np.array([0, 1.15, 0])
            pos[-1] = last + off
            side = last - off
            pos.append(side)
            links.append((n - 2, len(pos) - 1))

        r = 0.30 if st.v else 0.36
        cells, axons, terminals = [], {}, {}
        outgoing = {}
        for a, b in links:
            outgoing.setdefault(a, []).append(b)
        for k, c in enumerate(pos):
            first_target = outgoing.get(k, [None])[0]
            axon_to = None
            if first_target is not None:
                v = pos[first_target] - c
                axon_to = v - v / np.linalg.norm(v) * (r + 0.32)   # stop short: the synaptic gap
            cell = sci.neuron(pal, cold, r=r, dendrites=6, seed=k + 1, axon_to=axon_to).move_to(c)
            # move_to recentres the whole group: put the soma back on its point
            cell.shift(c - cell[1].get_center())
            cells.append(cell)
        for a, b in links:
            if b == outgoing[a][0]:
                ax = cells[a].axon
            else:                                   # extra branch: a collateral from the same axon
                v = pos[b] - pos[a]
                end = pos[a] + v - v / np.linalg.norm(v) * (r + 0.32)
                mid = (pos[a] + end) / 2 + np.array([0.25, 0.25, 0])
                ax = sci.smooth([pos[a] + v / np.linalg.norm(v) * r, mid, end], cold, 3.0, 0.95)
                cells[a].add(ax)
            axons[(a, b)] = ax
            terminals[(a, b)] = Circle(radius=0.075).set_fill(cold, 1).set_stroke(width=0).move_to(ax.get_end())

        net = VGroup(*cells, *terminals.values())
        fit_h, fit_w = (area_top - area_bot) * 0.92, st.sw * 0.94
        net.scale(min(fit_h / net.height, fit_w / net.width, 2.2))
        net.move_to([st.cx, (area_top + area_bot) / 2, 0])

        labels = VGroup()
        if p.labels:
            c0 = cells[0]
            s = 0.33 * p.text_size
            dend = c0[0][0].get_end()
            labels.add(sci.callout(dend, "dendrites", (-0.3, 1) if not st.v else (1, 0.7), pal["muted"], pal, s, 0.45))
            labels.add(sci.callout(c0[1].get_center(), "cell body", (0.2, -1) if not st.v else (-0.4, 1), pal["muted"], pal, s, 0.55))
            ax0 = axons[links[0]]
            labels.add(sci.callout(ax0.point_from_proportion(0.55), "axon", (0.3, 1) if not st.v else (-1, -0.8), pal["muted"], pal, s, 0.5))
            t0 = terminals[links[0]].get_center()
            labels.add(sci.callout(t0, "synapse", (0.5, -1) if not st.v else (1, -0.5), hi, pal, s, 0.55))

        # ---- first frame: the network is already there
        scene.add(net)
        scene.play(FadeIn(title), FadeIn(cap), FadeIn(labels), run_time=0.3)

        frame = scene.camera.frame
        home_w, home_c = frame.width, frame.get_center()

        def fire(k):
            soma = cells[k][1]
            ring = Circle(radius=soma.width / 2).set_stroke(hi, 4, 0.9).move_to(soma)
            return [soma.animate(rate_func=rate_functions.there_and_back_with_pause).set_fill(hi, 1),
                    ring.animate(rate_func=rate_functions.ease_out_cubic).scale(2.6).set_stroke(opacity=0)]

        def hop(a, b, t):
            ax = axons[(a, b)]
            spark = sci.glow_dot(hi, 0.07).move_to(ax.get_start())
            flash = ax.copy().set_stroke(hi, 7, 1)
            return spark, [MoveAlongPath(spark, ax, rate_func=rate_functions.ease_in_out_sine, run_time=t),
                           ShowPassingFlash(flash, time_width=0.45, run_time=t)]

        def cross(a, b, t):
            term = terminals[(a, b)].get_center()
            target = cells[b][1].get_center()
            d = target - term
            gap_end = term + d / np.linalg.norm(d) * max(0.12, np.linalg.norm(d) - cells[b][1].width / 2)
            dots = VGroup(*[Dot(term + np.random.uniform(-0.05, 0.05, 3) * [1, 1, 0], radius=0.028, color=pal["mint"])
                            for _ in range(5)])
            moves = [d_.animate(rate_func=rate_functions.ease_out_sine).move_to(gap_end + np.random.uniform(-0.08, 0.08, 3) * [1, 1, 0])
                     for d_ in dots]
            return dots, moves

        order = [links[0][0]] + [b for _, b in links]
        hops = len(links)
        avail = clock.left - (2.6 if p.synapse_zoom else 0.6)
        per = max(0.45, min(1.6 / p.speed, avail / max(hops, 1) / 1.5))
        scene.play(*fire(order[0]), run_time=0.45)
        zoomed = False
        for i, (a, b) in enumerate(links):
            if clock.left < 0.6:
                break
            t = min(per, max(0.3, clock.left * 0.45))
            spark, anims = hop(a, b, t)
            scene.add(spark)
            scene.play(*anims)
            if p.synapse_zoom and not zoomed and clock.left > per * (hops - i) + 1.2:
                zoomed = True
                term = terminals[(a, b)].get_center()
                scene.play(frame.animate(rate_func=rate_functions.ease_in_out_sine).set(width=home_w * 0.38).move_to(term),
                           FadeOut(labels), FadeOut(spark), run_time=0.7)
                dots, moves = cross(a, b, 0.9)
                note = sci.tag("neurotransmitter", pal["mint"], pal, 0.13 if not st.v else 0.12)
                note.next_to(term, sci.UP if not st.v else sci.LEFT, buff=0.18)
                scene.play(FadeIn(dots, scale=0.5), FadeIn(note), run_time=0.25)
                scene.play(LaggedStart(*moves, lag_ratio=0.15), run_time=0.8)
                scene.play(frame.animate(rate_func=rate_functions.ease_in_out_sine).set(width=home_w).move_to(home_c),
                           FadeOut(dots), FadeOut(note), *fire(b), run_time=0.7)
            else:
                dots, moves = cross(a, b, t * 0.5)
                scene.play(FadeOut(spark), FadeIn(dots), run_time=0.12)
                scene.play(*moves, *fire(b), FadeOut(dots, run_time=0.4), run_time=max(0.35, t * 0.5))
        sci.finish(scene, clock, p.camera)
