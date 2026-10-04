"""Opening / chapter title: a single light arrives, the title writes itself under it."""

from manim import BOLD, DOWN, UP, FadeIn, Text, VGroup, Write, linear, smooth

from beatframe import brand
from beatframe.templates.base import Template, glow


class TitleCard(Template):
    name = "title_card"
    description = "Big two-line title under a single drifting light"

    class Params(Template.Params):
        line1: str = "YOU'VE NEVER"
        line2: str = "TOUCHED ANYTHING"
        kicker: str = ""          # small line above, e.g. "CHAPTER 2"

    def build(self, scene, p, duration):
        light = glow(0.12, brand.GLOW).move_to(UP * 4.6 + 2.5 * DOWN * 0)
        l1 = Text(p.line1, font=brand.SERIF, weight=BOLD, color=brand.PAPER).scale(0.95)
        l2 = Text(p.line2, font=brand.SERIF, weight=BOLD, color=brand.GLOW).scale(1.25)
        title = VGroup(l1, l2).arrange(DOWN, buff=0.35).shift(DOWN * 0.6)
        items = [light, title]
        if p.kicker:
            k = Text(p.kicker, font=brand.SANS, color=brand.DIM).scale(0.45)
            k.next_to(title, UP, buff=0.6)
            items.append(k)

        frame = scene.camera.frame
        t_in = min(1.2, duration * 0.25)
        scene.play(light.animate.move_to(UP * 1.9), run_time=t_in, rate_func=smooth)
        scene.play(FadeIn(l1, shift=UP * 0.2), run_time=min(0.7, duration * 0.15))
        anims = [Write(l2)]
        if p.kicker:
            anims.append(FadeIn(items[-1]))
        scene.play(*anims, run_time=min(1.1, duration * 0.2))

        rest = duration - getattr(scene.renderer, "time", 0)
        if rest > 0.2:
            scene.play(
                frame.animate.scale(0.94),
                light.animate.shift(UP * 0.15).scale(1.15),
                run_time=rest, rate_func=linear,
            )
