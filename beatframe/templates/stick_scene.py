"""A stick figure in a place, doing one thing for the whole beat, with an optional thought bubble and headline.

Every action has an entrance (quick, so the first frame already shows the figure moving) and a loop
that keeps going until the beat ends, so the figure never stands frozen like a picture.
Body actions (touch_nose, cover_ears, pinch_nose...) are the "try it right now" moments.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
from manim import UP, FadeIn, GrowFromCenter, linear, rate_functions

from beatframe.templates.base import Template
from beatframe.templates.kit import (
    DRIFT, PaletteName, Stick, add_stick, background, bubble, caption_bar, floor_y, fw, icon, palette, rest_of, setting,
)

Setting = Literal["plain", "kitchen", "bedroom", "office", "outdoor", "lab", "street", "night"]
Action = Literal["walk_in", "idle", "think", "point", "wave", "freeze", "run", "sleep", "jump", "shrug", "scared",
                 "talk", "look_around", "touch_nose", "cover_ears", "cover_eye", "pinch_nose", "facepalm", "hum", "yawn",
                 "swallow", "breathe", "pinch_elbow", "lick_elbow", "wiggle_fingers"]
Bubble = Literal["none", "question", "exclaim", "bulb", "heart", "zzz", "clock", "brain", "eye", "phone", "apple", "star",
                 "moon", "music"]

FACE_FOR = {"walk_in": "neutral", "idle": "happy", "think": "thinking", "point": "happy", "wave": "happy",
            "freeze": "confused", "run": "scared", "sleep": "sleepy", "jump": "happy", "shrug": "confused", "scared": "scared",
            "talk": "happy", "look_around": "confused", "touch_nose": "surprised", "cover_ears": "scared",
            "cover_eye": "thinking", "pinch_nose": "confused", "facepalm": "sad", "hum": "happy", "yawn": "sleepy",
            "swallow": "thinking", "breathe": "surprised", "pinch_elbow": "happy", "lick_elbow": "confused",
            "wiggle_fingers": "surprised"}
MOVES_IN = ("walk_in", "run", "freeze")          # actions that start mid-stride


class StickScene(Template):
    name = "stick_scene"
    description = ("Bright stick-figure scene: a place, an action that keeps moving all beat (incl. try-it moves: "
                   "touch_nose, cover_ears, pinch_nose…), a thought bubble and an optional headline")
    theme = "bright"
    vertical_width = 8.0

    class Params(Template.Params):
        setting: Setting = "plain"
        action: Action = "walk_in"
        bubble: Bubble = "none"
        caption: str = ""                  # headline at the top (empty = none)
        palette: PaletteName = "auto"

    def build(self, scene, p, duration):
        pal = palette(p.palette, scene.seed)
        scene.add(background(pal, floor=p.setting not in ("night",)), setting(p.setting, pal))
        W = fw()
        home = -W * 0.08
        # on screen from the first frame (mid-stride when it walks in): an empty first second loses viewers
        start = home - W * 0.3 if p.action in MOVES_IN else home
        st = add_stick(scene, Stick(x=start, accent=pal["a"], face=FACE_FOR[p.action]))
        intro = [FadeIn(caption_bar(p.caption, pal), shift=UP * 0.2)] if p.caption else []

        self._enter(scene, st, p.action, intro, duration, W, home)

        if p.bubble != "none":
            top = st.head_top()
            b = bubble(icon(p.bubble, 0.9 * (1.15 if W < 9 else 1), pal), "thought")
            b.move_to(top + np.array([1.15, 0.85, 0]))
            if b.get_right()[0] > W / 2 - 0.2:
                b.shift(np.array([-(b.get_right()[0] - (W / 2 - 0.2)), 0, 0]))
            scene.play(GrowFromCenter(b), run_time=0.35)

        self._loop(scene, st, p.action, duration, W, pal)

    # -- entrance: the first move, quick -----------------------------------------------
    def _enter(self, scene, st, a, intro, duration, W, home):
        def play(*anims, t=0.45, **kw):
            scene.play(*anims, *intro, run_time=t, **kw)

        if a in ("walk_in", "freeze"):
            st.walk.set_value(1)
            play(st.x.animate.set_value(home), t=min(1.2, duration * 0.3), rate_func=linear)
            st.walk.set_value(0)
            if a == "freeze":
                st.set_face("confused")
                scene.play(st.tilt.animate.set_value(0.25), st.arm_l.animate.set_value(-0.5), run_time=0.3)
        elif a == "run":
            st.walk.set_value(1.6)
            play(st.x.animate.set_value(W * 0.18), st.arm_r.animate.set_value(0.9), t=min(1.0, duration * 0.3),
                 rate_func=rate_functions.ease_out_sine)
        elif a == "think":
            play(st.reach("r", "chin"), st.tilt.animate.set_value(-0.15), st.arm_l.animate.set_value(0.35), t=0.45)
        elif a == "point":
            play(st.arm_r.animate.set_value(1.65), st.elbow_r.animate.set_value(0.0), t=0.4)
        elif a == "wave":
            play(st.arm_r.animate.set_value(1.9), st.elbow_r.animate.set_value(1.0), t=0.35)
        elif a == "sleep":
            play(st.tilt.animate.set_value(0.45), st.arm_l.animate.set_value(-0.05), st.arm_r.animate.set_value(0.05), t=0.5)
        elif a == "jump":
            play(st.jump.animate(rate_func=rate_functions.there_and_back).set_value(0.9),
                 st.arm_l.animate.set_value(-2.6), st.arm_r.animate.set_value(2.6), t=0.55)
        elif a == "shrug":
            play(st.arm_l.animate.set_value(-1.35), st.arm_r.animate.set_value(1.35),
                 st.elbow_l.animate.set_value(-1.2), st.elbow_r.animate.set_value(-1.2), st.tilt.animate.set_value(0.18), t=0.4)
        elif a == "scared":
            play(st.arm_l.animate.set_value(-2.3), st.arm_r.animate.set_value(2.3), st.tremble.animate.set_value(1.0), t=0.3)
        elif a == "talk":
            play(st.talk.animate.set_value(1.0), st.arm_r.animate.set_value(0.9), st.elbow_r.animate.set_value(1.1), t=0.3)
        elif a == "look_around":
            play(st.tilt.animate.set_value(0.2), t=0.3)
        elif a in ("touch_nose", "cover_eye", "facepalm"):
            part = {"touch_nose": "nose", "cover_eye": "eye", "facepalm": "forehead"}[a]
            play(st.reach("r", part), st.tilt.animate.set_value(0.1 if a == "facepalm" else 0.0), t=0.45)
        elif a == "cover_ears":
            play(st.reach("r", "ear"), st.reach("l", "ear_back"), st.tremble.animate.set_value(0.4), t=0.4)
        elif a == "pinch_nose":
            play(st.reach("r", "nose"), t=0.45)
        elif a == "hum":
            play(st.talk.animate.set_value(0.35), st.tilt.animate.set_value(-0.1), t=0.3)
        elif a == "yawn":
            play(st.arm_l.animate.set_value(-2.8), st.arm_r.animate.set_value(2.8), st.talk.animate.set_value(0.5), t=0.6)
        elif a == "swallow":
            play(st.reach("r", "throat"), t=0.4)
        elif a == "breathe":
            play(st.reach("r", "chest"), st.breath.animate.set_value(1.0), t=0.6)
        elif a == "pinch_elbow":                      # left arm bent to show its elbow, right hand pinches it
            play(st.arm_l.animate.set_value(1.2), st.elbow_l.animate.set_value(1.6), st.reach("r", "elbow_other"), t=0.5)
        elif a == "lick_elbow":                       # folds the arm up and strains toward the elbow, tongue out
            play(st.arm_l.animate.set_value(2.35), st.elbow_l.animate.set_value(-2.5), st.tongue.animate.set_value(1.0),
                 st.tilt.animate.set_value(0.3), t=0.5)
        elif a == "wiggle_fingers":
            play(st.arm_r.animate.set_value(1.9), st.elbow_r.animate.set_value(0.55), st.fingers.animate.set_value(1.0), t=0.4)
        elif intro:                                   # "idle": nothing to do but the headline
            scene.play(*intro, run_time=0.3)

    # -- loop: keep moving until the beat ends -------------------------------------------
    def _loop(self, scene, st, a, duration, W, pal):
        rest = rest_of(scene, duration)
        if rest <= 0.2:
            return
        total, left = rest, rest
        notes = []

        def step(anims, t, _rate=None):
            """One loop move of t seconds, with the slow camera push continuing underneath."""
            nonlocal left
            t = min(t, left)
            if t <= 0.05:
                return False
            cam = scene.camera.frame.animate(rate_func=linear).scale(DRIFT ** (t / total))
            scene.play(*anims, cam, run_time=t)
            left -= t
            return left > 0.05

        k = 0
        while left > 0.05:
            k += 1
            if a == "walk_in":            # turns to face the viewer side and back, looks around
                go = step([st.tilt.animate.set_value(0.12 * (-1) ** k), st.arm_r.animate.set_value(0.18 + 0.15 * (k % 2))], 1.1)
            elif a == "run":             # keeps running on the spot, panting
                st.walk.set_value(1.6)
                go = step([st.arm_r.animate.set_value(0.6 + 0.5 * (k % 2)), st.tilt.animate.set_value(0.1 * (-1) ** k)], 0.5, linear)
            elif a == "think":           # taps the chin, eyes wander
                go = step([st.tilt.animate.set_value(-0.15 + 0.14 * (k % 2)), st.arm_l.animate.set_value(0.35 - 0.2 * (k % 2))], 0.7)
            elif a == "point":           # jabs forward
                go = step([st.arm_r.animate.set_value(1.65 + 0.18 * (k % 2)), st.elbow_r.animate.set_value(0.25 * (k % 2))], 0.4)
            elif a == "wave":
                go = step([st.arm_r.animate.set_value(1.9 + 0.15 * (k % 2)), st.elbow_r.animate.set_value(1.0 - 0.55 * (k % 2))], 0.28)
            elif a == "freeze":          # small startled shivers
                go = step([st.tremble.animate.set_value(0.35 * (k % 2)), st.tilt.animate.set_value(0.25 - 0.08 * (k % 2))], 0.5)
            elif a == "sleep":           # slow deep breaths, a Z rises
                if k == 1:
                    st.life.set_value(0.0)
                    z = icon("zzz", 0.7, pal).move_to(st.head_top() + np.array([0.7, 0.3, 0]))
                    notes.append(z)
                    go = step([FadeIn(z, shift=UP * 0.4), st.jump.animate.set_value(0.03)], 1.0)
                else:
                    go = step([st.jump.animate.set_value(0.03 * (k % 2)), notes[0].animate.shift(UP * 0.15)], 1.0)
            elif a == "jump":
                go = step([st.jump.animate(rate_func=rate_functions.there_and_back).set_value(0.75),
                           st.arm_l.animate.set_value(-2.6 + 0.3 * (k % 2)), st.arm_r.animate.set_value(2.6 - 0.3 * (k % 2))], 0.55, linear)
            elif a == "shrug":
                go = step([st.arm_l.animate.set_value(-1.35 + 0.45 * (k % 2)), st.arm_r.animate.set_value(1.35 - 0.45 * (k % 2)),
                           st.tilt.animate.set_value(0.18 * (-1) ** k)], 0.6)
            elif a == "scared":          # trembles, steps back
                go = step([st.x.animate.shift(np.array([-0.08 * W / 8, 0, 0])), st.tilt.animate.set_value(0.12 * (-1) ** k)], 0.6)
            elif a == "talk":            # gestures while talking
                go = step([st.arm_r.animate.set_value(0.9 + 0.6 * (k % 2)), st.elbow_r.animate.set_value(1.1 - 0.5 * (k % 2)),
                           st.arm_l.animate.set_value(-0.18 - 0.3 * ((k + 1) % 2)), st.tilt.animate.set_value(0.08 * (-1) ** k)], 0.5)
            elif a == "look_around":     # looks one way, then the other
                go = step([st.facing.animate.set_value((-1) ** k), st.tilt.animate.set_value(0.2 * (-1) ** k)], 0.7)
            elif a == "touch_nose":      # taps the nose
                go = step([st.reach_r.animate.set_value(1.0 - 0.12 * (k % 2)), st.tilt.animate.set_value(-0.06 * (k % 2))], 0.35)
            elif a == "cover_ears":      # presses the ears, shakes a little
                go = step([st.tilt.animate.set_value(0.1 * (-1) ** k), st.reach_l.animate.set_value(1.0 - 0.15 * (k % 2))], 0.45)
            elif a == "cover_eye":       # peeks around with the other eye
                go = step([st.tilt.animate.set_value(0.15 * (-1) ** k)], 0.7)
            elif a == "facepalm":
                go = step([st.tilt.animate.set_value(0.1 + 0.12 * (k % 2))], 0.6)
            elif a in ("pinch_nose", "hum"):     # music notes rise (hum); with the nose pinched they stop short
                note = icon("music", 0.45, pal).move_to(st.head_center() + np.array([0.55, 0.1, 0]))
                rise = 0.25 if a == "pinch_nose" else 1.0
                anims = [FadeIn(note, shift=UP * 0.3 * rise, scale=0.6), st.tilt.animate.set_value(-0.1 + 0.08 * (k % 2))]
                if notes:
                    anims.append(notes[-1].animate.shift(UP * 0.5 * rise).set_opacity(0.0))
                notes.append(note)
                go = step(anims, 0.55)
            elif a == "yawn":
                go = step([st.arm_l.animate.set_value(-2.8 + 0.4 * (k % 2)), st.arm_r.animate.set_value(2.8 - 0.4 * (k % 2)),
                           st.talk.animate.set_value(0.5 * ((k + 1) % 2))], 0.8)
            elif a == "swallow":         # gulp after gulp
                st.gulp.set_value(0.0)
                go = step([st.gulp.animate.set_value(1.0), st.tilt.animate.set_value(0.08 * (k % 2))], 0.8)
            elif a == "breathe":         # slow, deep, conscious breaths
                go = step([st.breath.animate.set_value(0.0 if k % 2 else 1.0)], 1.2)
            elif a == "pinch_elbow":     # pinches and pulls, feels nothing
                go = step([st.reach_r.animate.set_value(1.0 - 0.15 * (k % 2)), st.arm_l.animate.set_value(1.2 + 0.08 * (k % 2)),
                           st.tilt.animate.set_value(0.1 * (-1) ** k)], 0.5)
            elif a == "lick_elbow":      # strains, never gets there
                go = step([st.arm_l.animate.set_value(2.35 + 0.12 * (k % 2)), st.tilt.animate.set_value(0.3 + 0.1 * (k % 2)),
                           st.tremble.animate.set_value(0.3 * (k % 2))], 0.5)
            elif a == "wiggle_fingers":  # the fingers move by themselves; the forearm twitches with them
                go = step([st.elbow_r.animate.set_value(0.55 + 0.08 * (k % 2)), st.tilt.animate.set_value(-0.1 + 0.05 * (k % 2))], 0.5)
            else:                        # idle: shifts weight
                go = step([st.arm_r.animate.set_value(0.18 + 0.2 * (k % 2)), st.tilt.animate.set_value(0.08 * (-1) ** k)], 1.0)
            if not go:
                break
