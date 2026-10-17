"""Shared kit for the science library (neuroscience, perception, experiments, biology).

The look ("Lab"): soft lavender / mint / sky / peach / coral line art on a deep dusk background
(or warm paper for light videos). Every template lays itself out from the real frame, so the same
scene composes properly in 16:9 and 9:16 (side by side vs stacked), and keeps its labels inside
the safe area: clear of burnt-in captions at the bottom and of the Shorts buttons and title.

Templates using this kit set `theme = "bright"` (they paint their own background, so the base
scene adds no dust) and `vertical_width = 8.0` (they get the real 8 x 14.2 portrait frame).
"""

from __future__ import annotations

from typing import Literal

import numpy as np
from manim import (
    BOLD, DOWN, LEFT, RIGHT, UP, Circle, Line, Rectangle, RoundedRectangle, Text, VGroup, VMobject, config,
    linear, rate_functions,
)
from pydantic import Field

from beatframe import brand
from beatframe.templates.base import Template

# ---- palettes -------------------------------------------------------------------------------------
PALETTES: dict[str, dict[str, str]] = {
    # deep dusk: the default, sits well next to the channel's dark 'One Light' scenes
    "dusk": dict(top="#221D42", bottom="#13102A", ink="#FBF7F0", muted="#A7A1CC", faint="#3B355F",
                 lavender="#B9A8FF", purple="#8D7BF2", mint="#7FE3C4", sky="#7CC4FF", peach="#FFC59E",
                 coral="#FF7F6E", warm="#FBF7F0", panel="#2A2450", dark=True),
    # deep sea blue
    "ocean": dict(top="#132A44", bottom="#0A1729", ink="#F4F8FB", muted="#97AFC8", faint="#2A4562",
                  lavender="#B7AEFF", purple="#8F86F0", mint="#78E6C8", sky="#86CFFF", peach="#FFC9A3",
                  coral="#FF8473", warm="#F7F3EA", panel="#1A3352", dark=True),
    # warm paper: for light videos; accents darkened so they read on the cream background
    "paper": dict(top="#FBF7F0", bottom="#EEE8F8", ink="#29233F", muted="#6D6790", faint="#DCD5EC",
                  lavender="#7A62E0", purple="#5B47C7", mint="#139A78", sky="#2D84D6", peach="#D9844E",
                  coral="#DD4E3A", warm="#FFFFFF", panel="#FFFFFF", dark=False),
}
PaletteName = Literal["dusk", "ocean", "paper"]
Accent = Literal["coral", "mint", "sky", "peach", "lavender"]
Camera = Literal["gentle", "still", "push", "drift"]


class SciParams(Template.Params):
    """Settings every science-library scene has (each template adds its own)."""
    palette: PaletteName = "dusk"
    highlight: Accent = "coral"          # the colour of the thing the scene is about
    title: str = ""                      # optional headline at the top
    labels: bool = True                  # anatomical / diagram labels
    text_size: float = Field(1.0, ge=0.7, le=1.4)
    speed: float = Field(1.0, ge=0.6, le=1.6)   # >1 = faster motion inside the same beat length
    camera: Camera = "gentle"            # still | gentle push | stronger push towards the subject | sideways drift


