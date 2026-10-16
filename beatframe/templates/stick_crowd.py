"""'1 in N' style statistic: a grid of people, some of them light up."""

from __future__ import annotations

import numpy as np
from manim import DOWN, UP, FadeIn, LaggedStart, VGroup

from beatframe.templates.base import Template
from beatframe.templates.kit import (
    INK, PaletteName, Budget, caption_bar, center_last_row, drift_camera, fh, flat_bg, fw, grid_shape, palette, person, pill,
    vertical, wrap_label,
)


class StickCrowd(Template):
    name = "stick_crowd"
    description = "A crowd of people icons where some light up: '1 in 10', '3 out of 4'..."
    theme = "bright"
    vertical_width = 8.0

    class Params(Template.Params):
        total: int = 10              # people in the grid (2..100)
        highlight: int = 1           # how many light up
        title: str = ""
        caption: str = "1 in 10 people"
        palette: PaletteName = "auto"

    def build(self, scene, p, duration):
        pal = palette(p.palette, scene.seed)
        flat_bg(scene, pal)
        W, H = fw(), fh()
        b = Budget(duration)
        n = max(2, min(100, p.total))
        k = max(0, min(n, p.highlight))
        cols, rows = grid_shape(n, 0.85 if vertical() else 2.4)
        area_w, area_h = W * 0.82, H * (0.56 if vertical() else 0.5)
        size = min(area_w / cols, area_h / rows) * 0.92
        grid = VGroup(*[person("#9AA5B1", size) for _ in range(n)])
        grid.arrange_in_grid(rows=rows, cols=cols, buff=size * 0.12)
        center_last_row(grid, cols)
        grid.move_to([0, H * 0.02, 0])
        rng = np.random.default_rng(scene.seed)
        hot = set(rng.choice(n, size=k, replace=False).tolist()) if k else set()

        if p.title:
            scene.play(FadeIn(caption_bar(p.title, pal), shift=UP * 0.2), run_time=b.t(0.08, 0.5))
        scene.play(LaggedStart(*[FadeIn(m, shift=UP * 0.15) for m in grid], lag_ratio=min(0.08, 1.2 / n)), run_time=b.t(0.3, 1.6))
        if hot:
            scene.play(*[grid[i].animate.set_fill(pal["a"], 1).scale(1.18) for i in hot], run_time=b.t(0.12, 0.6))
        if p.caption:
            cap = pill(p.caption, INK, 0.62 if vertical() else 0.55).next_to(grid, DOWN, buff=0.5)
            scene.play(FadeIn(cap, shift=UP * 0.2), run_time=b.t(0.08, 0.45))
        drift_camera(scene, duration)
