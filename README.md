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

## Custom scenes (`scene: custom`)

When no template fits a beat, write that beat's own Manim code into the script. The animation can
wait for a spoken word, so it lands exactly when the narrator says it.

```yaml
  - text: "Your brain fills the gap before you notice it."
    scene: custom
    params:
      theme: night          # night | bright
      fallback: statement   # used if the code fails (default: statement with the beat's text)
      code: |
        gap = Rectangle(width=4, height=2).set_stroke(PAPER, 3)
        scene.play(Create(gap), run_time=0.6)
        wait_until("fills")
        scene.play(gap.animate.set_fill(GLOW, 0.8), run_time=0.5)
```

In `code`: `scene`/`self`, all of Manim, brand colours (NIGHT, PAPER, GLOW, EMBER, DIM, SERIF, SANS),
`frame_w()`, `frame_h()`, `fit()`, `glow()`, `kit`, `duration`, `words`, `at("word")`,
`wait_until("word" | seconds)`, `now()`, `rest()`. Full list: `beatframe/templates/custom.py`.

If a custom scene fails at render time the video still renders: that beat uses its fallback, and the
error is saved in `build/custom_errors.txt` (Studio shows it under the script).

## Pre-render check

`beatframe check project.yaml` (and the Script tab in Studio) checks, before rendering: scene names and
params, custom code that does not parse, cue words the narrator never says, missing image/music/voice
files, beats that show exactly the same picture, the same scene 3+ times in a row, and one scene
filling more than 30% of a long video. `--test` also test-renders every custom scene at 240p.

Own recordings (`voice.provider: files`) get real word timings when faster-whisper is installed:
`.venv/bin/pip install -e '.[whisper]'`.

## Scene library

A custom scene that came out well can be reused: in Studio press **Save scene to library** under a
custom beat, or `beatframe save-scene project.yaml --beat 7 --name gap_fill`. It is stored in
`scene_library/gap_fill.yaml` and works like a template from then on: `scene: gap_fill`, with
`params: {vars: {label: "..."}}` read in its code as `v["label"]`. The style guard applies to every
custom and library scene: `Text(...)` gets the channel font and colour and never overflows the frame,
and `safe(group)` fits a whole group into the safe area.

## Variety

`beatframe check` compares the script with the last 3 videos: the same custom code again, or the same
favourite scenes again, gets a warning. `beatframe history` prints the made topics and the scene mix of
the last 5 videos; the same block is appended to the Stats report in Studio, so Claude sees it too.

## Transitions

Beats are joined with short varied transitions (fade, smooth slide, wipe, circle...) that never repeat
twice in a row; a new chapter dips to black. Every beat still starts exactly on its voice. Turn them
off with `video: {transitions: cut}`; change the length with `transition_seconds` (default 0.3).

## Pictures (`scene: photo`)

A full-frame picture with a slow Ken Burns move (in, out, left, right, up; auto picks one) and an
optional caption:

```yaml
  - text: "In 1953, one man lost the ability to make new memories."
    scene: photo
    params: {prompt: "1950s hospital room, a man by a window", caption: "Patient H.M., 1953"}
```

Without `image` the file is `images/beat_NNN.png`. `beatframe image-prompts project.yaml` (and the
Script tab) lists every picture still missing with its file name and full prompt, ready to paste into
Google Flow or Gemini. Replacing a picture re-renders only its beat.

## Channel profiles

`profiles/*.yaml` hold a channel's look: colours, fonts, music mood, picture style and voice.
`beatframe profile use war-maps` makes one active (copied to `profile.yaml`), `beatframe profile off`
returns to the built-in Human Unknowns look, `beatframe profile` shows the active one. Extra fonts go in
a `fonts/` folder next to the app.
