"""AI content planning with the Gemini key already set for AI review.

Four jobs, all grounded in the channel's own data (the last Stats report, the topics already made,
the channel rules in CLAUDE_KANAL.md):
  ideas  - new video ideas with a hook and the reason they fit
  hooks  - opening lines for one topic
  plan   - a publishing plan for the next days
  script - a Beatframe YAML draft for one idea (checked by the real parser before it is shown)

Everything generated is saved locally in <projects>/.ideas/ideas.json, so nothing is lost when
the page closes. Without a Gemini key nothing is generated (no made-up placeholder ideas).
"""

from __future__ import annotations

import json
import secrets
import time
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from beatframe import brand, history

# ---- answer shapes -------------------------------------------------------------------------


class Idea(BaseModel):
    title: str = Field(description="YouTube title, under 60 characters, English")
    hook: str = Field(description="The first sentence the narrator says, a 'You/Your' claim, English")
    angle: str = Field(description="One sentence: the surprising angle or study behind it, English")
    format: Literal["short", "long"]
    why: str = Field(description="In Uzbek: which numbers or past videos make this a good bet")


class Ideas(BaseModel):
    ideas: list[Idea]


class Hook(BaseModel):
    hook: str = Field(description="Opening line, English, at most 12 words")
    kind: str = Field(description="claim, test-it-now, number, contrast or question")
    why: str = Field(description="In Uzbek, one short sentence")


class Hooks(BaseModel):
    hooks: list[Hook]


class PlanItem(BaseModel):
    day: str = Field(description="Day label, e.g. 'Mon 19 Oct'")
    format: Literal["short", "long"]
    title: str
    note: str = Field(description="In Uzbek: what to do that day (script, render, publish time...)")


class Plan(BaseModel):
    summary: str = Field(description="In Uzbek: the plan's idea in 2 sentences")
    items: list[PlanItem]


class Draft(BaseModel):
    yaml: str = Field(description="A complete Beatframe YAML script")
    notes: str = Field(description="In Uzbek: what to check before rendering")


class PlannerError(RuntimeError):
    pass


# ---- storage ----------------------------------------------------------------------------------
def store_file(projects_root: Path) -> Path:
    return Path(projects_root) / ".ideas" / "ideas.json"


