"""Project file format (YAML) and its validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator


class Voice(BaseModel):
    provider: Literal["edge", "files", "silent"] = "edge"
    name: str = "en-US-AndrewNeural"   # edge-tts voice
    rate: str = "+0%"                  # edge-tts speaking rate, e.g. "-5%"
    files_dir: str | None = None       # provider=files: folder with 001.mp3, 002.mp3, ...
    words_per_second: float = 2.4      # provider=silent: estimated pace


class Beat(BaseModel):
    text: str
    scene: str
    params: dict[str, Any] = Field(default_factory=dict)
    chapter: str | None = None         # start a YouTube chapter at this beat
    pad: float = 0.35                  # seconds of breathing room after the voice
    min_duration: float = 2.0


class Video(BaseModel):
    width: int = 1920
    height: int = 1080
    fps: int = 30


class Project(BaseModel):
    title: str
    voice: Voice = Voice()
    video: Video = Video()
    beats: list[Beat]

    @field_validator("beats")
    @classmethod
    def _not_empty(cls, v: list[Beat]) -> list[Beat]:
        if not v:
            raise ValueError("a project needs at least one beat")
        return v


def load_project(path: str | Path) -> Project:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return Project.model_validate(data)
