"""Storyboard, Thumbnail Lab, Compare versions, AI quality history, Ideas and the Stats table."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest
from PIL import Image

from beatframe import planner, quality, thumblab, versions
from beatframe.render import ClipJob, clip_key, reuse_moved_clips
from beatframe.web import insights

SCRIPT = """title: "Feature test"
video: {format: long}
beats:
  - text: "One beat about the brain."
    scene: statement
    params: {text: "One"}
  - text: "Two beats about the eye."
    scene: statement
    params: {text: "Two"}
  - text: "Three beats about the ear."
    scene: statement
    params: {text: "Three"}
"""


@pytest.fixture()
def studio(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from beatframe.web.app import create_app

    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    root = tmp_path / "projects"
    folder = root / "feature-test"
    (folder / "output").mkdir(parents=True)
    (folder / "feature-test.yaml").write_text(SCRIPT, encoding="utf-8")
    return TestClient(create_app(root)), root, folder


def _review(score, created, issues=()):
    return {"video": "final.mp4", "video_mtime": 1, "model": "m", "created": created,
            "review": {"score": score, "verdict": "ready" if score >= 8 else "fix_first", "summary": "s",
                       "first_seconds": "f", "strengths": [],
                       "issues": [{"beat": 1, "time": "0:00", "severity": s, "category": c, "problem": "p", "fix": "f"}
                                  for s, c in issues]}}


# ---- storyboard ------------------------------------------------------------------------------
def test_storyboard_reorders_beats_and_relabels_renders(studio):
    client, root, folder = studio
    manifest = folder / "output" / "preview.json"
    manifest.write_text(json.dumps({"timeline": [{"beat": i, "start": i - 1, "end": i} for i in (1, 2, 3)],
                                    "beats": [1, 2, 3]}))
    r = client.post("/p/feature-test/storyboard/order", json={"order": [3, 1, 2]})
    assert r.json() == {"ok": True, "changed": True}
    import yaml
    beats = yaml.safe_load((folder / "feature-test.yaml").read_text())["beats"]
    assert [b["params"]["text"] for b in beats] == ["Three", "One", "Two"]
    tl = json.loads(manifest.read_text())["timeline"]
    assert [(t["beat"], t["start"]) for t in tl] == [(2, 0), (3, 1), (1, 2)]   # old 3 is now beat 1, at 2 s


def test_reorder_keeps_photo_pictures(studio):
    client, _, folder = studio
    import yaml
    data = yaml.safe_load((folder / "feature-test.yaml").read_text())
    data["beats"][0] = {"text": "A picture.", "scene": "photo", "params": {"prompt": "a room"}}
    (folder / "feature-test.yaml").write_text(yaml.safe_dump(data))
    client.post("/p/feature-test/storyboard/order", json={"order": [2, 1, 3]})
    beats = yaml.safe_load((folder / "feature-test.yaml").read_text())["beats"]
    assert beats[1]["scene"] == "photo" and beats[1]["params"]["image"] == "images/beat_001.png"


def test_storyboard_rejects_a_wrong_order(studio):
    client, _, _ = studio
    assert client.post("/p/feature-test/storyboard/order", json={"order": [1, 1, 2]}).status_code == 400
    assert client.post("/p/feature-test/storyboard/order", json={"order": [1, 2]}).status_code == 400


def test_storyboard_duplicate(studio):
    client, _, folder = studio
    client.post("/p/feature-test/storyboard/duplicate/2", follow_redirects=False)
    import yaml
    texts = [b["params"]["text"] for b in yaml.safe_load((folder / "feature-test.yaml").read_text())["beats"]]
    assert texts == ["One", "Two", "Two", "Three"]


def test_moved_beat_reuses_its_clip(tmp_path):
    a = ClipJob(1, "statement", {"text": "A"}, 2.0, 192, 108, 10)
    b = ClipJob(2, "statement", {"text": "B"}, 2.0, 192, 108, 10)
    (tmp_path / f"001_{clip_key(a)}.mp4").write_bytes(b"A")
    (tmp_path / f"002_{clip_key(b)}.mp4").write_bytes(b"B")
    swapped = [ClipJob(1, "statement", {"text": "B"}, 2.0, 192, 108, 10), ClipJob(2, "statement", {"text": "A"}, 2.0, 192, 108, 10)]
    assert reuse_moved_clips(swapped, tmp_path) == 2
    assert (tmp_path / f"001_{clip_key(swapped[0])}.mp4").read_bytes() == b"B"
    assert (tmp_path / f"002_{clip_key(swapped[1])}.mp4").read_bytes() == b"A"


# ---- compare / versions --------------------------------------------------------------------------
def test_versions_keep_earlier_renders(tmp_path):
    out = tmp_path / "output"
    out.mkdir()
    for k in range(5):
        v = out / "preview.mp4"
        v.write_bytes(b"x" * (k + 1))
        (out / "preview.json").write_text(json.dumps({"duration": k}))
        import os
        os.utime(v, (1_700_000_000 + k * 60, 1_700_000_000 + k * 60))
        versions.archive(v)
    kept = sorted((out / "versions").glob("preview@*.mp4"))
    assert len(kept) == versions.KEEP["preview"]
    (out / "preview.mp4").write_bytes(b"now")
    vids = versions.available(out, "")
    assert vids[0]["current"] and vids[0]["label"] == "Preview" and len(vids) == 1 + versions.KEEP["preview"]
    assert versions.resolve(out, vids[1]["id"]) is not None
    assert versions.resolve(out, "../../etc/passwd") is None


# ---- thumbnail lab -------------------------------------------------------------------------------
def test_thumbnail_lab_variants_and_publish_choice(studio):
    client, _, folder = studio
    tdir = folder / "output" / "thumbs"
    tdir.mkdir()
    Image.new("RGB", (640, 360), (40, 60, 120)).save(tdir / "thumb_1_beat001.png")
    r = client.get("/p/feature-test/thumbs/preview.jpg", params={"source": "thumb_1_beat001.png", "text": "Hi there"})
    assert r.status_code == 200 and r.headers["content-type"] == "image/jpeg"
    client.post("/p/feature-test/thumbs/variant", data={"source": "thumb_1_beat001.png", "text": "Big claim", "style": "pop"},
                follow_redirects=False)
    data = thumblab.load(folder / "output", "")
    assert len(data["variants"]) == 1
    v = data["variants"][0]
    img = Image.open(tdir / v["file"])
    assert img.size == (1280, 720) and (tdir / v["file"]).stat().st_size < 2_000_000
    client.post("/p/feature-test/thumbs/select", data={"file": v["file"]}, follow_redirects=False)
    assert thumblab.load(folder / "output", "")["selected"] == v["file"]
    page = client.get("/p/feature-test?tab=publish").text
    assert f'value="{v["file"]}" form="pubform" checked' in page
    client.post(f"/p/feature-test/thumbs/delete/{v['id']}", follow_redirects=False)
    assert not thumblab.load(folder / "output", "")["variants"] and not (tdir / v["file"]).exists()


def test_thumbnail_needs_a_frame(studio):
    client, _, folder = studio
    r = client.post("/p/feature-test/thumbs/variant", data={"text": "x"}, follow_redirects=False)
    assert "lab_error" in r.headers["location"]


# ---- quality history -------------------------------------------------------------------------------
def test_quality_history_reads_every_review(tmp_path):
    folder = tmp_path / "vid"
    out = folder / "output"
    out.mkdir(parents=True)
    (folder / "vid.yaml").write_text('title: "Vid"\nbeats: []\nsource: import\n')
    quality.append(out, "_short", _review(5, "2026-10-01T10:00:00", [("high", "hook")]))
    latest = _review(8, "2026-10-03T10:00:00", [("low", "pacing")])
    quality.append(out, "_short", latest)
    (out / "review_short.json").write_text(json.dumps(latest))        # the current file repeats the last one
    reviews = quality.all_reviews(tmp_path)
    assert [r["score"] for r in reviews] == [5, 8]
    s = quality.summary(reviews)
    assert s["count"] == 2 and s["projects"] == 1 and s["improved"] == [3] and s["ready"] == 1
    assert s["by_category"]["hook"]["high"] == 1


def test_quality_page_with_and_without_reviews(studio):
    client, _, folder = studio
    assert "No AI reviews yet" in client.get("/quality").text
    (folder / "output" / "review.json").write_text(json.dumps(_review(7, "2026-10-02T09:00:00", [("medium", "visual")])))
    html = client.get("/quality").text
    assert "Score over time" in html and '"score": 7' in html


# ---- ideas -----------------------------------------------------------------------------------------------
def test_ideas_generate_save_star_delete(studio, monkeypatch):
    client, root, _ = studio

    def fake(prompt, schema, log=print):
        assert "MADE IN BEATFRAME" in prompt and "Feature test" in prompt     # grounded in the made topics
        return schema(ideas=[planner.Idea(title="Your Ears Lie", hook="Your ears lie to you.", angle="a",
                                          format="short", why="w")]), "gemini-test"

    monkeypatch.setattr(planner, "generate_json", fake)
    html = client.post("/ideas/run", data={"kind": "ideas", "brief": "", "fmt": "short", "count": 3}).text
    assert "Your Ears Lie" in html
    item = planner.load(root)["items"][0]
    client.post(f"/ideas/{item['id']}/star")
    assert planner.get(root, item["id"])["starred"]
    assert "Your Ears Lie" in client.get("/ideas").text
    client.post(f"/ideas/{item['id']}/delete")
    assert not planner.load(root)["items"]


def test_idea_script_draft_is_checked_and_opens_in_studio(studio, monkeypatch):
    client, root, _ = studio
    draft = SCRIPT.replace("Feature test", "Drafted")
    monkeypatch.setattr(planner, "generate_json", lambda p, schema, log=print: (schema(yaml=draft, notes="n"), "m"))
    html = client.post("/ideas/run", data={"kind": "script", "brief": "An idea", "fmt": "long"}).text
    assert "Passes Beatframe" in html
    item = planner.load(root)["items"][0]
    r = client.get(f"/ideas/{item['id']}/use", follow_redirects=False)
    home = client.get(r.headers["location"]).text
    assert "Drafted" in home


def test_ideas_without_key_say_so(studio):
    client, _, _ = studio
    html = client.post("/ideas/run", data={"kind": "ideas"}).text
    assert "alert err" in html and "key" in html.lower()
    assert "Add the key in Settings" in client.get("/ideas").text


def test_broken_draft_is_flagged():
    res = planner.check_yaml("title: x\nbeats:\n  - text: hi\n    scene: nope\n")
    assert not res["valid"] and res["problems"]


# ---- stats table -------------------------------------------------------------------------------------------
def test_report_table_reads_by_header():
    text = ("type | published | age | length | title | views | avg view | % viewed | likes | comments | subs | status\n"
            "S | 2026-10-01 | 5d | 0:24 | A | 1,200 | 0:14 | 58.3% | 40 | 2 | +5 | public\n"
            "L | 2026-09-01 | 30d | 9:50 | B | - | - | - | 1 | 0 | - | PRIVATE\n")
    rows = insights.report_table(text)
    assert rows[0] == {**rows[0], "type": "short", "views": 1200, "viewed": 58.3, "avg_view": 14, "subs": 5}
    assert rows[1]["views"] is None and rows[1]["type"] == "long"
