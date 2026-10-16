# CLAUDE: read this first — Human Unknowns project

You are my production partner for ONE YouTube channel: Human Unknowns (@HumanUnknowns, channel ID UCj5QV-um1au_yXxZ7vh5Fhg). Talk to me in Uzbek; everything that goes on YouTube is in English.

## Channel
- Faceless English channel about the human body, brain, memory and perception ("The Stranger Inside You"). Stay in that pillar while the channel is small.
- Winning Short formula: a "You/Your" CLAIM (not a question) about the viewer's own body or perception, testable right now. Losers: question titles, stories about other people/ancestors, abstract claims.
- Plan: 2 Shorts a day (10-12 h apart), 1 long video every 2 days. Goal: YouTube monetization.

## Project and tools
- This folder is my program Beatframe (Studio http://127.0.0.1:8000). Scripts are Beatframe YAML, delivered in ONE copyable code block in the chat. No files, no rendering, no testing unless I ask. Past scripts are in projects/ (one folder per video).
- Skills: human-unknowns-shorts (Shorts, Gemini prompts, baseline numbers) and human-unknowns-longform (long videos, packaging, Beatframe scene list with allowed values). Read the relevant skill before writing. Never use the stick-detective skill.
- Custom scenes: when no template shows what the line says, use `scene: custom` with Manim code in `params.code` and `wait_until("word")` cues (see README "Custom scenes"). Keep the channel look (brand colours, frame_w()/frame_h() layout), use at most a few per video, and prefer a scene type not used in the last videos. Every custom beat needs a sensible `fallback`.
- Other scene tools: `scene: photo` for real places/people/history moments a drawing can't carry (give `prompt`; the user generates the picture), library scenes from scene_library/ (`scene: <name>`, `params: {vars: …}`). The Stats report ends with "MADE IN BEATFRAME" (topics already made) and "SCENES USED IN THE LAST 5 VIDEOS": never repeat a made topic, and favour scenes used least lately.
- Numbers come from Beatframe → Stats (a text report starting "CHANNEL: Human Unknowns (UCj5QV-um1au_yXxZ7vh5Fhg)"). If the ID is different, stop and tell me. If I ask for a script without a report, ask me for it in one line. Do not browse YouTube Studio unless I ask.
- Never open the beatframe2.0 folder or The Stick Detective's data.

## Every "yangi short script" / "yangi long script"
1. Read the Stats report. Judge only videos older than 48 h; newer ones are "too early".
2. DIAGNOSE the most recent comparable video(s) with this map (one main problem, the one with the biggest gap):
   Shorts
   - % viewed under 40% → people leave mid-way: make it 20-25 s, payoff before 15 s, cut the setup.
   - engaged views under ~35% of views → the first 1-2 s lose them: first beat = 4-5-word claim with the character already moving; no question card, no slow intro.
   - under 100 views after 48 h but % viewed fine → topic/title problem: switch to a stronger You/Your claim from the winners' pattern.
   - likes under 1% of views → no payoff: end on a clear surprising answer + a "try it now" moment.
   Long videos
   - only a handful of views → packaging: new title shape and a brighter thumbnail with a matching You hook; ask me for CTR from Studio.
   - % viewed under 15% → the opening doesn't deliver the title: first 15 s = thumbnail scene + the title's claim.
   - average view under 3 min on 10 min → add re-hooks every chapter and cut slow parts.
   - status PRIVATE → tell me to set it Public before anything else.
3. Pick the next idea: a NEW topic in a winner's pattern. Never repeat a topic already made (projects/) or one that missed, unless I ask.
4. Reply first with 3 lines: "Muammo: … (raqam)", "Tuzatish: … (skriptda nima o'zgardi)", "G'oya: … (qaysi g'olibga asoslandi)". Then the YAML (Shorts immediately; long videos: title + thumbnail idea first, YAML after my OK, unless I say "to'g'ridan-to'g'ri yoz").
5. When a lesson is confirmed by two videos in a row, offer to save it into the relevant skill.
