"""Two stick figures talking: lines appear in speech bubbles, alternating speakers."""

from __future__ import annotations

import numpy as np
from manim import UP, FadeIn, FadeOut, GrowFromPoint

from beatframe.templates.base import Template
from beatframe.templates.kit import (
    PaletteName, Budget, Stick, add_stick, background, bubble, drift_camera, fw, palette, setting, wrap_label, vertical,
)


class StickTalk(Template):
    name = "stick_talk"
    description = "Two stick figures in conversation; each line pops up in a speech bubble"
    theme = "bright"
    vertical_width = 8.0

    class Params(Template.Params):
        lines: list[str] = ["Why did I come in here?", "Your brain closed the chapter."]
        setting: str = "plain"         # plain | kitchen | bedroom | office | outdoor | lab | street
        palette: PaletteName = "auto"

    def build(self, scene, p, duration):
        pal = palette(p.palette, scene.seed)
        scene.add(background(pal), setting(p.setting if p.setting != "office" else "plain", pal))
        W = fw()
        b = Budget(duration)
        xa, xb = -W * 0.27, W * 0.27
        a = add_stick(scene, Stick(x=xa, accent=pal["a"], face="happy", facing=1))
        c = add_stick(scene, Stick(x=xb, accent=pal["c"], face="neutral", facing=-1))
        lines = p.lines[:6] or ["…"]
        per = max(0.6, (duration * 0.85) / len(lines))
        shown = None
        for i, text in enumerate(lines):
            who, other = (a, c) if i % 2 == 0 else (c, a)
            t = wrap_label(text, 0.48 if vertical() else 0.46, chars=16 if vertical() else 24, max_width=W * 0.55)
            bub = bubble(t, "speech", pad=0.28)
            top = who.head_top()
            bub.move_to(top + np.array([(0.9 if i % 2 == 0 else -0.9), 0.35 + bub.height / 2, 0]))
            dx = min(0, W / 2 - 0.2 - bub.get_right()[0]) + max(0, -W / 2 + 0.2 - bub.get_left()[0])
            bub.shift(np.array([dx, 0, 0]))
            who.set_face("happy" if i % 2 == 0 else "surprised" if i == 1 else "thinking")
            # the speaker's mouth moves and their hand gestures; the listener goes quiet
            anims = [GrowFromPoint(bub, top), who.arm_r.animate.set_value(1.3), who.elbow_r.animate.set_value(0.9),
                     who.talk.animate.set_value(1.0), other.talk.animate.set_value(0.0),
                     other.arm_r.animate.set_value(0.2), other.elbow_r.animate.set_value(0.22)]
            if shown is not None:
                anims.append(FadeOut(shown))
            t_in = min(0.45, per * 0.4)
            scene.play(*anims, run_time=t_in)
            hold = max(0.05, per - t_in) if i < len(lines) - 1 else 0.05
            if hold > 0.3:                      # a second gesture while the line is "spoken"
                scene.play(who.arm_r.animate.set_value(0.8), who.elbow_r.animate.set_value(1.4),
                           other.tilt.animate.set_value(0.1 * (-1) ** i), run_time=hold)
            else:
                scene.wait(hold)
            shown = bub
        a.talk.set_value(0.0)
        c.talk.set_value(0.0)
        drift_camera(scene, duration)
