"""Brand tokens shared by every template (Human Unknowns 'One Light' look)."""

from pathlib import Path

NIGHT = "#0c1729"   # background
DEEP = "#08101e"    # darker background accents
PAPER = "#f5eedb"   # primary text and line work
GLOW = "#fbaa58"    # warm light
EMBER = "#f08034"   # single accent
DIM = "#5a6b88"     # secondary text, guides

SERIF = "Playfair Display"
SANS = "Figtree"

FONT_DIR = Path(__file__).parent / "assets" / "fonts"


def register_fonts() -> None:
    """Make the bundled fonts available to Manim/Pango without installing them."""
    try:
        import manimpango
    except ImportError:  # pragma: no cover
        return
    for ttf in FONT_DIR.glob("*.ttf"):
        manimpango.register_font(str(ttf))
