"""A spoken line shown as large text, one key word lit in ember."""

import re
import textwrap

from manim import BOLD, DOWN, UP, AnimationGroup, FadeIn, Text, VGroup, linear

from beatframe import brand
from beatframe.templates.base import Template


class Statement(Template):
    name = "statement"
    description = "Large statement, words arrive one by one, one keyword glows"

    class Params(Template.Params):
        text: str = "Not your phone. Not this screen."
        highlight: str = ""        # word to light up (case-insensitive)
        max_chars: int = 20        # wrap width per line

    def build(self, scene, p, duration):
        # one sentence per block, then wrap each block
        sentences = [s for s in re.split(r"(?<=[.!?])\s+", p.text.strip()) if s]
        lines = []
        for s in sentences:
            lines += textwrap.wrap(s, p.max_chars)

        rows, words_all = VGroup(), []
        for line in lines:
            row = VGroup()
            for w in line.split():
                hot = p.highlight and w.strip(".,!?;:'\"").lower() == p.highlight.lower()
                t = Text(w, font=brand.SERIF, weight=BOLD, color=brand.EMBER if hot else brand.PAPER).scale(1.15)
                row.add(t)
                words_all.append(t)
            row.arrange(buff=0.28, aligned_edge=DOWN)
            rows.add(row)
        rows.arrange(DOWN, buff=0.45)
        if rows.width > 12.4:
            rows.scale_to_fit_width(12.4)
        if rows.height > 6.4:
            rows.scale_to_fit_height(6.4)

        reveal = min(duration * 0.55, 0.22 * len(words_all) + 0.4)
        scene.play(
            AnimationGroup(*[FadeIn(w, shift=UP * 0.15) for w in words_all], lag_ratio=0.6),
            run_time=reveal,
        )
        rest = duration - getattr(scene.renderer, "time", 0)
        if rest > 0.2:
            scene.play(scene.camera.frame.animate.scale(0.95), run_time=rest, rate_func=linear)
