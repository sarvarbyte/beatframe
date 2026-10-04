"""Projects live on disk exactly like the CLI uses them: projects/<slug>/<slug>.yaml."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, get_args, get_origin, Literal

from pydantic import ValidationError

from beatframe.pipeline import validate
from beatframe.schema import Beat, Project, dump_project, parse_project
from beatframe.templates import REGISTRY, get_template


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:48] or "video"


def friendly_error(e: Exception) -> str:
    if isinstance(e, ValidationError):
        lines = []
        for err in e.errors():
            loc = ".".join(str(x) for x in err["loc"])
            lines.append(f"{loc}: {err['msg']}")
        return "\n".join(lines)
    return str(e)


@dataclass
class ProjectInfo:
    slug: str
    title: str
    beats: int
    modified: float
    has_final: bool
    has_preview: bool
    duration: float | None


class Store:
    def __init__(self, root: Path):
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    # ---- paths -----------------------------------------------------------
    def folder(self, slug: str) -> Path:
        if not re.fullmatch(r"[a-z0-9-]+", slug):
            raise KeyError(slug)
        return self.root / slug

    def file(self, slug: str) -> Path:
        return self.folder(slug) / f"{slug}.yaml"

    def output(self, slug: str) -> Path:
        return self.folder(slug) / "output"

    # ---- read ------------------------------------------------------------
    def list(self) -> list[ProjectInfo]:
        items = []
        for f in sorted(self.root.glob("*/*.yaml")):
            if f.stem != f.parent.name:
                continue
            try:
                p = parse_project(f.read_text(encoding="utf-8"))
                title, beats = p.title, len(p.beats)
            except Exception:  # noqa: BLE001
                title, beats = f"{f.stem} (script has errors)", 0
            out = f.parent / "output"
            items.append(ProjectInfo(
                slug=f.stem, title=title, beats=beats,
                modified=max(f.stat().st_mtime, *(x.stat().st_mtime for x in out.glob("*.mp4"))) if out.exists() and any(out.glob("*.mp4")) else f.stat().st_mtime,
                has_final=(out / "final.mp4").exists(),
                has_preview=(out / "preview.mp4").exists(),
                duration=None,
            ))
        return sorted(items, key=lambda i: -i.modified)

    def exists(self, slug: str) -> bool:
        return self.file(slug).exists()

    def raw(self, slug: str) -> str:
        return self.file(slug).read_text(encoding="utf-8")

    def load(self, slug: str) -> Project:
        return parse_project(self.raw(slug))

    # ---- write -----------------------------------------------------------
    def check_text(self, text: str) -> tuple[Project | None, str]:
        """Parse + validate pasted YAML. Returns (project, error_message)."""
        try:
            p = parse_project(text)
        except Exception as e:  # noqa: BLE001
            return None, friendly_error(e)
        problems = validate(p)
        if problems:
            return None, "\n".join(problems)
        return p, ""

    def create(self, text: str) -> tuple[str | None, str]:
        p, err = self.check_text(text)
        if not p:
            return None, err
        base = slugify(p.title)
        slug, n = base, 2
        while self.exists(slug):
            slug, n = f"{base}-{n}", n + 1
        self.folder(slug).mkdir(parents=True, exist_ok=True)
        self.file(slug).write_text(text.strip() + "\n", encoding="utf-8")
        return slug, ""

    def save_text(self, slug: str, text: str) -> str:
        p, err = self.check_text(text)
        if not p:
            return err
        self.file(slug).write_text(text.strip() + "\n", encoding="utf-8")
        return ""

    def save(self, slug: str, project: Project) -> None:
        self.file(slug).write_text(dump_project(project), encoding="utf-8")

    def outputs(self, slug: str) -> dict[str, Any]:
        out = self.output(slug)
        files = {}
        for name in ("final.mp4", "preview.mp4", "subtitles.srt", "chapters.txt"):
            f = out / name
            if f.exists():
                files[name] = {"mtime": int(f.stat().st_mtime), "size": f.stat().st_size}
        thumbs = sorted(p.name for p in (out / "thumbs").glob("*.png")) if (out / "thumbs").exists() else []
        files["thumbs"] = thumbs
        return files

    def chapters(self, slug: str) -> str:
        f = self.output(slug) / "chapters.txt"
        return f.read_text(encoding="utf-8").strip() if f.exists() else ""


# ---- template params -> form fields ------------------------------------------

def template_fields(scene: str, values: dict) -> list[dict]:
    """Describe a template's params so the page can draw a matching form."""
    cls = get_template(scene)
    fields = []
    for name, info in cls.Params.model_fields.items():
        ann = info.annotation
        current = values.get(name, info.default)
        f = {"name": name, "value": current, "default": info.default}
        if ann is bool:
            f["kind"] = "bool"
        elif ann in (int, float):
            f["kind"] = "number"
            f["step"] = "1" if ann is int else "any"
        elif get_origin(ann) is Literal:
            f["kind"] = "select"
            f["options"] = list(get_args(ann))
        elif get_origin(ann) is list:
            f["kind"] = "list"
            f["value"] = ", ".join(str(x) for x in (current or []))
        else:
            f["kind"] = "textarea" if len(str(current or "")) > 60 else "text"
        fields.append(f)
    return fields


def params_from_form(scene: str, form: dict) -> dict:
    """Turn submitted form fields (prefixed 'p.') back into a params dict."""
    cls = get_template(scene)
    out: dict = {}
    for name, info in cls.Params.model_fields.items():
        key = f"p.{name}"
        ann = info.annotation
        if ann is bool:
            val = form.get(key) in ("on", "true", "1")
        elif key not in form:
            continue
        else:
            raw = str(form[key]).strip()
            if ann is int:
                val = int(float(raw)) if raw else info.default
            elif ann is float:
                val = float(raw) if raw else info.default
            elif get_origin(ann) is list:
                val = [x.strip() for x in raw.split(",") if x.strip()]
            else:
                val = raw
        if val != info.default:
            out[name] = val
    return out


def template_catalog() -> list[dict]:
    return [{"name": n, "description": REGISTRY[n].description} for n in sorted(REGISTRY)]


def new_beat(after: Beat | None = None) -> Beat:
    return Beat(text="New sentence for the narrator.", scene="statement",
                params={"text": "New sentence for the narrator."})


def now() -> float:
    return time.time()
