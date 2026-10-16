"""A spoken line shown as large text, one key word lit in ember."""

import re
import textwrap

import numpy as np
from manim import BOLD, DOWN, UP, AnimationGroup, Circle, Dot, FadeIn, Text, VGroup, linear

from beatframe import brand
from beatframe.templates.kit import DRIFT
from beatframe.templates.base import Template, frame_h, frame_w, soft_glow, width_ratio


def _motif(kind: str) -> VGroup | None:
    """Quiet moving background so text beats don't feel like slides."""
    if kind == "orb":
        g = soft_glow(3.4, brand.EMBER, layers=10, strength=0.03)
        g.t = 0.0
        g.k = 1.0

        def breathe(m, dt):
            m.t += dt
            k = 1 + 0.08 * np.sin(m.t * 1.3)
            m.scale(k / m.k)
            m.k = k
        g.add_updater(breathe)
        return g
    if kind == "rings":
        rings = VGroup(*[Circle(radius=1).set_stroke(brand.GLOW, 1.5, 0) for _ in range(5)])
        rings.t = 0.0

        def grow(m, dt):
            m.t += dt
            for i, c in enumerate(m):
                ph = (m.t * 0.22 + i / len(m)) % 1.0
                c.set(width=2 * (0.5 + 7.5 * ph)).move_to([0, 0, 0])
                c.set_stroke(opacity=0.22 * (1 - ph))
        rings.add_updater(grow)
        return rings
    if kind == "particles":
        rng = np.random.default_rng(11)
        half_w, half_h = 7.5 * width_ratio(), 4.5 * frame_h() / 8   # 7.5 x 4.5 in a 16:9 frame
        dots = VGroup()
        for _ in range(70):
            d = Dot([rng.uniform(-half_w, half_w), rng.uniform(-half_h, half_h), 0], radius=rng.uniform(0.015, 0.04),
                    color=brand.GLOW).set_opacity(rng.uniform(0.15, 0.5))
            d.v = rng.uniform(0.15, 0.45)
            dots.add(d)

        def drift(m, dt):
            for d in m:
                d.shift(UP * d.v * dt)
                if d.get_y() > half_h:
                    d.shift(DOWN * 2 * half_h)
        dots.add_updater(drift)
        return dots
    return None


class Statement(Template):
    name = "statement"
    description = "Large statement, words arrive one by one, one keyword glows"
    vertical_width = 8.0

    class Params(Template.Params):
        text: str = "Not your phone. Not this screen."
        highlight: str = ""        # word to light up (case-insensitive)
        max_chars: int = 20        # wrap width per line (16:9; narrower frames wrap shorter)
        motif: str = "none"        # none | orb | rings | particles  (quiet moving background)

    def build(self, scene, p, duration):
        # one sentence per block, then wrap each block
        sentences = [s for s in re.split(r"(?<=[.!?])\s+", p.text.strip()) if s]
        wrap = max(8, round(p.max_chars * width_ratio() ** 0.6))
        lines = []
        for s in sentences:
            lines += textwrap.wrap(s, wrap)

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
        max_w, max_h = frame_w() * 0.872, frame_h() * 0.8   # 12.4 x 6.4 in a 16:9 frame
        if rows.width > max_w:
            rows.scale_to_fit_width(max_w)
        if rows.height > max_h:
            rows.scale_to_fit_height(max_h)

        bg = _motif(p.motif)
        if bg is not None:
            scene.add(bg)
        reveal = min(duration * 0.55, 0.22 * len(words_all) + 0.4)
        scene.play(
            AnimationGroup(*[FadeIn(w, shift=UP * 0.15) for w in words_all], lag_ratio=0.6),
            run_time=reveal,
        )
        rest = duration - getattr(scene.renderer, "time", 0)
        if rest > 0.2:
            scene.play(scene.camera.frame.animate.scale(DRIFT), run_time=rest, rate_func=linear)
