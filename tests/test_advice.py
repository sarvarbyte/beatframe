"""Retention tips on a script, before rendering."""

from beatframe.advice import script_advice
from beatframe.schema import Beat, Project


def _short(*beats):
    return Project(title="t", video={"format": "short"}, beats=[Beat(text=t, scene=s, params=p) for t, s, p in beats])


def test_a_good_short_gets_no_tips():
    p = _short(("You can't see your nose.", "stick_scene", {"action": "run"}),
               ("Your brain deletes it.", "brain_light", {}),
               ("Try it right now.", "kinetic_text", {"text": "Try it"}),
               ("Close one eye.", "body_map", {}))
    assert script_advice(p) == []


def test_slow_question_opener_and_text_cards_in_a_row_are_flagged():
    p = _short(("Why do you never notice your own nose at all, every single day?", "question_hook", {}),
               ("Because.", "statement", {}), ("Your brain.", "kinetic_text", {}), ("Hides it.", "statement", {}))
    tips = " | ".join(script_advice(p))
    for expected in ("Beat 1 has 13 words", "Beat 1 is a question", "opens on a text card",
                     "Beats 1-4 are all text cards", "try it right now"):
        assert expected in tips


def test_long_shorts_and_long_beats():
    long_line = " ".join(["word"] * 20)                      # ~8 s
    p = _short(*[(long_line, "body_map", {})] * 4)
    tips = script_advice(p)
    assert any(t.startswith("About ") for t in tips)
    assert any("Beats 1, 2, 3, 4 run longer than 6 s" in t for t in tips)
    # a long video allows longer beats and does not ask for a try-it moment
    assert not any("try it" in t for t in script_advice(p, "long"))
    assert not any("longer than" in t for t in script_advice(p, "long"))


def test_still_character_in_the_first_beat():
    p = _short(("You blink a lot.", "stick_scene", {"action": "idle"}), ("Try it.", "body_map", {}))
    assert any("stands still" in t for t in script_advice(p))
