# Beatframe

Narration script in, animated documentary out.

You write a YAML file: each **beat** is one spoken sentence plus the scene template that
should play under it. Beatframe makes the voice, renders every beat with Manim at exactly
the length of its voice, and joins everything into one video with subtitles, chapters and
thumbnail candidates.

```
script.yaml ─► voice (TTS) ─► per-beat Manim clips (cached, parallel) ─► final.mp4
                                                                       ├─ subtitles.srt
                                                                       ├─ chapters.txt
                                                                       └─ thumbs/
```

## Install (Ubuntu)

```bash
sudo apt install ffmpeg libpango1.0-dev libcairo2-dev pkg-config python3-venv \
    python3-dev build-essential libgl1-mesa-dev
cd beatframe
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Use

```bash
beatframe templates                              # what scenes exist, and their params
beatframe check   projects/touch/touch.yaml      # validate without rendering
beatframe preview projects/touch/touch.yaml      # fast 480p look (≈1 min)
beatframe preview projects/touch/touch.yaml --beats 3   # just one beat
beatframe make    projects/touch/touch.yaml      # full 1080p video
beatframe clean   projects/touch/touch.yaml      # drop the cache
```

Results land in `projects/<name>/output/`. Only beats whose text, scene, params or
template code changed are rendered again.

## Voice

```yaml
voice:
  provider: edge            # free neural voices, needs internet
  name: en-US-AndrewNeural
  rate: "-5%"
```

* `files` - your own recordings: set `files_dir`, name them `001.mp3`, `002.mp3`, ... (one per beat)
* `silent` - no voice; length estimated from the word count (layout tests)

## Project file

```yaml
title: "My video"
beats:
  - text: "What the narrator says."
    scene: statement            # template name
    chapter: "Intro"            # optional: starts a YouTube chapter
    params: {text: "What the narrator says.", highlight: "narrator"}
```

## Templates

| name | what it does |
|---|---|
| `title_card` | two-line title under a single drifting light |
| `statement` | large text, words arrive one by one, one keyword glows |
| `scale_zoom` | continuous dive: fingertip → skin → cells → atoms |
| `electron_repulsion` | two rows of atoms approach; the gap never closes |
| `source_card` | a number from a study counts up, citation underneath |

Add a template: create `beatframe/templates/<name>.py` with a `Template` subclass
(`name`, a pydantic `Params`, and `build(scene, p, duration)`). It is picked up automatically.

## Layout

```
beatframe/
├── brand.py          colours, fonts
├── schema.py         YAML format (pydantic)
├── tts.py            voice providers
├── render.py         per-beat Manim render, cache, workers
├── assemble.py       ffmpeg join, loudness, SRT, chapters, thumbnails
├── pipeline.py       the whole run
├── cli.py            command line
└── templates/        one file per scene template
projects/touch/touch.yaml   example: opening of the "touch" video
```

Roadmap: web app (FastAPI + HTMX + background render queue), 9:16 Shorts export,
more templates.
