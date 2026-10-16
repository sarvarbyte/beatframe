"""Studio features added on top of the core app: Storyboard, Thumbnail Lab, Compare, Quality and Ideas.

Each one reads and writes the same project files the rest of Beatframe uses; nothing here shows a
number that is not on disk (renders, manifests, AI reviews, the last Stats report).
"""

from __future__ import annotations

import io
import json
import shutil
from pathlib import Path

from fastapi import Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response

from beatframe import planner, quality, thumblab, versions
from beatframe.formats import get_format
from beatframe.pipeline import output_name
from beatframe.web import insights, stats


def register(app, *, store, jobs, page, get_slug, tpl) -> None:
    root = store.root

    # ------------------------------------------------------------------ helpers for templates
    def lab_ctx(slug: str, fmt: str) -> dict:
        spec = get_format(fmt)
        out = store.output(slug)
        data = thumblab.load(out, spec.suffix)
        video = next((out / output_name(k, spec.name) for k in ("final", "preview")
                      if (out / output_name(k, spec.name)).exists()), None)
        dur = None
        if video:
            try:
                dur = json.loads(video.with_suffix(".json").read_text(encoding="utf-8")).get("duration")
            except (OSError, ValueError):
                pass
        return {"variants": data["variants"], "selected": data["selected"], "sources": thumblab.sources(out, spec.suffix),
                "dir": thumblab.thumbs_dir(out, spec.suffix).name, "video": video.name if video else "",
                "duration": dur, "styles": list(thumblab.STYLES), "defaults": thumblab.DEFAULTS}

    def compare_ctx(slug: str, fmt: str) -> list[dict]:
        return versions.available(store.output(slug), get_format(fmt).suffix)

    def project_quality(slug: str) -> list[dict]:
        return quality.project_reviews(store.folder(slug))

    def frames_ok(slug: str, fmt: str) -> bool:
        """True when the newest render has a beat timeline, so per-beat stills can be cut from it."""
        out = store.output(slug)
        vids = [out / output_name(k, fmt) for k in ("preview", "final") if (out / output_name(k, fmt)).exists()]
        if not vids:
            return False
        try:
            return bool(json.loads(max(vids, key=lambda v: v.stat().st_mtime).with_suffix(".json")
                                   .read_text(encoding="utf-8")).get("timeline"))
        except (OSError, ValueError):
            return False

    tpl.env.globals.update(frames_ok=frames_ok, lab_ctx=lab_ctx, compare_ctx=compare_ctx, project_quality=project_quality,
                           tojson_safe=lambda v: json.dumps(v, ensure_ascii=False).replace("</", "<\\/"))

    def fmt_of(slug: str) -> str:
        return store.load(slug).video.format

    # ------------------------------------------------------------------ storyboard
    @app.post("/p/{slug}/storyboard/order")
    async def storyboard_order(request: Request, slug: str):
        """New beat order from the storyboard: a permutation of 1..n (old positions, in the new order)."""
        slug = get_slug(slug)
        if jobs.active(slug):
            return JSONResponse({"ok": False, "error": "A render is running. Wait for it to finish, then reorder."},
                                status_code=409)
        body = await request.json()
        order = [int(x) for x in body.get("order", [])]
        project = store.load(slug)
        n = len(project.beats)
        if sorted(order) != list(range(1, n + 1)):
            return JSONResponse({"ok": False, "error": "The order does not match this project's beats. Reload the page."},
                                status_code=400)
        if order == list(range(1, n + 1)):
            return {"ok": True, "changed": False}
        # a photo beat without `image` uses images/beat_NNN.png by position: pin that name before it moves
        for k, b in enumerate(project.beats, 1):
            if b.scene == "photo" and not str(b.params.get("image") or "").strip():
                b.params = {**b.params, "image": f"images/beat_{k:03d}.png"}
        project.beats = [project.beats[i - 1] for i in order]
        store.save(slug, project)
        _renumber_renders(store.output(slug), order)
        shutil.rmtree(store.folder(slug) / "build" / "frames", ignore_errors=True)
        return {"ok": True, "changed": True}

    @app.post("/p/{slug}/storyboard/duplicate/{i}")
    def storyboard_duplicate(slug: str, i: int):
        slug = get_slug(slug)
        project = store.load(slug)
        if not 1 <= i <= len(project.beats):
            raise HTTPException(404, "no such beat")
        project.beats.insert(i, project.beats[i - 1].model_copy(deep=True))
        store.save(slug, project)
        return RedirectResponse(f"/p/{slug}?tab=storyboard#sb-{i + 1}", status_code=303)

    # ------------------------------------------------------------------ thumbnail lab
    def _lab_out(slug: str) -> tuple[Path, str, str]:
        fmt = fmt_of(slug)
        return store.output(slug), get_format(fmt).suffix, fmt

    @app.get("/p/{slug}/thumbs/preview.jpg")
    def thumb_preview(request: Request, slug: str):
        slug = get_slug(slug)
        out, suffix, fmt = _lab_out(slug)
        settings = dict(request.query_params)
        src = thumblab.thumbs_dir(out, suffix) / str(settings.get("source", ""))
        if not settings.get("source") or not src.exists():
            raise HTTPException(404, "pick a frame")
        img = thumblab.render(src, settings, fmt)
        img.thumbnail((960, 960))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=82)
        return Response(buf.getvalue(), media_type="image/jpeg", headers={"Cache-Control": "no-store"})

    @app.post("/p/{slug}/thumbs/variant")
    async def thumb_variant(request: Request, slug: str):
        slug = get_slug(slug)
        out, suffix, fmt = _lab_out(slug)
        form = dict(await request.form())
        try:
            entry = thumblab.create(out, suffix, fmt, form, replace=form.get("replace", ""))
        except thumblab.LabError as e:
            return RedirectResponse(f"/p/{slug}?tab=thumbs&lab_error={e}", status_code=303)
        return RedirectResponse(f"/p/{slug}?tab=thumbs&made={entry['id']}#variants", status_code=303)

    @app.post("/p/{slug}/thumbs/grab")
    def thumb_grab(slug: str, seconds: float = Form(...)):
        slug = get_slug(slug)
        out, suffix, fmt = _lab_out(slug)
        video = next((out / output_name(k, fmt) for k in ("final", "preview") if (out / output_name(k, fmt)).exists()),
                     out / output_name("final", fmt))
        try:
            name = thumblab.grab_frame(video, seconds, out, suffix)
        except thumblab.LabError as e:
            return RedirectResponse(f"/p/{slug}?tab=thumbs&lab_error={e}", status_code=303)
        return RedirectResponse(f"/p/{slug}?tab=thumbs&source={name}", status_code=303)

    @app.post("/p/{slug}/thumbs/select")
    def thumb_select(slug: str, file: str = Form(""), next: str = Form("thumbs")):
        slug = get_slug(slug)
        out, suffix, _ = _lab_out(slug)
        try:
            thumblab.select(out, suffix, file)
        except thumblab.LabError as e:
            return RedirectResponse(f"/p/{slug}?tab=thumbs&lab_error={e}", status_code=303)
        tab = next if next in ("thumbs", "publish") else "thumbs"
        return RedirectResponse(f"/p/{slug}?tab={tab}", status_code=303)

    @app.post("/p/{slug}/thumbs/delete/{vid}")
    def thumb_delete(slug: str, vid: str):
        slug = get_slug(slug)
        out, suffix, _ = _lab_out(slug)
        thumblab.delete(out, suffix, vid)
        return RedirectResponse(f"/p/{slug}?tab=thumbs#variants", status_code=303)

    # ------------------------------------------------------------------ compare
    @app.get("/p/{slug}/compare/videos")
    def compare_videos(slug: str):
        slug = get_slug(slug)
        return {"videos": compare_ctx(slug, fmt_of(slug))}

    # ------------------------------------------------------------------ quality history
    @app.get("/quality", response_class=HTMLResponse)
    def quality_page(request: Request):
        reviews = quality.all_reviews(root)
        return page(request, "quality.html", nav="quality", crumb="AI quality", reviews=reviews,
                    summary=quality.summary(reviews), points=quality.chart_points(reviews),
                    categories=quality.CATEGORIES)

    # ------------------------------------------------------------------ ideas
    @app.get("/ideas", response_class=HTMLResponse)
    def ideas_page(request: Request, kind: str = "ideas"):
        from beatframe import review
        data = planner.load(root)
        return page(request, "ideas.html", nav="ideas", crumb="Ideas", items=data["items"],
                    has_key=review.has_key("gemini"), kind=kind if kind in ("ideas", "hooks", "plan", "script") else "ideas",
                    has_stats=bool(stats.last_report().get("text")))

    @app.post("/ideas/run", response_class=HTMLResponse)
    def ideas_run(request: Request, kind: str = Form("ideas"), brief: str = Form(""), fmt: str = Form("short"),
                  count: int = Form(6), days: int = Form(7)):
        try:
            res = planner.run(kind, brief, root, stats.last_report().get("text", ""), fmt=fmt,
                              count=max(1, min(12, count)), days=max(3, min(14, days)), log=lambda m: None)
        except planner.PlannerError as e:
            return HTMLResponse(f'<div class="alert err" id="idea-error">{_esc(str(e))}</div>', status_code=200)
        item = planner.add(root, kind, brief, res["payload"], res["model"])
        return page(request, "_idea.html", it=item, fresh=True)

    @app.post("/ideas/{item_id}/star", response_class=HTMLResponse)
    def ideas_star(request: Request, item_id: str):
        it = planner.get(root, item_id)
        if not it:
            raise HTTPException(404)
        planner.update(root, item_id, starred=not it.get("starred"))
        return page(request, "_idea.html", it=planner.get(root, item_id))

    @app.post("/ideas/{item_id}/delete", response_class=HTMLResponse)
    def ideas_delete(item_id: str):
        planner.delete(root, item_id)
        return HTMLResponse("")

    @app.get("/ideas/{item_id}/use")
    def ideas_use(item_id: str):
        """Open a drafted script in the Studio form (nothing is created until Generate is pressed)."""
        it = planner.get(root, item_id)
        if not it or it["kind"] != "script":
            raise HTTPException(404)
        return RedirectResponse(f"/?idea={item_id}", status_code=303)

    # ------------------------------------------------------------------ analytics data
    @app.get("/api/stats")
    def stats_data():
        last = stats.last_report()
        return {"when": last.get("when", ""), "rows": insights.report_table(last.get("text", "")),
                "summary": insights.report_summary(last.get("text", ""))}


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _renumber_renders(out_dir: Path, order: list[int]) -> None:
    """After a reorder, the existing renders still show the beats in the old order. Their manifests are
    relabelled (old beat k -> its new number), so per-beat stills and the storyboard stay right until the
    next render."""
    new_of = {old: new for new, old in enumerate(order, 1)}
    for manifest in list(out_dir.glob("*.json")):
        if manifest.stem.split("_")[0] not in ("preview", "final", "beat"):
            continue
        try:
            data = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(data.get("timeline"), list):
            continue
        for t in data["timeline"]:
            if t.get("beat") in new_of:
                t["beat"] = new_of[t["beat"]]
        if isinstance(data.get("beats"), list):
            data["beats"] = [new_of.get(b, b) for b in data["beats"]]
        manifest.write_text(json.dumps(data, indent=2), encoding="utf-8")