# ---- stage: frame size, orientation, safe area --------------------------------------------------------
class Stage:
    """Frame geometry for one render. Units are Manim scene units.

    Long (16:9): burnt-in subtitles sit in the bottom 8-17% of the frame, so the safe area is
    7% .. 83% from the top; a scene's own caption goes at the bottom of that area.
    Short (9:16): Beatframe's subtitles sit 31-40% above the bottom (above the Shorts title and
    buttons). The illustration uses 11% .. 59% from the top; a scene's own caption goes in the
    `foot` band below the subtitles (about 75% from the top). Sides keep clear of the Shorts
    like/comment column on the right.
    """

    def __init__(self) -> None:
        self.w, self.h = config.frame_width, config.frame_height
        self.v = self.h > self.w
        if self.v:
            self.top, self.bottom = self.h * 0.39, -self.h * 0.09
            self.left, self.right = -self.w * 0.43, self.w * 0.38
            self.foot = -self.h * 0.255
        else:
            self.top, self.bottom = self.h * 0.43, -self.h * 0.33
            self.left, self.right = -self.w * 0.45, self.w * 0.45
            self.foot = None
        self.cx = (self.left + self.right) / 2
        self.cy = (self.top + self.bottom) / 2
        self.sw, self.sh = self.right - self.left, self.top - self.bottom

    def content(self, title: bool) -> tuple[float, float]:
        """(top, bottom) of the area under the headline."""
        return (self.top - (self.h * 0.085 if self.v else self.h * 0.115) if title else self.top), self.bottom

    def place_caption(self, cap) -> float:
        """Put a scene caption where it stays readable; returns how much height it takes from the
        bottom of the content area (0 in Shorts, where it sits below the subtitles)."""
        if not len(cap):
            return 0.0
        if self.v:
            cap.move_to([self.cx, self.foot, 0])
            return 0.0
        cap.move_to([self.cx, self.bottom + cap.height / 2, 0])
        return cap.height + 0.3

    @property
    def u(self) -> float:
        return 1.0


def pal_of(p) -> dict:
    return PALETTES.get(getattr(p, "palette", "dusk"), PALETTES["dusk"])


def hi_of(p, pal: dict) -> str:
    return pal[getattr(p, "highlight", "coral")]


# ---- text ---------------------------------------------------------------------------------------------------
def text(s: str, size: float, color: str, bold: bool = False, serif: bool = False, max_w: float | None = None) -> Text:
    t = Text(s, font=brand.SERIF if serif else brand.SANS, weight=BOLD if bold else "NORMAL", color=color).scale(size)
    if max_w and t.width > max_w:
        t.scale_to_fit_width(max_w)
    return t


def wrapped(s: str, size: float, color: str, chars: int, max_w: float, bold: bool = False, serif: bool = False,
            align: str = "center") -> VGroup:
    import textwrap

    lines = textwrap.wrap(s, chars) or [""]
    g = VGroup(*[text(line, size, color, bold, serif) for line in lines]).arrange(DOWN, buff=0.13 * size / 0.5)
    if align == "left":
        for m in g:
            m.align_to(g, LEFT)
    if g.width > max_w:
        g.scale_to_fit_width(max_w)
    return g


def headline(s: str, st: Stage, pal: dict, scale: float = 1.0) -> VGroup:
    """Title at the top of the safe area with a short accent rule under it."""
    if not s:
        return VGroup()
    size = (0.62 if st.v else 0.6) * scale
    t = wrapped(s, size, pal["ink"], chars=22 if st.v else 40, max_w=st.sw * 0.94, bold=True)
    rule = Line(LEFT * 0.35, RIGHT * 0.35).set_stroke(pal["lavender"], 4)
    g = VGroup(t, rule).arrange(DOWN, buff=0.16)
    g.move_to([st.cx, st.top - g.height / 2, 0])
    return g


def tag(s: str, color: str, pal: dict, size: float = 0.34) -> VGroup:
    """A small rounded label: coloured dot + text on a translucent panel."""
    size *= 1.15            # labels must stay readable on a phone
    t = text(s, size, pal["ink"], bold=True)
    dot = Circle(radius=0.07 * size / 0.34).set_stroke(width=0).set_fill(color, 1)
    row = VGroup(dot, t).arrange(RIGHT, buff=0.12 * size / 0.34)
    box = RoundedRectangle(width=row.width + 0.36 * size / 0.34, height=row.height + 0.22 * size / 0.34,
                           corner_radius=(row.height + 0.22) / 2).set_stroke(color, 1.5, 0.7)
    box.set_fill(pal["panel"], 0.82 if pal["dark"] else 0.95)
    return VGroup(box, row.move_to(box))


