"""Thumbnail Lab: design YouTube thumbnail variants from the video's own frames.

A variant = a source frame + a few design choices (text, layout, colour style, crop, light).
Variants are drawn with Pillow into output/thumbs<suffix>/lab_<id>.jpg (JPEG, under YouTube's
2 MB limit), so the existing Publish upload picks them up like any other thumbnail candidate.
Their settings and the one chosen for publishing live in output/thumb_lab<suffix>.json.
"""

from __future__ import annotations

import json
import secrets
import subprocess
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from beatframe import brand

SIZES = {"long": (1280, 720), "short": (1080, 1920)}
STYLES = {
    # name: (text fill, outline/shadow, box fill or None, accent)
    "bold": ("#ffffff", "#1e2140", None, "#ffd34d"),
    "pop": ("#1e2140", None, "#ffd34d", "#ff7e67"),
    "ember": ("#ffffff", None, "#f08034", "#ffd34d"),
    "violet": ("#ffffff", None, "#5b4cf0", "#ffd34d"),
    "clean": ("#ffffff", "#000000", None, "#a78bfa"),
}
POSITIONS = ("top", "center", "bottom")
DEFAULTS = {"source": "", "text": "", "sub": "", "position": "bottom", "style": "bold", "font": "sans",
            "size": 1.0, "zoom": 1.0, "fx": 0.5, "fy": 0.5, "darken": 0.15, "saturation": 1.15,
            "contrast": 1.08, "badge": "", "align": "left"}


class LabError(RuntimeError):
    pass


def thumbs_dir(out_dir: Path, suffix: str) -> Path:
    return out_dir / f"thumbs{suffix}"


def meta_file(out_dir: Path, suffix: str) -> Path:
    return out_dir / f"thumb_lab{suffix}.json"


def load(out_dir: Path, suffix: str) -> dict:
    try:
        data = json.loads(meta_file(out_dir, suffix).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    data.setdefault("variants", [])
    data.setdefault("selected", "")
    # drop entries whose image was deleted by hand
    tdir = thumbs_dir(out_dir, suffix)
    data["variants"] = [v for v in data["variants"] if (tdir / v["file"]).exists()]
    if data["selected"] and not (tdir / data["selected"]).exists():
        data["selected"] = ""
    return data


def save(out_dir: Path, suffix: str, data: dict) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    meta_file(out_dir, suffix).write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def sources(out_dir: Path, suffix: str) -> list[str]:
    """Frames that can be a thumbnail's picture: the render's thumbnail candidates and grabbed frames
    (never the lab's own variants)."""
    tdir = thumbs_dir(out_dir, suffix)
    if not tdir.exists():
        return []
    return sorted(p.name for p in tdir.iterdir()
                  if p.suffix.lower() in (".png", ".jpg", ".jpeg") and not p.name.startswith("lab_"))


def grab_frame(video: Path, seconds: float, out_dir: Path, suffix: str) -> str:
    """Take a full-size still from the video at `seconds` and add it to the sources."""
    if not video.exists():
        raise LabError("Render the video first: frames are taken from it.")
    tdir = thumbs_dir(out_dir, suffix)
    tdir.mkdir(parents=True, exist_ok=True)
    name = f"frame_{seconds:07.2f}s.png".replace(".", "_", 1)
    res = subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0.0, seconds):.2f}", "-i", str(video),
                          "-frames:v", "1", str(tdir / name)], capture_output=True, text=True)
    if res.returncode != 0 or not (tdir / name).exists():
        raise LabError("Could not take a frame at that time.")
    return name


