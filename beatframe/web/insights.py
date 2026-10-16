"""What the pages show about a project's progress, computed from files on disk.

  * workflow(...)       - the 5 steps (Script, Preview, AI review, Final, Publish) and the next step
  * report_summary(...) - headline numbers from the last Stats report
  * published(...)      - which titles are live on the channel (from the last Stats report or an upload)
"""

from __future__ import annotations

import json
import re
from pathlib import Path

STEPS = ["Script", "Preview", "AI review", "Final", "Publish"]


def _num(s: str) -> float | None:
    s = s.strip().replace(",", "").rstrip("%")
    try:
        return float(s)
    except ValueError:
        return None


def report_rows(text: str) -> list[dict]:
    """Video rows of a Stats report: type, title, views, % viewed, likes."""
    rows, in_table = [], False
    for line in (text or "").splitlines():
        if line.startswith("type |"):
            in_table = True
            continue
        if not in_table or " | " not in line:
            continue
        cells = [c.strip() for c in line.split(" | ")]
        if len(cells) < 13:
            continue
        rows.append({"type": cells[0], "title": cells[4], "views": _num(cells[5]),
                     "viewed": _num(cells[8]), "likes": _num(cells[9]), "status": cells[12]})
    return rows


def report_summary(text: str) -> dict:
    """Views and watch time of the period, average % viewed and likes over the listed videos."""
    out: dict = {}
    m = re.search(r"LAST (\d+) DAYS: views ([\d,]+) · watch ([\d.]+) h · subs \+(\d+) / -(\d+)", text or "")
    if m:
        out.update(days=int(m.group(1)), views=int(m.group(2).replace(",", "")), watch=float(m.group(3)),
                   subs=int(m.group(4)) - int(m.group(5)))
    m = re.search(r"subscribers ([\d,]+)", text or "")
    if m:
        out["subscribers"] = int(m.group(1).replace(",", ""))
    rows = report_rows(text)
    viewed = [r["viewed"] for r in rows if r["viewed"] is not None]
    out["avg_viewed"] = round(sum(viewed) / len(viewed), 1) if viewed else None
    out["likes"] = int(sum(r["likes"] or 0 for r in rows)) if rows else None
    out["videos"] = len(rows)
    return out


def _norm(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", re.sub(r"#\w+", "", title.lower())).strip()


def published_index(report_text: str) -> dict[tuple[str, str], dict]:
    """(S|L, normalised title) -> report row, for public videos."""
    return {(r["type"], _norm(r["title"])): r for r in report_rows(report_text)
            if r["status"].lower() == "public" and (r["views"] or 0) >= 0}


def published(out_dir: Path, suffix: str, fmt: str, title: str, index: dict) -> dict | None:
    """Where this video is live: an upload made from Studio, or a matching public video in the report."""
    f = out_dir / f"publish{suffix}.json"
    if f.exists():
        try:
            return json.loads(f.read_text(encoding="utf-8"))
        except ValueError:
            pass
    row = index.get(("S" if fmt == "short" else "L", _norm(title)))
    return {"source": "report", "views": row["views"], "viewed": row["viewed"]} if row else None


def workflow(project, out: dict, review: dict | None, review_stale: bool, live: dict | None,
             tips: int = 0) -> dict:
    """The 5 steps with their state, and the one next thing to do (title, text, action)."""
    imported = bool(project and project.imported)
    has_preview = bool(out.get("preview")) or imported
    has_final = bool(out.get("final"))
    r = review.get("review") if review else None
    high = [i for i in (r or {}).get("issues", []) if i.get("severity") == "high"]
    done = [True, has_preview, bool(r) and not review_stale, has_final, bool(live)]
    current = next((i for i, d in enumerate(done) if not d), len(STEPS))
    detail = [
        "Imported card" if imported else (f"{len(project.beats)} beats" + (f" · {tips} tips" if tips else "")) if project else "",
        "Imported video" if imported else ("480p ready" if out.get("preview") else "Not rendered"),
        (f"{r['score']}/10" + (f" · {len(high)} high" if high else "")) if r else "Not reviewed",
        "1080p ready" if has_final else "Not rendered",
        "Live" if live else "Not published",
    ]
    steps = [{"label": s, "state": "done" if done[i] else ("current" if i == current else "todo"), "detail": detail[i]}
             for i, s in enumerate(STEPS)]

    if not has_preview:
        nxt = {"title": "Render a quick preview", "text": "A 480p look at the whole video in about a minute.",
               "action": "preview", "label": "Render preview"}
    elif not r or review_stale:
        nxt = {"title": "Let the AI watch it", "text": "It checks the hook, pacing, captions and facts against "
               "the channel's rules and points at the exact beat.", "action": "review", "label": "Review with AI"}
    elif high and not imported:
        b = high[0].get("beat") or 0
        nxt = {"title": f"Fix the {high[0].get('category', 'main')} problem before you go final",
               "text": high[0].get("problem", ""), "action": "edit", "beat": b,
               "label": f"Improve beat {b}" if b else "Open Edit beats"}
    elif not has_final:
        nxt = {"title": "Render the final video", "text": "Full quality with captions, chapters and thumbnails.",
               "action": "final", "label": "Render final"}
    elif not live:
        nxt = {"title": "Publish it", "text": "Upload to YouTube from here, or download the files for a manual upload.",
               "action": "publish", "label": "Go to Publish"}
    else:
        views = live.get("views")
        nxt = {"title": "It's live", "text": (f"{int(views):,} views so far. " if views is not None else "") +
               "Check the numbers on the Stats page after 48 hours.", "action": "stats", "label": "Open Stats"}
    return {"steps": steps, "done": sum(done), "current": current, "next": nxt}