def callout(target, s: str, direction, color: str, pal: dict, size: float = 0.32, dist: float = 0.9) -> VGroup:
    """A label at `direction` from `target` (a point), joined by a thin leader line."""
    target = np.array(target, dtype=float)
    lab = tag(s, color, pal, size)
    d = np.zeros(3)
    d[:len(direction)] = np.array(direction, dtype=float)[:3]
    d = d / (np.linalg.norm(d) + 1e-9)
    lab.move_to(target + d * dist + d * np.array([lab.width / 2, lab.height / 2, 0]))
    edge = -np.sign(d) * np.array([1.0 if abs(d[0]) > 0.3 else 0.0, 1.0 if abs(d[1]) > 0.3 else 0.0, 0.0])
    end = lab.get_critical_point(edge)
    leader = Line(target, end).set_stroke(color, 1.6, 0.8)
    pin = Circle(radius=0.045).set_stroke(width=0).set_fill(color, 1).move_to(target)
    return VGroup(leader, pin, lab)


def card(w: float, h: float, pal: dict, stroke: str | None = None, opacity: float | None = None) -> RoundedRectangle:
    r = RoundedRectangle(width=w, height=h, corner_radius=min(0.28, h * 0.2))
    r.set_fill(pal["panel"], opacity if opacity is not None else (0.72 if pal["dark"] else 0.92))
    return r.set_stroke(stroke or pal["faint"], 1.5, 0.9)


# ---- background ----------------------------------------------------------------------------------------------
def background(scene, pal: dict, st: Stage, seed: int = 0, grid: bool = False) -> VGroup:
    """Gradient, two soft colour pools and (optionally) a faint lab grid. All static: no per-frame cost."""
    bg = Rectangle(width=st.w * 1.6, height=st.h * 1.6).set_stroke(width=0)
    bg.set_fill(color=[pal["top"], pal["bottom"]], opacity=1).set_sheen_direction(DOWN)
    rng = np.random.default_rng(seed)
    pools = VGroup()
    for col, (sx, sy) in ((pal["purple"], (-0.32, 0.30)), (pal["sky"], (0.34, -0.28))):
        for k in range(6, 0, -1):
            c = Circle(radius=st.h * 0.09 * k).set_stroke(width=0).set_fill(col, 0.018 if pal["dark"] else 0.02)
            pools.add(c.move_to([st.w * sx + rng.uniform(-0.3, 0.3), st.h * sy, 0]))
    g = VGroup(bg, pools)
    if grid:
        step = st.h / 12
        lines = VGroup(*[Line([x, -st.h, 0], [x, st.h, 0]) for x in np.arange(-st.w, st.w, step)],
                       *[Line([-st.w, y, 0], [st.w, y, 0]) for y in np.arange(-st.h, st.h, step)])
        g.add(lines.set_stroke(pal["faint"], 0.8, 0.35))
    g.set_z_index(-50)
    scene.add(g)
    return g


# ---- timing ----------------------------------------------------------------------------------------------------
class Clock:
    """Splits a beat into phases. `t(share, lo, hi)` = share of the beat, clamped, scaled by speed."""

    def __init__(self, scene, duration: float, speed: float = 1.0):
        self.scene, self.d, self.speed = scene, duration, max(0.6, min(1.6, speed))

    @property
    def now(self) -> float:
        return getattr(self.scene.renderer, "time", 0.0)

    @property
    def left(self) -> float:
        return self.d - self.now

    def t(self, share: float, lo: float = 0.2, hi: float = 3.0) -> float:
        return max(lo, min(hi, self.d * share / self.speed))

    def fits(self, seconds: float, reserve: float = 0.25) -> bool:
        return self.left - reserve > seconds


def finish(scene, clock: Clock, camera: str, focus=None, scale: float | None = None) -> None:
    """Use the rest of the beat: a camera move (or a hold) that never ends on a frozen frame."""
    rest = clock.left
    if rest <= 1 / config.frame_rate:
        return
    frame = scene.camera.frame
    if rest < 0.3 or camera == "still":
        scene.wait(rest)
        return
    if camera == "push":
        anim = frame.animate(rate_func=rate_functions.ease_in_out_sine).scale(scale or 0.86)
        if focus is not None:
            anim = frame.animate(rate_func=rate_functions.ease_in_out_sine).scale(scale or 0.86).move_to(
                frame.get_center() * 0.5 + np.array(focus) * 0.5)
    elif camera == "drift":
        anim = frame.animate(rate_func=linear).shift(RIGHT * frame.width * 0.035).scale(0.97)
    else:
        anim = frame.animate(rate_func=linear).scale(scale or 0.95)
    scene.play(anim, run_time=rest)