def clean(settings: dict) -> dict:
    """Settings from a form, with types and ranges fixed (anything unknown falls back to the default)."""
    s = dict(DEFAULTS)
    for k, v in (settings or {}).items():
        if k not in DEFAULTS:
            continue
        if isinstance(DEFAULTS[k], float):
            try:
                v = float(v)
            except (TypeError, ValueError):
                continue
        s[k] = v
    s["text"], s["sub"], s["badge"] = str(s["text"])[:60], str(s["sub"])[:80], str(s["badge"])[:16]
    s["position"] = s["position"] if s["position"] in POSITIONS else "bottom"
    s["style"] = s["style"] if s["style"] in STYLES else "bold"
    s["font"] = s["font"] if s["font"] in ("sans", "serif") else "sans"
    s["align"] = s["align"] if s["align"] in ("left", "center") else "left"
    clamp = {"size": (0.6, 1.6), "zoom": (1.0, 2.0), "fx": (0, 1), "fy": (0, 1), "darken": (0, 0.7),
             "saturation": (0.5, 1.8), "contrast": (0.7, 1.6)}
    for k, (lo, hi) in clamp.items():
        s[k] = min(hi, max(lo, float(s[k])))
    return s


def _font(kind: str, px: int, weight: str = "Black") -> ImageFont.FreeTypeFont:
    path = brand.FONT_DIR / ("PlayfairDisplay.ttf" if kind == "serif" else "Figtree.ttf")
    f = ImageFont.truetype(str(path), px)
    try:
        f.set_variation_by_name(weight)
    except (OSError, ValueError, AttributeError):
        pass
    return f


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        trial = f"{cur} {w}".strip()
        if draw.textlength(trial, font=font) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines[:3]


def _cover(img: Image.Image, size: tuple[int, int], zoom: float, fx: float, fy: float) -> Image.Image:
    """Scale to cover the thumbnail, zoom in, and keep the focus point (fx, fy) in view."""
    W, H = size
    scale = max(W / img.width, H / img.height) * zoom
    img = img.resize((max(W, round(img.width * scale)), max(H, round(img.height * scale))), Image.LANCZOS)
    x = round((img.width - W) * fx)
    y = round((img.height - H) * fy)
    return img.crop((x, y, x + W, y + H))


