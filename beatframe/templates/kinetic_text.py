"""Big bold words that pop in one by one on a bright background; key words sit in colour blocks."""

from __future__ import annotations

from manim import DOWN, UP, FadeIn, RoundedRectangle, VGroup, linear

from beatframe.templates.base import Template
from beatframe.templates.kit import (
    INK, WHITE, PaletteName, Budget, drift_camera, fh, flat_bg, fw, label, palette, vertical,
)


class KineticText(Template):
    name = "kinetic_text"
    description = "Bright kinetic typography: words pop in, highlighted words get colour blocks"
    theme = "bright"
    vertical_width = 8.0

    class Params(Template.Params):
        text: str = "Your brain deletes the old room"
        highlight: str = "deletes, room"     # comma separated words to put in colour blocks
        palette: PaletteName = "auto"

    def build(self, scene, p, duration):
        pal = palette(p.palette, scene.seed)
        flat_bg(scene, pal)
        W, H = fw(), fh()
        b = Budget(duration)
        hot = {w.strip().lower() for w in p.highlight.split(",") if w.strip()}
        colors = [pal["a"], pal["b"], pal["c"], pal["d"]]
        size = 1.05 if vertical() else 1.0
        max_w = W * 0.86
        words, k = [], 0
        for w in p.text.split():
            key = w.strip(".,!?;:'\"").lower()
            if key in hot:
                t = label(w, size, WHITE)
                blk = RoundedRectangle(width=t.width + 0.35, height=t.height + 0.3, corner_radius=0.14).set_stroke(width=0)
                blk.set_fill(colors[k % 4], 1)
                k += 1
                words.append(VGroup(blk, t.move_to(blk)))
            else:
                words.append(VGroup(label(w, size, INK)))
        # greedy line wrap by width
        lines, cur, cur_w = [], [], 0.0
        for m in words:
            add = m.width + (0.3 if cur else 0)
            if cur and cur_w + add > max_w:
                lines.append(cur)
                cur, cur_w = [], 0.0
                add = m.width
            cur.append(m)
            cur_w += add
        if cur:
            lines.append(cur)
        rows = VGroup(*[VGroup(*ln).arrange(buff=0.3) for ln in lines]).arrange(DOWN, buff=0.35)
        if rows.width > max_w:
            rows.scale_to_fit_width(max_w)
        if rows.height > H * 0.75:
            rows.scale_to_fit_height(H * 0.75)
        rows.move_to([0, 0.1, 0])
        flat = [m for row in rows for m in row]
        each = b.t(0.6 / max(len(flat), 1), 0.3)
        for m in flat:
            scene.play(FadeIn(m, shift=UP * 0.25, scale=1.15), run_time=each)
        drift_camera(scene, duration)
