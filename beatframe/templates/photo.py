"""A full-frame picture (AI-generated or a photo) with a slow Ken Burns move and an optional caption.

    - text: "In 1953, one man lost the ability to make new memories."
      scene: photo
      params:
        image: images/beat_007.png        # in the project folder
        prompt: "1950s hospital room, a man sitting by a window, cinematic, soft light"
        move: in                          # auto | in | out | left | right | up
        caption: "Patient H.M., 1953"

`beatframe image-prompts project.yaml` lists every picture still to make with its prompt and file name.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal

from manim import DOWN, LEFT, RIGHT, UP, FadeIn, ImageMobject, Rectangle, Text, VGroup, linear

from beatframe import brand
from beatframe.templates.base import Template, fit, frame_h, frame_w

MOVES = ["in", "out", "left", "right", "up"]


class Photo(Template):
    name = "photo"
    description = "Full-frame picture with a slow Ken Burns move (zoom/pan) and an optional caption"
    vertical_width = 8.0

    class Params(Template.Params):
        image: str = ""
        prompt: str = ""              # what to generate (used by `beatframe image-prompts`, not drawn)
        move: Literal["auto", "in", "out", "left", "right", "up"] = "auto"
        caption: str = ""
        darken: float = 0.25          # 0..0.8, so captions and dust stay readable

    def build(self, scene, p, duration):
        w, h = frame_w(), frame_h()
        path = Path(p.image)
        if not p.image or not path.exists():
            # a clear placeholder, so a missing picture is obvious in the preview
            frame = Rectangle(width=w * 0.8, height=h * 0.62).set_stroke(brand.DIM, 3)
            title = Text("Picture missing", font=brand.SANS, color=brand.GLOW).scale(0.9)
            name = Text(Path(p.image).name if p.image else "(no image set)", font=brand.SANS, color=brand.PAPER).scale(0.6)
            hint = Text("Script tab → Pictures to make", font=brand.SANS, color=brand.DIM).scale(0.45)
            body = VGroup(title, name, hint).arrange(DOWN, buff=0.35)
            fit(body, w * 0.72, h * 0.55)
            scene.add(frame, body.move_to(frame))
            scene.wait(max(0.1, duration - 0.05))
            return

        img = ImageMobject(str(path))
        img.scale(max(w / img.width, h / img.height) * 1.14)      # cover the frame with room to move
        move = p.move
        if move == "auto":           # repeatable per image, so re-renders look the same
            move = MOVES[int(hashlib.md5(p.image.encode()).hexdigest(), 16) % len(MOVES)]
        if move == "out":
            img.scale(1.10)
        elif move == "left":
            img.shift(RIGHT * w * 0.04)
        elif move == "right":
            img.shift(LEFT * w * 0.04)
        elif move == "up":
            img.shift(DOWN * h * 0.04)
        scene.add(img)
        if p.darken > 0:
            shade = Rectangle(width=w * 1.3, height=h * 1.3).set_stroke(width=0)
            shade.set_fill(brand.NIGHT, min(0.8, p.darken))
            scene.add(shade)

        target = {"in": lambda m: m.animate(rate_func=linear).scale(1.10),
                  "out": lambda m: m.animate(rate_func=linear).scale(1 / 1.10),
                  "left": lambda m: m.animate(rate_func=linear).shift(LEFT * w * 0.08),
                  "right": lambda m: m.animate(rate_func=linear).shift(RIGHT * w * 0.08),
                  "up": lambda m: m.animate(rate_func=linear).shift(UP * h * 0.08)}[move]

        anims = [target(img)]
        if p.caption:
            label = fit(Text(p.caption, font=brand.SANS, color=brand.PAPER).scale(0.6), w * 0.85)
            bar = Rectangle(width=label.width + 0.6, height=label.height + 0.35).set_stroke(width=0)
            bar.set_fill(brand.DEEP, 0.75)
            cap = VGroup(bar, label).to_edge(DOWN, buff=h * 0.12)
            share = min(1.0, 0.5 / max(duration, 0.5))           # the caption fades in over ~0.5 s
            anims.append(FadeIn(cap, rate_func=lambda t: min(1.0, t / share)))
        scene.play(*anims, run_time=max(0.1, duration - 0.02))