def render(src: Path, settings: dict, fmt: str) -> Image.Image:
    s = clean(settings)
    W, H = SIZES.get(fmt, SIZES["long"])
    img = Image.open(src).convert("RGB")
    img = _cover(img, (W, H), s["zoom"], s["fx"], s["fy"])
    img = ImageEnhance.Color(img).enhance(s["saturation"])
    img = ImageEnhance.Contrast(img).enhance(s["contrast"])
    if s["darken"] > 0 and (s["text"] or s["sub"]):
        # darken towards the text so it stays readable; the rest of the picture keeps its light
        grad = Image.new("L", (1, 256))
        for i in range(256):
            t = i / 255
            a = {"top": 1 - t, "bottom": t, "center": 1 - abs(t - 0.5) * 2}[s["position"]]
            grad.putpixel((0, i), round(255 * s["darken"] * min(1, a * 1.3)))
        mask = grad.resize((W, H))
        img = Image.composite(Image.new("RGB", (W, H), (12, 14, 30)), img, mask)
    draw = ImageDraw.Draw(img)
    fill, outline, box, accent = STYLES[s["style"]]
    unit = min(W, H)
    margin = round(unit * 0.07)
    blocks = []
    if s["text"]:
        f = _font(s["font"], round(unit * 0.15 * s["size"]))
        blocks.append(("main", _wrap(draw, s["text"].upper() if s["font"] == "sans" else s["text"], f, W - 2 * margin), f))
    if s["sub"]:
        f2 = _font("sans", round(unit * 0.058 * s["size"]), "Bold")
        blocks.append(("sub", _wrap(draw, s["sub"], f2, W - 2 * margin), f2))
    gap = round(unit * 0.02)
    heights = []
    for _, lines, f in blocks:
        asc, desc = f.getmetrics()
        heights.append(len(lines) * (asc + desc) + (len(lines) - 1) * gap)
    total = sum(heights) + gap * 2 * max(0, len(blocks) - 1)
    y = {"top": margin, "center": (H - total) // 2, "bottom": H - margin - total}[s["position"]]
    for (kind, lines, f), h in zip(blocks, heights):
        asc, desc = f.getmetrics()
        for line in lines:
            tw = draw.textlength(line, font=f)
            x = margin if s["align"] == "left" else round((W - tw) / 2)
            col = fill if kind == "main" else ("#ffffff" if box is None else fill)
            if box and kind == "main":
                pad = round(unit * 0.018)
                draw.rounded_rectangle((x - pad, y - pad // 2, x + tw + pad, y + asc + desc + pad // 2),
                                       radius=round(unit * 0.02), fill=box)
            stroke = round(f.size * 0.07) if outline and kind == "main" else 0
            if not box and kind == "main":     # a soft shadow so white text reads on any frame
                shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
                ImageDraw.Draw(shadow).text((x + 4, y + 6), line, font=f, fill=(0, 0, 0, 150))
                img.paste(shadow.filter(ImageFilter.GaussianBlur(8)), (0, 0), shadow.filter(ImageFilter.GaussianBlur(8)))
                draw = ImageDraw.Draw(img)
            draw.text((x, y), line, font=f, fill=col, stroke_width=stroke, stroke_fill=outline or None)
            y += asc + desc + gap
        y += gap * 2
    if s["badge"]:
        fb = _font("sans", round(unit * 0.05), "Black")
        tw = draw.textlength(s["badge"].upper(), font=fb)
        asc, desc = fb.getmetrics()
        pad = round(unit * 0.02)
        bx, by = W - margin - tw - 2 * pad, margin
        draw.rounded_rectangle((bx, by, bx + tw + 2 * pad, by + asc + desc + pad), radius=pad, fill=accent)
        draw.text((bx + pad, by + pad // 2), s["badge"].upper(), font=fb, fill="#1e2140")
    return img


def save_jpeg(img: Image.Image, dest: Path) -> None:
    for q in (90, 82, 72, 60):          # stay under YouTube's 2 MB thumbnail limit
        img.save(dest, "JPEG", quality=q, optimize=True, progressive=True)
        if dest.stat().st_size < 1_900_000:
            return


def create(out_dir: Path, suffix: str, fmt: str, settings: dict, replace: str = "") -> dict:
    s = clean(settings)
    tdir = thumbs_dir(out_dir, suffix)
    src = tdir / s["source"]
    if not s["source"] or not src.exists() or s["source"].startswith("lab_"):
        raise LabError("Pick a frame for the picture first.")
    data = load(out_dir, suffix)
    vid = replace if replace and any(v["id"] == replace for v in data["variants"]) else secrets.token_hex(3)
    name = f"lab_{vid}.jpg"
    save_jpeg(render(src, s, fmt), tdir / name)
    entry = {"id": vid, "file": name, "settings": s, "created": time.strftime("%Y-%m-%d %H:%M"),
             "label": s["text"] or s["sub"] or "No text"}
    data["variants"] = [v for v in data["variants"] if v["id"] != vid] + [entry]
    save(out_dir, suffix, data)
    return entry


def delete(out_dir: Path, suffix: str, vid: str) -> None:
    data = load(out_dir, suffix)
    for v in data["variants"]:
        if v["id"] == vid:
            (thumbs_dir(out_dir, suffix) / v["file"]).unlink(missing_ok=True)
            if data["selected"] == v["file"]:
                data["selected"] = ""
    data["variants"] = [v for v in data["variants"] if v["id"] != vid]
    save(out_dir, suffix, data)


def select(out_dir: Path, suffix: str, file: str) -> None:
    """Choose the thumbnail Publish should upload ('' = let YouTube pick)."""
    data = load(out_dir, suffix)
    if file and not (thumbs_dir(out_dir, suffix) / file).exists():
        raise LabError("That thumbnail no longer exists.")
    data["selected"] = file
    save(out_dir, suffix, data)
