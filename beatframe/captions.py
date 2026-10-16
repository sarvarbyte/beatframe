"""Word-by-word captions: voice word timings -> short phrases -> an .ass file that ffmpeg burns in.

The words shown are the script's own (with its punctuation and spelling); the voice only supplies
the timing. Both are matched letter by letter, so "10%" in the script still lines up with however
the voice split it.

Styles:
  pop     - 2-4 words at a time, upper case; the word being spoken turns warm and grows a little
  karaoke - the phrase fills with colour as it is spoken
  plain   - the phrase, no highlight
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

from beatframe import brand
from beatframe.schema import Beat, Captions

# Scenes that already put the sentence on screen: no captions on top of them unless the beat says so.
TEXT_SCENES = {"kinetic_text", "statement", "title_card", "question_hook", "myth_fact", "stick_talk"}

BREAK_AFTER = (".", ",", "!", "?", ";", ":", "—", "–", "…")


@dataclass
class Word:
    text: str
    start: float
    end: float


# Scenes whose `caption` param is the headline at the top; in every other scene a caption is written
# under the picture, right where the burned-in captions go, so the two would overlap.
TOP_CAPTION_SCENES = {"stick_scene"}


def beat_wants_captions(beat: Beat) -> bool:
    if beat.captions is not None:
        return beat.captions
    if beat.scene in TEXT_SCENES:
        return False
    return not (str(beat.params.get("caption") or "").strip() and beat.scene not in TOP_CAPTION_SCENES)


# ---- timing -----------------------------------------------------------------------------
def _norm(s: str) -> str:
    return re.sub(r"[^0-9a-z]", "", s.lower())


def align(text: str, timed: list[dict]) -> list[Word]:
    """Give every word of the script a start and end taken from the voice's word timings."""
    tokens = text.split()
    if not tokens:
        return []
    stream, owner = [], []
    for k, w in enumerate(timed):
        for ch in _norm(w["word"]):
            stream.append(ch)
            owner.append(k)
    chars, char_tok = [], []
    for k, t in enumerate(tokens):
        for ch in _norm(t):
            chars.append(ch)
            char_tok.append(k)

    spans: list[list[float] | None] = [None] * len(tokens)
    token_of: dict[int, int] = {}          # voice word -> script word it was matched to

    def stretch(k: int, w: dict) -> None:
        span = spans[k]
        if span is None:
            spans[k] = [w["start"], w["end"]]
        else:
            span[0], span[1] = min(span[0], w["start"]), max(span[1], w["end"])

    for a, b, n in SequenceMatcher(None, chars, stream, autojunk=False).get_matching_blocks():
        for j in range(n):
            token_of[owner[b + j]] = char_tok[a + j]
            stretch(char_tok[a + j], timed[owner[b + j]])
    # tokens with no letters ("." "%" "—"): their time belongs to the word before them
    last = None
    for k, w in enumerate(timed):
        if k in token_of:
            last = token_of[k]
        elif last is not None and not _norm(w["word"]):
            stretch(last, w)

    # words the voice said differently (or not at all): share the gap between their neighbours
    end_all = timed[-1]["end"] if timed else 0.0
    k = 0
    while k < len(tokens):
        if spans[k] is not None:
            k += 1
            continue
        j = k
        while j < len(tokens) and spans[j] is None:
            j += 1
        lo = spans[k - 1][1] if k > 0 else (timed[0]["start"] if timed else 0.0)
        hi = spans[j][0] if j < len(tokens) else max(lo, end_all)
        step = max(hi - lo, 0.0) / (j - k)
        for m in range(k, j):
            spans[m] = [lo + step * (m - k), lo + step * (m - k + 1)]
        k = j
    return [Word(t, s[0], max(s[1], s[0] + 0.05)) for t, s in zip(tokens, spans)]


def group(words: list[Word], max_words: int, max_chars: int, max_secs: float = 1.6) -> list[list[Word]]:
    """Cut the words into short phrases: at punctuation, at pauses, or when a phrase gets long."""
    out, cur = [], []
    for i, w in enumerate(words):
        if cur and (len(cur) >= max_words
                    or len(" ".join(x.text for x in cur + [w])) > max_chars
                    or w.end - cur[0].start > max_secs
                    or w.start - cur[-1].end > 0.4):
            out.append(cur)
            cur = []
        cur.append(w)
        if w.text.endswith(BREAK_AFTER):
            out.append(cur)
            cur = []
    if cur:
        out.append(cur)
    return out


