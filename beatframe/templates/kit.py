"""Building blocks for the bright ("sunny") templates: palettes, backgrounds, rooms, an
animated stick figure, icons, bubbles and cards.

Everything is sized from the frame (frame_w / frame_h), so the same template works in
16:9 and 9:16. Templates using this kit set `theme = "bright"` and `vertical_width = 8.0`.

Variety: palette "auto" picks a palette from the beat's seed, so two beats with the same
template still look different.
"""

from __future__ import annotations

import numpy as np
from manim import (
    BOLD, DOWN, LEFT, ORIGIN, RIGHT, UP, Arc, Circle, Dot, Ellipse, Line, Polygon, Rectangle,
    RoundedRectangle, Square, Star, Text, ValueTracker, VGroup, VMobject, always_redraw, config,
)

from beatframe import brand

INK = "#2B2D42"
WHITE = "#FFFFFF"

PALETTES: dict[str, dict[str, str]] = {
    "sunny": dict(top="#FFF3CF", bottom="#FFDDA6", floor="#F2B66B", a="#FB8500", b="#EF476F", c="#118AB2", d="#06A77D", soft="#FFE8BF"),
    "mint":  dict(top="#E2F8EC", bottom="#BDEBD3", floor="#74C69D", a="#06A77D", b="#FB8500", c="#3A86FF", d="#EF476F", soft="#D2F2E1"),
    "sky":   dict(top="#E1F0FF", bottom="#BCDDFF", floor="#8EB8DE", a="#3A86FF", b="#FB8500", c="#EF476F", d="#06A77D", soft="#D3E8FF"),
    "berry": dict(top="#FFE3EC", bottom="#FFC4D4", floor="#E58FA8", a="#EF476F", b="#3A86FF", c="#FB8500", d="#06A77D", soft="#FFD6E2"),
    "lilac": dict(top="#EFE3FF", bottom="#D8C2FF", floor="#A98BE0", a="#8338EC", b="#FB8500", c="#06A77D", d="#EF476F", soft="#E4D4FF"),
    "peach": dict(top="#FFE9DC", bottom="#FFC9AD", floor="#EE9E7C", a="#F3722C", b="#3A86FF", c="#8338EC", d="#06A77D", soft="#FFDCCB"),
}
PALETTE_NAMES = list(PALETTES)
SKIN = "#FFFFFF"


