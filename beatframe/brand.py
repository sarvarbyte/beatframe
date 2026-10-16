"""Brand tokens shared by every template (Human Unknowns 'One Light' look)."""

from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
MUSIC_MOOD = "wonder"   # generated background music: mystery | wonder | epic | tense | calm

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
    for folder in (FONT_DIR, APP_DIR / "fonts"):      # app-folder fonts/ holds a profile's own fonts
        for ttf in list(folder.glob("*.ttf")) + list(folder.glob("*.otf")):
            manimpango.register_font(str(ttf))


# ---- niche profile -------------------------------------------------------------------------
# profile.yaml in the app folder (copied from profiles/<name>.yaml by `beatframe profile use <name>`)
# overrides the look above for another channel: colours, fonts, music mood, picture style, voice.
# Without it everything stays Human Unknowns' 'One Light' look.
PROFILE_FILE = APP_DIR / "profile.yaml"
PROFILE_TEXT = ""
PROFILE: dict = {}
IMAGE_STYLE = ""      # appended to every picture prompt (beatframe image-prompts)
CHANNEL = "Human Unknowns"
VOICE = ""            # e.g. "kokoro am_michael"; ovoz.txt still wins when it exists


def _load_profile() -> None:
    global PROFILE_TEXT, PROFILE, NIGHT, DEEP, PAPER, GLOW, EMBER, DIM, SERIF, SANS, MUSIC_MOOD
    global IMAGE_STYLE, CHANNEL, VOICE
    try:
        import yaml

        PROFILE_TEXT = PROFILE_FILE.read_text(encoding="utf-8")
        PROFILE = yaml.safe_load(PROFILE_TEXT) or {}
    except (OSError, ImportError):
        return
    except Exception:  # noqa: BLE001 - a broken profile must not stop the app
        PROFILE_TEXT, PROFILE = "", {}
        return
    c = PROFILE.get("colors") or {}
    NIGHT, DEEP = c.get("background", NIGHT), c.get("background_dark", DEEP)
    PAPER, GLOW = c.get("text", PAPER), c.get("light", GLOW)
    EMBER, DIM = c.get("accent", EMBER), c.get("muted", DIM)
    f = PROFILE.get("fonts") or {}
    SERIF, SANS = f.get("title", SERIF), f.get("body", SANS)
    MUSIC_MOOD = PROFILE.get("music_mood", MUSIC_MOOD)
    IMAGE_STYLE = PROFILE.get("image_style", IMAGE_STYLE)
    CHANNEL = PROFILE.get("channel", CHANNEL)
    VOICE = PROFILE.get("voice", VOICE)


_load_profile()
