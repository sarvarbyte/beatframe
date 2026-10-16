"""Quick checks for the Short/Long format plumbing (no rendering). Run: python -m pytest tests"""

import pytest
from pydantic import ValidationError

from beatframe.formats import frame_size, get_format
from beatframe.schema import Project, Video


def test_formats_resolve_to_the_right_sizes():
    assert get_format("long").size() == (1920, 1080)
    assert get_format("short").size() == (1080, 1920)
    assert get_format("short").size(preview=True) == (480, 854)
    assert get_format(None).name == "long"
    with pytest.raises(ValueError):
        get_format("square")


def test_frame_size_keeps_long_identical_to_manim_default():
    assert frame_size(1920, 1080) == (8 * 16 / 9, 8.0)
    assert frame_size(854, 480) == (8 * 16 / 9, 8.0)      # preview snaps to exact 16:9
    assert frame_size(1080, 1920) == (8.0, 8 * 16 / 9)
    assert frame_size(480, 854) == (8.0, 8 * 16 / 9)


def test_video_settings():
    assert Video().size() == (1920, 1080)                       # old projects stay long
    assert Video(width=1920, height=1080).size() == (1920, 1080)  # explicit size still works
    assert Video(format="short").size() == (1080, 1920)
    assert Video(width=1920, height=1080, fps=24).with_format("short").size() == (1080, 1920)
    assert Video(width=1920, height=1080, fps=24).with_format("short").fps == 24
    with pytest.raises(ValidationError):
        Video(format="short", width=1920, height=1080)           # landscape size + short format
    with pytest.raises(ValidationError):
        Video(width=1920)                                        # half a size


def test_project_without_video_block_is_long():
    p = Project.model_validate({"title": "t", "beats": [{"text": "a", "scene": "statement"}]})
    assert p.video.format == "long"


def test_portrait_frame_follows_template_width():
    assert frame_size(1080, 1920, 11.6) == (11.6, 11.6 * 16 / 9)
    from beatframe.templates import REGISTRY, get_template
    get_template("statement")
    for name, cls in REGISTRY.items():
        assert 8.0 <= cls.vertical_width <= 8 * 16 / 9 + 1e-9, name


def test_output_names():
    from beatframe.pipeline import output_name
    assert output_name("final", "long") == "final.mp4"
    assert output_name("final", "short") == "final_short.mp4"
    assert output_name("beat_preview", "short") == "beat_preview_short.mp4"
