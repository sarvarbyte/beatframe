"""AI quality history: every AI review a project ever got, across all projects.

A review is saved as output/review<suffix>.json and replaced by the next one. So each new review
is also appended to output/review_history<suffix>.jsonl, and the current review files are folded in
too (older projects reviewed before the history existed still count, once).
Nothing here invents a score: it only reads what the AI review wrote.
"""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime
from pathlib import Path

import yaml

SUFFIXES = {"long": "", "short": "_short"}
CATEGORIES = ["hook", "pacing", "visual", "voice", "captions", "text", "fact", "ending", "other"]
SEVERITIES = ["high", "medium", "low"]


def history_file(out_dir: Path, suffix: str) -> Path:
    return out_dir / f"review_history{suffix}.jsonl"


def append(out_dir: Path, suffix: str, result: dict) -> None:
    """Remember one review (called right after it is saved)."""
    with history_file(out_dir, suffix).open("a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")


def _read_jsonl(f: Path) -> list[dict]:
    out = []
    try:
        for line in f.read_text(encoding="utf-8").splitlines():
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    except OSError:
        pass
    return out


def _title(folder: Path) -> str:
    try:
        data = yaml.safe_load((folder / f"{folder.name}.yaml").read_text(encoding="utf-8")) or {}
        return str(data.get("title") or folder.name)
    except (OSError, yaml.YAMLError):
        return folder.name


def project_reviews(folder: Path) -> list[dict]:
    """All reviews of one project, oldest first: {slug, title, fmt, created, score, verdict, issues...}."""
    out_dir = folder / "output"
    title = _title(folder)
    rows: dict[tuple, dict] = {}
    for fmt, suffix in SUFFIXES.items():
        entries = _read_jsonl(history_file(out_dir, suffix))
        try:
            entries.append(json.loads((out_dir / f"review{suffix}.json").read_text(encoding="utf-8")))
        except (OSError, ValueError):
            pass
        for e in entries:
            r = e.get("review") or {}
            if r.get("score") is None or not e.get("created"):
                continue
            key = (fmt, e["created"])          # the current file is usually also the last history line
            issues = r.get("issues") or []
            rows[key] = {
                "slug": folder.name, "title": title, "fmt": fmt, "created": e["created"],
                "score": int(r["score"]), "verdict": r.get("verdict", ""), "model": e.get("model", ""),
                "video": e.get("video", ""), "summary": r.get("summary", ""),
                "issues": [{"beat": i.get("beat", 0), "severity": i.get("severity", "low"),
                            "category": i.get("category", "other"), "problem": i.get("problem", ""),
                            "time": i.get("time", "")} for i in issues],
            }
    return sorted(rows.values(), key=lambda x: x["created"])


def all_reviews(projects_root: Path) -> list[dict]:
    out: list[dict] = []
    for f in sorted(Path(projects_root).glob("*/*.yaml")):
        if f.stem == f.parent.name:
            out += project_reviews(f.parent)
    return sorted(out, key=lambda x: x["created"])


def summary(reviews: list[dict]) -> dict:
    """Numbers for the Quality page, computed only from saved reviews."""
    if not reviews:
        return {"count": 0}
    latest: dict[str, dict] = {}
    for r in reviews:
        latest[f'{r["slug"]}|{r["fmt"]}'] = r            # oldest first, so the last one wins
    cats = Counter(i["category"] for r in reviews for i in r["issues"])
    sev = Counter(i["severity"] for r in reviews for i in r["issues"])
    by_cat = {c: {s: 0 for s in SEVERITIES} for c in CATEGORIES}
    for r in reviews:
        for i in r["issues"]:
            by_cat.setdefault(i["category"], {s: 0 for s in SEVERITIES})[i["severity"]] += 1
    scores = [r["score"] for r in reviews]
    first, last = reviews[0], reviews[-1]
    # improvement: projects reviewed more than once, first vs last score
    deltas = []
    for key in latest:
        own = [r for r in reviews if f'{r["slug"]}|{r["fmt"]}' == key]
        if len(own) > 1:
            deltas.append(own[-1]["score"] - own[0]["score"])
    return {
        "count": len(reviews), "projects": len(latest),
        "avg": round(sum(scores) / len(scores), 1), "best": max(scores), "worst": min(scores),
        "ready": sum(1 for r in latest.values() if r["verdict"] == "ready"),
        "first": first["created"][:10], "last": last["created"][:10],
        "top_category": cats.most_common(1)[0] if cats else None,
        "severity": {s: sev.get(s, 0) for s in SEVERITIES},
        "by_category": {c: v for c, v in by_cat.items() if sum(v.values())},
        "latest": sorted(latest.values(), key=lambda r: r["created"], reverse=True),
        "improved": deltas,
    }


def chart_points(reviews: list[dict]) -> list[dict]:
    """One point per review for the score-over-time chart."""
    pts = []
    for r in reviews:
        try:
            t = datetime.fromisoformat(r["created"]).timestamp()
        except ValueError:
            continue
        pts.append({"t": t, "date": r["created"][:16].replace("T", " "), "score": r["score"], "title": r["title"],
                    "slug": r["slug"], "fmt": r["fmt"], "issues": len(r["issues"]),
                    "high": sum(1 for i in r["issues"] if i["severity"] == "high")})
    return pts
