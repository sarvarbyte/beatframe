"""Template library: categories, favourites, recently used, saved presets, reusable compositions and
real per-template preview renders.

Everything personal lives in ~/.beatframe/ (per computer, never inside a project):
  library.json        {"favorites": [...], "recent": [{"name", "when"}]}
  presets.json        [{"id", "template", "name", "params", "created"}]
  compositions.json   [{"id", "name", "beats": [{text, scene, params, ...}], "created"}]
  template_previews/  <template>/<clip key>/001_<key>.mp4  (real Manim renders, reused by key)
"""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

from beatframe.render import ClipJob, clip_key, render_clip
from beatframe.templates import REGISTRY, get_template

STATIC_SCENES = Path(__file__).parent / "web" / "static" / "scenes"

CATEGORIES = ["Neuroscience", "Human perception", "Experiments", "Biology", "Physics & scale",
              "Data & facts", "Text & titles", "Stick figures", "Media & code"]

# categories of the templates that existed before the science library (new ones declare `category`)
LEGACY = {
    "brain_light": "Neuroscience", "nerve_race": "Neuroscience", "ion_channel": "Neuroscience",
    "prediction": "Neuroscience", "rubber_hand": "Human perception", "skin_receptors": "Human perception",
    "body_map": "Human perception", "atom_scale": "Physics & scale", "cosmic_zoom": "Physics & scale",
    "earth_finger": "Physics & scale", "electron_repulsion": "Physics & scale", "scale_zoom": "Physics & scale",
    "bar_chart": "Data & facts", "stat_pop": "Data & facts", "source_card": "Data & facts", "timeline": "Data & facts",
    "myth_fact": "Data & facts", "icon_list": "Data & facts", "process_cycle": "Data & facts",
    "statement": "Text & titles", "title_card": "Text & titles", "kinetic_text": "Text & titles",
    "question_hook": "Text & titles", "stick_compare": "Stick figures", "stick_crowd": "Stick figures",
    "stick_doorway": "Stick figures", "stick_scene": "Stick figures", "stick_talk": "Stick figures",
    "photo": "Media & code", "custom": "Media & code",
}


def category(name: str) -> str:
    cls = REGISTRY.get(name)
    return getattr(cls, "category", None) or LEGACY.get(name, "Media & code" if getattr(cls, "library_code", None) else "Text & titles")


def _home() -> Path:
    return Path.home() / ".beatframe"


# ---- small JSON stores ---------------------------------------------------------------------------
def _read(name: str, default):
    try:
        return json.loads((_home() / name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _write(name: str, data) -> None:
    _home().mkdir(parents=True, exist_ok=True)
    tmp = _home() / (name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(_home() / name)


def state() -> dict:
    data = _read("library.json", {})
    return {"favorites": list(data.get("favorites", [])), "recent": list(data.get("recent", []))}


def toggle_favorite(name: str) -> bool:
    s = state()
    on = name not in s["favorites"]
    s["favorites"] = [n for n in s["favorites"] if n != name] + ([name] if on else [])
    _write("library.json", s)
    return on


def touch_recent(name: str) -> None:
    s = state()
    s["recent"] = [{"name": name, "when": time.strftime("%Y-%m-%d %H:%M")}] + [r for r in s["recent"] if r.get("name") != name]
    s["recent"] = s["recent"][:8]
    _write("library.json", s)


# ---- presets ---------------------------------------------------------------------------------------
def presets(template: str | None = None) -> list[dict]:
    items = _read("presets.json", [])
    return [p for p in items if not template or p.get("template") == template]


def save_preset(template: str, name: str, params: dict) -> dict:
    get_template(template).Params.model_validate(params)        # never store settings that cannot render
    items = _read("presets.json", [])
    item = {"id": uuid.uuid4().hex[:8], "template": template, "name": (name or "Preset").strip()[:60],
            "params": params, "created": time.strftime("%Y-%m-%d %H:%M")}
    items = [p for p in items if not (p["template"] == template and p["name"] == item["name"])] + [item]
    _write("presets.json", items)
    return item


def get_preset(pid: str) -> dict | None:
    return next((p for p in _read("presets.json", []) if p.get("id") == pid), None)


def delete_preset(pid: str) -> None:
    _write("presets.json", [p for p in _read("presets.json", []) if p.get("id") != pid])


# ---- compositions (a reusable run of beats) ---------------------------------------------------------
BEAT_KEYS = ("text", "scene", "params", "min_duration", "transition", "chapter", "pad")


def compositions() -> list[dict]:
    return _read("compositions.json", [])


def save_composition(name: str, beats: list) -> dict:
    """beats: schema.Beat objects. Only what is needed to recreate them is stored."""
    data = []
    for b in beats:
        d = b.model_dump(mode="json", exclude_defaults=True) | {"text": b.text, "scene": b.scene}
        data.append({k: v for k, v in d.items() if k in BEAT_KEYS})
    item = {"id": uuid.uuid4().hex[:8], "name": (name or "Composition").strip()[:60], "beats": data,
            "created": time.strftime("%Y-%m-%d %H:%M")}
    _write("compositions.json", [c for c in compositions() if c["name"] != item["name"]] + [item])
    return item


def get_composition(cid: str) -> dict | None:
    return next((c for c in compositions() if c.get("id") == cid), None)


def delete_composition(cid: str) -> None:
    _write("compositions.json", [c for c in compositions() if c.get("id") != cid])


def composition_beats(comp: dict) -> list:
    from beatframe.schema import Beat
    return [Beat(**b) for b in comp.get("beats", [])]


# ---- real previews ---------------------------------------------------------------------------------------
def preview_job(name: str, params: dict, fmt: str, seconds: float, preset: str = "eco") -> ClipJob:
    from beatframe import renderconf
    w, h, fps = renderconf.preset_size(preset, fmt == "short")
    return ClipJob(1, name, params, round(max(2.0, min(20.0, seconds)), 1), w, h, fps)


def preview_dir(job: ClipJob) -> Path:
    return _home() / "template_previews" / job.template / clip_key(job)


def cached_preview(job: ClipJob) -> Path | None:
    f = preview_dir(job) / f"001_{clip_key(job)}.mp4"
    return f if f.exists() else None


def render_preview(job: ClipJob, cancel=None) -> Path:
    return render_clip(job, preview_dir(job), cancel)


def static_loop(name: str) -> str | None:
    """The catalogue loop (a real render of the defaults, made by `beatframe scene-thumbs`)."""
    return f"/static/scenes/{name}.mp4" if (STATIC_SCENES / f"{name}.mp4").exists() else None


def catalog() -> list[dict]:
    from beatframe.web.store import template_fields
    get_template(next(iter(REGISTRY), "title_card"))
    fav = set(state()["favorites"])
    out = []
    for n in sorted(REGISTRY):
        cls = REGISTRY[n]
        out.append({"name": n, "title": n.replace("_", " ").capitalize(), "description": cls.description,
                    "category": category(n), "short_native": cls.vertical_width <= 8.0,
                    "fields": template_fields(n, {}), "favorite": n in fav,
                    "poster": f"/static/scenes/{n}.png" if (STATIC_SCENES / f"{n}.png").exists() else None,
                    "loop": static_loop(n), "new": bool(getattr(cls, "category", None))})
    return out