# ---- drawing helpers ---------------------------------------------------------------------------------------
def smooth(points, color: str, width: float, opacity: float = 1.0) -> VMobject:
    pts = [np.append(np.array(p, dtype=float), [0.0] * (3 - len(p))) for p in points]   # (x, y) or (x, y, z)
    return VMobject().set_points_smoothly(pts).set_stroke(color, width, opacity)


def glow_dot(color: str, r: float = 0.08, halo: int = 4) -> VGroup:
    """A small light: core + a few transparent rings (cheap: 5 circles)."""
    g = VGroup(*[Circle(radius=r * (1 + 0.8 * k)).set_stroke(width=0).set_fill(color, 0.22 * (1 - k / (halo + 1)))
                 for k in range(halo, 0, -1)])
    g.add(Circle(radius=r).set_stroke(width=0).set_fill(color, 1))
    return g


def head_profile(scale: float = 1.0, facing: int = 1) -> VMobject:
    """Side view of a human head and neck (facing right), about 3.2 x 3.6 units at scale 1.
    Proportions follow a standard profile: forehead, brow, nose, lips, chin, jaw, back of skull, nape."""
    pts = [(-0.30, -1.75), (-0.32, -1.15), (-0.62, -0.62), (-1.02, -0.18), (-1.20, 0.45), (-1.05, 1.15),
           (-0.55, 1.62), (0.15, 1.75), (0.78, 1.45), (1.05, 0.95), (1.12, 0.50), (1.18, 0.30),
           (1.52, -0.10), (1.20, -0.22), (1.20, -0.40), (1.32, -0.52), (1.18, -0.66), (1.24, -0.82),
           (1.08, -1.00), (0.72, -1.12), (0.42, -1.18), (0.40, -1.75)]
    m = VMobject().set_points_smoothly([np.array([x * facing, y, 0]) * scale for x, y in pts])
    return m


def ear_shape(scale: float = 1.0) -> VMobject:
    pts = [(0, 0.32), (0.16, 0.26), (0.2, 0.05), (0.12, -0.18), (0.02, -0.32), (-0.08, -0.26), (-0.04, -0.08),
           (-0.12, 0.08), (-0.1, 0.26), (0, 0.32)]
    return VMobject().set_points_smoothly([np.array([x, y, 0]) * scale for x, y in pts])


def neuron(pal: dict, color: str, r: float = 0.22, dendrites: int = 5, seed: int = 0, axon_to=None) -> VGroup:
    """A neuron: soma, branching dendrites and (optionally) an axon towards `axon_to` (relative point)."""
    rng = np.random.default_rng(seed)
    soma = Circle(radius=r).set_fill(color, 0.9).set_stroke(pal["ink"], 1.2, 0.35)
    nucleus = Circle(radius=r * 0.38).set_fill(pal["bottom"], 0.55).set_stroke(width=0)
    branches = VGroup()
    base_angles = np.linspace(0, 2 * np.pi, dendrites, endpoint=False) + rng.uniform(0, 1)
    for a in base_angles:
        if axon_to is not None:
            ax = np.arctan2(axon_to[1], axon_to[0])
            if abs((a - ax + np.pi) % (2 * np.pi) - np.pi) < 0.7:
                continue
        L = r * rng.uniform(2.2, 3.2)
        d = np.array([np.cos(a), np.sin(a), 0])
        n = np.array([-d[1], d[0], 0])
        start, mid, end = d * r * 0.9, d * L * 0.55 + n * rng.uniform(-0.15, 0.15) * L, d * L
        branches.add(smooth([start, mid, end], color, 2.6, 0.9))
        for sgn in (-1, 1):
            tip = end + (d * 0.45 + n * sgn * 0.55) * L * 0.35
            branches.add(smooth([mid + (end - mid) * 0.5, tip], color, 1.8, 0.8))
    g = VGroup(branches, soma, nucleus)
    if axon_to is not None:
        to = np.array(axon_to, dtype=float)
        n = np.array([-to[1], to[0], 0]) / (np.linalg.norm(to) + 1e-9)
        axon = smooth([to * 0.0 + to / np.linalg.norm(to) * r, to * 0.35 + n * 0.12, to * 0.7 - n * 0.1, to],
                      color, 3.0, 0.95)
        g.add(axon)
        g.axon = axon
    return g


