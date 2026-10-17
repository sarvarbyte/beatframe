"""An evolutionary tree that grows from a common ancestor to today's species along a time axis.
Every living species ends on the 'today' line, so no modern species is shown as the ancestor of
another; branch points are shared ancestors that no longer exist.

Accuracy notes: topologies are standard; divergence times are rounded approximations from
molecular-clock studies (e.g. TimeTree) and are labelled "about". Great apes: human-chimp ~6-7 Mya,
gorilla ~9, orangutan ~15, gibbons ~18. Vertebrates: mouse-human ~90, lizard-bird ~280,
mammal-reptile ~320, amphibian-amniote ~350, lobe-/ray-finned fish ~430, shark ~460 Mya.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
from manim import (
    DOWN, LEFT, RIGHT, UP, Circle, Create, DashedLine, FadeIn, Line, VGroup, rate_functions,
)

from beatframe.templates import sci
from beatframe.templates.sci import SciParams, Stage

# (age in million years, [children]) ; leaves are names
TREES = {
    "apes": (18, [(15, [(9, [(6.5, ["Human", (1.5, ["Chimpanzee", "Bonobo"])]), "Gorilla"]), "Orangutan"]), "Gibbon"]),
    "vertebrates": (460, ["Shark", (430, ["Ray-finned fish", (350, ["Frog", (320, [(280, ["Lizard", "Bird"]), (90, ["Mouse", "Human"])])])])]),
}


class EvolutionTree(sci.Template):
    name = "evolution_tree"
    description = "Evolutionary tree growing along a time axis to today's species; shared ancestors marked"
    category = "Biology"
    theme = "bright"
    vertical_width = 8.0

    class Params(SciParams):
        tree: Literal["apes", "vertebrates"] = "apes"
        focus: str = "Human"                 # this lineage is highlighted back to the root
        caption: str = "Branch points are shared ancestors, not today's species"

    def build(self, scene, p, duration):
        st, pal = Stage(), sci.pal_of(p)
        hi = sci.hi_of(p, pal)
        clock = sci.Clock(scene, duration, p.speed)
        sci.guard(scene, duration)
        sci.background(scene, pal, st, seed=89)
        ts = p.text_size
        title = sci.headline(p.title, st, pal, ts)
        top, bottom = st.content(bool(p.title))
        cap = sci.wrapped(p.caption, 0.4 * ts, pal["muted"], 30 if st.v else 66, st.sw * 0.92) if p.caption else VGroup()
        bottom += st.place_caption(cap)
        root = TREES[p.tree]

        leaves = []
        def collect(n):
            if isinstance(n, str):
                leaves.append(n)
            else:
                for c in n[1]:
                    collect(c)
        collect(root)
        label_size = (0.36 if st.v else 0.4) * ts
        names = {n: sci.text(n, label_size, pal["ink"], bold=n == p.focus) for n in leaves}
        name_w = max(m.width for m in names.values()) + 0.3
        axis_h = 0.9
        x_today = st.right - name_w
        x_root = st.left + 0.3
        y_top, y_bot = top - 0.75, bottom + axis_h          # room above the tree for the ancestor note
        age_max = root[0] * 1.08
        X = lambda age: x_today - (x_today - x_root) * age / age_max
        ys = {n: y_top - (y_top - y_bot) * k / max(len(leaves) - 1, 1) for k, n in enumerate(leaves)}

        branches = []        # (parent age, child) edges with geometry, in drawing order
        def layout(n):
            if isinstance(n, str):
                return ys[n]
            yc = [layout(c) for c in n[1]]
            y = sum(yc) / len(yc)
            n_y[id(n)] = y
            return y
        n_y = {}
        layout(root)

        def contains(n, leaf):
            return n == leaf if isinstance(n, str) else any(contains(c, leaf) for c in n[1])

        def build_edges(n, parent_age):
            if isinstance(n, str):
                return
            age = n[0]
            x = X(age)
            y0 = min(ys[l] if isinstance(l, str) else n_y[id(l)] for l in n[1])
            y1 = max(ys[l] if isinstance(l, str) else n_y[id(l)] for l in n[1])
            vert = Line([x, y0, 0], [x, y1, 0])
            node = Circle(radius=0.07).set_fill(pal["warm"], 1).set_stroke(width=0).move_to([x, n_y[id(n)], 0])
            kids = []
            for c in n[1]:
                cy = ys[c] if isinstance(c, str) else n_y[id(c)]
                cx = x_today if isinstance(c, str) else X(c[0])
                kids.append((Line([x, cy, 0], [cx, cy, 0]), c))
            branches.append((age, n, vert, node, kids))
            for c in n[1]:
                build_edges(c, age)
        build_edges(root, None)
        stem = Line([x_root - 0.15, n_y[id(root)], 0], [X(root[0]), n_y[id(root)], 0])

        on_path = lambda n: p.focus in leaves and contains(n, p.focus)
        def style(line, n_or_leaf):
            return line.set_stroke(hi if on_path(n_or_leaf) else pal["lavender"], 5 if on_path(n_or_leaf) else 3.5)
        style(stem, root)

        # time axis
        ax = Line([x_root, bottom + 0.45, 0], [x_today, bottom + 0.45, 0]).set_stroke(pal["muted"], 2)
        ticks = VGroup()
        step = {"apes": 5, "vertebrates": 100}[p.tree]
        for a in range(0, int(age_max) + 1, step):
            x = X(a)
            if x < x_root:
                continue
            ticks.add(Line([x, bottom + 0.4, 0], [x, bottom + 0.5, 0]).set_stroke(pal["muted"], 2),
                      sci.text("today" if a == 0 else str(a), 0.26 * ts, pal["muted"]).next_to([x, bottom + 0.4, 0], DOWN, buff=0.08))
        unit = sci.text("million years ago (about)", 0.26 * ts, pal["muted"]).next_to(ax, UP, buff=0.08).align_to(ax, LEFT)
        today = DashedLine([x_today, y_top + 0.15, 0], [x_today, bottom + 0.5, 0], dash_length=0.08).set_stroke(pal["faint"], 2)

        # the whole tree is visible faintly from the first frame; it then grows in colour
        ghost = VGroup(stem.copy(), *[m.copy() for b in branches for m in [b[2], b[3]] + [ln for ln, _ in b[4]]])
        ghost.set_stroke(pal["faint"], 2.5, 0.9).set_fill(opacity=0.25)
        ghost_names = VGroup(*[names[n].copy().set_opacity(0.25).next_to([x_today, ys[n], 0], RIGHT, buff=0.12) for n in leaves])
        scene.add(ax, ticks, unit, today, ghost, ghost_names)
        scene.play(FadeIn(title), FadeIn(cap), Create(stem), run_time=0.3)
        branches.sort(key=lambda b: -b[0])
        grow = max(1.0, clock.left - 1.6)
        per = grow / len(branches)
        for age, n, vert, node, kids in branches:
            style(vert, n)
            for line, c in kids:
                style(line, c)
            leaf_labels = [names[c].next_to(line.get_end(), RIGHT, buff=0.12) for line, c in kids if isinstance(c, str)]
            scene.play(FadeIn(node, scale=0.5), Create(vert), run_time=per * 0.3)
            scene.play(*[Create(line) for line, _ in kids], *[FadeIn(l, shift=LEFT * 0.1) for l in leaf_labels], run_time=per * 0.7)
        # the most recent shared ancestor of the focus species
        target = next((b for b in sorted(branches, key=lambda b: b[0]) if on_path(b[1])), None)
        if target is not None and clock.left > 0.8:
            node = target[3]
            ring = Circle(radius=0.2).move_to(node).set_stroke(hi, 4)
            note = sci.tag(f"shared ancestor · about {target[0]:g} million years ago", hi, pal, 0.3 * ts)
            if note.width > st.sw:
                note.scale_to_fit_width(st.sw)
            note.move_to([min(max(node.get_x(), st.left + note.width / 2), st.right - note.width / 2), top - note.height / 2 - 0.05, 0])
            lead = DashedLine(note.get_bottom(), ring.get_top(), dash_length=0.07).set_stroke(hi, 2)
            scene.play(Create(ring), FadeIn(note), Create(lead), run_time=0.5)
            sci.finish(scene, clock, p.camera, focus=node.get_center())
        else:
            sci.finish(scene, clock, p.camera)
