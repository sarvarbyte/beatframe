"""Word-by-word captions: aligning voice timings to the script, phrasing, and the .ass output."""

from beatframe.captions import align, beat_wants_captions, build_ass, group
from beatframe.schema import Beat, Captions
from beatframe.tts import estimate_words


def _w(word, start, end):
    return {"word": word, "start": start, "end": end}


def test_align_keeps_script_words_and_attaches_kokoro_punctuation():
    # Kokoro gives punctuation as its own tokens; the script's words (with punctuation) are shown
    timed = [_w("Your", 0.35, 0.5), _w("nose", 0.5, 0.9), _w(".", 0.9, 1.0), _w("Look", 1.0, 1.3), _w("!", 1.3, 1.4)]
    words = align("Your nose. Look!", timed)
    assert [w.text for w in words] == ["Your", "nose.", "Look!"]
    assert (words[0].start, words[1].end, words[2].end) == (0.35, 1.0, 1.4)


def test_align_matches_differently_split_words_and_fills_missing_ones():
    # "10%" spoken as two tokens; "really" missing from the timings entirely
    timed = [_w("It", 0.0, 0.2), _w("is", 0.2, 0.4), _w("10", 0.4, 0.7), _w("%", 0.7, 0.9), _w("true", 1.3, 1.6)]
    words = align("It is 10% really true", timed)
    assert [w.text for w in words] == ["It", "is", "10%", "really", "true"]
    assert (words[2].start, words[2].end) == (0.4, 0.9)
    assert 0.9 <= words[3].start < words[3].end <= 1.3
    assert all(a.start <= b.start for a, b in zip(words, words[1:]))


def test_align_without_timings_and_estimate():
    assert align("", []) == []
    est = estimate_words("one two three", 3.0)
    assert len(est) == 3 and est[0]["start"] >= 0 and est[-1]["end"] <= 3.0
    words = align("one two three", est)
    assert [w.text for w in words] == ["one", "two", "three"]


def test_group_breaks_at_punctuation_pauses_and_size():
    words = align("Try it. Plug your ears and hum.", estimate_words("Try it. Plug your ears and hum.", 3.0))
    phrases = [" ".join(w.text for w in p) for p in group(words, max_words=3, max_chars=18)]
    assert phrases[0] == "Try it."
    assert all(len(p.split()) <= 3 for p in phrases)
    assert phrases[-1].endswith("hum.")


def test_text_scenes_skip_captions_unless_asked():
    assert beat_wants_captions(Beat(text="x", scene="body_map"))
    assert not beat_wants_captions(Beat(text="x", scene="kinetic_text"))
    assert beat_wants_captions(Beat(text="x", scene="kinetic_text", captions=True))
    assert not beat_wants_captions(Beat(text="x", scene="body_map", captions=False))
    # a caption written under the picture would collide; a headline at the top would not
    assert not beat_wants_captions(Beat(text="x", scene="brain_light", params={"caption": "you hear it"}))
    assert beat_wants_captions(Beat(text="x", scene="stick_scene", params={"caption": "headline"}))
    assert beat_wants_captions(Beat(text="x", scene="brain_light", params={"caption": ""}))


def test_captions_mode_follows_format():
    assert Captions().enabled("short") and not Captions().enabled("long")
    assert Captions(mode="on").enabled("long") and not Captions(mode="off").enabled("short")
    # YAML turns a bare `off` into False
    import yaml
    assert Captions.model_validate(yaml.safe_load("{mode: off}")).mode == "off"
    assert Captions.model_validate(yaml.safe_load("{mode: on}")).mode == "on"


def test_ass_events_are_offset_by_beat_start_and_escaped():
    words = align("Hello {there}", [_w("Hello", 0.1, 0.5), _w("there", 0.5, 0.9)])
    ass = build_ass([(10.0, 12.0, words)], Captions(style="pop"), 1080, 1920)
    events = [l for l in ass.splitlines() if l.startswith("Dialogue:")]
    assert len(events) == 2                                  # one per spoken word
    assert events[0].startswith("Dialogue: 0,0:00:10.10,0:00:10.50")
    assert "{THERE}" not in ass and "(THERE)" in ass
    assert "PlayResY: 1920" in ass

    karaoke = build_ass([(0.0, 2.0, words)], Captions(style="karaoke"), 1920, 1080)
    assert sum(l.startswith("Dialogue:") for l in karaoke.splitlines()) == 1 and "\\kf" in karaoke
