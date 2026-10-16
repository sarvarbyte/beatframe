"""Video formats: the single place that knows what "short" and "long" mean.

Everything else asks this module for sizes, so there are no scattered 9:16 checks.

  long  -> 16:9, 1920x1080  (YouTube, documentaries)  - the original Beatframe look
  short -> 9:16, 1080x1920  (Shorts, Reels, TikTok)

Manim coordinates: long frames are 14.2 x 8 units. Short frames are 8 x 14.2 for templates
that lay themselves out responsively; templates drawn for 16:9 declare how much of their
width must stay visible (Template.vertical_width) and get a wider portrait view.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

FormatName = Literal["long", "short"]
DEFAULT_FORMAT: FormatName = "long"
SHORT_SIDE_UNITS = 8.0


@dataclass(frozen=True)
class VideoFormat:
    name: FormatName
    label: str
    aspect: str
    width: int
    height: int
    preview_width: int
    preview_height: int
    description: str

    @property
    def vertical(self) -> bool:
        return self.height > self.width

    @property
    def suffix(self) -> str:
        """Added to cache folders and output names. Long keeps the original names."""
        return "" if self.name == "long" else f"_{self.name}"

    def size(self, preview: bool = False) -> tuple[int, int]:
        return (self.preview_width, self.preview_height) if preview else (self.width, self.height)

    def to_dict(self) -> dict:
        return {
            "name": self.name, "label": self.label, "aspect": self.aspect,
            "width": self.width, "height": self.height, "description": self.description,
        }


FORMATS: dict[str, VideoFormat] = {
    "long": VideoFormat("long", "Long", "16:9", 1920, 1080, 854, 480,
                        "Landscape video for YouTube and documentary content"),
    "short": VideoFormat("short", "Short", "9:16", 1080, 1920, 480, 854,
                         "Vertical video for Shorts, Reels and TikTok"),
}


def get_format(name: str | None) -> VideoFormat:
    key = (name or DEFAULT_FORMAT).lower()
    if key not in FORMATS:
        raise ValueError(f"unknown video format '{name}'. Use: {', '.join(FORMATS)}")
    return FORMATS[key]


def frame_size(pixel_width: int, pixel_height: int, vertical_width: float = SHORT_SIDE_UNITS) -> tuple[float, float]:
    """Manim frame (width, height) in scene units for a pixel size.

    Landscape: the short side is 8 units (Manim's default 14.2 x 8 frame). Sizes within 1% of
    16:9 (like the 854x480 preview) snap to exactly 16:9, so long renders are identical to
    the original Beatframe.

    Portrait: `vertical_width` units fit across the frame. 8 (default) is the native 8 x 14.2
    frame that responsive templates lay out for; a template drawn for 16:9 can ask for a
    wider view (up to 14.2) so its composition stays inside the frame.
    """
    ratio = max(pixel_width, pixel_height) / min(pixel_width, pixel_height)
    if abs(ratio - 16 / 9) < 0.01 * 16 / 9:
        ratio = 16 / 9
    if pixel_width >= pixel_height:
        return SHORT_SIDE_UNITS * ratio, SHORT_SIDE_UNITS
    return vertical_width, vertical_width * ratio
