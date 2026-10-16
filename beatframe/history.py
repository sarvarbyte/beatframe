"""What was already made: topics and scenes of every project, for variety and for picking new ideas.

    beatframe history            # copyable text: made videos (newest first) + scene use in the last 5

The same block is added to the end of the Stats report, so Claude sees the made topics and the
scenes used lately without opening the projects folder.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import yaml


@dataclass
class Made:
    slug: str
    title: str
    format: str
    when: datetime
    rendered: bool
    imported: bool
    scenes: list[str] = field(default_factory=list)
    custom_codes: set[str] = field(default_factory=set)


def code_hash(code: str) -> str:
    return hashlib.sha1(re.sub(r"\s+", " ", code).strip().encode()).hexdigest()[:10]


def made(projects_root: Path) -> list[Made]:
    """Every project, newest first. Broken YAML files are skipped, not fatal."""
    out = []
    for f in sorted(Path(projects_root).glob("*/*.yaml")):
        if f.stem != f.parent.name:
            continue
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            continue
        beats = data.get("beats") or []
        fmt = str((data.get("video") or {}).get("format") or "long")
        outs = f.parent / "output"
        rendered = any(outs.glob("final*.mp4")) if outs.is_dir() else False
        out.append(Made(
            slug=f.parent.name, title=str(data.get("title") or f.parent.name), format=fmt,
            when=datetime.fromtimestamp(f.stat().st_mtime), rendered=rendered,
            imported=data.get("source") == "import",
            scenes=[str(b.get("scene", "")) for b in beats if isinstance(b, dict)],
            custom_codes={code_hash(str((b.get("params") or {}).get("code", ""))) for b in beats
                          if isinstance(b, dict) and b.get("scene") == "custom"},
        ))
    return sorted(out, key=lambda m: m.when, reverse=True)


def recent(projects_root: Path, exclude: str = "", n: int = 5) -> list[Made]:
    return [m for m in made(projects_root) if m.slug != exclude and not m.imported][:n]


def report(projects_root: Path, n_recent: int = 5) -> str:
    items = made(projects_root)
    if not items:
        return ""
    lines = ["MADE IN BEATFRAME (newest first) — don't repeat these topics:"]
    for m in items:
        state = "imported" if m.imported else ("rendered" if m.rendered else "draft")
        lines.append(f"{m.when:%Y-%m-%d} | {m.format} | {state} | {m.title}")
    rec = recent(projects_root, n=n_recent)
    if rec:
        use = Counter(s for m in rec for s in m.scenes)
        total = sum(use.values()) or 1
        lines += ["", f"SCENES USED IN THE LAST {len(rec)} VIDEOS (prefer the rarely used ones):",
                  " · ".join(f"{s} {n * 100 // total}%" for s, n in use.most_common(12))]
    return "\n".join(lines)