def palette(name: str, seed: int) -> dict[str, str]:
    """A palette by name; "auto" rotates through them by beat seed."""
    if name in PALETTES:
        return PALETTES[name]
    return PALETTES[PALETTE_NAMES[(seed // 13) % len(PALETTE_NAMES)]]


# ---- frame helpers ---------------------------------------------------------------
def fw() -> float:
    return config.frame_width


def fh() -> float:
    return config.frame_height


def vertical() -> bool:
    return config.frame_height > config.frame_width


def unit() -> float:
    """Size multiplier: things are a bit bigger in tall frames, where there is room."""
    return 1.5 if vertical() else 1.15


def floor_y() -> float:
    """Where feet stand: lower third in long frames, a bit below centre in tall ones."""
    return -fh() * (0.18 if vertical() else 0.30)


def label(text: str, size: float = 0.5, color: str = INK, bold: bool = True, max_width: float | None = None,
          t2c: dict | None = None) -> Text:
    t = Text(text, font=brand.SANS, weight=BOLD if bold else "NORMAL", color=color, t2c=t2c or {}).scale(size)
    mw = max_width or fw() * 0.86
    if t.width > mw:
        t.scale_to_fit_width(mw)
    return t


def wrap_label(text: str, size: float, color: str = INK, chars: int = 22, max_width: float | None = None,
               bold: bool = True, t2c: dict | None = None) -> VGroup:
    """Multi-line centred text (wraps on words). t2c colours words: {"forget": "#EF476F"}."""
    import textwrap

    lines = textwrap.wrap(text, chars) or [""]
    g = VGroup(*[label(l, size, color, bold, max_width,
                       {k: v for k, v in (t2c or {}).items() if k and k in l}) for l in lines]).arrange(DOWN, buff=0.12 * size / 0.5)
    mw = max_width or fw() * 0.86
    if g.width > mw:
        g.scale_to_fit_width(mw)
    return g


# ---- backgrounds and rooms ---------------------------------------------------------
def background(pal: dict, floor: bool = True) -> VGroup:
    sky = Rectangle(width=fw() + 0.2, height=fh() + 0.2).set_stroke(width=0)
    sky.set_fill(color=[pal["top"], pal["bottom"]], opacity=1).set_sheen_direction(DOWN)
    g = VGroup(sky)
    if floor:
        y = floor_y()
        fl = Rectangle(width=fw() + 0.2, height=fh() / 2 + y + 0.2).set_stroke(width=0).set_fill(pal["floor"], 1)
        fl.move_to([0, (y + -fh() / 2 - 0.2) / 2, 0])
        edge = Line([-fw() / 2 - 0.1, y, 0], [fw() / 2 + 0.1, y, 0]).set_stroke(INK, 2, 0.12)
        g.add(fl, edge)
    g.set_z_index(-20)
    return g


def _window(w: float, h: float) -> VGroup:
    frame = RoundedRectangle(width=w, height=h, corner_radius=0.08).set_stroke("#7B4B2A", 6).set_fill("#9ED0FF", 1)
    bars = VGroup(Line(frame.get_top(), frame.get_bottom()), Line(frame.get_left(), frame.get_right())).set_stroke("#7B4B2A", 5)
    return VGroup(frame, bars)


def setting(kind: str, pal: dict) -> VGroup:
    """Simple props for a scene. Kinds: plain, kitchen, bedroom, office, outdoor, lab, street, night."""
    y = floor_y()
    W = fw()
    g = VGroup()
    if kind == "kitchen":
        win = _window(1.9, 1.5).move_to([-W * 0.28, y + 2.9, 0])
        counter = RoundedRectangle(width=W * 0.34, height=1.1, corner_radius=0.08).set_stroke(width=0).set_fill(pal["d"], 1)
        counter.move_to([-W * 0.30, y + 0.55, 0])
        top = Rectangle(width=W * 0.36, height=0.16).set_stroke(width=0).set_fill(INK, 0.25).next_to(counter, UP, buff=0)
        fridge = RoundedRectangle(width=1.25, height=2.7, corner_radius=0.12).set_stroke(width=0).set_fill("#CFE6FF", 1)
        fridge.move_to([W * 0.36, y + 1.35, 0])
        line = Line(fridge.get_left() + UP * 0.35, fridge.get_right() + UP * 0.35).set_stroke("#8FB4DB", 4)
        handle = Line(fridge.get_left() + RIGHT * 0.2 + UP * 0.8, fridge.get_left() + RIGHT * 0.2 + UP * 1.1).set_stroke("#8FB4DB", 5)
        g.add(win, counter, top, fridge, line, handle)
    elif kind == "bedroom":
        win = _window(1.7, 1.3).move_to([W * 0.30, y + 3.0, 0])
        frame = RoundedRectangle(width=W * 0.42, height=0.55, corner_radius=0.1).set_stroke(width=0).set_fill("#7B4B2A", 1)
        frame.move_to([-W * 0.22, y + 0.45, 0])
        mattress = RoundedRectangle(width=W * 0.40, height=0.4, corner_radius=0.15).set_stroke(width=0).set_fill(WHITE, 1).next_to(frame, UP, buff=-0.05)
        blanket = RoundedRectangle(width=W * 0.28, height=0.42, corner_radius=0.15).set_stroke(width=0).set_fill(pal["a"], 1)
        blanket.align_to(mattress, RIGHT).align_to(mattress, DOWN).shift(UP * 0.12)
        pillow = RoundedRectangle(width=0.8, height=0.35, corner_radius=0.15).set_stroke(width=0).set_fill(pal["soft"], 1)
        pillow.next_to(mattress, UP, buff=-0.15).align_to(mattress, LEFT).shift(RIGHT * 0.15)
        head = RoundedRectangle(width=0.2, height=1.6, corner_radius=0.08).set_stroke(width=0).set_fill("#7B4B2A", 1)
        head.next_to(frame, LEFT, buff=-0.1).align_to(frame, DOWN)
        g.add(win, frame, mattress, blanket, pillow, head)
    elif kind == "office":
        dx = W * 0.25
        desk = Rectangle(width=W * 0.32, height=0.16).set_stroke(width=0).set_fill("#7B4B2A", 1).move_to([dx, y + 1.25, 0])
        legs = VGroup(*[Rectangle(width=0.14, height=1.2).set_stroke(width=0).set_fill("#5C3A21", 1)
                        .move_to([dx + s * W * 0.13, y + 0.6, 0]) for s in (-1, 1)])
        screen = RoundedRectangle(width=1.4, height=0.9, corner_radius=0.08).set_stroke(INK, 5).set_fill(pal["c"], 1)
        screen.move_to([dx, y + 1.95, 0])
        stand = Rectangle(width=0.12, height=0.3).set_stroke(width=0).set_fill(INK, 1).next_to(screen, DOWN, buff=0)
        plant = VGroup(RoundedRectangle(width=0.5, height=0.55, corner_radius=0.08).set_stroke(width=0).set_fill(pal["b"], 1),
                       *[Ellipse(width=0.28, height=0.6).set_stroke(width=0).set_fill(pal["d"], 1).rotate(a).shift(UP * 0.5 + RIGHT * a * 0.35)
                         for a in (-0.5, 0, 0.5)])
        plant.move_to([-W * 0.36, y + 0.55, 0])
        g.add(desk, legs, screen, stand, plant)
    elif kind == "outdoor":
        sun = VGroup(Circle(radius=0.55).set_stroke(width=0).set_fill("#FFD166", 1),
                     *[Line(ORIGIN, RIGHT * 0.25).shift(RIGHT * 0.75).rotate(a, about_point=ORIGIN).set_stroke("#FFB703", 5)
                       for a in np.linspace(0, 2 * np.pi, 9)[:-1]])
        sun.move_to([W * 0.32, fh() * 0.32, 0])
        for x, h in ((-W * 0.34, 2.4), (-W * 0.18, 1.8)):
            trunk = Rectangle(width=0.22, height=h * 0.5).set_stroke(width=0).set_fill("#7B4B2A", 1).move_to([x, y + h * 0.25, 0])
            crown = Circle(radius=h * 0.33).set_stroke(width=0).set_fill(pal["d"], 1).move_to([x, y + h * 0.62, 0])
            g.add(trunk, crown)
        cloud = VGroup(*[Circle(radius=r).set_stroke(width=0).set_fill(WHITE, 0.9).shift(RIGHT * dx + UP * dy)
                         for r, dx, dy in ((0.35, 0, 0), (0.45, 0.45, 0.12), (0.32, 0.9, 0))]).move_to([-W * 0.05, fh() * 0.36, 0])
        g.add(sun, cloud)
    elif kind == "lab":
        bench = Rectangle(width=W * 0.5, height=0.16).set_stroke(width=0).set_fill(INK, 0.6).move_to([W * 0.15, y + 1.1, 0])
        g.add(bench)
        for i, col in enumerate((pal["a"], pal["c"], pal["d"])):
            x = W * 0.03 + i * 0.75
            body = Polygon([x - 0.28, y + 1.18, 0], [x + 0.28, y + 1.18, 0], [x + 0.1, y + 1.75, 0], [x - 0.1, y + 1.75, 0])
            body.set_stroke(INK, 4).set_fill(col, 0.85)
            neck = Rectangle(width=0.2, height=0.35).set_stroke(INK, 4).set_fill(WHITE, 0.6).move_to([x, y + 1.92, 0])
            g.add(body, neck)
        board = RoundedRectangle(width=2.2, height=1.3, corner_radius=0.08).set_stroke("#7B4B2A", 6).set_fill(WHITE, 1)
        board.move_to([-W * 0.28, y + 3.0, 0])
        scribble = VGroup(*[Line(board.get_left() + RIGHT * 0.3 + UP * k, board.get_left() + RIGHT * (0.9 + 0.5 * (k % 2)) + UP * k)
                            for k in (0.3, 0.0, -0.3)]).set_stroke(pal["c"], 4)
        g.add(board, scribble)
    elif kind == "street":
        for i, (x, h, col) in enumerate(((-W * 0.38, 3.2, pal["c"]), (-W * 0.16, 2.4, pal["a"]), (W * 0.2, 3.6, pal["b"]), (W * 0.42, 2.6, pal["d"]))):
            b = Rectangle(width=W * 0.18, height=h).set_stroke(width=0).set_fill(col, 0.85).move_to([x, y + h / 2, 0])
            wins = VGroup(*[Square(0.22).set_stroke(width=0).set_fill(WHITE, 0.75).move_to([x + dx, y + 0.6 + dy, 0])
                            for dx in (-W * 0.04, W * 0.04) for dy in np.arange(0, h - 0.9, 0.6)])
            g.add(b, wins)
    elif kind == "night":
        moon = VGroup(Circle(radius=0.5).set_stroke(width=0).set_fill("#FFF3B0", 1))
        moon.move_to([W * 0.3, fh() * 0.3, 0])
        rng = np.random.default_rng(3)
        stars = VGroup(*[Dot([rng.uniform(-W / 2, W / 2), rng.uniform(0.5, fh() / 2), 0], radius=rng.uniform(0.02, 0.05), color=WHITE)
                         for _ in range(40)])
        g.add(stars, moon)
    g.set_z_index(-10)
    return g


def _round(mob) -> None:
    """Round line caps where this Manim version supports it."""
    try:
        from manim import CapStyleType
        for m in mob.family_members_with_points():
            m.set_cap_style(CapStyleType.ROUND)
    except Exception:  # noqa: BLE001 - purely cosmetic
        pass


# ---- the stick figure -----------------------------------------------------------------
FACES = ["neutral", "happy", "surprised", "confused", "scared", "thinking", "sleepy", "sad"]

# body points a hand can reach (Stick.reach): offsets from the head centre (x is "forward")
# or from the shoulder, in units of the figure's size
REACH = {
    "nose": ("head", 0.43, -0.06), "mouth": ("head", 0.36, -0.18), "eye": ("head", 0.30, 0.06),
    "ear": ("head", 0.43, 0.04), "ear_back": ("head", -0.43, 0.04), "chin": ("head", 0.30, -0.33),
    "head": ("head", 0.05, 0.44), "throat": ("head", 0.26, -0.46), "elbow_other": ("elbow", 0.0, 0.0),
    "forehead": ("head", 0.34, 0.24), "chest": ("shoulder", 0.24, -0.32), "belly": ("shoulder", 0.2, -0.62),
    "forward": ("shoulder", 0.86, 0.12), "up": ("shoulder", 0.18, 0.86), "out": ("shoulder", 0.62, -0.5),
}
UPPER_ARM, FOREARM, THIGH, SHIN = 0.45, 0.42, 0.60, 0.58


class Stick:
    """An animated stick figure with elbows and knees. Animate it through its trackers:

        x, y (feet), walk (0 still .. 1 walking), arm_l / arm_r (radians from straight down,
        positive = forward), elbow_l / elbow_r (elbow bend), tilt (head), jump (height),
        face (index in FACES), facing (+1 right, -1 left), talk (0..1 mouth moving),
        tremble (0..1 shaking), life (0..1 idle breathing, swaying and blinking; on by default),
        breath (0..1 a deep breath: chest and shoulders rise), gulp (0..1 a swallow travelling down
        the throat), tongue (0..1 sticking out), fingers (0..1 fingers spread and wiggling).

    Hands can go to a body part: `scene.play(st.reach("r", "nose"))`, later `st.release("r")`.
    `mob` is an always-redrawn VGroup; add it with add_stick(scene, st).
    """

    def __init__(self, x: float = 0.0, y: float | None = None, s: float | None = None,
                 accent: str = "#FB8500", face: str = "neutral", facing: int = 1):
        self.s = (s or 1.0) * unit()
        self.accent = accent
        self.x = ValueTracker(x)
        self.y = ValueTracker(floor_y() if y is None else y)
        self.walk = ValueTracker(0.0)
        self.arm_l = ValueTracker(-0.18)
        self.arm_r = ValueTracker(0.18)
        self.elbow_l = ValueTracker(0.22)
        self.elbow_r = ValueTracker(0.22)
        self.tilt = ValueTracker(0.0)
        self.jump = ValueTracker(0.0)
        self.face = ValueTracker(FACES.index(face))
        self.facing = ValueTracker(facing)
        self.talk = ValueTracker(0.0)
        self.tremble = ValueTracker(0.0)
        self.life = ValueTracker(1.0)
        self.breath = ValueTracker(0.0)
        self.gulp = ValueTracker(0.0)
        self.tongue = ValueTracker(0.0)
        self.fingers = ValueTracker(0.0)
        self.reach_l = ValueTracker(0.0)
        self.reach_r = ValueTracker(0.0)
        self.target = {"l": "chin", "r": "chin"}
        self.phase = 0.0                     # walk cycle
        self.t = (abs(x) * 7.31 + sum(map(ord, accent)) * 0.137) % 3.4   # idle clock; offset so figures differ
        self.mob = always_redraw(self._draw)
        clock = VMobject()   # invisible driver for the walk cycle and idle motion

        def tick(m, dt):
            self.phase += dt * 9.0 * self.walk.get_value()
            self.t += dt
        clock.add_updater(tick)
        self.clock = clock

    # -- control ---------------------------------------------------------------------
    def set_face(self, name: str) -> None:
        self.face.set_value(FACES.index(name))

    def reach(self, side: str, part: str):
        """Animation: the hand on `side` ("l"/"r") goes to a body part (see REACH)."""
        self.target[side] = part
        return (self.reach_l if side == "l" else self.reach_r).animate.set_value(1.0)

    def release(self, side: str):
        return (self.reach_l if side == "l" else self.reach_r).animate.set_value(0.0)

    def head_top(self) -> np.ndarray:
        s = self.s
        return np.array([self.x.get_value(), self.y.get_value() + self.jump.get_value() + 2.85 * s, 0])

    def head_center(self) -> np.ndarray:
        return self.head_top() + DOWN * 0.43 * self.s

    # -- drawing ---------------------------------------------------------------------
    def _point(self, part: str, head_c, sh, f) -> np.ndarray:
        base, dx, dy = REACH.get(part, REACH["chin"])
        if base == "elbow":                     # the other arm's elbow (set while drawing)
            return getattr(self, "_elbow_l", sh)
        origin = head_c if base == "head" else sh
        return origin + np.array([dx * self.s * f, dy * self.s, 0])

    def _arm(self, sh, ang, bend, weight, part, head_c, f, side_sign):
        """Shoulder -> (elbow, hand): forward kinematics blended with reaching for a body part."""
        s = self.s
        a, b = UPPER_ARM * s, FOREARM * s
        up_fk, fore_fk = ang, ang + bend
        if weight > 0.001:
            tgt = self._point(part, head_c, sh, f) + np.array([0, 0.02 * side_sign * s, 0])
            v = tgt - sh
            d = float(np.clip(np.hypot(v[0], v[1]), abs(a - b) + 1e-3, a + b - 1e-3))
            ang_t = np.arctan2(v[0] * f, -v[1])
            alpha = np.arccos(np.clip((a * a + d * d - b * b) / (2 * a * d), -1, 1))
            up_ik = ang_t - alpha
            elbow = sh + np.array([np.sin(up_ik) * a * f, -np.cos(up_ik) * a, 0])
            w2 = tgt - elbow
            fore_ik = np.arctan2(w2[0] * f, -w2[1])
            up_fk, fore_fk = up_fk + (up_ik - up_fk) * weight, fore_fk + (fore_ik - fore_fk) * weight
        elbow = sh + np.array([np.sin(up_fk) * a * f, -np.cos(up_fk) * a, 0])
        hand = elbow + np.array([np.sin(fore_fk) * b * f, -np.cos(fore_fk) * b, 0])
        return elbow, hand

    def _draw(self) -> VGroup:
        s = self.s
        t, life, w = self.t, self.life.get_value(), self.walk.get_value()
        still = life * (1 - min(w, 1))
        shake = self.tremble.get_value()
        x = self.x.get_value() + np.sin(t * 0.9) * 0.025 * s * still + np.sin(t * 57) * 0.03 * s * shake
        y = self.y.get_value() + self.jump.get_value()
        f = 1 if self.facing.get_value() >= 0 else -1
        sw = np.sin(self.phase) * 0.55 * w
        lw = 9 * s

        bob = abs(np.sin(self.phase)) * 0.05 * s * w + (0.5 + 0.5 * np.sin(t * 2.4)) * 0.03 * s * still
        lift = self.breath.get_value() * 0.11 * s              # a deep breath lifts chest and shoulders
        hip = np.array([x, y + 1.1 * s, 0]) + UP * bob * 0.5
        neck = np.array([x, y + 2.05 * s, 0]) + UP * (bob + lift)
        sh = np.array([x, y + 1.88 * s, 0]) + UP * (bob + lift * 1.2)
        head_c = neck + UP * 0.42 * s

        def seg(start, ang, length):
            return start + np.array([np.sin(ang) * length * f, -np.cos(ang) * length, 0])

        # legs: thigh swings with the walk, the knee bends on the forward swing
        legs = VGroup()
        for k, sign in enumerate((1, -1)):
            th = sign * sw + (0.1 if k == 0 else -0.1)
            knee_bend = max(0.0, np.sin(self.phase + (0 if k == 0 else np.pi))) * 0.75 * w + 0.04
            knee = seg(hip, th, THIGH * s)
            foot = seg(knee, th - knee_bend, SHIN * s)
            legs.add(VMobject().set_points_as_corners([hip, knee, foot]))
        body = Line(hip, neck)

        swing = sw * 0.9 if w else 0.0
        idle = np.sin(t * 1.7) * 0.06 * still
        arms, hands = VGroup(), []
        for side, ang, bend, reach, sign in (("l", self.arm_l.get_value() - swing - idle, self.elbow_l.get_value(), self.reach_l.get_value(), -1),
                                             ("r", self.arm_r.get_value() + swing + idle, self.elbow_r.get_value(), self.reach_r.get_value(), 1)):
            elbow, hand = self._arm(sh, ang, bend, reach, self.target[side], head_c, f, sign)
            if side == "l":
                self._elbow_l = elbow
            arms.add(VMobject().set_points_as_corners([sh, elbow, hand]))
            hands.append((elbow, hand))
        extras = VGroup()
        fing = self.fingers.get_value()
        if fing > 0.01:                          # spread fingers on the right hand, wiggling
            elbow, hand = hands[1]
            d = (hand - elbow) / (np.linalg.norm(hand - elbow) + 1e-9)
            base = np.arctan2(d[1], d[0])
            for k, off in enumerate((-0.55, -0.18, 0.18, 0.55)):
                a = base + off * fing + np.sin(t * 22 + k * 1.7) * 0.28 * fing
                extras.add(Line(hand, hand + np.array([np.cos(a), np.sin(a), 0]) * 0.17 * s * (0.6 + 0.4 * fing)))
            extras.set_stroke(INK, lw * 0.55)
        figure = VGroup(legs, body, arms, extras).set_stroke(INK, lw)
        if len(extras):
            extras.set_stroke(INK, lw * 0.55)
        _round(figure)
        scarf = VGroup(Line(neck + LEFT * 0.17 * s, neck + RIGHT * 0.17 * s),
                       Line(neck + RIGHT * 0.1 * s * f, neck + np.array([-0.12 * s * f - sw * 0.08, -0.38 * s, 0]))).set_stroke(self.accent, 11 * s)
        head = Circle(radius=0.40 * s).set_fill(SKIN, 1).set_stroke(INK, lw * 0.95).move_to(head_c)
        gulp = self.gulp.get_value()
        if 0.02 < gulp < 0.98:                   # a lump travelling down the throat
            pos = neck + UP * 0.12 * s + (DOWN * 0.42 * s) * gulp
            extras.add(Circle(radius=0.075 * s).set_fill(INK, 1).set_stroke(width=0).move_to(pos + RIGHT * 0.02 * s * f))
        face = self._face(head_c, s, f)
        tilt = self.tilt.get_value() + np.sin(t * 1.1) * 0.05 * still
        face.rotate(tilt * f, about_point=head_c)
        # hands in front of the face go on top of it
        front = VGroup(*[arm for arm, r in zip(arms, (self.reach_l, self.reach_r)) if r.get_value() > 0.5])
        return VGroup(figure, scarf, head, face, front.copy() if len(front) else VGroup())

    def _face(self, c, s, f) -> VGroup:
        kind = FACES[int(round(self.face.get_value())) % len(FACES)]
        ex = c + np.array([0.06 * s * f, 0.05 * s, 0])
        eyes = VGroup(*[Dot(ex + np.array([dx * s * f, 0, 0]), radius=0.045 * s, color=INK) for dx in (0.0, 0.19)])
        mc = c + np.array([0.14 * s * f, -0.15 * s, 0])
        lw = 5 * s
        if kind == "happy":
            mouth = Arc(radius=0.12 * s, start_angle=-np.pi * 0.85, angle=np.pi * 0.7, arc_center=mc + UP * 0.08 * s).set_stroke(INK, lw)
        elif kind == "surprised":
            mouth = Circle(radius=0.06 * s).set_stroke(INK, lw).move_to(mc)
        elif kind == "scared":
            mouth = Ellipse(width=0.16 * s, height=0.11 * s).set_stroke(INK, lw).move_to(mc)
            eyes = VGroup(*[Circle(radius=0.06 * s).set_stroke(INK, 3 * s).set_fill(WHITE, 1).move_to(e.get_center()) for e in eyes],
                          *[Dot(e.get_center(), radius=0.025 * s, color=INK) for e in eyes])
        elif kind == "confused":
            mouth = VMobject().set_points_smoothly([mc + LEFT * 0.1 * s, mc + UP * 0.04 * s, mc + RIGHT * 0.1 * s + DOWN * 0.02 * s]).set_stroke(INK, lw)
            brow = Line(ex + np.array([0.12 * s * f, 0.12 * s, 0]), ex + np.array([0.27 * s * f, 0.17 * s, 0])).set_stroke(INK, 4 * s)
            mouth = VGroup(mouth, brow)
        elif kind == "thinking":
            eyes = VGroup(*[Dot(e.get_center() + UP * 0.05 * s + RIGHT * 0.03 * s * f, radius=0.045 * s, color=INK) for e in eyes])
            mouth = Line(mc + LEFT * 0.06 * s, mc + RIGHT * 0.08 * s).set_stroke(INK, lw)
        elif kind == "sleepy":
            eyes = VGroup(*[Line(e.get_center() + LEFT * 0.05 * s, e.get_center() + RIGHT * 0.05 * s).set_stroke(INK, 4 * s) for e in eyes])
            mouth = Line(mc + LEFT * 0.05 * s, mc + RIGHT * 0.05 * s).set_stroke(INK, lw)
        elif kind == "sad":
            mouth = Arc(radius=0.12 * s, start_angle=np.pi * 0.15, angle=np.pi * 0.7, arc_center=mc + DOWN * 0.1 * s).set_stroke(INK, lw)
        else:
            mouth = Line(mc + LEFT * 0.08 * s, mc + RIGHT * 0.08 * s).set_stroke(INK, lw)
        tongue = self.tongue.get_value()
        if tongue > 0.01:                                  # tongue out (pink), mouth open
            tip = mc + np.array([0.2 * s * f * tongue, -0.04 * s, 0])
            mouth = VGroup(Ellipse(width=0.15 * s, height=0.09 * s).set_stroke(INK, lw).set_fill(INK, 0.85).move_to(mc),
                           Line(mc, tip).set_stroke("#EF6F8E", 9 * s))
            _round(mouth)
        talk = self.talk.get_value()
        if talk > 0.01 and kind != "sleepy" and tongue <= 0.01:              # talking: the mouth opens and closes
            open_ = (0.5 + 0.5 * np.sin(self.t * 13.0)) * talk
            mouth = Ellipse(width=0.15 * s, height=max(0.02, 0.13 * open_) * s).set_stroke(INK, lw).set_fill(INK, 0.85).move_to(mc)
        # blink every few seconds (not when eyes are already closed or wide open in fear)
        if kind not in ("sleepy", "scared") and self.life.get_value() > 0.5 and (self.t % 3.4) < 0.13:
            eyes = VGroup(*[Line(e.get_center() + LEFT * 0.045 * s, e.get_center() + RIGHT * 0.045 * s).set_stroke(INK, 4 * s) for e in eyes])
        return VGroup(eyes, mouth)


def add_stick(scene, stick: Stick) -> Stick:
    scene.add(stick.clock, stick.mob)
    return stick


# ---- icons -----------------------------------------------------------------------------
ICONS = ["question", "exclaim", "bulb", "heart", "star", "zzz", "clock", "moon", "sun", "eye", "brain",
         "phone", "book", "apple", "check", "cross", "house", "drop", "bolt", "fire", "globe", "key", "music", "none"]


def icon(name: str, size: float = 1.0, pal: dict | None = None) -> VGroup:
    """A simple flat icon about `size` units across."""
    pal = pal or PALETTES["sunny"]
    r = size / 2
    lw = 6 * size
    g = VGroup()
    if name in ("question", "exclaim"):
        g = VGroup(Text("?" if name == "question" else "!", font=brand.SANS, weight=BOLD, color=pal["b"]).scale(size * 1.6))
    elif name == "bulb":
        glow_ = Circle(radius=r * 1.25).set_stroke(width=0).set_fill("#FFD166", 0.35)
        bulb = Circle(radius=r * 0.7).set_stroke(INK, lw * 0.7).set_fill("#FFD166", 1).shift(UP * r * 0.15)
        base = RoundedRectangle(width=r * 0.6, height=r * 0.42, corner_radius=0.04).set_stroke(INK, lw * 0.6).set_fill("#9AA5B1", 1).next_to(bulb, DOWN, buff=-0.02)
        rays = VGroup(*[Line(ORIGIN, UP * r * 0.25).shift(UP * r * 1.0).rotate(a, about_point=ORIGIN).set_stroke("#F4A300", lw * 0.6)
                        for a in (-1.1, -0.55, 0, 0.55, 1.1)]).shift(UP * r * 0.15)
        g = VGroup(glow_, rays, bulb, base)
    elif name == "heart":
        lobes = VGroup(*[Circle(radius=r * 0.5).shift(np.array([dx, r * 0.2, 0])) for dx in (-r * 0.45, r * 0.45)])
        tip = Polygon([-r * 0.93, r * 0.05, 0], [r * 0.93, r * 0.05, 0], [0, -r * 0.95, 0])
        g = VGroup(lobes, tip).set_stroke(width=0).set_fill(pal["b"], 1)
    elif name == "star":
        g = VGroup(Star(n=5, outer_radius=r, inner_radius=r * 0.45).set_stroke(width=0).set_fill("#FFD166", 1))
    elif name == "zzz":
        g = VGroup(*[Text("Z", font=brand.SANS, weight=BOLD, color=pal["c"]).scale(size * k).shift(np.array([dx, dy, 0]) * size)
                     for k, dx, dy in ((0.9, -0.25, -0.25), (0.65, 0.12, 0.08), (0.45, 0.38, 0.35))])
    elif name == "clock":
        g = VGroup(Circle(radius=r).set_stroke(INK, lw * 0.7).set_fill(WHITE, 1),
                   Line(ORIGIN, UP * r * 0.6).set_stroke(INK, lw * 0.6), Line(ORIGIN, RIGHT * r * 0.45).set_stroke(pal["b"], lw * 0.6),
                   Dot(radius=r * 0.08, color=INK))
    elif name == "moon":
        g = VGroup(Circle(radius=r).set_stroke(width=0).set_fill("#FFE066", 1),
                   Circle(radius=r * 0.85).set_stroke(width=0).set_fill(pal["top"], 1).shift(RIGHT * r * 0.45 + UP * r * 0.25))
    elif name == "sun":
        g = VGroup(Circle(radius=r * 0.55).set_stroke(width=0).set_fill("#FFD166", 1),
                   *[Line(ORIGIN, UP * r * 0.25).shift(UP * r * 0.75).rotate(a, about_point=ORIGIN).set_stroke("#FFB703", lw * 0.7)
                     for a in np.linspace(0, 2 * np.pi, 9)[:-1]])
    elif name == "eye":
        g = VGroup(Ellipse(width=size, height=size * 0.55).set_stroke(INK, lw * 0.7).set_fill(WHITE, 1),
                   Circle(radius=r * 0.3).set_stroke(width=0).set_fill(pal["c"], 1), Dot(radius=r * 0.12, color=INK))
    elif name == "brain":
        g = brain_shape(size, pal)
    elif name == "phone":
        g = VGroup(RoundedRectangle(width=size * 0.55, height=size, corner_radius=size * 0.08).set_stroke(INK, lw * 0.7).set_fill(pal["c"], 1),
                   RoundedRectangle(width=size * 0.45, height=size * 0.75, corner_radius=0.03).set_stroke(width=0).set_fill(WHITE, 0.9))
    elif name == "book":
        left = Polygon([-r, -r * 0.7, 0], [0, -r * 0.55, 0], [0, r * 0.75, 0], [-r, r * 0.6, 0]).set_stroke(INK, lw * 0.6).set_fill(WHITE, 1)
        right = left.copy().flip(UP, about_point=ORIGIN)
        g = VGroup(left, right, Line([0, -r * 0.55, 0], [0, r * 0.75, 0]).set_stroke(pal["b"], lw * 0.7))
    elif name == "apple":
        g = VGroup(Circle(radius=r * 0.75).set_stroke(width=0).set_fill(pal["b"], 1),
                   Line(UP * r * 0.6, UP * r * 0.95).set_stroke("#7B4B2A", lw * 0.6),
                   Ellipse(width=r * 0.5, height=r * 0.25).set_stroke(width=0).set_fill(pal["d"], 1).move_to(UP * r * 0.85 + RIGHT * r * 0.25))
    elif name == "check":
        g = VGroup(Circle(radius=r).set_stroke(width=0).set_fill("#06A77D", 1),
                   VMobject().set_points_as_corners([[-r * 0.45, 0, 0], [-r * 0.1, -r * 0.35, 0], [r * 0.5, r * 0.35, 0]]).set_stroke(WHITE, lw))
    elif name == "cross":
        g = VGroup(Circle(radius=r).set_stroke(width=0).set_fill("#EF476F", 1),
                   Line([-r * 0.4, -r * 0.4, 0], [r * 0.4, r * 0.4, 0]).set_stroke(WHITE, lw),
                   Line([-r * 0.4, r * 0.4, 0], [r * 0.4, -r * 0.4, 0]).set_stroke(WHITE, lw))
    elif name == "house":
        g = VGroup(Rectangle(width=size * 0.75, height=size * 0.55).set_stroke(width=0).set_fill(pal["d"], 1).shift(DOWN * r * 0.4),
                   Polygon([-r * 0.95, r * 0.15, 0], [r * 0.95, r * 0.15, 0], [0, r, 0]).set_stroke(width=0).set_fill(pal["c"], 1),
                   Rectangle(width=size * 0.2, height=size * 0.3).set_stroke(width=0).set_fill("#7B4B2A", 1).shift(DOWN * r * 0.55))
    elif name == "drop":
        d = VMobject().set_points_smoothly([[0, r, 0], [r * 0.6, -r * 0.2, 0], [0, -r * 0.8, 0], [-r * 0.6, -r * 0.2, 0], [0, r, 0]])
        g = VGroup(d.set_stroke(width=0).set_fill(pal["c"], 1))
    elif name == "bolt":
        g = VGroup(Polygon([r * 0.1, r, 0], [-r * 0.55, -r * 0.05, 0], [-r * 0.05, -r * 0.05, 0], [-r * 0.2, -r, 0], [r * 0.55, r * 0.15, 0], [r * 0.05, r * 0.15, 0])
                   .set_stroke(INK, lw * 0.4).set_fill("#FFD166", 1))
    elif name == "fire":
        outer = VMobject().set_points_smoothly([[0, r, 0], [r * 0.7, -r * 0.2, 0], [0, -r * 0.85, 0], [-r * 0.7, -r * 0.2, 0], [0, r, 0]])
        inner = outer.copy().scale(0.55).shift(DOWN * r * 0.25)
        g = VGroup(outer.set_stroke(width=0).set_fill("#F3722C", 1), inner.set_stroke(width=0).set_fill("#FFD166", 1))
    elif name == "globe":
        g = VGroup(Circle(radius=r).set_stroke(INK, lw * 0.5).set_fill(pal["c"], 1),
                   Ellipse(width=size * 0.45, height=size * 0.3).set_stroke(width=0).set_fill(pal["d"], 1).shift(LEFT * r * 0.25 + UP * r * 0.2),
                   Ellipse(width=size * 0.3, height=size * 0.4).set_stroke(width=0).set_fill(pal["d"], 1).shift(RIGHT * r * 0.35 + DOWN * r * 0.3))
    elif name == "key":
        g = VGroup(Circle(radius=r * 0.35).set_stroke("#F4A300", lw).shift(LEFT * r * 0.5),
                   Line(LEFT * r * 0.15, RIGHT * r * 0.9).set_stroke("#F4A300", lw),
                   Line(RIGHT * r * 0.6, RIGHT * r * 0.6 + DOWN * r * 0.3).set_stroke("#F4A300", lw))
    elif name == "music":
        g = VGroup(Line(UP * r * 0.8, DOWN * r * 0.4).set_stroke(INK, lw * 0.8).shift(RIGHT * r * 0.2),
                   Ellipse(width=r * 0.6, height=r * 0.42).set_stroke(width=0).set_fill(INK, 1).move_to(DOWN * r * 0.45 + LEFT * r * 0.05),
                   Line(UP * r * 0.8, UP * r * 0.5 + RIGHT * r * 0.55).set_stroke(INK, lw * 0.8).shift(RIGHT * r * 0.2))
    return g


def brain_shape(size: float = 2.0, pal: dict | None = None, color: str = "#FF8FAB", groove: str = "#E05780") -> VGroup:
    r = size / 2
    lobes = VGroup(*[Circle(radius=r * k).set_stroke(width=0).set_fill(color, 1).shift(np.array([dx, dy, 0]) * r)
                     for k, dx, dy in ((0.5, -0.45, 0.15), (0.52, 0.0, 0.32), (0.5, 0.45, 0.15), (0.46, -0.32, -0.25), (0.46, 0.32, -0.25), (0.5, 0, -0.02))])
    lw = 5 * size / 2
    grooves = VGroup(
        VMobject().set_points_smoothly([[0, 0.78 * r, 0], [-0.08 * r, 0.3 * r, 0], [0.06 * r, -0.2 * r, 0], [0, -0.6 * r, 0]]),
        *[VMobject().set_points_smoothly([[sx * 0.62 * r, 0.42 * r, 0], [sx * 0.32 * r, 0.3 * r, 0], [sx * 0.42 * r, 0.02 * r, 0], [sx * 0.2 * r, -0.05 * r, 0]]) for sx in (-1, 1)],
        *[VMobject().set_points_smoothly([[sx * 0.7 * r, -0.12 * r, 0], [sx * 0.5 * r, -0.32 * r, 0], [sx * 0.25 * r, -0.4 * r, 0]]) for sx in (-1, 1)],
    ).set_stroke(groove, lw)
    return VGroup(lobes, grooves)


def bubble(content, kind: str = "thought", pad: float = 0.25, pal: dict | None = None) -> VGroup:
    """A white bubble around `content` (a mobject). kind: thought | speech."""
    w, h = content.width + 2 * pad, content.height + 2 * pad
    body = RoundedRectangle(width=max(w, h * 1.1), height=h, corner_radius=min(h / 2, 0.5)).set_stroke(INK, 5).set_fill(WHITE, 1)
    body.move_to(content.get_center())
    tail = VGroup()
    if kind == "thought":
        tail = VGroup(Circle(radius=0.11).set_stroke(INK, 4).set_fill(WHITE, 1).next_to(body, DOWN, buff=0.06).shift(LEFT * body.width * 0.25),
                      Circle(radius=0.07).set_stroke(INK, 4).set_fill(WHITE, 1).next_to(body, DOWN, buff=0.3).shift(LEFT * body.width * 0.32))
    else:
        tri = Polygon([-0.15, 0, 0], [0.15, 0, 0], [-0.25, -0.35, 0]).set_stroke(INK, 5).set_fill(WHITE, 1)
        tri.next_to(body, DOWN, buff=-0.06).shift(LEFT * body.width * 0.2)
        cover = Rectangle(width=0.28, height=0.08).set_stroke(width=0).set_fill(WHITE, 1).move_to(tri.get_top() + DOWN * 0.04)
        tail = VGroup(tri, cover)
    return VGroup(tail, body, content.copy())


def card(w: float, h: float, color: str = WHITE, radius: float = 0.22, shadow: bool = True) -> VGroup:
    face = RoundedRectangle(width=w, height=h, corner_radius=radius).set_stroke(width=0).set_fill(color, 1)
    if not shadow:
        return VGroup(face)
    sh = face.copy().set_fill(INK, 0.12).shift(DOWN * 0.08 + RIGHT * 0.05)
    return VGroup(sh, face)


def pill(text: str, color: str, size: float = 0.42, text_color: str = WHITE) -> VGroup:
    t = label(text, size, text_color)
    p = RoundedRectangle(width=t.width + 0.6 * size / 0.42, height=t.height + 0.36 * size / 0.42,
                         corner_radius=(t.height + 0.36) / 2).set_stroke(width=0).set_fill(color, 1)
    return VGroup(p, t.move_to(p))


def caption_bar(text: str, pal: dict) -> VGroup:
    """A headline pill at the top of the frame (used by several templates)."""
    t = wrap_label(text, 0.62 if vertical() else 0.58, WHITE, chars=20 if vertical() else 38)
    bg = RoundedRectangle(width=t.width + 0.6, height=t.height + 0.4, corner_radius=0.25).set_stroke(width=0).set_fill(INK, 0.88)
    g = VGroup(bg, t.move_to(bg))
    g.move_to([0, fh() / 2 - g.height / 2 - fh() * (0.10 if vertical() else 0.07), 0])
    return g


def rest_of(scene, duration: float) -> float:
    return duration - getattr(scene.renderer, "time", 0.0)


def blobs(pal: dict, seed: int = 0, n: int = 5) -> VGroup:
    """Large soft circles drifting slowly in the background (gives plain backgrounds some life)."""
    rng = np.random.default_rng(seed)
    g = VGroup()
    for i in range(n):
        c = Circle(radius=rng.uniform(0.9, 2.0)).set_stroke(width=0)
        c.set_fill([pal["a"], pal["b"], pal["c"], pal["d"]][i % 4], 0.10)
        c.move_to([rng.uniform(-fw() / 2, fw() / 2), rng.uniform(-fh() / 2, fh() / 2), 0])
        c.v = np.array([rng.uniform(-0.12, 0.12), rng.uniform(-0.08, 0.08), 0])
        g.add(c)

    def drift(m, dt):
        for c in m:
            c.shift(c.v * dt)
    g.add_updater(drift)
    g.set_z_index(-15)
    return g


def person(color: str = INK, size: float = 0.6) -> VGroup:
    """A simple person icon (head + rounded body) for crowds and diagrams."""
    head = Circle(radius=size * 0.22).set_stroke(width=0).set_fill(color, 1).shift(UP * size * 0.32)
    body = RoundedRectangle(width=size * 0.62, height=size * 0.5, corner_radius=size * 0.24).set_stroke(width=0).set_fill(color, 1)
    body.shift(DOWN * size * 0.18)
    return VGroup(head, body)


class Budget:
    """Spreads a template's animations over the beat so the clip never runs longer than its voice.

    t(share, cap) -> seconds: `share` of the whole beat, but at most `cap` seconds.
    Keep the shares of one template below ~0.8 in total; the rest is a slow camera drift.
    """

    def __init__(self, duration: float):
        self.d = duration

    def t(self, share: float, cap: float) -> float:
        return max(0.15, min(cap, self.d * share))


def flat_bg(scene, pal: dict) -> None:
    """Gradient background with drifting blobs, no floor."""
    scene.add(background(pal, floor=False), blobs(pal, getattr(scene, "seed", 0)))


# How far the camera pushes in over a beat's remaining time. Strong enough that a held scene
# never looks frozen (4% read as a still frame on a phone).
DRIFT = 0.9


def drift_camera(scene, duration: float, scale: float = DRIFT):
    from manim import linear as _lin

    rest = rest_of(scene, duration)
    if rest > 0.15:
        scene.play(scene.camera.frame.animate(rate_func=_lin).scale(scale), run_time=rest)


def grid_shape(n: int, ratio: float) -> tuple[int, int]:
    """Columns and rows for n items: as close to `ratio` (cols / rows) as possible, few empty slots."""
    best = None
    for cols in range(1, n + 1):
        rows = -(-n // cols)
        score = 0.15 * (rows * cols - n) + abs(np.log((cols / rows) / ratio))
        if best is None or score < best[0]:
            best = (score, cols, rows)
    return best[1], best[2]


def center_last_row(group: VGroup, cols: int) -> None:
    """arrange_in_grid leaves a short last row on the left; move it to the middle."""
    n = len(group)
    left = n % cols
    if left and n > cols:
        row = group[n - left:]
        full = group[n - left - cols:n - left]
        VGroup(*row).set_x(VGroup(*full).get_x())


def fit_between(mob, top: float, bottom: float, max_width: float | None = None):
    """Scale down (never up) and centre a mobject vertically between two y values."""
    if mob.height > top - bottom:
        mob.scale_to_fit_height(top - bottom)
    if max_width and mob.width > max_width:
        mob.scale_to_fit_width(max_width)
    return mob.set_y((top + bottom) / 2)


def parse_pair(item: str, default_left: str = "") -> tuple[str, str]:
    """'icon|text' or '1904|text' -> (left, right). Without '|' the left part is default_left."""
    if "|" in item:
        a, b = item.split("|", 1)
        return a.strip(), b.strip()
    return default_left, item.strip()


# Literal types for template params (Studio shows them as dropdowns)
from typing import Literal as _Literal  # noqa: E402

IconName = _Literal[tuple(ICONS)]
PaletteName = _Literal[("auto", *PALETTE_NAMES)]
