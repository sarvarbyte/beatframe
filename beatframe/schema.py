"""Project file format (YAML) and its validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from beatframe.formats import DEFAULT_FORMAT, FormatName, VideoFormat, get_format


class Voice(BaseModel):
    provider: Literal["edge", "kokoro", "files", "silent"] = "edge"
    name: str = "en-US-AndrewMultilingualNeural"   # edge: en-US-...Neural | kokoro: am_michael, bm_george, af_heart...
    rate: str = "+0%"                  # base speaking rate, e.g. "-5%"
    pitch: str = "+0Hz"                # base pitch (edge only), e.g. "-2Hz"
    style: Literal["auto", "flat"] = "auto"   # auto = speed/pitch follow each sentence (hooks, questions, punchlines)
    expressiveness: float = 1.0        # 0 = flat ... 1 = normal ... 1.5 = very lively
    upgrade: bool = True               # swap old flat edge voices (Christopher, Andrew...) for the Multilingual ones
    files_dir: str | None = None       # provider=files: folder with 001.mp3, 002.mp3, ...
    words_per_second: float = 2.4      # provider=silent: estimated pace

    @model_validator(mode="after")
    def _kokoro_name(self) -> "Voice":
        if self.provider == "kokoro" and "-" in self.name:   # an edge name left over: pick a kokoro voice
            self.name = "am_michael"
        return self


class Audio(BaseModel):
    """Background music and sound effects under the voice."""
    music: str = "auto"                # auto (generated, royalty-free) | none | a file in the project folder ("music.mp3")
    mood: Literal["auto", "mystery", "wonder", "epic", "tense", "calm"] = "auto"
    music_volume: float = 0.5          # 0..1 (music is ducked under the voice automatically)
    sfx: bool = True                   # soft whoosh on scene changes, a low hit on chapter starts
    sfx_volume: float = 0.5


class Captions(BaseModel):
    """Word-by-word captions burned into the video, timed from the voice."""
    mode: Literal["auto", "on", "off"] = "auto"          # auto = on for short, off for long
    style: Literal["pop", "karaoke", "plain"] = "pop"   # pop: the spoken word lights up and grows
    position: Literal["lower", "center"] = "lower"

    @field_validator("mode", mode="before")
    @classmethod
    def _yaml_on_off(cls, v):
        """YAML reads a bare on / off as true / false."""
        return {True: "on", False: "off"}.get(v, v) if isinstance(v, bool) else v

    def enabled(self, video_format: str) -> bool:
        return self.mode == "on" or (self.mode == "auto" and video_format == "short")


class Beat(BaseModel):
    text: str
    scene: str
    params: dict[str, Any] = Field(default_factory=dict)
    chapter: str | None = None         # start a YouTube chapter at this beat
    captions: bool | None = None       # None = automatic (off for scenes that already show the text)
    pad: float = 0.35                  # seconds of breathing room after the voice
    min_duration: float = 2.0


class Video(BaseModel):
    format: FormatName = DEFAULT_FORMAT   # long (16:9, 1920x1080) | short (9:16, 1080x1920)
    width: int | None = None              # optional override; normally taken from `format`
    height: int | None = None
    fps: int = 30
    transitions: Literal["auto", "cut"] = "auto"   # auto: varied short transitions, a dip to black at chapters
    transition_seconds: float = Field(0.3, ge=0.1, le=1.0)

    @model_validator(mode="after")
    def _size_matches_format(self) -> "Video":
        if (self.width is None) != (self.height is None):
            raise ValueError("video.width and video.height must be given together (or both left out)")
        if self.width is not None and (self.height > self.width) != get_format(self.format).vertical:
            raise ValueError(f"video size {self.width}x{self.height} does not match format '{self.format}'")
        return self

    @property
    def spec(self) -> VideoFormat:
        return get_format(self.format)

    def size(self, preview: bool = False) -> tuple[int, int]:
        """Pixel size to render at. Previews always use the format's 480p size."""
        if preview or self.width is None:
            return self.spec.size(preview)
        return self.width, self.height

    def with_format(self, name: str) -> "Video":
        """The same settings in another format (an explicit size only survives if the format is unchanged)."""
        if get_format(name).name == self.format:
            return self
        return Video(format=get_format(name).name, fps=self.fps, transitions=self.transitions,
                     transition_seconds=self.transition_seconds)


class Project(BaseModel):
    title: str
    description: str = ""              # YouTube description (chapters are added automatically)
    tags: list[str] = Field(default_factory=list)
    voice: Voice = Voice()
    audio: Audio = Audio()
    video: Video = Video()
    captions: Captions = Captions()
    beats: list[Beat] = Field(default_factory=list)

    # A finished video made elsewhere (Gemini, CapCut...) that Beatframe only reviews and publishes.
    # Its video is output/final.mp4 (final_short.mp4); there are no beats to render.
    source: Literal["beatframe", "import"] = "beatframe"
    script: str = ""                   # import: the narration / voiceover, for the AI review
    chapters: str = ""                 # import: "00:00 Intro" lines for the description (long videos)
    made_with: str = ""                # import: e.g. gemini, capcut
    synthetic: bool = False            # import: realistic AI people/events -> YouTube's altered-content label

    @property
    def imported(self) -> bool:
        return self.source == "import"

    @model_validator(mode="after")
    def _has_content(self) -> "Project":
        if not self.beats and not self.imported:
            raise ValueError("a project needs at least one beat (or `source: import` for a finished video)")
        return self


def parse_project(text: str) -> Project:
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ValueError("the script must be a YAML mapping with at least 'title' and 'beats' "
                         "(or 'title' and 'source: import' for a finished video)")
    return Project.model_validate(data)


def load_project(path: str | Path) -> Project:
    return parse_project(Path(path).read_text(encoding="utf-8"))


def dump_project(project: Project) -> str:
    data = project.model_dump(mode="json", exclude_defaults=True)
    data.setdefault("title", project.title)
    if project.beats or not project.imported:
        data["beats"] = [b.model_dump(mode="json", exclude_defaults=True) | {"text": b.text, "scene": b.scene}
                         for b in project.beats]
    return yaml.dump(data, Dumper=_BlockDumper, sort_keys=False, allow_unicode=True, width=100)


class _BlockDumper(yaml.SafeDumper):
    """Safe YAML, but multi-line strings (a custom scene's code) stay readable `|` blocks."""


def _str(dumper, value: str):
    if "\n" in value:
        return dumper.represent_scalar("tag:yaml.org,2002:str", value, style="|")
    return dumper.represent_scalar("tag:yaml.org,2002:str", value)


_BlockDumper.add_representer(str, _str)
