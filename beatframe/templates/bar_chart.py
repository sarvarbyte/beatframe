"""Animated bar chart: bars grow, values count, one bar can be highlighted.
Vertical bars in 16:9, horizontal bars in 9:16 (easier to read on a phone)."""

from __future__ import annotations

from manim import DOWN, LEFT, RIGHT, UP, FadeIn, GrowFromEdge, Line, RoundedRectangle, VGroup

from beatframe.templates.base import Template
from beatframe.templates.kit import (
    INK, PaletteName, Budget, caption_bar, drift_camera, fh, flat_bg, fw, label, palette, vertical,
)


class BarChart(Template):
    name = "bar_chart"
    description = "Bars grow to their values (labels, values, unit); highlight one of them"
    theme = "bright"
    vertical_width = 8.0

    class Params(Template.Params):
        title: str = ""
        labels: list[str] = ["Babies", "Teens", "Adults"]
        values: list[float] = [16, 9, 7]
        unit: str = "h"
        highlight: int = 0            # 1-based bar to colour; 0 = all coloured
        palette: PaletteName = "auto"

    def build(self, scene, p, duration):
        pal = palette(p.palette, scene.seed)
        flat_bg(scene, pal)
        W, H = fw(), fh()
        b = Budget(duration)
        n = max(1, min(len(p.labels), len(p.values), 6))
        labels, values = p.labels[:n], [max(0.0, float(v)) for v in p.values[:n]]
        top = max(values) or 1
        colors = [pal["a"], pal["c"], pal["b"], pal["d"]]
        tall = vertical()
        if p.title:
            scene.play(FadeIn(caption_bar(p.title, pal), shift=UP * 0.2), run_time=b.t(0.08, 0.5))

        def fmt(v):
            return (f"{v:g}" if v != int(v) else f"{int(v)}") + p.unit

        bars = VGroup()
        if tall:
            area_w, gap = W * 0.52, 0.35
            bh = min(1.0, (H * 0.5 - gap * (n - 1)) / n)
            y0 = (n - 1) * (bh + gap) / 2 - 0.3
            x0 = -W * 0.18
            axis = Line([x0, y0 + bh, 0], [x0, y0 - (n - 1) * (bh + gap) - bh, 0]).set_stroke(INK, 5, 0.6)
            for i, (lab, v) in enumerate(zip(labels, values)):
                col = colors[i % 4] if not p.highlight or p.highlight == i + 1 else "#B8C0CC"
                w = max(0.08, area_w * v / top)
                bar = RoundedRectangle(width=w, height=bh, corner_radius=min(0.15, bh / 3)).set_stroke(width=0).set_fill(col, 1)
                bar.move_to([x0 + w / 2, y0 - i * (bh + gap), 0])
                name = label(lab, 0.38, INK, max_width=W * 0.28).next_to([x0, bar.get_y(), 0], LEFT, buff=0.2)
                val = label(fmt(v), 0.4, INK).next_to(bar, RIGHT, buff=0.15)
                bars.add(VGroup(bar, name, val))
        else:
            area_h, gap = H * 0.5, 0.5
            bw = min(1.6, (W * 0.7 - gap * (n - 1)) / n)
            base = -H * 0.28
            x_start = -((n - 1) * (bw + gap)) / 2
            axis = Line([x_start - bw, base, 0], [-x_start + bw, base, 0]).set_stroke(INK, 5, 0.6)
            for i, (lab, v) in enumerate(zip(labels, values)):
                col = colors[i % 4] if not p.highlight or p.highlight == i + 1 else "#B8C0CC"
                h = max(0.08, area_h * v / top)
                bar = RoundedRectangle(width=bw, height=h, corner_radius=min(0.15, bw / 4)).set_stroke(width=0).set_fill(col, 1)
                bar.move_to([x_start + i * (bw + gap), base + h / 2, 0])
                name = label(lab, 0.36, INK, max_width=bw + gap * 0.8).next_to([bar.get_x(), base, 0], DOWN, buff=0.25)
                val = label(fmt(v), 0.42, INK).next_to(bar, UP, buff=0.15)
                bars.add(VGroup(bar, name, val))
        scene.play(FadeIn(axis), *[FadeIn(g[1]) for g in bars], run_time=b.t(0.1, 0.5))
        edge = LEFT if tall else DOWN
        scene.play(*[GrowFromEdge(g[0], edge) for g in bars], run_time=b.t(0.3, 1.3))
        scene.play(*[FadeIn(g[2], shift=(RIGHT if tall else UP) * 0.15) for g in bars], run_time=b.t(0.1, 0.45))
        if p.highlight and 1 <= p.highlight <= n:
            g = bars[p.highlight - 1]
            scene.play(g.animate.scale(1.06), run_time=b.t(0.06, 0.3))
        drift_camera(scene, duration)
