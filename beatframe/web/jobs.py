"""A tiny in-process job queue: one worker thread runs renders/uploads in order.

For a single user on a laptop this is all we need (no Redis). Each job keeps its
log lines and a progress fraction that the page polls.
"""

from __future__ import annotations

import queue
import threading
import time
import traceback
import uuid
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Job:
    id: str
    slug: str
    kind: str                     # preview | make | beat | upload
    label: str
    total: int = 1
    done: int = 0
    status: str = "queued"        # queued | running | done | failed
    lines: list[str] = field(default_factory=list)
    error: str = ""
    result: dict = field(default_factory=dict)
    created: float = field(default_factory=time.time)
    finished: float | None = None

    @property
    def progress(self) -> float:
        if self.status == "done":
            return 1.0
        return min(0.99, self.done / max(self.total, 1))

    def log(self, msg: str) -> None:
        self.lines.append(msg)
        if msg.strip().startswith("beat "):
            self.done += 1


class JobManager:
    def __init__(self) -> None:
        self.jobs: dict[str, Job] = {}
        self.q: "queue.Queue[tuple[Job, Callable[[Job], dict | None]]]" = queue.Queue()
        threading.Thread(target=self._worker, daemon=True).start()

    def submit(self, slug: str, kind: str, label: str, total: int, fn: Callable[[Job], dict | None]) -> Job:
        job = Job(id=uuid.uuid4().hex[:10], slug=slug, kind=kind, label=label, total=total)
        self.jobs[job.id] = job
        self.q.put((job, fn))
        return job

    def latest(self, slug: str) -> Job | None:
        mine = [j for j in self.jobs.values() if j.slug == slug]
        return max(mine, key=lambda j: j.created) if mine else None

    def active(self, slug: str) -> Job | None:
        j = self.latest(slug)
        return j if j and j.status in ("queued", "running") else None

    def _worker(self) -> None:
        while True:
            job, fn = self.q.get()
            job.status = "running"
            try:
                job.result = fn(job) or {}
                job.status = "done"
            except Exception as e:  # noqa: BLE001
                job.status = "failed"
                job.error = str(e) or e.__class__.__name__
                job.lines.append(traceback.format_exc(limit=3))
            finally:
                job.finished = time.time()
                self.q.task_done()
