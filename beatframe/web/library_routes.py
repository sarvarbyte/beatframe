"""Template Library pages (catalogue, detail editor with real preview renders, presets, favourites),
laptop render settings, and the composer actions on the storyboard (compositions, durations,
transitions, single-scene previews)."""

from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi import Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from beatframe import library, renderconf
from beatframe.schema import Beat
from beatframe.templates import REGISTRY, get_template
from beatframe.web.store import params_from_form, template_fields

TRANSITIONS = [None, "cut", "fade", "fadeblack", "dissolve", "smoothleft", "smoothup", "wipeleft", "wipeup",
               "slideleft", "slideup", "circleopen", "radial"]


def recent_stats(root: Path, limit: int = 12) -> list[dict]:
    """Measured cost of the newest uncached clip renders (projects and library previews)."""
    files = list(root.glob("*/build/render_stats.jsonl")) + list((Path.home() / ".beatframe" / "template_previews").glob("*/render_stats.jsonl"))
    rows = []
    for f in files:
        try:
            for line in f.read_text(encoding="utf-8").splitlines()[-limit:]:
                rows.append(json.loads(line))
        except (OSError, ValueError):
            continue
    rows.sort(key=lambda r: r.get("when", ""), reverse=True)
    return rows[:limit]


def register(app, *, store, jobs, page, get_slug, tpl, submit_render) -> None:
    tpl.env.globals.update(render_settings=renderconf.load, render_presets=renderconf.PRESETS,
                           recent_render_stats=lambda: recent_stats(store.root),
                           compositions=library.compositions, transitions=TRANSITIONS)

    def _known(name: str) -> str:
        try:
            get_template(name)
        except KeyError:
            raise HTTPException(404, "no such template")
        return name

    # ------------------------------------------------------------------ library
    @app.get("/templates", response_class=HTMLResponse)
    def library_page(request: Request):
        items = library.catalog()
        st = library.state()
        recent = [i for r in st["recent"] for i in items if i["name"] == r.get("name")]
        cats = [c for c in library.CATEGORIES if any(i["category"] == c for i in items)]
        return page(request, "templates.html", nav="templates", crumb="Templates", items=items, recent=recent,
                    categories=cats, presets=library.presets())

    @app.get("/templates/{name}", response_class=HTMLResponse)
    def template_detail(request: Request, name: str, preset: str = "", fmt: str = "long", seconds: float = 6.0):
        name = _known(name)
        values = {}
        chosen = library.get_preset(preset) if preset else None
        if chosen and chosen["template"] == name:
            values = chosen["params"]
        fmt = fmt if fmt in ("long", "short") else "long"
        job = library.preview_job(name, values, fmt, seconds)
        cached = library.cached_preview(job)
        cls = REGISTRY[name]
        return page(request, "template_detail.html", nav="templates", crumb=name, tname=name, cls=cls,
                    category=library.category(name), fields=template_fields(name, values), values=values,
                    defaults={f["name"]: f["default"] for f in template_fields(name, {})},
                    preset=chosen, presets=library.presets(name), fmt=fmt, seconds=job.duration,
                    cached=cached, loop=library.static_loop(name), favorite=name in library.state()["favorites"],
                    projects=_project_choices())

    def _project_choices() -> list[dict]:
        return [{"slug": i.slug, "title": i.title, "beats": i.beats, "format": i.fmt}
                for i in store.list() if not i.imported and not i.broken]

    def _form_params(name: str, form: dict) -> dict:
        params = params_from_form(name, form)
        get_template(name).Params.model_validate(params)
        return params

    @app.post("/templates/{name}/preview", response_class=HTMLResponse)
    async def template_preview(request: Request, name: str):
        name = _known(name)
        form = dict(await request.form())
        try:
            params = _form_params(name, form)
        except Exception as e:  # noqa: BLE001
            return page(request, "_tpl_preview.html", tname=name, error=_friendly(e))
        fmt = form.get("fmt") if form.get("fmt") in ("long", "short") else "long"
        job = library.preview_job(name, params, fmt, float(form.get("seconds") or 6))
        cached = library.cached_preview(job)
        library.touch_recent(name)
        if cached:
            return page(request, "_tpl_preview.html", tname=name, video=_url(cached), fmt=fmt, cached=True)

        def run(j) -> dict:
            out = library.render_preview(job, cancel=j.cancel)
            j.done = 1
            return {"video": _url(out), "stats": job.stats}

        j = jobs.submit("_templates", "tpl", f"{name} · {fmt} · {job.width}×{job.height}", 1, run, fmt=fmt)
        return page(request, "_tpl_preview.html", tname=name, job=j, fmt=fmt)

    @app.get("/templates/{name}/preview/{job_id}", response_class=HTMLResponse)
    def template_preview_status(request: Request, name: str, job_id: str):
        j = jobs.jobs.get(job_id)
        if not j:
            raise HTTPException(404)
        if j.status == "done":
            return page(request, "_tpl_preview.html", tname=name, video=j.result.get("video"), fmt=j.fmt, stats=j.result.get("stats"))
        return page(request, "_tpl_preview.html", tname=name, job=j, fmt=j.fmt,
                    ahead=sum(1 for o in jobs.jobs.values() if o.status == "running" and o.id != j.id))

    @app.post("/templates/{name}/preview/{job_id}/cancel", response_class=HTMLResponse)
    def template_preview_cancel(request: Request, name: str, job_id: str):
        jobs.cancel(job_id)
        return page(request, "_tpl_preview.html", tname=name, job=jobs.jobs.get(job_id), fmt="long")

    @app.get("/library-preview/{template}/{key}/{file}")
    def preview_file(template: str, key: str, file: str):
        from fastapi.responses import FileResponse
        base = (Path.home() / ".beatframe" / "template_previews").resolve()
        f = (base / template / key / file).resolve()
        if base not in f.parents or not f.exists() or f.suffix != ".mp4":
            raise HTTPException(404)
        return FileResponse(f, media_type="video/mp4")

    def _url(f: Path) -> str:
        return f"/library-preview/{f.parent.parent.name}/{f.parent.name}/{f.name}"

    @app.post("/templates/{name}/favorite", response_class=HTMLResponse)
    def template_favorite(request: Request, name: str):
        on = library.toggle_favorite(_known(name))
        return HTMLResponse(_fav_button(name, on))

    @app.post("/templates/{name}/preset")
    async def template_preset(request: Request, name: str):
        name = _known(name)
        form = dict(await request.form())
        try:
            item = library.save_preset(name, form.get("preset_name", ""), _form_params(name, form))
        except Exception as e:  # noqa: BLE001
            return RedirectResponse(f"/templates/{name}?error={_friendly(e)}", status_code=303)
        return RedirectResponse(f"/templates/{name}?preset={item['id']}&fmt={form.get('fmt', 'long')}", status_code=303)

    @app.post("/templates/presets/{pid}/delete")
    def preset_delete(pid: str):
        p = library.get_preset(pid)
        library.delete_preset(pid)
        return RedirectResponse(f"/templates/{p['template']}" if p else "/templates", status_code=303)

    @app.post("/templates/{name}/use")
    async def template_use(request: Request, name: str):
        """Add this template (with the editor's settings) as a new beat to a project."""
        name = _known(name)
        form = dict(await request.form())
        slug = get_slug(form.get("project", ""))
        try:
            params = _form_params(name, form)
        except Exception as e:  # noqa: BLE001
            return RedirectResponse(f"/templates/{name}?error={_friendly(e)}", status_code=303)
        if jobs.active(slug):
            return RedirectResponse(f"/templates/{name}?error=That project is rendering. Try again when it finishes.", status_code=303)
        project = store.load(slug)
        text = (form.get("text") or "").strip() or "New sentence for the narrator."
        beat = Beat(text=text, scene=name, params=params)
        pos = form.get("position", "end")
        at = len(project.beats) if pos == "end" else max(0, min(len(project.beats), int(pos)))
        project.beats.insert(at, beat)
        store.save(slug, project)
        library.touch_recent(name)
        return RedirectResponse(f"/p/{slug}?tab=storyboard#sb-{at + 1}", status_code=303)

    # ------------------------------------------------------------------ render settings
    @app.post("/settings/render")
    def save_render_settings(workers: int = Form(1), nice: int = Form(10), preview_preset: str = Form("eco")):
        renderconf.save(renderconf.RenderSettings(workers=workers, nice=nice, preview_preset=preview_preset))
        return RedirectResponse("/settings#render", status_code=303)

    # ------------------------------------------------------------------ composer (storyboard)
    @app.post("/p/{slug}/storyboard/beat/{i}")
    def storyboard_beat(slug: str, i: int, min_duration: float = Form(2.0), transition: str = Form("")):
        """Minimum length and the transition into this beat, edited from its storyboard card."""
        slug = get_slug(slug)
        project = store.load(slug)
        if not 1 <= i <= len(project.beats):
            raise HTTPException(404)
        b = project.beats[i - 1]
        b.min_duration = max(0.5, min(30.0, float(min_duration)))
        b.transition = transition if transition in TRANSITIONS[1:] else None
        project.beats[i - 1] = Beat(**b.model_dump())
        store.save(slug, project)
        return RedirectResponse(f"/p/{slug}?tab=storyboard#sb-{i}", status_code=303)

    @app.post("/p/{slug}/storyboard/preview/{i}")
    def storyboard_preview(slug: str, i: int):
        slug = get_slug(slug)
        if not jobs.active(slug):
            submit_render(slug, "beat", only=[i])
        return RedirectResponse(f"/p/{slug}?tab=video", status_code=303)

    @app.post("/p/{slug}/storyboard/preview-all")
    def storyboard_preview_all(slug: str):
        slug = get_slug(slug)
        if not jobs.active(slug):
            submit_render(slug, "preview")
        return RedirectResponse(f"/p/{slug}?tab=video", status_code=303)

    @app.post("/p/{slug}/compositions/save")
    def composition_save(slug: str, name: str = Form(""), first: int = Form(1), last: int = Form(0)):
        slug = get_slug(slug)
        beats = store.load(slug).beats
        last = last or len(beats)
        first, last = max(1, first), min(len(beats), last)
        if first > last:
            raise HTTPException(400, "empty range")
        library.save_composition(name or f"{store.load(slug).title} {first}-{last}", beats[first - 1:last])
        return RedirectResponse(f"/p/{slug}?tab=storyboard&saved=composition#composer", status_code=303)

    @app.post("/p/{slug}/compositions/{cid}/insert")
    def composition_insert(slug: str, cid: str, position: str = Form("end")):
        slug = get_slug(slug)
        comp = library.get_composition(cid)
        if not comp:
            raise HTTPException(404)
        if jobs.active(slug):
            return RedirectResponse(f"/p/{slug}?tab=storyboard", status_code=303)
        project = store.load(slug)
        at = len(project.beats) if position == "end" else max(0, min(len(project.beats), int(position)))
        new = library.composition_beats(comp)
        for b in new:
            get_template(b.scene).Params.model_validate(b.params)
        project.beats[at:at] = new
        store.save(slug, project)
        return RedirectResponse(f"/p/{slug}?tab=storyboard#sb-{at + 1}", status_code=303)

    @app.post("/compositions/{cid}/delete")
    def composition_delete(cid: str, back: str = Form("/templates")):
        library.delete_composition(cid)
        return RedirectResponse(back if back.startswith("/") else "/templates", status_code=303)


def _fav_button(name: str, on: bool) -> str:
    star = ('<svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 3.5 2.6 5.4 5.9.8-4.3 4.1 1 5.8L12 16.9l-5.2 2.7 1-5.8-4.3-4.1 5.9-.8z"/></svg>')
    return (f'<button class="favbtn{" on" if on else ""}" hx-post="/templates/{name}/favorite" hx-swap="outerHTML" '
            f'aria-pressed="{str(on).lower()}" title="{"Remove from" if on else "Add to"} favourites">{star}</button>')


def _friendly(e: Exception) -> str:
    msg = str(e)
    if "validation error" in msg:
        lines = [ln.strip() for ln in msg.splitlines()[1:] if ln.strip() and not ln.strip().startswith("For further")]
        return "; ".join(lines[:4])[:300]
    return msg[:300]
