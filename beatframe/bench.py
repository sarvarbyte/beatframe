"""Measure what rendering really costs on this computer.

    beatframe bench neural_impulse bone_conduction --preset eco --preset quality --format long --format short

Each template is rendered once uncached (a fresh temp folder, so Beatframe's clip cache cannot help)
and then asked again from the same folder (the cached case: Beatframe reuses the clip without starting
Manim). Manim's own frame cache is always off (--disable_caching), so the uncached numbers are honest.
Results go to bench_report.md / bench_report.json in the output folder.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Callable

from beatframe import renderconf
from beatframe.render import ClipJob, render_clip


def _probe(clip: Path) -> dict:
    try:
        out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                              "stream=width,height,r_frame_rate,nb_frames", "-of", "json", str(clip)],
                             capture_output=True, text=True, check=True).stdout
        s = json.loads(out)["streams"][0]
        num, den = (int(x) for x in s["r_frame_rate"].split("/"))
        return {"out_width": s["width"], "out_height": s["height"], "out_fps": round(num / den, 2),
                "frames": int(s.get("nb_frames", 0) or 0)}
    except (OSError, subprocess.CalledProcessError, KeyError, ValueError, IndexError):
        return {}


def run(templates: list[str], presets: list[str], formats: list[str], seconds: float = 4.0,
        params: dict[str, dict] | None = None, out_dir: Path | None = None,
        log: Callable[[str], None] = print) -> list[dict]:
    rows = []
    for name in templates:
        for fmt in formats:
            for preset in presets:
                w, h, fps = renderconf.preset_size(preset, fmt == "short")
                job = ClipJob(1, name, dict((params or {}).get(name, {})), seconds, w, h, fps)
                with tempfile.TemporaryDirectory(prefix="beatframe_bench_") as tmp:
                    row = {"template": name, "format": fmt, "preset": preset, "clip_seconds": seconds}
                    try:
                        clip = render_clip(job, Path(tmp))
                        row.update(job.stats, **_probe(clip), status="ok")
                        t0 = time.monotonic()
                        render_clip(ClipJob(1, name, job.params, seconds, w, h, fps), Path(tmp))
                        row["cached_seconds"] = round(time.monotonic() - t0, 3)
                    except RuntimeError as e:
                        row.update(status="error", error=str(e)[-400:])
                rows.append(row)
                log(f"  {name:<24} {fmt:<5} {preset:<8} {row.get('seconds', '-'):>6} s  "
                    f"{row.get('peak_rss_mb', '-'):>6} MiB  {row.get('cpu_percent', '-'):>4}% CPU  {row['status']}")
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "bench_report.json").write_text(json.dumps(rows, indent=2), encoding="utf-8")
        (out_dir / "bench_report.md").write_text(markdown(rows), encoding="utf-8")
    return rows


def markdown(rows: list[dict]) -> str:
    head = ("| template | format | preset | output | clip s | render s | cached s | peak RSS MiB | CPU % | MB | status |\n"
            "|---|---|---|---|---|---|---|---|---|---|---|\n")
    body = "".join(
        f"| {r['template']} | {r['format']} | {r['preset']} | {r.get('out_width', '?')}x{r.get('out_height', '?')}"
        f"@{r.get('out_fps', '?')} | {r['clip_seconds']} | {r.get('seconds', '-')} | {r.get('cached_seconds', '-')} | "
        f"{r.get('peak_rss_mb', '-')} | {r.get('cpu_percent', '-')} | {r.get('mb', '-')} | {r['status']} |\n"
        for r in rows)
    return head + body
