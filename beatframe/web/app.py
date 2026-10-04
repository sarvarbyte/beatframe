"""Beatframe Studio: paste a script, watch it render, edit beats, publish."""

from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from beatframe import pipeline
from beatframe.schema import Beat
from beatframe.templates import get_template
from beatframe.web import youtube
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
    tpl.env.globals.update(templates_list=template_catalog, fmt_time=lambda t: time.strftime("%d %b %H:%M", time.localtime(t)))
    app.mount("/static", StaticFiles(directory=str(HERE / "static")), name="static")
    app.mount("/files", StaticFiles(directory=str(store.root)), name="files")
    redirect_uri = f"http://127.0.0.1:{port}/youtube/callback"

    def page(request: Request, name: str, **ctx) -> HTMLResponse:
        return tpl.TemplateResponse(request, name, ctx)

    def get_slug(slug: str) -> str:
        try:
            if store.exists(slug):
                return slug
        except KeyError:
            pass
        raise HTTPException(404, "project not found")

    # ---------------------------------------------------------------- jobs
    def submit_render(slug: str, kind: str, only: list[int] | None = None) -> Job:
        project = store.load(slug)
        total = len(only) if only else len(project.beats)
        label = {"preview": "Preview (480p)", "make": "Final video (1080p)", "beat": f"Beat {only[0] if only else ''} preview"}[kind]

        def run(job: Job) -> dict:
            p = store.load(slug)
            res = pipeline.run(
                p, store.file(slug), preview=(kind != "make"), only=only, log=job.log,
                out_name="beat_preview.mp4" if kind == "beat" else None,
            )
            return {"video": res.video.name, "seconds": round(res.total, 1)}

        return jobs.submit(slug, kind, label, total, run)

    def submit_upload(slug: str, meta: dict, captions: bool, thumb: str) -> Job:
        out = store.output(slug)

        def run(job: Job) -> dict:
            def prog(f: float) -> None:
                job.done = int(f * 100)
            return youtube.upload(
                out / "final.mp4", meta, log=job.lines.append, progress=prog,
                captions=(out / "subtitles.srt") if captions else None,
                thumbnail=(out / "thumbs" / thumb) if thumb else None,
            )

        return jobs.submit(slug, "upload", "YouTube upload", 100, run)

    # ---------------------------------------------------------------- home
    @app.get("/", response_class=HTMLResponse)
    def home(request: Request):
        return page(request, "home.html", projects=store.list(), example=EXAMPLE, script="", error="")

    @app.post("/check", response_class=HTMLResponse)
    def check(request: Request, script: str = Form("")):
        if not script.strip():
            return HTMLResponse("")
        p, err = store.check_text(script)
        return page(request, "_check.html", project=p, error=err)

    @app.post("/projects")
    def create(request: Request, script: str = Form(...), render: str = Form("preview")):
        slug, err = store.create(script)
        if not slug:
            return page(request, "home.html", projects=store.list(), example=EXAMPLE, script=script, error=err)
        if render in ("preview", "make"):
            submit_render(slug, render)
        return RedirectResponse(f"/p/{slug}", status_code=303)

    # ------------------------------------------------------------- project
    @app.get("/p/{slug}", response_class=HTMLResponse)
    def project_page(request: Request, slug: str, tab: str = "video"):
        slug = get_slug(slug)
        try:
            project, perr = store.load(slug), ""
        except Exception as e:  # noqa: BLE001
            project, perr, tab = None, friendly_error(e), "script"
        out = store.outputs(slug)
        beats = []
        if project:
            for i, b in enumerate(project.beats, 1):
                beats.append({"i": i, "beat": b, "fields": template_fields(b.scene, b.params)})
        desc = ""
        if project:
            desc = "\n\n".join(x for x in [project.description.strip(), store.chapters(slug),
                                           "Narration: AI voice. Animation made with Beatframe by Human Unknowns."] if x)
        return page(
            request, "project.html", slug=slug, project=project, perr=perr, tab=tab, out=out, beats=beats,
            raw=store.raw(slug), job=jobs.latest(slug), desc=desc,
            yt={"configured": youtube.is_configured(), "connected": youtube.is_connected() if tab == "publish" else None,
                "channel": youtube.channel_name() if tab == "publish" and youtube.is_connected() else "",
                "secret": youtube.secret_info(), "config_dir": str(youtube.CONFIG_DIR)},
        )

    @app.get("/p/{slug}/job", response_class=HTMLResponse)
    def job_status(request: Request, slug: str):
        slug = get_slug(slug)
        return page(request, "_job.html", slug=slug, job=jobs.latest(slug), out=store.outputs(slug))

    @app.post("/p/{slug}/render", response_class=HTMLResponse)
    def render(request: Request, slug: str, kind: str = Form("preview")):
        slug = get_slug(slug)
        if not jobs.active(slug):
            submit_render(slug, "make" if kind == "make" else "preview")
        return page(request, "_job.html", slug=slug, job=jobs.latest(slug), out=store.outputs(slug))

    # ---------------------------------------------------------------- beats
    def _beat_ctx(slug: str, i: int, saved: str = "", error: str = "") -> dict:
        project = store.load(slug)
        b = project.beats[i - 1]
        return {"slug": slug, "b": {"i": i, "beat": b, "fields": template_fields(b.scene, b.params)},
                "saved": saved, "error": error, "out": store.outputs(slug), "job": jobs.latest(slug)}

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
            beat = Beat(text=form.get("text", "").strip(), scene=scene, params=params,
                        chapter=(form.get("chapter") or "").strip() or None)
        except Exception as e:  # noqa: BLE001
            return page(request, "_beat.html", **_beat_ctx(slug, i, error=friendly_error(e)))
        project.beats[i - 1] = beat
        store.save(slug, project)
        action = form.get("action", "save")
        if action == "preview" and not jobs.active(slug):
            submit_render(slug, "beat", only=[i])
        return page(request, "_beat.html", **_beat_ctx(slug, i, saved="Saved" + (" — rendering preview…" if action == "preview" else "")))

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

    # --------------------------------------------------------------- script
    @app.post("/p/{slug}/script", response_class=HTMLResponse)
    def save_script(request: Request, slug: str, script: str = Form(...), action: str = Form("save")):
        slug = get_slug(slug)
        err = store.save_text(slug, script)
        if err:
            return page(request, "_check.html", project=None, error=err)
        if action == "preview" and not jobs.active(slug):
            submit_render(slug, "preview")
            return HTMLResponse("", headers={"HX-Redirect": f"/p/{slug}"})
        return page(request, "_check.html", project=store.load(slug), error="", saved=True)

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
        if not (store.output(slug) / "final.mp4").exists():
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
            submit_upload(slug, meta, captions == "on", thumb)
        return page(request, "_job.html", slug=slug, job=jobs.latest(slug), out=store.outputs(slug))

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

    @app.post("/youtube/disconnect")
    def yt_disconnect(next: str = Form("/")):
        youtube.disconnect()
        return RedirectResponse(next, status_code=303)

    return app


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
