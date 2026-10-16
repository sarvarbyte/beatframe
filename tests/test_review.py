"""AI review #1 with a fake Gemini client: model choice, prompt contents, saving, errors."""

import json
import os
from types import SimpleNamespace

import pytest

from beatframe import review
from beatframe.schema import Beat, Project

ANSWER = {
    "score": 6, "verdict": "fix_first", "summary": "Hook sekin.", "first_seconds": "Bo'sh kadr.",
    "issues": [
        {"beat": 3, "time": "0:08", "severity": "low", "category": "visual", "problem": "p3", "fix": "f3", "new_text": ""},
        {"beat": 1, "time": "0:00", "severity": "high", "category": "hook", "problem": "p1", "fix": "f1",
         "new_text": "Your nose is invisible."},
    ],
    "strengths": ["Ovoz aniq."],
}


class FakeFiles:
    def __init__(self):
        self.deleted = []

    def upload(self, file, config=None):
        self.path = file
        return SimpleNamespace(name="files/1", state=SimpleNamespace(name="PROCESSING"))

    def get(self, name):
        return SimpleNamespace(name=name, state=SimpleNamespace(name="ACTIVE"))

    def delete(self, name):
        self.deleted.append(name)


class FakeModels:
    def __init__(self, names, error=None):
        # error: one message raised on every call, or {model: [messages raised on its first calls]}
        self.names, self.error, self.calls = names, error, []

    def list(self):
        return [SimpleNamespace(name=f"models/{n}", supported_actions=["generateContent"]) for n in self.names]

    def generate_content(self, model, contents, config):
        self.calls.append((model, contents, config))
        if isinstance(self.error, dict) and self.error.get(model):
            raise RuntimeError(self.error[model].pop(0))
        if isinstance(self.error, str):
            raise RuntimeError(self.error)
        return SimpleNamespace(parsed=None, text=json.dumps(ANSWER))


def _setup(tmp_path, monkeypatch, error=None, keys=("gemini",)):
    out = tmp_path / "output"
    out.mkdir(parents=True)
    (out / "preview_short.mp4").write_bytes(b"fake")
    (out / "preview_short.json").write_text(json.dumps(
        {"duration": 9, "timeline": [{"beat": 1, "start": 0, "end": 3.2}, {"beat": 2, "start": 3.2, "end": 9}]}))
    client = SimpleNamespace(files=FakeFiles(), models=FakeModels(
        ["gemini-2.5-flash", "gemini-3.0-flash", "gemini-3.0-flash-lite", "gemini-9-pro"], error))
    monkeypatch.setattr(review, "_client", lambda: client)
    monkeypatch.setattr(review, "api_key", lambda provider="gemini": "k" if provider in keys else "")
    monkeypatch.setattr(review.time, "sleep", lambda s: None)
    monkeypatch.delenv("BEATFRAME_GEMINI_MODEL", raising=False)
    review._MODELS.clear()
    project = Project(title="Your nose", video={"format": "short"}, beats=[
        Beat(text="You can see your nose.", scene="stick_scene", params={"action": "run"}),
        Beat(text="Your brain hides it.", scene="statement", chapter="Why"),
    ])
    return project, tmp_path / "p.yaml", client


def test_review_runs_saves_and_cleans_up(tmp_path, monkeypatch):
    project, file, client = _setup(tmp_path, monkeypatch)
    steps = []
    res = review.run_review(project, file, log=lambda m: None, step=steps.append)

    assert steps == [1, 2, 3]
    model, contents, config = client.models.calls[0]
    assert model == "gemini-3.0-flash"                      # newest plain flash, not lite / pro
    prompt = contents[1]
    assert "Beat 1 (0.0-3.2s) scene=stick_scene" in prompt and "voice: Your brain hides it." in prompt
    assert "[chapter: Why]" in prompt and "Short" in prompt
    assert config.media_resolution is None                   # short video: normal detail
    assert client.files.deleted == ["files/1"]

    saved = review.latest(tmp_path / "output", "short")
    assert saved == res and saved["video"] == "preview_short.mp4"
    assert [i["severity"] for i in saved["review"]["issues"]] == ["high", "low"]    # most severe first


def test_busy_model_is_retried_then_the_next_model_answers(tmp_path, monkeypatch):
    busy = "503 UNAVAILABLE. This model is currently experiencing high demand."
    project, file, client = _setup(tmp_path, monkeypatch, error={"gemini-3.0-flash": [busy] * 3})
    notes = []
    res = review.run_review(project, file, log=lambda m: None, status=notes.append)
    assert [c[0] for c in client.models.calls] == ["gemini-3.0-flash"] * 3 + ["gemini-2.5-flash"]
    assert res["model"] == "gemini-2.5-flash"
    assert any("busy" in n for n in notes)


def test_quota_skips_to_next_model_and_errors_are_friendly(tmp_path, monkeypatch):
    project, file, client = _setup(tmp_path, monkeypatch, error="429 RESOURCE_EXHAUSTED")
    with pytest.raises(review.ReviewError, match="limit"):
        review.run_review(project, file, log=lambda m: None)
    # each model once: flash models newest first, then the newest flash-lite
    assert [c[0] for c in client.models.calls] == ["gemini-3.0-flash", "gemini-2.5-flash", "gemini-3.0-flash-lite"]
    assert client.files.deleted == ["files/1"]

    project, file, client = _setup(tmp_path / "b", monkeypatch, error="503 UNAVAILABLE")
    with pytest.raises(review.ReviewError, match="overloaded"):
        review.run_review(project, file, log=lambda m: None)


