"""A stick figure walks from one room into another; an idea it carried can fade on the way."""

from __future__ import annotations

import numpy as np
from manim import UP, FadeIn, FadeOut, GrowFromCenter, Rectangle, RoundedRectangle, VGroup, linear

from beatframe.templates.base import Template
from beatframe.templates.kit import (
    INK, PaletteName, Budget, Stick, add_stick, background, bubble, caption_bar, drift_camera, floor_y, fh, fw, icon,
    label, palette, pill,
)


class StickDoorway(Template):
    name = "stick_doorway"
    description = "Stick figure walks through a door from one room to the next; the idea it carried can vanish"
    theme = "bright"
    vertical_width = 8.0

    class Params(Template.Params):
        left_label: str = "kitchen"
        right_label: str = "living room"
        carry: str = "bulb"            # icon above the head before the door (none = nothing)
        forget: bool = True            # after the door the idea fades and a "?" appears
        caption: str = ""
        palette: PaletteName = "auto"

    def build(self, scene, p, duration):
        pal = palette(p.palette, scene.seed)
        W, H = fw(), fh()
        y = floor_y()
        bg = background(pal, floor=True)
        right_wall = Rectangle(width=W / 2 + 0.1, height=H + 0.2).set_stroke(width=0).set_fill(pal["soft"], 1)
        right_wall.move_to([W / 4, 0, 0]).set_z_index(-19)
        door_h = 3.6 * (1.25 if H > W else 1.0)
        frame = RoundedRectangle(width=1.7, height=door_h, corner_radius=0.06).set_stroke("#7B4B2A", 14).set_fill("#FFF8EC", 1)
        frame.move_to([0, y + door_h / 2, 0])
        leaf = RoundedRectangle(width=0.5, height=door_h - 0.1, corner_radius=0.04).set_stroke(width=0).set_fill("#B5835A", 1)
        leaf.next_to(frame, LEFT_DIR(), buff=0).align_to(frame, UP_DIR()).shift(np.array([0.25, -0.05, 0]))
        door = VGroup(frame, leaf).set_z_index(-5)
        ll = pill(p.left_label, pal["a"], 0.42).move_to([-W / 4, y + door_h + 0.75, 0])
        rl = pill(p.right_label, pal["c"], 0.42).move_to([W / 4, y + door_h + 0.75, 0])
        scene.add(bg, right_wall, door)
        b = Budget(duration)
        anims = [FadeIn(ll, shift=UP * 0.2), FadeIn(rl, shift=UP * 0.2)]
        if p.caption:
            anims.append(FadeIn(caption_bar(p.caption, pal), shift=UP * 0.2))
        st = add_stick(scene, Stick(x=-W * 0.36, accent=pal["a"], face="happy"))
        scene.play(*anims, run_time=b.t(0.12, 0.6))

        carried = None
        if p.carry != "none":
            carried = icon(p.carry, 0.85, pal)
            carried.add_updater(lambda m: m.move_to(st.head_top() + UP * 0.65))
            scene.play(GrowFromCenter(carried), run_time=b.t(0.08, 0.4))

        st.walk.set_value(1)
        scene.play(st.x.animate.set_value(W * 0.30), run_time=b.t(0.45, 3.0), rate_func=linear)
        st.walk.set_value(0)

        if carried is not None and p.forget:
            carried.clear_updaters()
            q = bubble(label("?", 0.9, pal["b"]), "thought").move_to(st.head_top() + np.array([0.9, 0.7, 0]))
            if q.get_right()[0] > W / 2 - 0.15:
                q.shift(np.array([W / 2 - 0.15 - q.get_right()[0], 0, 0]))
            st.set_face("confused")
            scene.play(carried.animate.set_opacity(0.0).scale(0.4).shift(UP * 0.6), st.tilt.animate.set_value(0.25),
                       run_time=b.t(0.1, 0.6))
            scene.play(GrowFromCenter(q), run_time=b.t(0.06, 0.35))
        drift_camera(scene, duration)


def LEFT_DIR():
    from manim import LEFT
    return LEFT


def UP_DIR():
    return UP