def wave_path(start, end, amp: float, cycles: float, phase: float = 0.0, samples: int = 80) -> VMobject:
    start, end = np.array(start, dtype=float), np.array(end, dtype=float)
    d = end - start
    L = np.linalg.norm(d) + 1e-9
    n = np.array([-d[1], d[0], 0]) / L
    ts = np.linspace(0, 1, samples)
    pts = [start + d * t + n * amp * np.sin(2 * np.pi * cycles * t + phase) * np.sin(np.pi * t) ** 0.5 for t in ts]
    return VMobject().set_points_smoothly(pts)


def arcs(center, radius: float, n: int, spread: float, angle: float, color: str, width: float = 3.0) -> VGroup:
    """Concentric sound-wave arcs pointing at `angle` (radians)."""
    from manim import Arc

    return VGroup(*[Arc(radius=radius * (k + 1), start_angle=angle - spread / 2, angle=spread, arc_center=np.array(center, dtype=float))
                    .set_stroke(color, width, 1 - k / (n + 1)) for k in range(n)])


def body_front(height: float = 6.0) -> VMobject:
    """Front view of a standing person as one smooth outline (head, neck, torso, arms, legs).
    Proportions: about 7.5 heads tall, shoulders ~2 heads wide."""
    from manim import Union, Circle as _C, RoundedRectangle as _R

    hd = height / 7.5
    head = _C(radius=hd * 0.5).move_to(UP * (height / 2 - hd * 0.5))
    neck = _R(width=hd * 0.42, height=hd * 0.5, corner_radius=hd * 0.1).move_to(UP * (height / 2 - hd * 1.1))
    torso = _R(width=hd * 1.9, height=hd * 2.9, corner_radius=hd * 0.45).move_to(UP * (height / 2 - hd * 2.65))
    hips = _R(width=hd * 1.6, height=hd * 1.0, corner_radius=hd * 0.35).move_to(UP * (height / 2 - hd * 3.95))
    parts = [head, neck, torso, hips]
    for s in (-1, 1):
        arm = _R(width=hd * 0.42, height=hd * 3.1, corner_radius=hd * 0.2).move_to(
            [s * hd * 1.12, height / 2 - hd * 3.0, 0]).rotate(s * 0.09, about_point=np.array([s * hd * 0.95, height / 2 - hd * 1.55, 0]))
        leg = _R(width=hd * 0.62, height=hd * 3.6, corner_radius=hd * 0.26).move_to([s * hd * 0.42, -height / 2 + hd * 1.8, 0])
        parts += [arm, leg]
    shape = parts[0]
    for p_ in parts[1:]:
        shape = Union(shape, p_)
    return shape


def guard(scene, duration: float) -> None:
    """Never run past the beat: animations are cut to whole frames (no rounding drift) and squeezed into
    what is left of the beat; anything that starts after the end is skipped. The pipeline pads every beat
    to its voice, so a scene that overran would desync the next cut."""
    fps = config.frame_rate
    frame = 1.0 / fps
    play0, wait0 = scene.play, scene.wait

    def left() -> float:
        return duration - getattr(scene.renderer, "time", 0.0)

    def whole(t: float) -> float:
        return max(1, int(np.floor(t * fps + 1e-6))) * frame

    def play(*anims, **kw):
        rem = left()
        if rem < frame - 1e-6 or not anims:
            return
        own = kw.get("run_time") or max(getattr(a, "run_time", 1.0) for a in anims)
        if own > rem + 1e-6:
            kw["run_time"] = whole(rem)
        elif "run_time" in kw:
            kw["run_time"] = whole(own)
        play0(*anims, **kw)

    def wait(t: float = 1.0, *a, **kw):
        rem = left()
        if rem < frame - 1e-6:
            return
        wait0(whole(min(t, rem)), *a, **kw)

    scene.play, scene.wait = play, wait