def test_no_video_and_no_key(tmp_path, monkeypatch):
    with pytest.raises(review.ReviewError, match="Render a preview"):
        review.pick_video(tmp_path, "long")
    for env in ("GEMINI_API_KEY", "OPENROUTER_API_KEY"):
        monkeypatch.delenv(env, raising=False)
    monkeypatch.setattr(review, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(review, "KEY_FILE", tmp_path / "nokey")
    assert not review.has_key()
    with pytest.raises(review.ReviewError, match="API key"):
        review._client()


def test_saved_key_is_private(tmp_path, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(review, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(review, "KEY_FILE", tmp_path / "gemini_key")
    review.save_key("  abc123 \n")
    assert review.api_key() == "abc123"
    assert oct(os.stat(tmp_path / "gemini_key").st_mode)[-3:] == "600"


def _no_ffmpeg(monkeypatch):
    monkeypatch.setattr(review, "_small_video", lambda video, duration, out: video)
    monkeypatch.setattr(review, "_frames", lambda video, duration, out: [("Stills 0:00-0:05", "AAAA")])
    monkeypatch.setitem(review._OR_STATE, "video", True)


class FakeOpenRouter:
    def __init__(self, answers):
        self.answers, self.models, self.kinds = list(answers), [], []

    def __call__(self, payload, key):
        self.models.append(payload["model"])
        parts = payload["messages"][0]["content"]
        self.kinds.append(parts[1]["type"] if parts[1]["type"] == "video_url" else parts[2]["type"])
        self.last_text = parts[0]["text"]
        return self.answers.pop(0)


def test_chain_falls_back_to_openrouter_when_gemini_is_busy(tmp_path, monkeypatch):
    project, file, client = _setup(tmp_path, monkeypatch, error="503 UNAVAILABLE", keys=("gemini", "openrouter"))
    _no_ffmpeg(monkeypatch)
    fenced = "Here you go:\n```json\n" + json.dumps(ANSWER) + "\n```"
    post = FakeOpenRouter([(503, {"error": {"message": "busy"}}), (503, {"error": {"message": "busy"}}),
                           (200, {"choices": [{"message": {"content": fenced}}]})])
    monkeypatch.setattr(review, "_openrouter_post", post)

    res = review.run_review(project, file, log=lambda m: None)
    nemotron, gemma = review.OPENROUTER_MODELS[0][0], review.OPENROUTER_MODELS[1][0]
    assert post.models == [nemotron, nemotron, gemma]          # busy one retried once, then the next
    assert res["model"] == f"openrouter:{gemma}"
    assert "cannot hear" in post.last_text                    # Gemma gets the video without sound
    assert res["fallbacks"] and res["fallbacks"][0].startswith("gemini:")
    assert res["review"]["issues"][0]["severity"] == "high"


def test_chain_skips_providers_without_key_and_reports_all_failures(tmp_path, monkeypatch):
    project, file, client = _setup(tmp_path, monkeypatch, keys=("openrouter",))
    _no_ffmpeg(monkeypatch)
    post = FakeOpenRouter([(200, {"choices": [{"message": {"content": "sorry, no"}}]})] +
                          [(429, {"error": {"message": "rate limited"}})] * 4)
    monkeypatch.setattr(review, "_openrouter_post", post)
    with pytest.raises(review.ReviewError, match="Every AI in the chain failed"):
        review.run_review(project, file, log=lambda m: None)
    assert client.models.calls == []                         # no Gemini key: Gemini never asked
    assert len(post.models) == 5

    monkeypatch.setattr(review, "api_key", lambda provider="gemini": "")
    with pytest.raises(review.ReviewError, match="No AI key"):
        review.run_review(project, file, log=lambda m: None)


def test_openrouter_key_is_saved_separately(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setattr(review, "CONFIG_DIR", tmp_path)
    monkeypatch.setattr(review, "KEY_FILE", tmp_path / "gemini_key")
    review.save_key("or-123", "openrouter")
    assert review.api_key("openrouter") == "or-123" and review.api_key("gemini") == ""
    assert review.has_key() and not review.has_key("gemini")


def test_free_account_gets_stills_and_wrapped_errors_count_as_busy(tmp_path, monkeypatch):
    project, file, client = _setup(tmp_path, monkeypatch, keys=("openrouter",))
    _no_ffmpeg(monkeypatch)
    loose = dict(ANSWER, issues=[dict(ANSWER["issues"][0], category="length", severity="HIGH", beat="Beat 3")])
    post = FakeOpenRouter([
        (402, {"error": {"message": "This request requires at least $1.00 in balance for video"}}),
        (200, {"error": {"message": "Upstream error: ResourceExhausted"}}),     # an error inside a 200
        (200, {"choices": [{"message": {"content": json.dumps(loose)}}]}),
    ])
    monkeypatch.setattr(review, "_openrouter_post", post)

    res = review.run_review(project, file, log=lambda m: None)
    nemotron = review.OPENROUTER_MODELS[0][0]
    assert post.models == [nemotron] * 3
    assert post.kinds == ["video_url", "image_url", "image_url"]   # after the 402: stills only
    assert "cannot hear" in post.last_text and "contact sheets" in post.last_text
    assert res["model"] == f"openrouter:{nemotron} (stills)"
    issue = res["review"]["issues"][0]                              # invented values are tidied up
    assert (issue["category"], issue["severity"], issue["beat"]) == ("other", "high", 3)
