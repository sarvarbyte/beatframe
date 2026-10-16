"""Importing a finished video made elsewhere: card parsing, format from the video, guards."""

import json
import subprocess

import pytest

from beatframe import importer, pipeline
from beatframe.web.store import Store

CARD = """title: "You Can't Tickle Yourself"
video: {format: long}
made_with: gemini
tags: [brain]
script: |
  You can't tickle yourself. Try it right now.
chapters: |
  00:00 Intro
"""


def _video(path, w, h, seconds=2, codec="libx264"):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"testsrc=size={w}x{h}:rate=10",
                    "-f", "lavfi", "-i", "sine=frequency=440", "-t", str(seconds), "-c:v", codec,
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path)], check=True)
    return path


def test_vertical_video_becomes_a_short_whatever_the_card_says(tmp_path):
    store = Store(tmp_path / "projects")
    slug, err, notes = store.create_import(CARD, _video(tmp_path / "v.mp4", 360, 640))
    assert err == "" and slug == "you-can-t-tickle-yourself"
    assert notes and "9:16" in notes[0]
    p = store.load(slug)
    assert p.imported and p.video.format == "short" and p.made_with == "gemini" and p.beats == []
    out = store.output(slug)
    manifest = json.loads((out / "final_short.json").read_text())
    assert manifest["source"] == "import" and manifest["height"] == 640 and manifest["duration"] > 1.5
    assert len(list((out / "thumbs_short").glob("*.png"))) == 5
    assert (out / "chapters.txt").read_text().startswith("00:00 Intro")
    with pytest.raises(ValueError, match="nothing to render"):
        pipeline.run(p, store.file(slug))

    # the same title again gets its own folder
    slug2, _, _ = store.create_import(CARD, _video(tmp_path / "w.mp4", 640, 360))
    assert slug2 == "you-can-t-tickle-yourself-2" and store.load(slug2).video.format == "long"


def test_non_mp4_is_converted(tmp_path):
    store = Store(tmp_path / "projects")
    slug, err, _ = store.create_import(CARD, _video(tmp_path / "v.mkv", 640, 360, codec="mpeg4"))
    assert err == ""
    assert importer.probe(store.output(slug) / "final.mp4")["vcodec"] == "h264"


def test_bad_cards_and_files_leave_nothing_behind(tmp_path):
    store = Store(tmp_path / "projects")
    good = _video(tmp_path / "v.mp4", 640, 360)
    for card, video, message in [("tags: [x]", good, "title"),
                                 ("title: x\nbeats:\n  - {text: hi, scene: statement}\nsource: beatframe", good, "Create"),
                                 (CARD, tmp_path / "missing.mp4", "not a video")]:
        slug, err, _ = store.create_import(card, video)
        assert slug is None and message in err
    assert list(store.root.iterdir()) == []
