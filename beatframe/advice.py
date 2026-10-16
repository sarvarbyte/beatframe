"""Script advice: the channel's retention rules checked on the YAML, before anything is rendered.

These are warnings, not errors: the script still renders. They catch what made past Shorts lose
viewers in the first seconds (a long or question-shaped first line, a text card instead of motion,
text cards in a row, Shorts longer than 25 s).
"""

from __future__ import annotations

from beatframe.captions import TEXT_SCENES
from beatframe.schema import Project

WORDS_PER_SECOND = 2.4
SLOW_OPENERS = {"title_card", "question_hook", "statement"}
STILL_ACTIONS = {"idle", "sleep"}


def seconds(text: str) -> float:
    return len(text.split()) / WORDS_PER_SECOND


def script_advice(project: Project, video_format: str | None = None) -> list[str]:
    fmt = video_format or project.video.format
    beats = project.beats
    tips: list[str] = []
    if not beats:          # an imported video: nothing to advise on
        return tips
    first = beats[0]
    n_first = len(first.text.split())

    if fmt == "short":
        total = sum(max(b.min_duration, seconds(b.text) + 0.35) for b in beats)
        if total > 26:
            tips.append(f"About {total:.0f} s long. Shorts that hold viewers here are 20-25 s: cut a beat.")
        if n_first > 6:
            tips.append(f"Beat 1 has {n_first} words. A 4-5-word claim hooks better (\"You can't see your nose.\").")
    elif seconds(" ".join(b.text for b in beats[:3])) > 15 and n_first > 12:
        tips.append("The first line is long. The first 15 s should say the title's claim straight away.")

    if first.text.strip().endswith("?"):
        tips.append("Beat 1 is a question. On this channel a You/Your claim works better than a question.")
    if first.scene in SLOW_OPENERS:
        tips.append(f"Beat 1 opens on a text card ({first.scene}). Start with motion: stick_scene with an action.")
    elif first.scene == "stick_scene" and first.params.get("action", "walk_in") in STILL_ACTIONS:
        tips.append("Beat 1's character stands still. Pick an action (walk_in, run, freeze, scared, point...).")

    short = fmt == "short"
    run = []
    for i, b in enumerate(beats + [None], 1):
        if b is not None and b.scene in TEXT_SCENES:
            run.append(i)
            continue
        if len(run) >= (3 if short else 4):
            tips.append(f"Beats {run[0]}-{run[-1]} are all text cards: nothing moves for a while. "
                        "Turn one into a visual scene.")
        run = []

    limit = 6 if short else 12          # seconds one picture can carry
    long_beats = [i for i, b in enumerate(beats, 1) if seconds(b.text) > limit]
    if long_beats:
        listed = ", ".join(map(str, long_beats[:8])) + (f" and {len(long_beats) - 8} more" if len(long_beats) > 8 else "")
        tips.append(f"Beat{'s' if len(long_beats) > 1 else ''} {listed} run{'' if len(long_beats) > 1 else 's'} "
                    f"longer than {limit} s on one picture. Split {'them' if len(long_beats) > 1 else 'it'} "
                    "so the screen changes more often.")

    if fmt == "short" and not any(w in b.text.lower() for b in beats for w in ("try", "right now", "go ahead")):
        tips.append("No \"try it right now\" moment. The Shorts that held best let viewers test the claim.")
    return tips
