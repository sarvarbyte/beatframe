"""A memory is stored as fragments and rebuilt at recall: some details fade, gaps are filled with what
usually fits, and the rebuilt picture can differ from the original. Ends with a before/after.

Accuracy notes (conceptual illustration): recall is reconstructive: the brain re-assembles a memory
from stored elements plus general knowledge (schemas), so details can drop out, be filled in or be
altered (classic work: Bartlett 1932; Loftus & Palmer 1974). How much changes differs from memory to
memory and person to person; many memories stay broadly accurate. The scene shows one example of
what CAN change, and its caption says "can", not "always".
"""

from __future__ import annotations

from typing import Literal

import numpy as np
from manim import (
    DOWN, LEFT, RIGHT, UP, Circle, DashedVMobject, Ellipse, FadeIn, FadeOut, Line, Polygon, Rectangle,
    RoundedRectangle, Transform, VGroup, rate_functions,
)
from pydantic import Field

from beatframe.templates import sci
from beatframe.templates.sci import SciParams, Stage


# ---- picture elements (drawn in a 6 x 4 'photo'; each is one fragment) -----------------------------------
def _sun(pal):
    return VGroup(Circle(radius=0.38).set_fill(pal["peach"], 1).set_stroke(width=0),
                  *[Line(np.array([np.cos(a), np.sin(a), 0]) * 0.52, np.array([np.cos(a), np.sin(a), 0]) * 0.72).set_stroke(pal["peach"], 4)
                    for a in np.linspace(0, 2 * np.pi, 9)[:-1]])


def _tree(pal, color=None):
    c = color or pal["mint"]
    return VGroup(Rectangle(width=0.18, height=0.8).set_fill("#8A6A55", 1).set_stroke(width=0).shift(DOWN * 0.55),
                  Circle(radius=0.5).set_fill(c, 1).set_stroke(width=0).shift(UP * 0.15),
                  Circle(radius=0.36).set_fill(c, 1).set_stroke(width=0).shift(UP * 0.0 + LEFT * 0.35),
                  Circle(radius=0.36).set_fill(c, 1).set_stroke(width=0).shift(UP * 0.0 + RIGHT * 0.35))


def _pine(pal, color=None):
    c = color or pal["mint"]
    return VGroup(Rectangle(width=0.16, height=0.4).set_fill("#8A6A55", 1).set_stroke(width=0).shift(DOWN * 0.75),
                  *[Polygon([-0.55 + 0.12 * k, -0.55 + 0.38 * k, 0], [0.55 - 0.12 * k, -0.55 + 0.38 * k, 0], [0, 0.05 + 0.38 * k, 0])
                    .set_fill(c, 1).set_stroke(width=0) for k in range(3)])


def _person(pal, color):
    return VGroup(Circle(radius=0.17).set_fill(pal["warm"], 1).set_stroke(width=0).shift(UP * 0.42),
                  RoundedRectangle(width=0.42, height=0.62, corner_radius=0.18).set_fill(color, 1).set_stroke(width=0),
                  Line(DOWN * 0.3 + LEFT * 0.1, DOWN * 0.7 + LEFT * 0.12).set_stroke(pal["ink"] if not pal["dark"] else "#3B355F", 6),
                  Line(DOWN * 0.3 + RIGHT * 0.1, DOWN * 0.7 + RIGHT * 0.12).set_stroke(pal["ink"] if not pal["dark"] else "#3B355F", 6))


def _balloon(pal, color):
    return VGroup(Ellipse(width=0.42, height=0.52).set_fill(color, 1).set_stroke(width=0),
                  Line(DOWN * 0.26, DOWN * 1.0 + RIGHT * 0.08).set_stroke(pal["muted"], 2))


def _bench(pal):
    return VGroup(Rectangle(width=1.1, height=0.12).set_fill("#B98A6A", 1).set_stroke(width=0),
                  Rectangle(width=1.1, height=0.1).set_fill("#B98A6A", 1).set_stroke(width=0).shift(UP * 0.28),
                  *[Rectangle(width=0.08, height=0.32).set_fill("#8A6A55", 1).set_stroke(width=0).shift(DOWN * 0.2 + RIGHT * dx) for dx in (-0.45, 0.45)])


