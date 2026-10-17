# Science Template Library

Twenty animation templates for Human Unknowns-style science videos, plus the Studio tools to find,
tune, preview and combine them. Every template is a normal Beatframe template: put its name in
`scene:` and its settings in `params:`, exactly like the older ones.

```yaml
  - text: "You hear your own voice two ways at once."
    scene: bone_conduction
    params: {source: own_voice, highlight: coral, title: "Why your recorded voice sounds wrong"}
```

## The templates

All of them lay themselves out for both formats (16:9 side by side, 9:16 stacked), keep labels
inside the safe area (above Long subtitles; in Shorts the picture sits above the subtitle band and
the scene's own caption goes below it, clear of the Shorts buttons), and share these settings:

| setting | values | what it does |
|---|---|---|
| `palette` | dusk (default) · ocean · paper | background and line colours (paper = light videos) |
| `highlight` | coral · mint · sky · peach · lavender | colour of the thing the scene is about |
| `title` | text | optional headline at the top |
| `labels` | true / false | anatomical and diagram labels |
| `text_size` | 0.7 – 1.4 | all text bigger or smaller |
| `speed` | 0.6 – 1.6 | motion faster or slower inside the same beat length |
| `camera` | gentle · still · push · drift | what the camera does in the remaining time |

| category | template | what it shows | its own settings |
|---|---|---|---|
| Neuroscience | `neural_impulse` | neurons fire in turn: impulse along the axon, neurotransmitter across the synapse (optional camera dive) | neurons 3-7, layout chain/branching, synapse_zoom, caption |
| | `memory_reconstruction` | a memory breaks into fragments and is rebuilt: lost, filled-in and changed details, then before/after | scene park/beach, changes 1-3, before_after, labels |
| | `attention_spotlight` | a spotlight of attention visits objects; the rest fades; optional unnoticed change | items 8-30, stops 1-5, stop_labels, missed_change, reveal_text |
| | `sleep_cycle` | a night's hypnogram drawn in time with a live brainwave-style trace | hours 5-10, cycles 3-6, focus (e.g. REM), caption |
| | `stress_response` | threat → brain → fast adrenaline route and slow cortisol route; heart rate rises | stimulus, slow_route, bpm_from/bpm_to, effects |
| Human perception | `bone_conduction` | sound through the air and through the skull, both to the cochlea | source own_voice/tuning_fork/headphones, mode compare/air/bone, labels |
| | `inner_ear` | outer → middle → inner ear → nerve; an uncoiled cochlea shows where a pitch peaks | pitch high/middle/low, uncoiled |
| | `retina_processing` | light focused upside down on the retina, then the retina close-up: rods/cones → bipolar → ganglion | close_up |
| | `touch_receptors` | a press dents the skin; spike trains show slow vs fast adapting receptors | stimulus fingertip/pin/brush, press_share |
| | `reflex_arc` | stimulus → sensory neuron → spinal cord → motor neuron → muscle; pain reaches the brain later | stimulus flame/pin, show_brain_path |
| Experiments | `blind_spot_test` | a working blind-spot test (correct eye instructions), a still test card, then the optic disc | open_eye, spacing, marker, phases full/instructions/test/explain |
| | `balance_experiment` | vision + inner ear + feet; eyes closed (and foam) increase sway on a live trace | steps eyes/eyes_and_foam, try_it |
| | `reaction_time` | countdown, sudden signal, running ms timer, response, see/decide/move | instruction, countdown, wait_seconds, reaction_ms, result_label |
| | `stroop_effect` | playable Stroop test: matching round, clashing round, why | words 4-9, rounds both/clash_only, explain |
| | `ring_finger_test` | middle finger folded: three fingers lift, the ring finger can't; tendon links | try_it, explain |
| Biology | `blood_circulation` | heart, lungs and body: two loops of flowing blood | cells, bpm |
| | `oxygen_exchange` | alveolus and capillary: O₂ into red blood cells, CO₂ out | molecules, breathing |
| | `dna_unzipping` | double helix unzips; new bases pair (A-T, G-C) into two copies | pairs, sequence, mode replicate/unzip, letters |
| | `immune_response` | macrophage engulfs, T cell recognises, B cell antibodies tag the rest | bacteria, antibodies |
| | `evolution_tree` | tree grows along a time axis to today's species; shared ancestor marked | tree apes/vertebrates, focus |

Each template file starts with **accuracy notes**: what is simplified, what the colours mean and
which claims the scene deliberately avoids (for example, bone conduction is shown as *also*,
never *instead of*, air conduction; the evolutionary tree ends every species on the "today" line so
no living species is drawn as another's ancestor).

### Beat length

A scene never runs past its beat: each template spreads its steps over the beat, and a guard in
`sci.py` cuts animations to whole frames and skips what would start after the end (tested at
2.5 s, 4 s and 10 s). Short beats therefore show less of the story. Recommended minimum lengths
(design estimates, not measurements):

| beat length | templates |
|---|---|
| 3 s + | `blood_circulation`, `oxygen_exchange` (continuous loops) |
| 5 s + | `neural_impulse`, `attention_spotlight`, `sleep_cycle`, `touch_receptors`, `reflex_arc`, `evolution_tree`, `blind_spot_test` with `phases: test` |
| 6-7 s + | `bone_conduction`, `inner_ear`, `retina_processing`, `reaction_time`, `dna_unzipping`, `immune_response` |
| 8-9 s + | `memory_reconstruction` (before/after), `stress_response` (both routes), `balance_experiment`, `ring_finger_test` |
| 12 s + | `blind_spot_test` full (instructions, a still test card, explanation), `stroop_effect` (two rounds + why) |

Use `min_duration` on the beat (Storyboard → Timing & transition) when the narration is shorter
than the experiment needs.

## Studio: Template library (Templates in the sidebar)

* **Search** by name, description or category; **category chips**; **Favourites**; **Short-ready only**.
* **Recently used** row (templates you previewed or added to a project).
* Cards play their real catalogue loop on hover (rendered by `beatframe scene-thumbs`).
* **Open a template** → editor:
  * left: the preview (16:9 or 9:16 switch) and the YAML for the beat, updated as you change settings;
  * right: the settings form (sliders for ranges, colour swatches for palette and highlight);
  * bottom: **Render preview** (a real Manim render at Eco quality, queued with the other renders so only
    one Manim process runs; cached by its settings, so a repeat is instant), **Save preset**, **Use template**
    (adds the scene with these settings as a new beat to a project).
  * When you change a setting the page says the preview shows the old settings until you render again.
* Presets live in `~/.beatframe/presets.json`, favourites and recent in `~/.beatframe/library.json`,
  preview renders in `~/.beatframe/template_previews/`.

## Composer (project → Storyboard tab)

* Drag to reorder (as before); every card now has **Timing & transition**: minimum length and the
  transition into that scene (automatic, cut, fade, dissolve, wipe, slide …), saved in the YAML as
  `min_duration` and `transition`.
* **Preview this scene** renders just that beat; **Preview the whole composition** renders the preview.
* **Save scenes as a composition** (a range of beats, with their text, settings, timing and transitions)
  and **Insert a saved composition** into any project (start, end or after a beat). Compositions live in
  `~/.beatframe/compositions.json`.

## Rendering on a laptop (Settings → Rendering on this computer)

| setting | default | why |
|---|---|---|
| Manim processes at once | **1** | each 1080p process measured at about 0.5-0.7 GB peak memory (docs/RENDER_BENCHMARK.md); the old default ran (CPU cores ÷ 2) at once |
| Priority (nice) | **10** | the browser and Studio stay responsive while rendering |
| Preview quality | **Eco** 480p · 15 fps | Balanced 720p · 30 fps, Quality 1080p · 30 fps; the final is always 1080p |

`BEATFRAME_WORKERS=2` overrides the process count for one run. A running render can be stopped
(■ Stop render); finished scenes stay cached. Every uncached clip records its real cost (seconds,
peak memory of the Manim process, CPU %) in `build/render_stats.jsonl`; Settings shows the latest.

## Command line

```bash
beatframe bench neural_impulse bone_conduction --preset eco --preset quality --format long --format short
beatframe contact-sheet neural_impulse bone_conduction --format long --format short
beatframe scene-thumbs                   # catalogue stills + loops for every template
beatframe scene-thumbs reaction_time     # only some
```

## Adding a science template

Create `beatframe/templates/<name>.py`, subclass `Template`, use `sci.SciParams` for the shared
settings and the helpers in `templates/sci.py` (`Stage` for the frame and safe areas, `background`,
`headline`, `tag`, `callout`, `Clock` for timing, `finish` for the camera at the end, drawing helpers).
Set `category`, `theme = "bright"` and `vertical_width = 8.0`. Editing `sci.py` re-renders every
template that uses it (the clip cache key includes it).


Visual QA: `docs/contact_sheets/` shows the start, middle and end frame of every template in both formats.
