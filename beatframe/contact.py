"""Contact sheets: first / middle / last frame of rendered clips, side by side, for visual QA.

    beatframe contact-sheet neural_impulse bone_conduction --format long --format short

Renders each template at the eco preset (real Manim renders, cached in ~/.beatframe/template_previews)
and writes contact_sheet_<format>.png.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from beatframe import brand

POINTS = (0.04, 0.5, 0.97)       # first frame (just after the 0.3 s snap-in), middle, end


def frames(clip: Path, duration: float, points=POINTS, width: int = 480) -> list[Image.Image]:
    out = []
    with tempfile.TemporaryDirectory() as tmp:
        for k, f in enumerate(points):
            png = Path(tmp) / f"{k}.png"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0.0, duration * f):.3f}", "-i", str(clip),
                            "-frames:v", "1", "-vf", f"scale={width}:-2", str(png)], check=True)
            out.append(Image.open(png).convert("RGB"))
    return out


def sheet(rows: list[tuple[str, list[Image.Image]]], out: Path, labels=("start", "middle", "end")) -> Path:
    if not rows:
        raise ValueError("nothing to put on the sheet")
    fw, fh = rows[0][1][0].size
    pad, head = 14, 34
    W = pad + len(rows[0][1]) * (fw + pad)
    H = pad + len(rows) * (fh + head + pad)
    img = Image.new("RGB", (W, H), (18, 16, 36))
    d = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype(str(brand.FONT_DIR / "Figtree.ttf"), 20)
    except OSError:
        font = ImageFont.load_default()
    y = pad
    for name, ims in rows:
        for k, im in enumerate(ims):
            x = pad + k * (fw + pad)
            d.text((x, y + 6), f"{name} · {labels[k] if k < len(labels) else k}", fill=(230, 226, 245), font=font)
            img.paste(im, (x, y + head))
        y += fh + head + pad
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out
