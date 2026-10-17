"""Projects live on disk exactly like the CLI uses them: projects/<slug>/<slug>.yaml."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, get_args, get_origin, Literal

from pydantic import ValidationError

from beatframe.formats import FORMATS, get_format
from beatframe.pipeline import output_name, validate
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
    fmt: str = "long"
    thumb: str | None = None          # path under the projects root, for /files/...
    broken: bool = False
    imported: bool = False
    score: int | None = None          # AI review score of this format's latest review
    live: dict | None = None          # filled in by the app: where the video is published

    @property
    def status(self) -> str:
        return "completed" if self.has_final else "draft"


def _video_info(f: Path) -> dict:
    """Size, time and render manifest (format, resolution, length) of an output video."""
    info = {"name": f.name, "mtime": int(f.stat().st_mtime), "size": f.stat().st_size}
    meta = f.with_suffix(".json")
    if meta.exists():
        try:
            info.update(json.loads(meta.read_text(encoding="utf-8")))
        except ValueError:
            pass
    return info


def _review_score(out: Path, fmt: str) -> int | None:
    f = out / f"review{get_format(fmt).suffix}.json"
    try:
        return int(json.loads(f.read_text(encoding="utf-8"))["review"]["score"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


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
            broken, fmt, imported = False, "long", False
            try:
                p = parse_project(f.read_text(encoding="utf-8"))
                title, beats, fmt, imported = p.title, len(p.beats), p.video.format, p.imported
            except Exception:  # noqa: BLE001
                title, beats, broken = f"{f.stem} (script has errors)", 0, True
            out = f.parent / "output"
            vids = list(out.glob("*.mp4")) if out.exists() else []
            finals = [v for v in vids if v.stem in ("final", "final_short")]
            dur = None
            if finals:
                dur = _video_info(max(finals, key=lambda v: v.stat().st_mtime)).get("duration")
            items.append(ProjectInfo(
                slug=f.stem, title=title, beats=beats,
                modified=max([f.stat().st_mtime] + [x.stat().st_mtime for x in vids]),
                has_final=bool(finals),
                has_preview=any(v.stem.startswith("preview") for v in vids),
                duration=dur, fmt=fmt, thumb=self.cover(f.stem), broken=broken, imported=imported,
                score=_review_score(out, fmt),
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

    def new_slug(self, title: str) -> str:
        base = slugify(title)
        slug, n = base, 2
        while self.exists(slug) or self.folder(slug).exists():
            slug, n = f"{base}-{n}", n + 1
        return slug

    def create_import(self, card_text: str, video: Path) -> tuple[str | None, str, list[str]]:
        """A project from a finished video + its import card. Returns (slug, error, notes)."""
        from beatframe import importer

        try:
            p = importer.parse_card(card_text)
            importer.probe(video)
        except (importer.ImportError_, ValidationError) as e:
            return None, friendly_error(e), []
        slug = self.new_slug(p.title)
        folder = self.folder(slug)
        folder.mkdir(parents=True)
        try:
            done = importer.import_video(p, card_text, video, folder, slug)
        except Exception as e:  # noqa: BLE001
            import shutil

            shutil.rmtree(folder, ignore_errors=True)
            return None, f"Could not import the video: {e}", []
        return slug, "", done["notes"]

    def save_text(self, slug: str, text: str) -> str:
        p, err = self.check_text(text)
        if not p:
            return err
        self.file(slug).write_text(text.strip() + "\n", encoding="utf-8")
        return ""

    def save(self, slug: str, project: Project) -> None:
        self.file(slug).write_text(dump_project(project), encoding="utf-8")

    def apply_options(self, slug: str, title: str = "", fmt: str = "") -> None:
        """Set the title and/or video format. The file is only rewritten if something changes,
        so a pasted script keeps its comments when the defaults are used."""
        project = self.load(slug)
        changed = False
        if title.strip() and title.strip() != project.title:
            project.title, changed = title.strip(), True
        if fmt and get_format(fmt).name != project.video.format:
            project.video, changed = project.video.with_format(fmt), True
        if changed:
            self.save(slug, project)

    def outputs(self, slug: str, fmt: str = "long") -> dict[str, Any]:
        """Rendered files of one format: final / preview / beat_preview videos, subtitles,
        chapters and thumbnail candidates. `other` lists videos of the other formats."""
        out = self.output(slug)
        spec = get_format(fmt)
        files: dict[str, Any] = {"fmt": spec.name, "spec": spec.to_dict()}
        for kind in ("final", "preview", "beat_preview"):
            f = out / output_name(kind, spec.name)
            files[kind] = _video_info(f) if f.exists() else None
        for name in ("subtitles.srt", "chapters.txt"):
            f = out / name
            files[name] = {"name": name, "mtime": int(f.stat().st_mtime), "size": f.stat().st_size} if f.exists() else None
        tdir = out / ("thumbs" + spec.suffix)
        files["thumb_dir"] = tdir.name
        # render candidates (thumb_*.png), grabbed frames and Thumbnail Lab designs (lab_*.jpg, listed first)
        found = [p.name for p in tdir.iterdir() if p.suffix.lower() in (".png", ".jpg", ".jpeg")] if tdir.exists() else []
        files["thumbs"] = sorted(found, key=lambda n: (not n.startswith("lab_"), n))
        files["other"] = [
            {"fmt": other.name, "label": other.label, "aspect": other.aspect, "kind": kind}
            for other in FORMATS.values() if other.name != spec.name
            for kind in ("final", "preview") if (out / output_name(kind, other.name)).exists()
        ]
        return files

    def beat_frame(self, slug: str, fmt: str, i: int) -> Path | None:
        """A still from the middle of beat i, taken from the newest preview/final of this format
        (cached in build/frames; a new render gives new stills)."""
        import subprocess

        out = self.output(slug)
        vids = [out / output_name(k, fmt) for k in ("preview", "final")]
        vids = [v for v in vids if v.exists()]
        if not vids:
            return None
        video = max(vids, key=lambda v: v.stat().st_mtime)
        try:
            timeline = json.loads(video.with_suffix(".json").read_text(encoding="utf-8")).get("timeline") or []
        except (OSError, ValueError):
            return None
        span = next((t for t in timeline if t.get("beat") == i), None)
        if not span:
            return None
        frames = self.folder(slug) / "build" / "frames"
        frames.mkdir(parents=True, exist_ok=True)
        f = frames / f"{video.stem}_{int(video.stat().st_mtime)}_{i:03d}.jpg"
        if not f.exists():
            for old in frames.glob(f"{video.stem}_*_{i:03d}.jpg"):
                old.unlink()
            t = span["start"] + (span["end"] - span["start"]) * 0.6
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1",
                            "-vf", "scale='if(gt(iw,ih),640,-2)':'if(gt(iw,ih),-2,640)'", "-q:v", "4", str(f)],
                           check=False)
        return f if f.exists() else None

    def cover(self, slug: str) -> str | None:
        """An image to show for the project in lists (relative to the projects root)."""
        out = self.output(slug)
        if not out.exists():
            return None
        for cand in [out / "thumbnail.jpg", out / "thumbnail.png",
                     *sorted((out / "thumbs").glob("*.png")), *sorted((out / "thumbs_short").glob("*.png"))]:
            if cand.exists():
                return str(cand.relative_to(self.root))
        return None

    def chapters(self, slug: str) -> str:
        f = self.output(slug) / "chapters.txt"
        return f.read_text(encoding="utf-8").strip() if f.exists() else ""


# ---- template params -> form fields ------------------------------------------

def template_fields(scene: str, values: dict) -> list[dict]:
    """Describe a template's params so the page can draw a matching form."""
    cls = get_template(scene)
    fields = []
    items = list(cls.Params.model_fields.items())
    try:                    # science-library scenes: their own settings first, the shared look settings last
        from beatframe.templates.sci import SciParams
        if issubclass(cls.Params, SciParams):
            shared = set(SciParams.model_fields)
            items = [i for i in items if i[0] not in shared] + [i for i in items if i[0] in shared]
    except ImportError:  # pragma: no cover
        pass
    for name, info in items:
        ann = info.annotation
        current = values.get(name, info.default)
        f = {"name": name, "value": current, "default": info.default}
        lo = next((m.ge for m in info.metadata if getattr(m, "ge", None) is not None), None)
        hi = next((m.le for m in info.metadata if getattr(m, "le", None) is not None), None)
        if ann is bool:
            f["kind"] = "bool"
        elif ann in (int, float) and lo is not None and hi is not None:
            f["kind"] = "range"           # a slider: the template declared its sensible limits
            span = hi - lo        # a step that lands exactly on the default and on round numbers
            f.update(min=lo, max=hi, step=1 if ann is int else (0.01 if span <= 1.5 else 0.05 if span <= 5 else 0.1 if span <= 20 else 1))
        elif ann in (int, float):
            f["kind"] = "number"
            f["step"] = "1" if ann is int else "any"
        elif get_origin(ann) is Literal and name in ("highlight", "palette") and _swatches(name, get_args(ann)):
            f["kind"] = "swatch"
            f["options"] = _swatches(name, get_args(ann))
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


def _swatches(name: str, options) -> list[dict]:
    """Colour chips for the science-library colour settings (palette = background, highlight = accent)."""
    from beatframe.templates import sci
    out = []
    for o in options:
        if name == "palette" and o in sci.PALETTES:
            pal = sci.PALETTES[o]
            out.append({"value": o, "colors": [pal["top"], pal["lavender"], pal["mint"], pal["coral"]]})
        elif name == "highlight" and o in sci.PALETTES["dusk"]:
            out.append({"value": o, "colors": [sci.PALETTES["dusk"][o]]})
        else:
            return []
    return out


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
    get_template(next(iter(REGISTRY), "title_card"))  # make sure every template module is imported
    return [{"name": n, "description": REGISTRY[n].description,
             "short_native": REGISTRY[n].vertical_width <= 8.0,
             "fields": template_fields(n, {})} for n in sorted(REGISTRY)]


def new_beat(after: Beat | None = None) -> Beat:
    return Beat(text="New sentence for the narrator.", scene="statement",
                params={"text": "New sentence for the narrator."})


def now() -> float:
    return time.time()