# ---- .ass output ------------------------------------------------------------------------
def _ass_color(hex_color: str, alpha: int = 0) -> str:
    r, g, b = hex_color.lstrip("#")[0:2], hex_color.lstrip("#")[2:4], hex_color.lstrip("#")[4:6]
    return f"&H{alpha:02X}{b}{g}{r}".upper()


def _ts(t: float) -> str:
    cs = int(round(max(t, 0.0) * 100))
    h, cs = divmod(cs, 360000)
    m, cs = divmod(cs, 6000)
    s, cs = divmod(cs, 100)
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _clean(s: str) -> str:
    return s.replace("\\", "/").replace("{", "(").replace("}", ")")


def build_ass(beats: list[tuple[float, float, list[Word]]], settings: Captions, width: int, height: int) -> str:
    """beats: (start in the video, end in the video, words timed from the beat's start)."""
    vertical = height > width
    unit = height / 1920 if vertical else height / 1080        # sizes below are for full HD
    size = round((82 if vertical else 62) * unit)
    outline = round((7 if vertical else 5) * unit, 1)
    shadow = round(3 * unit, 1)
    if settings.position == "center":
        align_code, margin_v = 5, 0
    else:   # lower: above the Shorts title/buttons; near the bottom on 16:9
        align_code, margin_v = 2, round((600 if vertical else 90) * unit)
    side = round((90 if vertical else 160) * unit)
    max_words, max_chars = (3, 18) if vertical else (5, 32)
    upper = settings.style == "pop"

    paper, glow = _ass_color(brand.PAPER), _ass_color(brand.GLOW)
    edge, back = _ass_color(brand.DEEP), _ass_color(brand.DEEP, 0x60)
    primary, secondary = (glow, paper) if settings.style == "karaoke" else (paper, paper)
    lines = [
        "[Script Info]", "ScriptType: v4.00+", f"PlayResX: {width}", f"PlayResY: {height}",
        "WrapStyle: 0", "ScaledBorderAndShadow: yes", "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, "
        "Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        f"Style: Cap,{brand.SANS},{size},{primary},{secondary},{edge},{back},-1,0,0,0,100,100,1,0,1,"
        f"{outline},{shadow},{align_code},{side},{side},{margin_v},1",
        "", "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    def event(t0: float, t1: float, text: str) -> None:
        if t1 - t0 >= 0.02:
            lines.append(f"Dialogue: 0,{_ts(t0)},{_ts(t1)},Cap,,0,0,0,,{text}")

    for b_start, b_end, words in beats:
        phrases = group(words, max_words, max_chars)
        for p_i, phrase in enumerate(phrases):
            t0 = b_start + phrase[0].start
            nxt = b_start + phrases[p_i + 1][0].start if p_i + 1 < len(phrases) else None
            t1 = min(nxt if nxt is not None else b_start + phrase[-1].end + 0.6, b_end)
            texts = [_clean(w.text.upper() if upper else w.text) for w in phrase]
            if settings.style == "plain":
                event(t0, t1, "{\\fad(60,0)}" + " ".join(texts))
            elif settings.style == "karaoke":
                parts, t = [], t0
                for w, txt in zip(phrase, texts):
                    w_end = b_start + w.end
                    parts.append(f"{{\\kf{max(1, round((w_end - t) * 100))}}}{txt}")
                    t = w_end
                event(t0, t1, "{\\fad(60,0)}" + " ".join(parts))
            else:   # pop: one event per spoken word, that word highlighted
                for k, w in enumerate(phrase):
                    s0 = t0 if k == 0 else b_start + w.start
                    s1 = b_start + phrase[k + 1].start if k + 1 < len(phrase) else t1
                    hot = (f"{{\\c{glow}\\fscx108\\fscy108}}{texts[k]}{{\\c{paper}\\fscx100\\fscy100}}")
                    body = " ".join(hot if m == k else texts[m] for m in range(len(phrase)))
                    event(s0, min(s1, t1), ("{\\fad(70,0)}" if k == 0 else "") + body)
    return "\n".join(lines) + "\n"


def write_ass(path: Path, beats: list[tuple[float, float, list[Word]]], settings: Captions,
              width: int, height: int) -> bool:
    """Write the captions file. Returns False (and writes nothing) when there is nothing to show."""
    if not any(words for _, _, words in beats):
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_ass(beats, settings, width, height), encoding="utf-8")
    return True