def _cloud(pal):
    return VGroup(*[Circle(radius=r).set_fill(pal["warm"], 0.9).set_stroke(width=0).shift(RIGHT * dx + UP * dy)
                    for r, dx, dy in ((0.26, -0.3, 0), (0.34, 0.05, 0.1), (0.24, 0.38, -0.02))])


def _dog(pal, color):
    body = Ellipse(width=0.6, height=0.3).set_fill(color, 1).set_stroke(width=0)
    head = Circle(radius=0.15).set_fill(color, 1).set_stroke(width=0).move_to(body.get_right() + UP * 0.12)
    ear = Ellipse(width=0.1, height=0.18).set_fill(pal["ink"] if not pal["dark"] else "#3B355F", 1).set_stroke(width=0).move_to(head.get_top() + LEFT * 0.04)
    legs = VGroup(*[Line(body.get_bottom() + RIGHT * dx, body.get_bottom() + RIGHT * dx + DOWN * 0.18) for dx in (-0.2, -0.08, 0.1, 0.2)]).set_stroke(color, 5)
    tail = Line(body.get_left(), body.get_left() + LEFT * 0.15 + UP * 0.15).set_stroke(color, 4)
    return VGroup(legs, tail, body, head, ear)


SCENES = {
    # name -> list of (key, factory(pal) -> mobject, position in the 6x4 photo)
    "park": lambda pal: [("sun", _sun(pal), (2.1, 1.25)), ("cloud", _cloud(pal), (-1.2, 1.35)),
                         ("tree", _tree(pal), (-2.1, -0.1)), ("bench", _bench(pal), (0.1, -1.05)),
                         ("person", _person(pal, pal["sky"]), (1.05, -0.85)), ("balloon", _balloon(pal, pal["coral"]), (1.55, 0.2)),
                         ("dog", _dog(pal, pal["peach"]), (-0.95, -1.35))],
    "beach": lambda pal: [("sun", _sun(pal), (-2.0, 1.2)), ("cloud", _cloud(pal), (1.4, 1.3)),
                          ("person", _person(pal, pal["coral"]), (-0.4, -0.9)), ("balloon", _balloon(pal, pal["lavender"]), (0.1, 0.25)),
                          ("dog", _dog(pal, pal["warm"]), (1.4, -1.35)), ("tree", _pine(pal), (2.3, -0.3)),
                          ("bench", _bench(pal), (-1.9, -1.1))],
}

# what recall does to some elements: (key, kind, change)
EDITS = {
    "park": [("dog", "lost", None), ("tree", "filled", "pine"), ("balloon", "changed", "lavender")],
    "beach": [("bench", "lost", None), ("tree", "filled", "round"), ("person", "changed", "sky")],
}