def load(projects_root: Path) -> dict:
    try:
        data = json.loads(store_file(projects_root).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    data.setdefault("items", [])
    return data


def _save(projects_root: Path, data: dict) -> None:
    f = store_file(projects_root)
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def add(projects_root: Path, kind: str, brief: str, payload: dict, model: str) -> dict:
    data = load(projects_root)
    item = {"id": secrets.token_hex(4), "kind": kind, "brief": brief, "model": model,
            "created": time.strftime("%Y-%m-%d %H:%M"), "starred": False, "payload": payload}
    data["items"].insert(0, item)
    _save(projects_root, data)
    return item


def update(projects_root: Path, item_id: str, **changes) -> None:
    data = load(projects_root)
    for it in data["items"]:
        if it["id"] == item_id:
            it.update(changes)
    _save(projects_root, data)


def delete(projects_root: Path, item_id: str) -> None:
    data = load(projects_root)
    data["items"] = [it for it in data["items"] if it["id"] != item_id]
    _save(projects_root, data)


def get(projects_root: Path, item_id: str) -> dict | None:
    return next((it for it in load(projects_root)["items"] if it["id"] == item_id), None)


# ---- context ----------------------------------------------------------------------------------
def context(projects_root: Path, stats_text: str = "") -> str:
    parts = []
    rules = brand.APP_DIR / "CLAUDE_KANAL.md"
    if rules.exists():
        parts.append("CHANNEL RULES\n" + rules.read_text(encoding="utf-8")[:6000])
    made = history.report(projects_root)
    if made:
        parts.append(made)
    if stats_text:
        parts.append("LATEST STATS REPORT\n" + stats_text[:8000])
    else:
        parts.append("No Stats report yet: say so in 'why' instead of quoting numbers.")
    return "\n\n".join(parts)


def scene_catalog() -> str:
    from beatframe.web.store import template_catalog
    lines = []
    for t in template_catalog():
        params = ", ".join(f["name"] for f in t.get("fields", [])) if t.get("fields") else ""
        lines.append(f"- {t['name']}: {t.get('description', '')}" + (f" (params: {params})" if params else ""))
    return "\n".join(lines)


# ---- generation -------------------------------------------------------------------------------
def generate_json(prompt: str, schema: type[BaseModel], log=print) -> tuple[BaseModel, str]:
    """Ask Gemini for JSON in `schema`. Replaced in tests; raises PlannerError with a plain reason."""
    from beatframe import review

    try:
        client = review._client()
        from google.genai import types

        config = types.GenerateContentConfig(response_mime_type="application/json", response_schema=schema,
                                             temperature=0.9)
        resp, model = review._generate(client, review.model_candidates(client), prompt, config, log, lambda m: None)
    except review.ReviewError as e:
        raise PlannerError(str(e)) from None
    except Exception as e:  # noqa: BLE001
        raise PlannerError(f"Gemini did not answer: {str(e)[:200]}") from None
    parsed = getattr(resp, "parsed", None)
    if parsed is None:
        try:
            parsed = schema.model_validate_json(resp.text)
        except Exception as e:  # noqa: BLE001
            raise PlannerError(f"Gemini's answer was not in the expected shape: {e}") from None
    return parsed, model


BASE = ("You are the content strategist of the YouTube channel described below. Use ONLY the facts in the "
        "context: never invent view counts or results. Titles and narration are in English, explanations in Uzbek.\n\n")


def run(kind: str, brief: str, projects_root: Path, stats_text: str = "", fmt: str = "short", count: int = 6,
        days: int = 7, log=print) -> dict:
    ctx = context(projects_root, stats_text)
    brief = brief.strip()
    if kind == "ideas":
        prompt = (f"{BASE}CONTEXT\n{ctx}\n\nTASK: propose {count} NEW video ideas"
                  f"{' for ' + fmt + ' videos' if fmt in ('short', 'long') else ''}. Never repeat a topic in "
                  f"MADE IN BEATFRAME. Follow the winners' pattern from the stats.\nCreator's note: {brief or '-'}")
        res, model = generate_json(prompt, Ideas, log)
        payload = {"ideas": [i.model_dump() for i in res.ideas][:count]}
    elif kind == "hooks":
        if not brief:
            raise PlannerError("Write the topic to get hooks for.")
        prompt = f"{BASE}CONTEXT\n{ctx}\n\nTASK: write 6 different opening hooks for this topic: {brief}"
        res, model = generate_json(prompt, Hooks, log)
        payload = {"hooks": [h.model_dump() for h in res.hooks][:8]}
    elif kind == "plan":
        today = time.strftime("%a %d %b %Y")
        prompt = (f"{BASE}CONTEXT\n{ctx}\n\nTASK: a publishing plan for the next {days} days starting {today}, "
                  f"following the cadence in the channel rules. Only new topics.\nCreator's note: {brief or '-'}")
        res, model = generate_json(prompt, Plan, log)
        payload = res.model_dump()
    elif kind == "script":
        if not brief:
            raise PlannerError("Write the idea (title and hook) to draft a script for.")
        prompt = (f"{BASE}CONTEXT\n{ctx}\n\nSCENES YOU MAY USE (scene name: params)\n{scene_catalog()}\n\n"
                  f"TASK: write a complete Beatframe YAML script ({fmt}: "
                  f"{'about 7 beats, 20-25 s' if fmt == 'short' else '45-55 beats, 10-12 min, with chapters'}) "
                  f"for this idea: {brief}\nThe YAML needs title, description, tags, video: {{format: {fmt}}} and "
                  f"beats (text, scene, params). Quote every text value.")
        res, model = generate_json(prompt, Draft, log)
        payload = {**res.model_dump(), **check_yaml(res.yaml)}
    else:
        raise PlannerError(f"unknown job {kind}")
    return {"payload": payload, "model": model}


def check_yaml(text: str) -> dict:
    """Run the draft through Beatframe's own parser and pre-render check."""
    from beatframe.preflight import preflight
    from beatframe.schema import parse_project

    try:
        p = parse_project(text)
    except Exception as e:  # noqa: BLE001
        return {"valid": False, "problems": [str(e).splitlines()[0][:300]]}
    problems = [str(x) for x in preflight(p) if x.level == "error"]
    return {"valid": not problems, "problems": problems, "beats": len(p.beats)}
