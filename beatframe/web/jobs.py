"""A tiny in-process job queue: one worker thread runs renders/uploads in order.

For a single user on a laptop this is all we need (no Redis). Render jobs get live
progress events from pipeline.run (stage, beat, done/total), so the page shows what the
pipeline is really doing; upload jobs report a 0-100 fraction.
"""

from __future__ import annotations

import queue
import threading
import time
import traceback
import uuid
from dataclasses import dataclass, field
from typing import Callable

# share of the progress bar each render stage owns (Manim rendering is the long part)
STAGE_SPAN = {"check": (0, 2), "voice": (2, 14), "render": (14, 90), "assemble": (90, 96),
              "extras": (96, 100), "done": (100, 100)}
STAGE_TEXT = {"queued": "Waiting in queue", "check": "Checking the script", "voice": "Generating voice",
              "render": "Rendering animation", "assemble": "Joining clips and audio",
              "extras": "Adding subtitles, chapters and thumbnails", "done": "Finished"}


@dataclass
class Job:
    id: str
    slug: str
    kind: str                     # preview | make | beat | upload
    label: str
    total: int = 1
    done: int = 0
    status: str = "queued"        # queued | running | done | failed | cancelled
    fmt: str = "long"             # video format of a render job
    stage: str = "queued"
    beat: int | None = None       # beat being rendered right now
    template: str | None = None
    percent: float = 0.0
    lines: list[str] = field(default_factory=list)
    error: str = ""
    result: dict = field(default_factory=dict)
    created: float = field(default_factory=time.time)
    started: float | None = None
    finished: float | None = None
    cancel: threading.Event = field(default_factory=threading.Event)   # set by "Stop render"

    @property
    def is_render(self) -> bool:
        return self.kind in ("preview", "make", "beat")

    @property
    def progress(self) -> float:
        if self.status == "done":
            return 1.0
        if self.is_render:
            return min(0.99, self.percent / 100)
        return min(0.99, self.done / max(self.total, 1))

    @property
    def stage_text(self) -> str:
        return STAGE_TEXT.get(self.stage, self.stage)

    @property
    def elapsed(self) -> int:
        if not self.started:
            return 0
        return int((self.finished or time.time()) - self.started)

    def log(self, msg: str) -> None:
        self.lines.append(msg)

    def on_progress(self, ev: dict) -> None:
        """Receives pipeline.run progress events."""
        stage = ev["stage"]
        self.stage = stage
        if "total" in ev:
            self.done, self.total = ev.get("done", 0), ev["total"]
        if stage == "render":
            self.beat, self.template = ev.get("beat", self.beat), ev.get("template", self.template)
        lo, hi = STAGE_SPAN.get(stage, (self.percent, self.percent))
        frac = self.done / self.total if stage in ("voice", "render") and self.total else 0.0
        self.percent = round(max(self.percent, lo + (hi - lo) * frac), 1)

    def steps(self) -> list[dict]:
        """The render checklist shown on the page: label, state (done|active|pending|failed), detail."""
        order = ["check", "voice", "render", "assemble"] + (["extras"] if self.kind == "make" else [])
        labels = {"check": "Check script", "voice": "Generate voice", "render": "Render scenes",
                  "assemble": "Combine with FFmpeg", "extras": "Subtitles, chapters & thumbnails"}
        cur = order.index(self.stage) if self.stage in order else (len(order) if self.stage == "done" else -1)
        out = []
        for i, key in enumerate(order):
            if self.status == "done" or i < cur:
                state = "done"
            elif i == cur:
                state = "failed" if self.status == "failed" else "active"
            else:
                state = "pending"
            detail = ""
            if key in ("voice", "render") and state in ("active", "failed") and self.stage == key and self.total:
                detail = f"{self.done}/{self.total}"
            out.append({"label": labels[key], "state": state, "detail": detail})
        return out


class JobManager:
    def __init__(self) -> None:
        self.jobs: dict[str, Job] = {}
        self.q: "queue.Queue[tuple[Job, Callable[[Job], dict | None]]]" = queue.Queue()
        threading.Thread(target=self._worker, daemon=True).start()

    def submit(self, slug: str, kind: str, label: str, total: int, fn: Callable[[Job], dict | None],
               fmt: str = "long") -> Job:
        job = Job(id=uuid.uuid4().hex[:10], slug=slug, kind=kind, label=label, total=total, fmt=fmt)
        self.jobs[job.id] = job
        self.q.put((job, fn))
        return job

    def latest(self, slug: str) -> Job | None:
        mine = [j for j in self.jobs.values() if j.slug == slug]
        return max(mine, key=lambda j: j.created) if mine else None

    def active(self, slug: str) -> Job | None:
        j = self.latest(slug)
        return j if j and j.status in ("queued", "running") else None

    def cancel(self, job_id: str) -> bool:
        """Stop a queued job, or a running render after killing its current Manim process
        (finished clips stay in the cache, so the next render resumes from there)."""
        job = self.jobs.get(job_id)
        if not job or job.status not in ("queued", "running"):
            return False
        job.cancel.set()
        if job.status == "queued":
            job.status, job.finished = "cancelled", time.time()
        return True

    def _worker(self) -> None:
        while True:
            job, fn = self.q.get()
            if job.cancel.is_set():
                self.q.task_done()
                continue
            job.status, job.started = "running", time.time()
            if job.is_render:
                job.on_progress({"stage": "check"})
            try:
                job.result = fn(job) or {}
                job.status = "done"
                if job.is_render:
                    job.on_progress({"stage": "done"})
            except Exception as e:  # noqa: BLE001
                if job.cancel.is_set():
                    job.status, job.error = "cancelled", "Stopped. Finished scenes stay cached."
                    continue
                job.status = "failed"
                job.error = str(e) or e.__class__.__name__
                job.lines.append(traceback.format_exc(limit=3))
            finally:
                job.finished = time.time()
                self.q.task_done()