class MemoryReconstruction(sci.Template):
    name = "memory_reconstruction"
    description = "A memory breaks into fragments and is rebuilt at recall: lost details, filled gaps, changes"
    category = "Neuroscience"
    theme = "bright"
    vertical_width = 8.0

    class Params(SciParams):
        scene: Literal["park", "beach"] = "park"
        changes: int = Field(3, ge=1, le=3)       # how many details differ after recall (lost, filled in, changed)
        before_after: bool = True
        original_label: str = "what happened"
        recalled_label: str = "what you remember"
        caption: str = "Each recall rebuilds the memory, and details can change"

    def build(self, scene, p, duration):
        st, pal = Stage(), sci.pal_of(p)
        hi = sci.hi_of(p, pal)
        clock = sci.Clock(scene, duration, p.speed)
        sci.guard(scene, duration)
        sci.background(scene, pal, st, seed=17)
        ts = p.text_size
        title = sci.headline(p.title, st, pal, ts)
        top, bottom = st.content(bool(p.title))
        cap = sci.wrapped(p.caption, 0.42 * ts, pal["muted"], 30 if st.v else 64, st.sw * 0.92) if p.caption else VGroup()
        bottom += st.place_caption(cap)

        items = SCENES[p.scene](pal)
        edits = EDITS[p.scene][: p.changes]

        def photo(elements):
            frame = RoundedRectangle(width=6.4, height=4.4, corner_radius=0.25).set_stroke(pal["warm"], 6).set_fill(pal["bottom"], 1)
            sky = RoundedRectangle(width=6.3, height=4.3, corner_radius=0.22).set_stroke(width=0)
            sky.set_fill(color=[pal["sky"], pal["panel"]], opacity=0.35).set_sheen_direction(DOWN)
            ground = Rectangle(width=6.3, height=1.4).set_fill(pal["mint"] if p.scene == "park" else pal["peach"], 0.25).set_stroke(width=0).shift(DOWN * 1.45)
            g = VGroup(frame, sky, ground)
            mob = {}
            for key, m, (x, y) in elements:
                m = m.copy().move_to([x, y, 0])
                mob[key] = m
                g.add(m)
            g.items = mob
            return g

        original = photo(items)
        k = min((top - bottom) * (0.62 if st.v else 0.8) / original.height, st.sw * (0.95 if st.v else 0.7) / original.width)
        original.scale(k).move_to([st.cx, (top + bottom) / 2, 0])
        orig_tag = sci.tag(p.original_label, pal["sky"], pal, 0.3 * ts).next_to(original, UP, buff=0.18)

        # ---- 1. the event (in place from the first frame)
        scene.add(original)
        scene.play(FadeIn(title), FadeIn(cap), FadeIn(orig_tag), run_time=0.3)
        scene.wait(min(0.8, clock.t(0.1, 0.3, 0.8)))

        # ---- 2. stored as fragments: each element drifts into its own shard; edited ones fade
        rng = np.random.default_rng(4)
        shards, homes = {}, {}
        for key, m in original.items.items():
            homes[key] = m.get_center()
            pad = max(m.width, m.height) * 0.62 + 0.12 * k
            sh = Polygon(*[np.array([np.cos(a), np.sin(a), 0]) * pad * rng.uniform(0.85, 1.1)
                           for a in np.linspace(0, 2 * np.pi, 7)[:-1] + rng.uniform(0, 1)])
            sh.set_stroke(pal["lavender"], 2, 0.8).set_fill(pal["panel"], 0.65).move_to(m)
            shards[key] = sh
        spread = 1.25
        targets = {key: original.get_center() + (homes[key] - original.get_center()) * spread + rng.uniform(-0.25, 0.25, 3) * [k, k, 0]
                   for key in homes}
        t = clock.t(0.16, 0.6, 1.6)
        lost_keys = [e[0] for e in edits if e[1] in ("lost", "filled")]
        scene.play(FadeOut(original[:3]), FadeOut(orig_tag), *[FadeIn(sh) for sh in shards.values()], run_time=0.4)
        angles = {key: rng.uniform(-0.25, 0.25) for key in homes}
        scene.play(*[VGroup(shards[key], original.items[key]).animate(rate_func=rate_functions.ease_in_out_sine).move_to(targets[key])
                     .rotate(angles[key]) for key in homes], run_time=t)
        note = sci.tag("stored as separate pieces", pal["lavender"], pal, 0.3 * ts)
        note.move_to([st.cx, original.get_bottom()[1] - 0.05, 0]) if not st.v else note.move_to([st.cx, original.get_top()[1] + 0.1, 0])
        scene.play(FadeIn(note), *[VGroup(shards[key], original.items[key]).animate.set_opacity(0.12) for key in lost_keys],
                   run_time=clock.t(0.1, 0.4, 0.9))

        # ---- 3. recall: pieces fly home; gaps are filled with what usually fits; a detail changes
        frame2 = photo([])
        frame2.scale(k).move_to(original.get_center())
        frame2.set_z_index(-5)          # the returning pieces stay on top of the new frame
        t = clock.t(0.16, 0.6, 1.5)
        moves = []
        for key in homes:
            if key in lost_keys:
                continue
            moves.append(original.items[key].animate(rate_func=rate_functions.ease_in_out_cubic).rotate(-angles[key]).move_to(homes[key]))
        scene.play(FadeIn(frame2[:3]), FadeOut(note), *[FadeOut(sh) for sh in shards.values()], *moves,
                   *[FadeOut(original.items[key]) for key in lost_keys], run_time=t)
        recalled = {key: original.items[key] for key in homes if key not in lost_keys}
        scene.add(*recalled.values())       # keep them in the scene after their shards were removed
        marks = VGroup()
        new_bits = VGroup()
        for key, kind, change in edits:
            pos = homes[key]
            if kind == "filled":
                filler = (_pine(pal, pal["mint"]) if change == "pine" else _tree(pal, pal["mint"])).scale(k)
                filler.move_to(pos)
                ghost = DashedVMobject(Circle(radius=max(filler.width, filler.height) * 0.62), num_dashes=24).set_stroke(pal["mint"], 3).move_to(pos)
                new_bits.add(filler)
                marks.add(VGroup(ghost, sci.tag("filled in", pal["mint"], pal, 0.24 * ts).next_to(ghost, UP, buff=0.05)))
            elif kind == "changed":
                m = recalled[key]
                col = pal.get(change, hi)
                ring = Circle(radius=max(m.width, m.height) * 0.75).set_stroke(hi, 3).move_to(pos)
                new_bits.add(VGroup())
                marks.add(VGroup(ring, sci.tag("changed", hi, pal, 0.24 * ts).next_to(ring, UP, buff=0.05)))
                fill_target = m[0] if key == "balloon" else m[1]
                scene.play(fill_target.animate.set_fill(col, 1), run_time=0.35)
            else:   # lost: an empty dashed outline where it was
                ghost = DashedVMobject(Circle(radius=0.45 * k), num_dashes=18).set_stroke(pal["muted"], 2.5).move_to(pos)
                marks.add(VGroup(ghost, sci.tag("lost", pal["muted"], pal, 0.24 * ts).next_to(ghost, DOWN, buff=0.05)))
        scene.play(FadeIn(new_bits, scale=0.8), FadeIn(marks), run_time=0.45)
        rec_tag = sci.tag(p.recalled_label, hi, pal, 0.3 * ts).next_to(frame2, UP, buff=0.18)
        scene.play(FadeIn(rec_tag), run_time=0.25)

        recalled_pic = VGroup(frame2, *recalled.values(), new_bits, marks)
        # ---- 4. before / after side by side
        if p.before_after and clock.left > 1.6:
            before = photo(items).scale(k)
            gap = 0.35
            if st.v:
                scale = min(1.0, ((top - bottom) - 1.0) / 2 / before.height, st.sw * 0.95 / before.width)
            else:
                scale = min(1.0, (st.sw - gap) / 2 / before.width * 0.98, (top - bottom - 0.6) / before.height)
            before.scale(scale)
            target_group = VGroup(before.copy(), recalled_pic.copy().scale(scale)).arrange(DOWN if st.v else RIGHT, buff=gap + 0.45)
            target_group.move_to([st.cx, (top + bottom) / 2 - 0.15, 0])
            before.move_to(target_group[0])
            b_tag = sci.tag(p.original_label, pal["sky"], pal, 0.28 * ts).next_to(before, UP, buff=0.12)
            scene.play(VGroup(recalled_pic, rec_tag).animate(rate_func=rate_functions.ease_in_out_sine).scale(scale).move_to(target_group[1].get_center() + UP * 0),
                       run_time=clock.t(0.1, 0.5, 0.9))
            scene.play(rec_tag.animate.next_to(recalled_pic, UP, buff=0.12), FadeIn(before, shift=RIGHT * 0.2 if not st.v else DOWN * 0.2),
                       FadeIn(b_tag), run_time=0.45)
        sci.finish(scene, clock, p.camera)
