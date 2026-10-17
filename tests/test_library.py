"""Science template library, render settings, Template Library pages, presets, compositions and the
composer actions. Includes real (tiny) Manim renders of every new template in both formats."""

import json
import subprocess
import sys
import threading
import time
from pathlib import Path

import pytest

from beatframe import library, renderconf
from beatframe.render import ClipJob, RenderCancelled, _run_manim, _source_hash, clip_key, render_clip
from beatframe.templates import REGISTRY, get_template

NEW = ["neural_impulse", "memory_reconstruction", "attention_spotlight", "sleep_cycle", "stress_response",
       "bone_conduction", "inner_ear", "retina_processing", "touch_receptors", "reflex_arc",
       "blind_spot_test", "balance_experiment", "reaction_time", "stroop_effect", "ring_finger_test",
       "blood_circulation", "oxygen_exchange", "dna_unzipping", "immune_response", "evolution_tree"]

SCRIPT = """title: "Library test"
voice: {provider: silent}
beats:
  - text: "One."
    scene: statement
    params: {text: "One"}
  - text: "Two."
    scene: statement
    params: {text: "Two"}
"""


@pytest.fixture()
def studio(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from beatframe.web.app import create_app

    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    root = tmp_path / "projects"
    folder = root / "library-test"
    (folder / "output").mkdir(parents=True)
    (folder / "library-test.yaml").write_text(SCRIPT, encoding="utf-8")
    return TestClient(create_app(root)), root, folder


# ---- registry and parameters ----------------------------------------------------------------------
def test_all_twenty_templates_are_registered_and_responsive():
    get_template("statement")
    for name in NEW:
        cls = REGISTRY[name]
        assert cls.vertical_width == 8.0 and cls.theme == "bright", name       # real 9:16 layout, own background
        assert getattr(cls, "category", "") in library.CATEGORIES, name
        assert cls.description and cls.Params.model_validate({})              # defaults are valid


@pytest.mark.parametrize("name,bad", [
    ("neural_impulse", {"neurons": 12}), ("sleep_cycle", {"hours": 2}), ("reaction_time", {"reaction_ms": 5}),
    ("evolution_tree", {"tree": "dinosaurs"}), ("bone_conduction", {"mode": "both"}), ("stroop_effect", {"words": 40}),
    ("blind_spot_test", {"spacing": 0.95}), ("memory_reconstruction", {"text_size": 3}), ("inner_ear", {"palette": "neon"}),
])
def test_invalid_settings_are_rejected(name, bad):
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        get_template(name).Params.model_validate(bad)


def test_editor_fields_have_sliders_and_swatches():
    from beatframe.web.store import params_from_form, template_fields
    fields = {f["name"]: f for f in template_fields("neural_impulse", {})}
    assert fields["text_size"]["kind"] == "range" and fields["neurons"]["kind"] == "range"
    assert fields["palette"]["kind"] == "swatch" and fields["highlight"]["kind"] == "swatch"
    assert list(fields)[0] == "neurons"                         # the template's own settings come first
    params = params_from_form("neural_impulse", {"p.neurons": "4", "p.palette": "paper", "p.labels": "on", "p.synapse_zoom": "on"})
    assert params == {"neurons": 4, "palette": "paper"}
    for name in NEW:                     # every slider can land exactly on its default (no silent change)
        for f in template_fields(name, {}):
            if f["kind"] == "range":
                k = (f["default"] - f["min"]) / f["step"]
                assert abs(k - round(k)) < 1e-6, (name, f["name"])


# ---- render settings and process control -----------------------------------------------------------
def test_render_settings_default_to_one_low_priority_worker(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("BEATFRAME_WORKERS", raising=False)
    s = renderconf.load()
    assert (s.workers, s.nice, s.preview_preset) == (1, 10, "eco")
    renderconf.save(renderconf.RenderSettings(workers=3, nice=30, preview_preset="nope"))
    s = renderconf.load()
    assert (s.workers, s.nice, s.preview_preset) == (3, 19, "eco")          # values are clamped
    monkeypatch.setenv("BEATFRAME_WORKERS", "2")
    assert renderconf.load().workers == 2
    assert renderconf.preset_size("eco", False) == (854, 480, 15)          # the original preview size: caches stay valid
    assert renderconf.preset_size("balanced", True) == (720, 1280, 30)
    assert renderconf.preset_size("quality", False) == (1920, 1080, 30)


def test_cancel_kills_the_running_process():
    stop = threading.Event()
    threading.Timer(0.3, stop.set).start()
    t0 = time.monotonic()
    with pytest.raises(RenderCancelled):
        _run_manim([sys.executable, "-c", "import time; time.sleep(30)"], 10, stop)
    assert time.monotonic() - t0 < 5


def test_process_cost_is_measured():
    code, err, stats = _run_manim([sys.executable, "-c", "x = bytearray(60_000_000); print(len(x))"], 10, None)
    assert code == 0 and stats["peak_rss_mb"] >= 55 and stats["seconds"] > 0 and "cpu_percent" in stats


def test_cache_key_follows_the_shared_kit(monkeypatch):
    import inspect
    from beatframe.templates import sci
    job = ClipJob(1, "neural_impulse", {}, 3.0, 854, 480, 15)
    before = clip_key(job)
    assert clip_key(ClipJob(5, "neural_impulse", {}, 3.0, 854, 480, 15)) == before            # position-independent
    assert clip_key(ClipJob(1, "neural_impulse", {"neurons": 4}, 3.0, 854, 480, 15)) != before
    real = inspect.getsource
    monkeypatch.setattr(inspect, "getsource", lambda m: real(m) + ("#changed" if m is sci else ""))
    assert _source_hash("neural_impulse") != before[:10] and clip_key(job) != before        # editing sci.py re-renders


# ---- real renders: every new template, both formats --------------------------------------------------
@pytest.mark.parametrize("name", NEW)
@pytest.mark.parametrize("fmt", ["long", "short"])
def test_template_renders(name, fmt, tmp_path):
    w, h = (256, 144) if fmt == "long" else (144, 256)
    seconds = 4.0 if fmt == "long" else 2.5            # short beats too: a scene must never overrun its beat
    job = ClipJob(1, name, {"title": "Test title"} if "title" in get_template(name).Params.model_fields else {}, seconds, w, h, 8)
    clip = render_clip(job, tmp_path)
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height,nb_frames",
                          "-show_entries", "format=duration", "-of", "json", str(clip)], capture_output=True, text=True, check=True).stdout
    info = json.loads(out)
    s = info["streams"][0]
    assert (s["width"], s["height"]) == (w, h)
    assert abs(float(info["format"]["duration"]) - seconds) <= 1 / 8 + 0.02     # fills the beat to the frame, no overrun
    assert job.stats["peak_rss_mb"] > 0


