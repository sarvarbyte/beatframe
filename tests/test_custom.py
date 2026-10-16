"""custom scenes, word cues and the pre-render check."""

from pathlib import Path

import pytest

from beatframe.pipeline import custom_extras
from beatframe.preflight import preflight
from beatframe.schema import parse_project
from beatframe.templates.custom import WordClock

WORDS = [{"word": "Your", "start": 0.1, "end": 0.3}, {"word": "brain", "start": 0.3, "end": 0.6},
         {"word": "fills", "start": 0.7, "end": 1.0}, {"word": "gaps.", "start": 1.0, "end": 1.4},
         {"word": "brain's", "start": 1.6, "end": 2.0}]


def project(beats: str, extra: str = ""):
    return parse_project(f'title: "t"\n{extra}beats:\n{beats}')


def test_word_clock_finds_words_and_repeats():
    c = WordClock(WORDS, 3.0)
    assert c.at("fills") == 0.7
    assert c.at("GAPS") == 1.0              # case and punctuation don't matter
    assert c.at("brain", 2) == 1.6          # brain's counts as the second "brain"
    with pytest.raises(KeyError, match="does not say"):
        c.at("heart")


def test_fallback_defaults_to_statement_with_beat_text():
    p = project('  - text: "Your brain fills gaps."\n    scene: custom\n    params: {code: "pass"}\n')
    extras = custom_extras(p.beats[0], WORDS)
    assert extras["fallback"] == ("statement", {"text": "Your brain fills gaps."})
    assert extras["words"] == WORDS


def test_preflight_catches_bad_code_and_unspoken_cues():
    p = project(
        '  - text: "Your brain fills gaps."\n    scene: custom\n    params: {code: "scene.play(\\n"}\n'
        '  - text: "Your brain fills gaps."\n    scene: custom\n    params: {code: "wait_until(\'heart\')"}\n'
        '  - text: "Your brain fills gaps."\n    scene: custom\n    params: {code: "wait_until(\'fills\')"}\n')
    issues = preflight(p)
    msgs = [(x.level, x.beat, x.msg) for x in issues]
    assert any(lvl == "error" and b == 1 and "line" in m for lvl, b, m in msgs)
    assert any(lvl == "error" and b == 2 and '"heart"' in m for lvl, b, m in msgs)
    assert not any(b == 3 and lvl == "error" for lvl, b, m in msgs)


def test_preflight_repeats_and_missing_files(tmp_path: Path):
    beat = '  - text: "Same line here."\n    scene: stat_pop\n    params: {value: "90%", label: "x"}\n'
    other = '  - text: "Look."\n    scene: statement\n    params: {text: "Look.", image: "pic.png"}\n'
    p = project(beat + beat + other, extra='audio: {music: "song.mp3"}\n')
    msgs = [str(x) for x in preflight(p, tmp_path)]
    assert any("same picture as beat 1" in m for m in msgs)
    assert any("pic.png" in m for m in msgs)
    assert any("song.mp3" in m for m in msgs)


def test_three_in_a_row_is_flagged():
    b = '  - text: "Line {n}."\n    scene: stat_pop\n    params: {{value: "{n}", label: "x"}}\n'
    p = project("".join(b.format(n=n) for n in range(3)))
    assert any("3 stat_pop scenes in a row" in str(x) for x in preflight(p))


@pytest.mark.slow
def test_custom_scene_renders_and_falls_back(tmp_path: Path):
    from beatframe.render import ClipJob, render_clip

    good = {"code": "c = Circle(radius=1).set_stroke(PAPER, 4)\nscene.play(Create(c), run_time=0.3)\n"
                    "wait_until('fills')\nscene.play(c.animate.set_fill(EMBER, 1), run_time=0.3)\n",
            "theme": "bright"}
    job = ClipJob(1, "custom", good, 1.5, 192, 108, 10, words=WORDS,
                  fallback=("custom", {"code": "pass"}))
    out = render_clip(job, tmp_path)
    assert out.exists() and not job.error

    bad = ClipJob(2, "custom", {"code": "scene.play(Nope())"}, 1.0, 192, 108, 10, words=WORDS,
                  fallback=("custom", {"code": "pass"}))
    out2 = render_clip(bad, tmp_path)
    assert out2.exists() and "Nope" in bad.error
    assert list(tmp_path.glob("002_*.failed.txt"))


def test_library_save_and_use(tmp_path: Path, monkeypatch):
    from beatframe.templates import custom
    from beatframe.templates.base import REGISTRY, get_template

    monkeypatch.setattr(custom, "LIBRARY", tmp_path)
    p = project('  - text: "Your brain fills gaps."\n    scene: custom\n'
                '    params: {code: "x = v.get(\'n\', 1)", theme: bright}\n')
    path = custom.save_to_library(p.beats[0], "gap_fill_test", "test scene")
    assert path.exists() and "code: |" in path.read_text() or "code:" in path.read_text()
    cls = get_template("gap_fill_test")
    assert cls.library_code.strip() == "x = v.get('n', 1)"
    params = cls.Params.model_validate({"vars": {"n": 3}})
    assert params.theme == "bright" and params.vars == {"n": 3}
    with pytest.raises(ValueError, match="built-in"):
        custom.save_to_library(p.beats[0], "statement")
    REGISTRY.pop("gap_fill_test", None)


def test_transitions_vary_and_dip_at_chapters():
    from beatframe.assemble import pick_transitions

    kinds = pick_transitions(12, [False] * 5 + [True] + [False] * 6, vertical=False)
    assert len(kinds) == 11 and kinds[4] == "fadeblack"
    assert all(a != b for a, b in zip(kinds, kinds[1:]))


def test_image_prompts_and_history(tmp_path: Path):
    from beatframe import history, images

    folder = tmp_path / "my-video"
    folder.mkdir()
    yaml_text = ('title: "My video"\nbeats:\n'
                 '  - text: "A man by a window."\n    scene: photo\n    params: {image: images/a.png}\n'
                 '  - text: "Old hospital."\n    scene: photo\n    params: {prompt: "1950s hospital"}\n')
    (folder / "my-video.yaml").write_text(yaml_text)
    p = parse_project(yaml_text)
    text = images.report(p, folder)
    assert "images/a.png" in text and "A scene showing: A man by a window" in text
    assert "images/beat_002.png" in text and "1950s hospital" in text
    rep = history.report(tmp_path)
    assert "My video" in rep and "photo 100%" in rep
