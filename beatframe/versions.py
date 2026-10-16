"""Earlier renders, kept for side-by-side comparison.

Every time a preview or final is rendered again, the one it replaces moves to
output/versions/<kind><suffix>@<YYYYmmdd-HHMMSS>.mp4 (with its .json manifest). Only the newest
few are kept per kind, so long videos don't fill the disk.
"""

from __future__ import annotations

import json
import shutil
import time
from pathlib import Path

KEEP = {"preview": 3, "final": 2}


def folder(out_dir: Path) -> Path:
    return out_dir / "versions"


def archive(video: Path) -> Path | None:
    """Move an existing render (and its manifest) into versions/ before it is replaced."""
    if not video.exists():
        return None
    kind = video.stem.split("_")[0]              # preview / final / beat
    if kind not in KEEP:
        return None
    dest_dir = folder(video.parent)
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(video.stat().st_mtime))
    dest = dest_dir / f"{video.stem}@{stamp}.mp4"
    shutil.move(str(video), dest)
    manifest = video.with_suffix(".json")
    if manifest.exists():
        shutil.copyfile(manifest, dest.with_suffix(".json"))
    _prune(dest_dir, video.stem, KEEP[kind])
    return dest


def _prune(dest_dir: Path, stem: str, keep: int) -> None:
    old = sorted(dest_dir.glob(f"{stem}@*.mp4"), key=lambda f: f.name, reverse=True)[keep:]
    for f in old:
        f.unlink(missing_ok=True)
        f.with_suffix(".json").unlink(missing_ok=True)


def _info(f: Path, label: str, current: bool) -> dict:
    try:
        manifest = json.loads(f.with_suffix(".json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        manifest = {}
    st = f.stat()
    return {
        "id": ("" if current else "versions/") + f.name, "label": label, "current": current,
        "kind": f.stem.split("_")[0].split("@")[0], "mtime": int(st.st_mtime), "size": st.st_size,
        "duration": manifest.get("duration"), "width": manifest.get("width"), "height": manifest.get("height"),
        "timeline": manifest.get("timeline") or [],
    }


def available(out_dir: Path, suffix: str) -> list[dict]:
    """Every video of one format that can be compared: current final/preview first, then earlier ones."""
    out: list[dict] = []
    for kind in ("final", "preview", "beat_preview"):
        f = out_dir / f"{kind}{suffix}.mp4"
        if f.exists():
            out.append(_info(f, {"final": "Final", "preview": "Preview", "beat_preview": "Beat preview"}[kind], True))
    vdir = folder(out_dir)
    if vdir.exists():
        for kind in ("final", "preview"):
            for f in sorted(vdir.glob(f"{kind}{suffix}@*.mp4"), key=lambda f: f.name, reverse=True):
                when = time.strftime("%d %b %H:%M", time.localtime(f.stat().st_mtime))
                out.append(_info(f, f"Earlier {kind} · {when}", False))
    return out


def resolve(out_dir: Path, vid: str) -> Path | None:
    """A video id from available() back to its file (never outside the output folder)."""
    f = (out_dir / vid).resolve()
    try:
        f.relative_to(out_dir.resolve())
    except ValueError:
        return None
    return f if f.exists() and f.suffix == ".mp4" else None