# ---- library pages, presets, favourites, previews, use in project -------------------------------------
def test_library_page_and_detail(studio):
    client, _, _ = studio
    html = client.get("/templates").text
    for name in ("neural_impulse", "evolution_tree", "statement"):
        assert f'data-name="{name}"' in html
    assert 'data-cat="Neuroscience"' in html and "Short-ready only" in html
    page = client.get("/templates/bone_conduction?fmt=short").text
    assert "Render preview" in page and 'name="p.source"' in page and "tplDefaults" in page


def test_favourites_presets_and_use_template(studio):
    client, root, folder = studio
    assert "on" in client.post("/templates/reaction_time/favorite").text
    assert library.state()["favorites"] == ["reaction_time"]
    r = client.post("/templates/reaction_time/preset", data={"preset_name": "Fast", "p.reaction_ms": "180", "p.palette": "paper",
                                                                 "p.labels": "on", "p.breakdown": "on"},
                    follow_redirects=False)
    pid = library.presets("reaction_time")[0]["id"]
    assert pid in r.headers["location"] and library.get_preset(pid)["params"] == {"reaction_ms": 180, "palette": "paper"}
    assert 'value="180"' in client.get(f"/templates/reaction_time?preset={pid}").text
    bad = client.post("/templates/reaction_time/preset", data={"preset_name": "x", "p.reaction_ms": "5"}, follow_redirects=False)
    assert "error=" in bad.headers["location"]
    r = client.post("/templates/reaction_time/use", data={"project": "library-test", "text": "How fast are you?",
                                                           "p.reaction_ms": "180", "p.labels": "on", "p.breakdown": "on", "position": "end"}, follow_redirects=False)
    assert r.headers["location"].endswith("#sb-3")
    import yaml
    beats = yaml.safe_load((folder / "library-test.yaml").read_text())["beats"]
    assert beats[-1] == {"text": "How fast are you?", "scene": "reaction_time", "params": {"reaction_ms": 180}}
    assert library.state()["recent"][0]["name"] == "reaction_time"


