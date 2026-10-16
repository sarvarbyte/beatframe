"""Two cases side by side (stacked in a tall frame), each with a stick figure, an icon and a verdict."""

from __future__ import annotations

from typing import Literal

import numpy as np
from manim import DOWN, UP, FadeIn, GrowFromCenter, VGroup

from beatframe.templates.base import Template
from beatframe.templates.kit import (
    INK, IconName, PaletteName, Budget, Stick, add_stick, card, caption_bar, drift_camera, fh, flat_bg, fw, icon,
    label, palette, vertical,
)

Result = Literal["none", "check", "cross"]


class StickCompare(Template):
    name = "stick_compare"
    description = "Two cases compared (A vs B): stick figure, icon and a check/cross verdict for each"
    theme = "bright"
    vertical_width = 8.0

    class Params(Template.Params):
        title: str = ""
        left_label: str = "through a door"
        right_label: str = "same room"
        left_icon: IconName = "question"
        right_icon: IconName = "bulb"
        left_result: Result = "cross"
        right_result: Result = "check"
        palette: PaletteName = "auto"

    def build(self, scene, p, duration):
        pal = palette(p.palette, scene.seed)
        flat_bg(scene, pal)
        W, H = fw(), fh()
        b = Budget(duration)
        tall = vertical()
        top_room = 1.6 if p.title else 0.4
        if tall:
            cw, ch = W * 0.84, (H - top_room - 2.2) / 2
            centers = [np.array([0, ch / 2 + 0.25 - top_room / 2, 0]), np.array([0, -ch / 2 - 0.25 - top_room / 2, 0])]
        else:
            cw, ch = W * 0.42, H * 0.70 - (0.4 if p.title else 0)
            centers = [np.array([-W * 0.235, -0.35 if p.title else 0, 0]), np.array([W * 0.235, -0.35 if p.title else 0, 0])]
        if p.title:
            scene.play(FadeIn(caption_bar(p.title, pal), shift=UP * 0.2), run_time=b.t(0.08, 0.5))

        panels = []
        for k, (c, lab, ic, res, col) in enumerate(zip(centers, (p.left_label, p.right_label), (p.left_icon, p.right_icon),
                                                        (p.left_result, p.right_result), (pal["a"], pal["c"]))):
            box = card(cw, ch, "#FFFFFF").move_to(c)
            head = label(lab.upper(), 0.42, col, max_width=cw * 0.85).next_to(box[-1].get_top(), DOWN, buff=0.3)
            s = min(0.75, ch / 4.6)
            stx = c[0] - cw * 0.18
            st = Stick(x=stx, y=c[1] - ch / 2 + 0.35, s=s, accent=col, face="neutral")
            ico = icon(ic, min(1.1, ch * 0.28), pal).move_to([c[0] + cw * 0.2, c[1] - ch * 0.05, 0])
            badge = icon(res, min(0.9, ch * 0.22), pal).move_to([c[0] + cw * 0.36, c[1] + ch / 2 - 0.45, 0]) if res != "none" else None
            panels.append((box, head, st, ico, badge, res))

        for box, head, st, ico, badge, res in panels:
            scene.play(FadeIn(box, shift=UP * 0.3), FadeIn(head), run_time=b.t(0.07, 0.4))
            add_stick(scene, st)
            scene.play(GrowFromCenter(ico), st.arm_r.animate.set_value(1.6), run_time=b.t(0.07, 0.4))
        for box, head, st, ico, badge, res in panels:
            if badge is not None:
                st.set_face("happy" if res == "check" else "confused")
                scene.play(GrowFromCenter(badge), run_time=b.t(0.06, 0.35))
        drift_camera(scene, duration)
