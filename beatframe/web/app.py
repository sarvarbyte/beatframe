"""Beatframe Studio: paste a script, watch it render, edit beats, publish."""

from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path
from urllib.parse import quote

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from beatframe import __version__, brand, importer, pipeline, review
from beatframe.advice import script_advice
from beatframe.preflight import preflight
from beatframe import history
from beatframe.formats import FORMATS, get_format
from beatframe.schema import Beat
from beatframe.templates import get_template
from beatframe.web import insights, stats, youtube
from beatframe.web.jobs import Job, JobManager
from beatframe.web.store import (
    Store, friendly_error, new_beat, params_from_form, template_catalog, template_fields,
)

HERE = Path(__file__).parent
EXAMPLE = '''title: "Your Video Title"
description: "One or two sentences for the YouTube description."
tags: [science, brain]

voice: {provider: edge, name: en-US-AndrewNeural, rate: "-5%"}

beats:
  - text: "The first thing the narrator says."
    scene: title_card
    chapter: "Intro"
    params: {line1: "YOU HAVE NEVER", line2: "TOUCHED ANYTHING"}
'''


def create_app(projects_root: Path, port: int = 8000) -> FastAPI:
    app = FastAPI(title="Beatframe Studio", docs_url=None, redoc_url=None)
    store = Store(projects_root)
    jobs = JobManager()
    tpl = Jinja2Templates(directory=str(HERE / "templates"))
    tpl.env.globals.update(
        templates_list=template_catalog, fmt_time=lambda t: time.strftime("%d %b %H:%M", time.localtime(t)),
        ago=_ago, fmt_size=_size, fmt_secs=_secs, formats=[f.to_dict() for f in FORMATS.values()],
        version=__version__, yt_connected=lambda: youtube.is_configured() and youtube.is_connected(),
    )
    app.mount("/static", StaticFiles(directory=str(HERE / "static")), name="static")
    app.mount("/fonts", StaticFiles(directory=str(brand.FONT_DIR)), name="fonts")
    app.mount("/files", StaticFiles(directory=str(store.root)), name="files")
    redirect_uri = f"http://127.0.0.1:{port}/youtube/callback"

    def page(request: Request, name: str, **ctx) -> HTMLResponse:
        ctx.setdefault("nav", "")
        ctx.setdefault("crumb", "")
        # shell: the top bar's status and the projects count in the sidebar
        running = [j for j in jobs.jobs.values() if j.status in ("queued", "running")]
        ctx["busy_job"] = running[0] if running else None
        ctx["project_count"] = sum(1 for f in store.root.glob("*/*.yaml") if f.stem == f.parent.name)
        return tpl.TemplateResponse(request, name, ctx)

    def live_index() -> dict:
        return insights.published_index(stats.last_report().get("text", ""))

    def projects_with_state() -> list:
        items, index = store.list(), live_index()
        for it in items:
            it.rendering = bool(jobs.active(it.slug))
            it.live = insights.published(store.output(it.slug), get_format(it.fmt).suffix, it.fmt, it.title, index)
        return items

    def get_slug(slug: str) -> str:
        try:
            if store.exists(slug):
                return slug
        except KeyError:
            pass
        raise HTTPException(404, "project not found")

    # ---------------------------------------------------------------- jobs
    def submit_render(slug: str, kind: str, only: list[int] | None = None) -> Job:
        """Queue a render in the project's video format (saved in its YAML)."""
        project = store.load(slug)
        spec = project.video.spec
        w, h = project.video.size(preview=(kind != "make"))
        total = len(only) if only else len(project.beats)
        label = {"preview": f"Preview · {spec.label} {spec.aspect} · {w}×{h}",
                 "make": f"Final video · {spec.label} {spec.aspect} · {w}×{h}",
                 "beat": f"Beat {only[0] if only else ''} preview · {spec.label} {spec.aspect}"}[kind]

        def run(job: Job) -> dict:
            p = store.load(slug)
            res = pipeline.run(
                p, store.file(slug), preview=(kind != "make"), only=only, log=job.log,
                out_name="beat_preview" if kind == "beat" else None,
                video_format=job.fmt, progress=job.on_progress,
            )
            return {"video": res.video.name, "seconds": round(res.total, 1)}

        return jobs.submit(slug, kind, label, total, run, fmt=spec.name)

    def submit_upload(slug: str, meta: dict, captions: bool, thumb: str, fmt: str) -> Job:
        out = store.output(slug)
        spec = get_format(fmt)

        def run(job: Job) -> dict:
            def prog(f: float) -> None:
                job.done = int(f * 100)
            res = youtube.upload(
                out / pipeline.output_name("final", spec.name), meta, log=job.lines.append, progress=prog,
                captions=(out / "subtitles.srt") if captions and (out / "subtitles.srt").exists() else None,
                thumbnail=(out / ("thumbs" + spec.suffix) / thumb) if thumb else None,
            )
            # remembered so Projects can show it as published
            (out / f"publish{spec.suffix}.json").write_text(json.dumps(
                {"source": "upload", "url": res.get("url"), "privacy": res.get("privacy"),
                 "publish_at": meta.get("publish_at") or "", "uploaded": time.strftime("%Y-%m-%d %H:%M")}),
                encoding="utf-8")
            return res

        return jobs.submit(slug, "upload", f"YouTube upload · {spec.label} {spec.aspect}", 100, run, fmt=spec.name)

    def submit_review(slug: str) -> Job:
        """Queue AI review #1 of the project's newest video (preview or final) in its current format."""
        project = store.load(slug)
        spec = project.video.spec

        def run(job: Job) -> dict:
            def step(n: int) -> None:
                job.done = n - 1
                job.stage = {1: "Sending the video to the AI", 2: "The AI is watching the video",
                             3: "Writing the review"}[n]
            try:
                res = review.run_review(store.load(slug), store.file(slug), spec.name, log=job.log, step=step,
                                        status=lambda m: setattr(job, "stage", m))
            except review.ReviewError as e:
                raise RuntimeError(str(e)) from None
            return {"score": res["review"]["score"], "issues": len(res["review"]["issues"])}

        return jobs.submit(slug, "review", f"AI review · {spec.label} {spec.aspect}", 3, run, fmt=spec.name)

    # ---------------------------------------------------------------- home
    def home_page(request: Request, script: str = "", error: str = "", title: str = "",
                  fmt: str = "long", render: str = "preview", mode: str = "create", card: str = "") -> HTMLResponse:
        items = projects_with_state()
        return page(request, "home.html", nav="studio", crumb="Import video" if mode == "import" else "Studio",
                    projects=items[:5], total=len(items), example=EXAMPLE,
                    script=script, error=error, title=title, fmt=get_format(fmt).name, render=render,
                    mode="import" if mode == "import" else "create", card=card, card_example=importer.CARD_EXAMPLE)

    @app.get("/api/palette")
    def palette_data():
        """Projects for the command palette (Ctrl/⌘+K): just titles, newest first, no video probing."""
        import yaml as _yaml
        out = []
        files = [f for f in store.root.glob("*/*.yaml") if f.stem == f.parent.name]
        for f in sorted(files, key=lambda f: -f.stat().st_mtime)[:60]:
            try:
                data = _yaml.safe_load(f.read_text(encoding="utf-8")) or {}
            except Exception:  # noqa: BLE001
                data = {}
            fmt = str((data.get("video") or {}).get("format") or "long")
            out.append({"slug": f.stem, "title": str(data.get("title") or f.stem), "fmt": fmt})
        return {"projects": out}

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request, format: str = "long", mode: str = "create", idea: str = ""):
        script = ""
        if idea:      # a script drafted on the Ideas page, opened here for checking before Generate
            from beatframe import planner
            it = planner.get(store.root, idea)
            if it and it["kind"] == "script":
                script = it["payload"].get("yaml", "")
                if "format: short" in script:
                    format = "short"
        return home_page(request, fmt=format if format in FORMATS else "long", mode=mode, script=script)

    @app.post("/check-import", response_class=HTMLResponse)
    def check_import(request: Request, card: str = Form("")):
        if not card.strip():
            return HTMLResponse("")
        try:
            p, err = importer.parse_card(card), ""
        except (importer.ImportError_, ValueError) as e:
            p, err = None, friendly_error(e)
        return page(request, "_check_import.html", project=p, error=err)

    @app.get("/projects", response_class=HTMLResponse)
    def projects_page(request: Request):
        items = projects_with_state()
        scores = [p.score for p in items if p.score is not None]
        summary = {"total": len(items), "drafts": sum(1 for p in items if not p.has_final and not p.has_preview),
                   "finals": sum(1 for p in items if p.has_final), "live": sum(1 for p in items if p.live),
                   "avg": round(sum(scores) / len(scores), 1) if scores else None, "reviewed": len(scores)}
        return page(request, "projects.html", nav="projects", crumb="Projects", projects=items, summary=summary)

    @app.get("/templates", response_class=HTMLResponse)
    def templates_page(request: Request):
        thumbs = {p.stem for p in (HERE / "static" / "scenes").glob("*.png")}
        return page(request, "templates.html", nav="templates", crumb="Templates", thumbs=thumbs)

    @app.get("/settings", response_class=HTMLResponse)
    def settings_page(request: Request):
        connected = youtube.is_configured() and youtube.is_connected()
        return page(request, "settings.html", nav="settings", crumb="Settings", root=str(store.root),
                    yt={"configured": youtube.is_configured(), "connected": connected,
                        "channel": youtube.channel_name() if connected else "",
                        "config_dir": str(youtube.CONFIG_DIR)},
                    ai={p: {"has_key": review.has_key(p), "from_env": bool(os.environ.get(env)),
                            "env": env, "key_file": str(review.key_file(p))}
                        for p, (env, _) in review.KEYS.items()})

    # ---------------------------------------------------------------- stats
    def stats_ctx() -> dict:
        connected = youtube.is_configured() and youtube.is_connected()
        return {"configured": youtube.is_configured(), "connected": connected,
                "scope": connected and stats.has_scope(), "channel": youtube.channel_name() if connected else "",
                "secret": youtube.secret_info()}

    @app.get("/stats", response_class=HTMLResponse)
    def stats_page(request: Request):
        last = stats.last_report()
        return page(request, "stats.html", nav="stats", crumb="Stats", yt=stats_ctx(), last=last,
                    summary=insights.report_summary(last.get("text", "")),
                    rows=insights.report_table(last.get("text", "")))

    @app.post("/stats/run", response_class=HTMLResponse)
    def stats_run(request: Request, days: int = Form(28)):
        days = days if days in (7, 28, 90) else 28
        try:
            text, error = stats.build_report(days=days), ""
            made = history.report(projects_root)
            if made:          # made topics + recent scenes, so Claude doesn't repeat them
                text = text.rstrip() + "\n\n" + made
                stats.LAST.write_text(text, encoding="utf-8")
        except stats.StatsError as e:
            text, error = "", str(e)
        except Exception as e:  # noqa: BLE001
            text, error = "", f"Could not read statistics: {e}"
        return page(request, "_stats.html", last={"text": text, "when": "just now"} if text else {}, error=error)

    @app.post("/check", response_class=HTMLResponse)
    def check(request: Request, script: str = Form("")):
        if not script.strip():
            return HTMLResponse("")
        p, err = store.check_text(script)
        return page(request, "_check.html", project=p, error=err, tips=script_advice(p) if p else [],
                    issues=[str(x) for x in preflight(p)] if p else [])

    @app.post("/projects")
    def create(request: Request, script: str = Form(...), render: str = Form("preview"),
               title: str = Form(""), format: str = Form("long")):
        fmt = format if format in FORMATS else "long"
        slug, err = store.create(script)
        if not slug:
            return home_page(request, script=script, error=err, title=title, fmt=fmt, render=render)
        store.apply_options(slug, title=title, fmt=fmt)   # name and format chosen in the form
        if render in ("preview", "make"):
            submit_render(slug, render)
        return RedirectResponse(f"/p/{slug}", status_code=303)

    # ------------------------------------------------------------- project
    @app.get("/p/{slug}", response_class=HTMLResponse)
    def project_page(request: Request, slug: str, tab: str = "video", note: str = "", lab_error: str = "",
                     source: str = "", made: str = "", a: str = "", b: str = ""):
        slug = get_slug(slug)
        try:
            project, perr = store.load(slug), ""
        except Exception as e:  # noqa: BLE001
            project, perr, tab = None, friendly_error(e), "script"
        out = store.outputs(slug, project.video.format if project else "long")
        beats = []
        if project:
            for i, b in enumerate(project.beats, 1):
                beats.append({"i": i, "beat": b, "fields": template_fields(b.scene, b.params)})
        desc, flow, rv, live = "", None, _review_ctx(slug, out), None
        if project:
            footer = ("" if project.imported else
                      "Narration: AI voice. Animation made with Beatframe by Human Unknowns.")
            desc = "\n\n".join(x for x in [project.description.strip(), store.chapters(slug), footer] if x)
            live = insights.published(store.output(slug), get_format(out["fmt"]).suffix, out["fmt"],
                                      project.title, live_index())
            flow = insights.workflow(project, out, rv["data"], rv.get("stale", False), live,
                                     tips=len(script_advice(project)) if not project.imported else 0)
        return page(
            request, "project.html", nav="projects", crumb="Project · " + {"edit": "Edit beats", "script": "Script", "publish": "Publish",
                                                                          "storyboard": "Storyboard", "thumbs": "Thumbnail Lab",
                                                                          "compare": "Compare"}.get(tab, "Video"),
            slug=slug, project=project, perr=perr, tab=tab, out=out, beats=beats, flow=flow, live=live,
            lab_error=lab_error[:200], lab_source=source, lab_made=made, cmp_a=a, cmp_b=b,
            raw=store.raw(slug), job=jobs.latest(slug), desc=desc, rv=rv, note=note[:300],
            yt={"configured": youtube.is_configured(), "connected": youtube.is_connected() if tab == "publish" else None,
                "channel": youtube.channel_name() if tab == "publish" and youtube.is_connected() else "",
                "secret": youtube.secret_info(), "config_dir": str(youtube.CONFIG_DIR)},
        )

    def _review_ctx(slug: str, out: dict) -> dict:
        """The saved AI review of this format, and whether the video changed since."""
        data = review.latest(store.output(slug), out["fmt"])
        if not data:
            return {"data": None, "has_key": review.has_key()}
        f = store.output(slug) / data["video"]
        stale = not f.exists() or int(f.stat().st_mtime) != data["video_mtime"]
        newer = [v for v in (out.get("final"), out.get("preview")) if v and v["mtime"] > data["video_mtime"]]
        return {"data": data, "stale": stale or bool(newer), "has_key": review.has_key()}

    def _outs(slug: str) -> dict:
        try:
            return store.outputs(slug, store.load(slug).video.format)
        except Exception:  # noqa: BLE001
            return store.outputs(slug)

    @app.get("/p/{slug}/job", response_class=HTMLResponse)
    def job_status(request: Request, slug: str):
        slug = get_slug(slug)
        return page(request, "_job.html", slug=slug, job=jobs.latest(slug), out=_outs(slug))

    @app.post("/p/{slug}/render", response_class=HTMLResponse)
    def render(request: Request, slug: str, kind: str = Form("preview")):
        slug = get_slug(slug)
        if store.load(slug).imported:
            return HTMLResponse('<div id="job" class="job"><p class="err">This is an imported video: '
                                'there is nothing to render.</p></div>')
        if not jobs.active(slug):
            submit_render(slug, "make" if kind == "make" else "preview")
        return page(request, "_job.html", slug=slug, job=jobs.latest(slug), out=_outs(slug))

    @app.post("/import")
    async def import_video(request: Request, card: str = Form(...), video: UploadFile = File(...)):
        """A finished video (Gemini, CapCut...) + its import card -> a project ready to review and publish."""
        suffix = Path(video.filename or "video.mp4").suffix.lower() or ".mp4"
        tmp = store.root / f".upload-{int(time.time() * 1000)}{suffix}"
        try:
            with tmp.open("wb") as f:
                while chunk := await video.read(1 << 20):
                    f.write(chunk)
            slug, err, notes = store.create_import(card, tmp)
        finally:
            tmp.unlink(missing_ok=True)
        if not slug:
            resp = home_page(request, mode="import", card=card, error=err)
            resp.status_code = 400
            return resp
        note = "?note=" + quote(" ".join(notes)) if notes else ""
        return RedirectResponse(f"/p/{slug}{note}", status_code=303)

    @app.post("/p/{slug}/review", response_class=HTMLResponse)
    def start_review(request: Request, slug: str):
        slug = get_slug(slug)
        if not jobs.active(slug):
            submit_review(slug)
        return page(request, "_job.html", slug=slug, job=jobs.latest(slug), out=_outs(slug))

    @app.post("/settings/key/{provider}")
    def save_ai_key(provider: str, key: str = Form("")):
        if provider in review.KEYS and key.strip():
            review.save_key(key, provider)
        return RedirectResponse("/settings", status_code=303)

    @app.post("/p/{slug}/format")
    def set_format(slug: str, format: str = Form(...), tab: str = Form("video")):
        """Switch the project between Short and Long; stored in the project's YAML."""
        slug = get_slug(slug)
        if format in FORMATS and not jobs.active(slug):
            store.apply_options(slug, fmt=format)
        return RedirectResponse(f"/p/{slug}?tab={tab}", status_code=303)

    # ---------------------------------------------------------------- beats
    def _beat_ctx(slug: str, i: int, saved: str = "", error: str = "") -> dict:
        project = store.load(slug)
        b = project.beats[i - 1]
        return {"slug": slug, "b": {"i": i, "beat": b, "fields": template_fields(b.scene, b.params)},
                "saved": saved, "error": error, "out": store.outputs(slug, project.video.format), "job": jobs.latest(slug)}

    @app.get("/p/{slug}/beats/{i}/frame.jpg")
    def beat_frame(slug: str, i: int):
        slug = get_slug(slug)
        f = store.beat_frame(slug, store.load(slug).video.format, i)
        if not f:
            raise HTTPException(404, "no frame yet")
        return FileResponse(f, media_type="image/jpeg", headers={"Cache-Control": "no-cache"})

    @app.get("/p/{slug}/beats/{i}/fields", response_class=HTMLResponse)
    def beat_fields(request: Request, slug: str, i: int, scene: str):
        slug = get_slug(slug)
        b = store.load(slug).beats[i - 1]
        values = b.params if scene == b.scene else {}
        return page(request, "_fields.html", fields=template_fields(scene, values))

    @app.post("/p/{slug}/beats/{i}", response_class=HTMLResponse)
    async def save_beat(request: Request, slug: str, i: int):
        slug = get_slug(slug)
        form = dict(await request.form())
        project = store.load(slug)
        try:
            scene = form.get("scene", project.beats[i - 1].scene)
            get_template(scene)
            params = params_from_form(scene, form)
            get_template(scene).Params.model_validate(params)
            # keep the fields the form doesn't show (pad, min_duration, captions)
            beat = Beat(**(project.beats[i - 1].model_dump() | dict(
                text=form.get("text", "").strip(), scene=scene, params=params,
                chapter=(form.get("chapter") or "").strip() or None)))
        except Exception as e:  # noqa: BLE001
            return page(request, "_beat.html", **_beat_ctx(slug, i, error=friendly_error(e)))
        project.beats[i - 1] = beat
        store.save(slug, project)
        action = form.get("action", "save")
        if action == "preview" and not jobs.active(slug):
            submit_render(slug, "beat", only=[i])
        return page(request, "_beat.html", **_beat_ctx(slug, i, saved="Saved" + (" — rendering preview…" if action == "preview" else "")))

    @app.post("/p/{slug}/beats/{i}/save-scene", response_class=HTMLResponse)
    def save_scene(request: Request, slug: str, i: int, name: str = Form(""), description: str = Form("")):
        from beatframe.templates.custom import save_to_library

        slug = get_slug(slug)
        beats = store.load(slug).beats
        if not 1 <= i <= len(beats):
            return HTMLResponse("", status_code=404)
        try:
            save_to_library(beats[i - 1], name.strip(), description.strip())
            return HTMLResponse(f'<span class="okmsg">✓ saved to the library · use <code>scene: {name.strip()}</code></span>')
        except ValueError as e:
            return HTMLResponse(f'<span class="alert err" style="display:inline-block">{e}</span>')

    @app.post("/p/{slug}/beats/{i}/{op}")
    def beat_op(slug: str, i: int, op: str):
        slug = get_slug(slug)
        project = store.load(slug)
        beats = project.beats
        k = i - 1
        if op == "delete" and len(beats) > 1:
            beats.pop(k)
        elif op == "add":
            beats.insert(k + 1, new_beat())
        elif op == "up" and k > 0:
            beats[k - 1], beats[k] = beats[k], beats[k - 1]
        elif op == "down" and k < len(beats) - 1:
            beats[k + 1], beats[k] = beats[k], beats[k + 1]
        store.save(slug, project)
        anchor = {"add": i + 1, "up": max(1, i - 1), "down": min(len(beats), i + 1)}.get(op, max(1, i - 1))
        return RedirectResponse(f"/p/{slug}?tab=edit#beat-{anchor}", status_code=303)

    def _pictures(p, slug: str) -> str:
        """Prompts for photo-scene pictures that are not in the project folder yet."""
        from beatframe import images
        if p.imported or not any(x["exists"] is False for x in images.wanted(p, store.file(slug).parent)):
            return ""
        return images.report(p, store.file(slug).parent)

    def _custom_errors(slug: str) -> str:
        """Errors of custom scenes that fell back in the last render (empty if none)."""
        f = store.file(slug).parent / "build" / "custom_errors.txt"
        try:
            return f.read_text(encoding="utf-8")[-4000:]
        except OSError:
            return ""

    # --------------------------------------------------------------- script
    @app.post("/p/{slug}/script", response_class=HTMLResponse)
    def save_script(request: Request, slug: str, script: str = Form(...), action: str = Form("save")):
        slug = get_slug(slug)
        err = store.save_text(slug, script)
        if err:
            return page(request, "_check.html", project=None, error=err)
        if action == "preview" and not jobs.active(slug) and not store.load(slug).imported:
            submit_render(slug, "preview")
            return HTMLResponse("", headers={"HX-Redirect": f"/p/{slug}"})
        p = store.load(slug)
        return page(request, "_check.html", project=p, error="", saved=True,
                    issues=[str(x) for x in preflight(p, store.file(slug).parent)],
                    errors=_custom_errors(slug), pictures=_pictures(p, slug))

    @app.post("/p/{slug}/delete")
    def delete_project(slug: str):
        slug = get_slug(slug)
        trash = store.root / ".trash"
        trash.mkdir(exist_ok=True)
        shutil.move(str(store.folder(slug)), str(trash / f"{slug}-{int(time.time())}"))
        return RedirectResponse("/", status_code=303)

    # -------------------------------------------------------------- publish
    @app.post("/p/{slug}/publish", response_class=HTMLResponse)
    def publish(
        request: Request, slug: str,
        title: str = Form(...), description: str = Form(""), tags: str = Form(""),
        privacy: str = Form("private"), publish_at: str = Form(""), tz_offset: int = Form(0),
        synthetic: str = Form(""), captions: str = Form(""), thumb: str = Form(""),
    ):
        slug = get_slug(slug)
        fmt = store.load(slug).video.format
        if not (store.output(slug) / pipeline.output_name("final", fmt)).exists():
            return HTMLResponse('<p class="err">Render the final video first.</p>')
        if not youtube.is_connected():
            return HTMLResponse('<p class="err">Connect YouTube first.</p>')
        meta = {
            "title": title.strip(), "description": description,
            "tags": [t.strip() for t in tags.split(",") if t.strip()],
            "privacy": privacy if privacy in ("private", "unlisted", "public") else "private",
            "publish_at": youtube.to_rfc3339(publish_at, tz_offset) if publish_at else "",
            "synthetic": synthetic == "on",
        }
        # remember title/description/tags in the script for next time
        project = store.load(slug)
        project.title = meta["title"]
        project.tags = meta["tags"]
        store.save(slug, project)
        if not jobs.active(slug):
            submit_upload(slug, meta, captions == "on", thumb, fmt)
        return page(request, "_job.html", slug=slug, job=jobs.latest(slug), out=_outs(slug))

    @app.get("/youtube/connect")
    def yt_connect(next: str = "/"):
        if not youtube.is_configured():
            raise HTTPException(400, f"Put client_secret.json in {youtube.CONFIG_DIR} first")
        app.state.yt_next = next
        return RedirectResponse(youtube.auth_url(redirect_uri))

    @app.get("/youtube/callback")
    def yt_callback(request: Request, state: str = "", error: str = ""):
        nxt = getattr(app.state, "yt_next", "/")
        if error:
            return RedirectResponse(f"{nxt}&yt_error={error}" if "?" in nxt else f"{nxt}?yt_error={error}")
        youtube.finish(state, str(request.url))
        return RedirectResponse(nxt)

    @app.post("/youtube/secret")
    async def yt_secret(file: UploadFile = File(...), next: str = Form("/")):
        import json as _json
        raw = await file.read()
        try:
            data = _json.loads(raw)
        except ValueError:
            raise HTTPException(400, "That is not a JSON file. Download the OAuth client JSON from Google Cloud.")
        if "installed" not in data:
            kind = "web" if "web" in data else "unknown"
            raise HTTPException(400, f"This client is type '{kind}'. Create an OAuth client of type 'Desktop app'.")
        youtube.CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        youtube.CLIENT_SECRET.write_bytes(raw)
        return RedirectResponse(next, status_code=303)

    @app.post("/youtube/disconnect")
    def yt_disconnect(next: str = Form("/")):
        youtube.disconnect()
        return RedirectResponse(next, status_code=303)

    from beatframe.web.features import register
    register(app, store=store, jobs=jobs, page=page, get_slug=get_slug, tpl=tpl)
    return app


