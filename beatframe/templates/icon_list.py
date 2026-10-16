"""Two to four icon cards that pop in one by one (a row in 16:9, a grid in 9:16)."""

from __future__ import annotations

from manim import DOWN, UP, FadeIn, GrowFromCenter, VGroup

from beatframe.templates.base import Template
from beatframe.templates.kit import (
    ICONS, INK, PaletteName, Budget, caption_bar, card, drift_camera, fh, fit_between, flat_bg, fw, icon, label, palette, parse_pair,
    pill, vertical, wrap_label,
)


class IconList(Template):
    name = "icon_list"
    description = "2-4 numbered icon cards ('icon|text') popping in one by one"
    theme = "bright"
    vertical_width = 8.0

    class Params(Template.Params):
        title: str = ""
        items: list[str] = ["sun|Light", "clock|Rhythm", "moon|Melatonin"]
        numbered: bool = True
        palette: PaletteName = "auto"

    def build(self, scene, p, duration):
        pal = palette(p.palette, scene.seed)
        flat_bg(scene, pal)
        W, H = fw(), fh()
        b = Budget(duration)
        items = [parse_pair(x, "star") for x in p.items[:4]] or [("star", "…")]
        n = len(items)
        tall = vertical()
        if tall:
            cols = 1 if n <= 3 else 2
        else:
            cols = n
        rows = (n + cols - 1) // cols
        top_room = 1.7 if p.title else 0.6
        cw = (W * 0.86 - (cols - 1) * 0.3) / cols
        ch = min((H - top_room - 1.0 - (rows - 1) * 0.3) / rows, cw * (0.62 if tall and cols == 1 else 1.15))
        colors = [pal["a"], pal["b"], pal["c"], pal["d"]]
        cards = VGroup()
        for i, (ic, text) in enumerate(items):
            box = card(cw, ch)
            face = box[-1]
            if tall and cols == 1:          # wide horizontal card: icon left, text right
                ico = icon(ic if ic in ICONS else "star", min(1.1, ch * 0.6), pal).move_to(face.get_left() + [ch * 0.55, 0, 0])
                t = wrap_label(text, 0.5, INK, chars=16, max_width=cw - ch * 1.25).next_to(ico, buff=0.35)
                content = VGroup(ico, t)
            else:
                ico = icon(ic if ic in ICONS else "star", min(1.2, cw * 0.38, ch * 0.4), pal).move_to(face.get_center() + UP * ch * 0.12)
                t = wrap_label(text, 0.42, INK, chars=12, max_width=cw * 0.86).next_to(ico, DOWN, buff=0.3)
                content = VGroup(ico, t)
            g = VGroup(box, content)
            if p.numbered:
                g.add(pill(str(i + 1), colors[i % 4], 0.36).move_to(face.get_corner(UP + [-1, 0, 0]) + [0.35, -0.3, 0]))
            cards.add(g)
        cards.arrange_in_grid(rows=rows, cols=cols, buff=0.3)
        bar = caption_bar(p.title, pal) if p.title else None
        top = (bar.get_bottom()[1] - 0.45) if bar else H / 2 - 0.6
        fit_between(cards, top, -H / 2 + (1.0 if tall else 0.7), max_width=W * 0.9)
        if bar:
            scene.play(FadeIn(bar, shift=UP * 0.2), run_time=b.t(0.08, 0.5))
        each = b.t(0.6 / n, 0.55)
        for g in cards:
            scene.play(FadeIn(g, shift=UP * 0.5, scale=0.85), run_time=each)
        drift_camera(scene, duration)