def test_preview_renders_for_real_and_is_cached(studio, monkeypatch):
    client, _, _ = studio
    monkeypatch.setattr(library, "preview_job", lambda n, p, f, s, preset="eco": ClipJob(1, n, p, 2.0, 160, 90, 6))
    html = client.post("/templates/reaction_time/preview", data={"fmt": "long", "seconds": "2"}).text
    job_id = html.split("/preview/")[1].split('"')[0]
    for _ in range(240):
        html = client.get(f"/templates/reaction_time/preview/{job_id}").text
        if "<video" in html or "failed" in html:
            break
        time.sleep(0.5)
    assert "<video" in html, html
    src = html.split('<video src="')[1].split('"')[0]
    assert client.get(src).status_code == 200
    again = client.post("/templates/reaction_time/preview", data={"fmt": "long", "seconds": "2"}).text
    assert "Cached render" in again


def test_render_settings_page(studio):
    client, _, _ = studio
    client.post("/settings/render", data={"workers": "2", "nice": "5", "preview_preset": "balanced"})
    s = renderconf.load()
    assert (s.workers, s.nice, s.preview_preset) == (2, 5, "balanced")
    html = client.get("/settings").text
    assert "Rendering on this computer" in html and "720p" in html


# ---- composer: timing, transitions, compositions ---------------------------------------------------------
def test_storyboard_timing_transition_and_compositions(studio):
    client, root, folder = studio
    import yaml
    client.post("/p/library-test/storyboard/beat/2", data={"min_duration": "4.5", "transition": "cut"})
    b = yaml.safe_load((folder / "library-test.yaml").read_text())["beats"][1]
    assert b["min_duration"] == 4.5 and b["transition"] == "cut"
    assert "transition" not in yaml.safe_load((folder / "library-test.yaml").read_text())["beats"][0]   # untouched beats stay clean
    client.post("/p/library-test/compositions/save", data={"name": "Pair", "first": "1", "last": "2"})
    comp = library.compositions()[0]
    assert comp["name"] == "Pair" and [x["scene"] for x in comp["beats"]] == ["statement", "statement"]
    client.post(f"/p/library-test/compositions/{comp['id']}/insert", data={"position": "0"})
    beats = yaml.safe_load((folder / "library-test.yaml").read_text())["beats"]
    assert len(beats) == 4 and beats[1]["transition"] == "cut"
    page = client.get("/p/library-test?tab=storyboard").text
    assert "Composer" in page and "Pair" in page and "Timing &amp; transition" in page


def test_cut_transition_is_a_one_frame_fade(tmp_path):
    from beatframe.assemble import join_with_transitions
    clips = []
    for k, col in enumerate(("red", "blue")):
        f = tmp_path / f"{k}.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color={col}:s=64x36:d=1:r=10", "-pix_fmt", "yuv420p", str(f)], check=True)
        clips.append(f)
    out = join_with_transitions(clips, [1.0, 1.0], ["", "cut"], tmp_path / "j.mp4", 10, d=0.3)
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(out)],
                               capture_output=True, text=True).stdout)
    assert abs(dur - 2.0) < 0.15