def _ago(t: float) -> str:
    d = time.time() - t
    if d < 60:
        return "just now"
    if d < 3600:
        return f"{int(d // 60)} min ago"
    if d < 86400:
        return f"{int(d // 3600)} h ago"
    if d < 7 * 86400:
        n = int(d // 86400)
        return f"{n} day{'s' if n > 1 else ''} ago"
    return time.strftime("%d %b", time.localtime(t))


def _size(n: int | None) -> str:
    if not n:
        return ""
    return f"{n / 1e6:.1f} MB" if n >= 1e6 else f"{max(1, round(n / 1e3))} KB"


def _secs(s: float | None) -> str:
    if not s:
        return ""
    s = int(round(s))
    return f"{s // 60}:{s % 60:02d}"


def serve(projects_root: Path, host: str = "127.0.0.1", port: int = 8000, open_browser: bool = True) -> None:
    import threading
    import webbrowser

    import uvicorn

    app = create_app(projects_root.resolve(), port)
    if open_browser:
        threading.Timer(1.2, lambda: webbrowser.open(f"http://127.0.0.1:{port}")).start()
    uvicorn.run(app, host=host, port=port, log_level="warning")


if os.environ.get("BEATFRAME_DEV"):  # uvicorn --reload support
    app = create_app(Path(os.environ.get("BEATFRAME_PROJECTS", "projects")).resolve())
