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

## Studio (web app)

```bash
beatframe web          # opens http://127.0.0.1:8000
```

Pick **Short** (9:16, 1080×1920 - Shorts, Reels, TikTok) or **Long** (16:9, 1920×1080 - YouTube),
paste a script, watch it render with live progress (stage, beat n / total, percent), edit beats (text, scene, params,
add / delete / reorder) and re-render only what changed, then publish: download files for
manual upload, or upload straight to YouTube (title, description with chapters, tags,
subtitles, thumbnail, visibility, schedule) through the YouTube Data API.

YouTube setup: create a Google Cloud project, enable YouTube Data API v3, add yourself
as a test user on the OAuth consent screen, create an OAuth client of type **Desktop app**
and save its JSON as `~/.beatframe/client_secret.json`. Until the project passes YouTube's
API audit, API uploads are locked to Private.

Built with FastAPI + Jinja + htmx; renders and uploads run on a background worker thread.

## CLI

```bash
beatframe templates                              # what scenes exist, and their params
beatframe check   projects/touch/touch.yaml      # validate without rendering
beatframe preview projects/touch/touch.yaml      # fast 480p look (≈1 min)
beatframe preview projects/touch/touch.yaml --beats 3   # just one beat
beatframe make    projects/touch/touch.yaml      # full 1080p video
beatframe make    projects/touch/touch.yaml --format short   # the same project as a 9:16 Short
beatframe clean   projects/touch/touch.yaml      # drop the cache
```

Results land in `projects/<name>/output/`: `final.mp4` / `preview.mp4` for long, `final_short.mp4` /
`preview_short.mp4` (and `thumbs_short/`) for short, each with a `.json` saying how it was rendered. Only beats whose text, scene, params or
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

## Captions

Word-by-word captions are burned into the video, timed from the voice (edge and kokoro report
when each word is spoken; `files` and `silent` are estimated). On by default for Shorts.

```yaml
captions:
  mode: auto        # auto (on for short, off for long) | on | off
  style: pop        # pop (spoken word lights up) | karaoke | plain
  position: lower   # lower | center
```

Scenes that already show the sentence (`kinetic_text`, `statement`, `title_card`, `question_hook`,
`myth_fact`, `stick_talk`) get no captions; a beat can override with `captions: true` / `false`.
Changing captions never re-renders a beat: they are added when the clips are joined.

## Project file

```yaml
title: "My video"
video: {format: short, fps: 30}   # long (16:9, default) | short (9:16)
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

Bright stick-figure templates (colourful, made for Shorts and Long alike; `palette: auto`
picks a different colour set per beat, or name one: sunny, mint, sky, berry, lilac, peach):

| name | what it does |
|---|---|
| `question_hook` | big question, puzzled stick figure, floating question marks (openers) |
| `stick_scene` | a place (kitchen, bedroom, office, street, park...), an action and a thought bubble |
| `stick_doorway` | walks from one room to the next; the idea it carried can vanish |
| `stick_compare` | A vs B with a stick figure, icon and check/cross for each |
| `stick_talk` | two stick figures, each line in a speech bubble |
| `stick_crowd` | a crowd where some people light up ("1 in 10") |
| `stat_pop` | a number counts up on a card, with icon, caption and source |
| `icon_list` | 2-4 numbered icon cards (`icon|text`) |
| `timeline` | 2-5 dated events (`year|what happened`) |
| `bar_chart` | bars grow to their values, one highlighted |
| `myth_fact` | the myth is crossed out, the fact gets a check |
| `kinetic_text` | words pop in, key words get colour blocks |
| `body_map` | body outline, one part glows with a label |
| `process_cycle` | 3-5 steps light up in order, optionally looping back |
| `brain_light` | big brain, one region lights up |

`projects/bright-demo/` uses every one of them. `beatframe templates` lists their settings.

Science library (20 templates for neuroscience, perception, experiments and biology:
`neural_impulse`, `bone_conduction`, `blind_spot_test`, `reaction_time`, `memory_reconstruction`,
`sleep_cycle`, `stress_response`, `inner_ear`, `retina_processing`, `touch_receptors`, `reflex_arc`,
`balance_experiment`, `stroop_effect`, `ring_finger_test`, `attention_spotlight`, `blood_circulation`,
`oxygen_exchange`, `dna_unzipping`, `immune_response`, `evolution_tree`): see
[docs/TEMPLATE_LIBRARY.md](docs/TEMPLATE_LIBRARY.md), which also covers the Template library page,
presets, compositions and the laptop render settings (one Manim process at a time by default).

Add a template: create `beatframe/templates/<name>.py` with a `Template` subclass
(`name`, a pydantic `Params`, and `build(scene, p, duration)`). It is picked up automatically.

Formats: long frames are 14.2 × 8 units. In short mode a template with `vertical_width = 8.0`
gets an 8 × 14.2 frame and lays itself out with the helpers in `templates/base.py`
(`frame_w()`, `frame_h()`, `width_ratio()`, `fit()`, `keep_inside_x()`); title_card, statement,
source_card, electron_repulsion and scale_zoom work this way. Templates drawn for 16:9 set
`vertical_width` to the part of their drawing that must stay visible (default 14.2), and the
portrait frame is widened to that. Sizes live in one place: `formats.py`.

## Layout

```
beatframe/
├── brand.py          colours, fonts
├── formats.py        Short / Long: sizes and frame units (the only place that knows them)
├── schema.py         YAML format (pydantic)
├── tts.py            voice providers
├── render.py         per-beat Manim render, cache, workers
├── assemble.py       ffmpeg join, loudness, SRT, chapters, thumbnails
├── pipeline.py       the whole run
├── cli.py            command line
└── templates/        one file per scene template
projects/touch/touch.yaml   example: opening of the "touch" video
```

Roadmap: AI script planner, more templates (and native 9:16 layouts for the 16:9 drawings).
