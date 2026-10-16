# Beatframe Studio — complete front-end description

This document describes every screen of **Beatframe Studio** in detail, so a designer (human or AI) can picture the whole product and redesign it without seeing it. It covers what the app does, the visual style, the layout shell, every page with all of its elements and states, shared components, responsive behaviour, and realistic sample content.

---

## 1. What the product is

Beatframe Studio is a **local desktop web app** (runs on the user's own computer at `http://127.0.0.1:8000`, opened in a browser) for **one YouTube creator** who runs a faceless English science channel called **Human Unknowns** (topic: the viewer's own body, brain and perception; tagline idea: "The stranger inside you").

The app turns a written script into a finished animated video, and then helps publish it:

1. **Write / paste a script** (YAML text). The script is a list of **beats**: one spoken sentence + the animated scene that plays under it.
2. **Render a preview** (fast, 480p). The app makes an AI voice, animates every beat, burns in word-by-word captions and joins everything.
3. **AI review**: an AI watches the preview and lists what to fix, beat by beat, with a score out of 10.
4. **Edit beats** and re-render only what changed.
5. **Render the final** video (1080p).
6. **Publish** to YouTube (title, description, tags, chapters, subtitles, thumbnail, schedule) straight from the app.

It can also **import a finished video made elsewhere** (e.g. generated in Google Gemini), review it with AI and publish it.

Two video formats exist everywhere in the app:
- **Short** — vertical **9:16**, 1080 × 1920 (YouTube Shorts, Reels, TikTok).
- **Long** — horizontal **16:9**, 1920 × 1080 (normal YouTube video).

There is a single user and no login screen. UI language: **English**. AI review text appears in **Uzbek** (Latin script) — the design must handle mixed English UI + Uzbek content.

Mood: a focused, professional creator tool — like a modern video editor or developer dashboard. Calm, dark, precise; not playful, not corporate.

---

## 2. Visual style (current design language — keep it, polish it)

**Theme:** dark only.

**Colours**
| Token | Hex | Use |
|---|---|---|
| Page background | `#0a0f1d` | main canvas (very dark navy) |
| Sidebar background | `#0c1222` | left navigation |
| Card | `#10182b` | panels/cards |
| Card raised 2 | `#151f36` | inputs, inner boxes, buttons |
| Card raised 3 | `#1b2642` | hover states |
| Hairline | `#1d2843` | borders, dividers |
| Strong hairline | `#2a3758` | input/button borders |
| Text | `#e9edf7` | primary text |
| Muted text | `#929db6` | secondary text |
| Faint text | `#626e88` | hints, captions, metadata |
| Accent blue | `#5b6cff` | links, focus, selected states |
| Accent violet | `#8b5cf6` | gradient end |
| Brand gradient | `linear-gradient(90deg, #4f6bff → #7a5cf8)` | primary buttons, logo tile |
| Success | `#34d399` (soft bg 12% alpha) | done, connected, ready |
| Warning | `#f5c35b` (soft bg 10% alpha) | tips, needs attention |
| Error | `#f87171` (soft bg 10% alpha) | failed, high-severity issues |
| YouTube red | `#ff4e45` | only the YouTube icon inside the upload button |

**Typography:** **Figtree** (geometric sans) for everything; a monospace font (JetBrains Mono / SF Mono style) for code, file names, beat numbers, scene names, timestamps.
- Page title (h1): 26px bold (22px on phones).
- Section title (h2): 19px bold. Card title (h3): 15.5px semibold.
- Body: 15px. Small/hints: 12.5–13px. Mono: 12.5px.

**Shapes:** cards have 12px rounded corners and a 1px hairline border; inner boxes and buttons 8px corners; chips/pills are fully rounded.

**Buttons**
- *Primary* — brand gradient fill, white text, soft blue glow shadow.
- *Secondary* — dark fill (`#151f36`) with a strong hairline border.
- *Ghost* — transparent, muted text, fills on hover.
- Sizes: small, normal, big (full-width on forms). Most buttons have a small line icon (18px, 1.8 stroke, rounded caps) before the label.

**Chips (status pills):** small rounded labels, 12px semibold — neutral grey, blue ("Short", "Imported"), green ("Connected", "Completed", "Key set", "Ready"), red ("Script error", "Fix first", "high"), dim ("Draft", "Not set").

**Icons:** thin outline line icons (home, folder, bar chart, grid, gear, play triangle, download arrow, eye, sparkle).

**Logo:** a small rounded-square tile filled with the blue→violet gradient containing a white "play" triangle, followed by the word **Beatframe** in bold. The same tile is the app icon.

**Motion:** subtle — hover colour changes, a progress bar that fills, a spinning loader, a pulsing dot on "Rendering". Respect reduced-motion.

---

## 3. App shell (on every page)

Two-column layout: **fixed left sidebar (236px)** + **main content area** (max content width ≈ 1200px, generous padding ~28–36px).

**Left sidebar** (top to bottom):
1. Logo (tile + "Beatframe").
2. Navigation list, each item = icon + label; the current page is highlighted (blue-tinted background, white text, thin blue inner border):
   - **Studio** (house icon) — create or import a video.
   - **Projects** (folder icon) — all videos.
   - **Stats** (bar-chart icon) — channel statistics.
   - **Templates** (4-squares icon) — catalogue of animated scenes.
   - **Settings** (gear icon).
3. Footer pinned to the bottom, separated by a hairline: a round avatar with initials **"HU"**, the channel name **Human Unknowns** and a small line "YouTube connected · v0.1.0" (or "Local studio" when not connected). Clicking it opens Settings.

**Page header pattern** (top of every page): big title on the left with a muted one-line description under it; optional action button(s) on the right.

---

## 4. Pages

### 4.1 Studio (home) — `/`

Title changes with the mode: **"Create Your AI Video"** / **"Import a Finished Video"**. Subtitle: "Turn your script into an animated video: voice, scenes, subtitles and chapters." Right side: secondary button **"My Projects"**.

Under the header, two **tabs** (underlined tab bar): **Create with Beatframe** | **Import a finished video**.

Layout below: **two columns** — a wide form card on the left, a 360px stack of side cards on the right.

#### Mode A — Create with Beatframe (left form card)
A vertical form split into numbered steps; each step has a small numbered circle (1, 2, 3) before its heading.

1. **Project details** — text field "Project name" with the note *"optional – taken from the script's title if empty"* and a live character counter "0/100" inside the field's right edge. Placeholder: "e.g. The Science of Touch".
2. **Video format** — two large selectable cards side by side:
   - **Short** `9:16` — a small vertical-rectangle drawing, text "Vertical video for Shorts, Reels and TikTok", "1080 × 1920" in mono.
   - **Long** `16:9` — a small horizontal-rectangle drawing, "Landscape video for YouTube and documentary content", "1920 × 1080".
   The selected card has a blue border, a light blue tint and a round blue checkmark in its top-right corner; the rectangle drawing glows softly.
3. **Script** — a big monospace code editor (textarea, ~16 rows) with a YAML example as placeholder. Under it: a character counter on the left and a small button **"Use example"** (copy icon) on the right.
   Below the editor a **live check box** appears while typing:
   - green: "✓ **The Science of Touch** — 7 beats, about 24 s of narration · script asks for **Short 9:16**";
   - red: "The script has a problem" + the error lines in mono;
   - yellow **"Retention tips"** box (the script still renders) with a bullet list, e.g. "Beat 1 has 9 words. A 4–5-word claim hooks better.", "Beats 3–5 are all text cards: nothing moves for a while.", "No 'try it right now' moment."
4. Collapsible **"Advanced settings"** (chevron). Inside, "After creating": three radio cards — **Render a preview** (480p, about a minute) · **Render the final video** (full quality + subtitles, chapters) · **Only create the project** (edit beats first).
5. Full-width big primary button **"✦ Generate Video →"**.

#### Mode B — Import a finished video (left form card)
1. **Video file** — a large dashed drop zone with an upload-arrow icon, text "Choose or drop the video" and a small line "MP4, MOV, WebM or MKV. Vertical becomes a Short, horizontal a Long video." States: hover/drag-over (blue border + blue tint); file chosen (solid green border, shows "gemini_tickle.mp4 · 2.8 MB").
2. **Import card** — monospace editor (same look as the script editor) for a short YAML text with: `title`, `video: {format: short}`, `made_with: gemini`, `description`, `tags`, `script` (the voiceover), `chapters`, `synthetic`. Footer: a hint line + **"Use example"** button. Live check below: green "✓ **Your Eyes Go Blind 3 Times a Second** — Short 9:16 · made with gemini · 8 words of script · 2 tags", or a red error, or a yellow note "No script: the AI review works better when it knows the voiceover."
3. Full-width big primary button **"Import Video →"** (while uploading it changes to "Importing… (large videos take a moment)" and is disabled).
4. Hint: "Next: press **Review with AI** on the project page, fix what it finds, then **Publish**."

#### Right column (both modes)
- **Recent projects** card — header "Recent projects" + link "View all"; a compact list of the last 5 projects (rows described in 4.2). Empty state: a small glowing dot tile + "Nothing yet. Your first video will appear here."
- **Formats** card — two mini comparison tiles (Short / Long) each with the shape drawing, name + ratio, resolution, and use ("Shorts, Reels, TikTok" / "YouTube, documentary").
- Collapsible **"Scenes you can use"** — a wrap of small mono chips with every scene name (title_card, statement, stick_scene, kinetic_text, brain_light, body_map…) + link "See every scene and its settings →".

---

### 4.2 Projects — `/projects`

Header: **"My Projects"**, subtitle "Your videos and drafts. Each one is a folder in `projects/`." Right: primary button **"＋ New Project"**.

One big card containing:
- **Filter pills** row: All · Completed · Rendering · Drafts — each with a small count badge; the active one is highlighted.
- **Project list** — one row per video (hover: row gets a raised background and border):
  - **Thumbnail** 64×40 (a frame from the video; fallback = dark navy→violet gradient with a warm orange glow spot).
  - **Title** (bold) and a muted meta line: "2 hours ago · 0:25 · 7 beats".
  - **Format chip**: blue "Short" or grey "Long".
  - **Status chip**: green "Completed" / blue pulsing "● Rendering" / grey "Preview" / dim "Draft" / red "Script error". (Imported videos show the blue "Imported" chip.)
- Empty state: glowing dot tile, "No projects yet", "Paste a script on the Studio page and your first video starts rendering.", button "Create a video".
- Filter with no matches: small text "Nothing here."

Sample rows:
- You've Never Heard Your Real Voice — Short — Completed — 0:25
- Your Brain Deletes Most of Your Week — Short — Completed — 0:35
- Why Time Speeds Up As You Get Older — Long — Completed — 11:42
- You Can't Lift Your Ring Finger — Short — Preview
- Your Brain Edits Everything You See — Long — Draft

---

### 4.3 Project page — `/p/<project>` (the main working screen)

**Header:** small back link "← All projects"; title (e.g. **You've Never Heard Your Real Voice**); meta line "7 beats · voice am_michael · `projects/you-ve-never-heard-your-real-voice`". For an imported video instead: blue chip **Imported** + "Short 9:16 · made with gemini".

Optional **info banner** (blue) after an import, e.g. "The card said long, but the video is 9:16: saved as Short."

**Toolbar card** (not shown for imported videos): left — label "Video format" + a compact segmented switch **[▯ Short 9:16] [▭ Long 16:9]** (switching re-saves the project's format); right — hint "1080 × 1920 final · 480p preview" + secondary button **"👁 Render preview"** + primary button **"▶ Render final"**. Both buttons are disabled while a job runs.

**Tabs:** **Video** · **Edit beats** · **Script** · **Publish** (imported videos: **Video** · **Import card** · **Publish**).

#### Job card (appears above the tab content while something runs)
A card showing a background job — render, AI review or YouTube upload:
- Left: spinner (running) / green check circle (done) / red ✕ (failed); title "Generating your video…" / "Video generated" / "Render failed" (or "AI is reviewing the video…" / "AI review ready", "Uploading to YouTube…" / "Uploaded"); under it a small label like "Preview · Short 9:16 · 480×854".
- Right: big percentage "67%".
- A thin full-width **progress bar** (gradient fill; red when failed).
- A line with current detail on the left ("Beat 4 / 7", "Step 2 / 3") and stage + elapsed time on the right ("Rendering animation · 18 s").
- **Render checklist** (renders only): numbered rows — Check script · Generate voice (3/7) · Render scenes (4/7) · Combine with FFmpeg · Subtitles, chapters & thumbnails — each with a state on the right: Done ✓ / In progress / Pending / Failed.
- While rendering: a "Current: beat 04, `brain_light` — Rendering with Manim…" mini-row with a film icon.
- When done: primary button "Watch preview" / "See the review" + hint "25.5 s long · rendered in 34 s"; for uploads a green box with the YouTube link and "open in Studio".
- Failed: red box with the error text.
- Collapsible **"Render log"** with the last lines in monospace.

#### Tab: Video
1. **Result card** ("Video ready" / "Preview ready" with a green check circle). Sub-text: "Download it, check it, or upload it to YouTube." or "Happy with it? Press **Render final**. Something off? Open **Edit beats**."
   Body in two parts:
   - **Video player** — vertical (phone-shaped, ~280px wide) for Shorts or wide 16:9 for Long, black background, native controls.
   - **Side panel**: a 2×2 grid of fact tiles (FORMAT Short (9:16) · RESOLUTION 1080 × 1920 · LENGTH 0:25 · FILE SIZE 2.9 MB), then stacked buttons: primary **Download**, secondary **Open preview**, secondary **Upload to YouTube** (YouTube icon in red); then a small file list (subtitles.srt 1 KB, chapters.txt) with download links; and a hint if the other format also exists.
   - Empty state (nothing rendered yet): glowing dot tile, "No short video yet", "Press **Render preview** for a quick 480p look in 9:16."
2. **AI review card** (anchor `#review`):
   - Header: "AI review" + a status chip on the right: red **"7/10 · Fix first"** or green **"9/10 · Ready"**.
   - Yellow warning if outdated: "This review is for an older render (final_short.mp4). Run it again to check the new one."
   - Summary paragraph (Uzbek), e.g. "Video ovoz haqidagi qiziqarli faktni yaxshi ochib bergan, lekin boshlanishi sekin…"
   - Small muted line: "**First 2 seconds:** …what the viewer sees and hears…"
   - **Issue list**, most severe first. Each issue is a bordered row with a coloured left edge (red = high, blue = medium, grey = low) containing: a severity chip (high/medium/low), a mono link **"beat 1"** (jumps to that beat in Edit beats) or "whole video", mono "0:00 · hook"; a bold problem sentence; "→ fix" sentence; optionally a suggested new English line in mono quotes, e.g. "Your own skull is tricking you every day."
   - "**Works:** …" line (strengths).
   - Metadata line: "gemini-3.5-flash-lite · 2026-10-13 11:22:01 · final_short.mp4" (+ "backup model: weaker than Gemini" when a fallback AI answered).
   - Button **"✦ Review with AI"** (primary) or **"Review again"** (secondary). If no AI key: hint "Add a free Gemini or OpenRouter key in Settings to run a review."

#### Tab: Edit beats
Intro hint: "Change a beat and press **Save & preview this beat** to see just that part…". Then one **beat card** per beat, stacked:
- Header row: a round **number** badge (1, 2, 3…), the **scene name** in mono (e.g. `stick_scene`), an optional chapter tag "§ Intro", and on the right four small icon buttons: ↑ move up · ↓ move down · + add after · ✕ delete (asks for confirmation).
- **Narration** textarea (2 rows) — the spoken sentence.
- Two fields side by side: **Scene** (dropdown of all scenes; changing it swaps the settings below) and **Chapter (optional)** "starts a YouTube chapter".
- **Scene settings** — a grid of auto-generated fields for that scene (text inputs, dropdowns, number inputs, checkboxes, comma-separated lists), e.g. for `stick_scene`: setting (plain/kitchen/bedroom/office…), action (walk_in/run/freeze/scared/point…), bubble (none/question/bulb/phone…), caption, palette.
- Buttons: **Save** (secondary) · **Save & preview this beat** (primary); success text "✓ Saved — rendering preview…"; red error box if invalid. A small video of just that beat appears in the job card when ready.

#### Tab: Script (or "Import card")
A red box if the script cannot be read. A large monospace editor with the whole YAML, the live check box under it, buttons **Save** and **Save & render preview**, hint "Paste a whole new version here to replace the script. `video: {format: short}` makes it a Short." At the bottom, a small ghost **"Delete this video"** (confirm dialog; moves it to a trash folder). For imported videos the render button is replaced by a hint that the video itself stays as imported.

#### Tab: Publish
Alerts at the top: yellow "Render the final short video first…" or blue "This is a vertical video under 3 minutes, so YouTube will publish it as a **Short**."
Two cards side by side:

**Upload to YouTube** card — three possible states:
1. *Not set up:* an ordered list of 6 setup steps with external links (Google Cloud project, enable YouTube Data API, consent screen, test user, Desktop OAuth client, download JSON), a file picker + **"Save client file"** button, hint about where credentials are stored.
2. *Not connected:* primary **"Connect YouTube"** + hint.
3. *Connected:* green chip "Connected: Human Unknowns" + ghost "Disconnect"; yellow note that API uploads stay Private until Google's audit; a big primary button **"Upload to Human Unknowns"**; hint "Goes public **today at 18:30**…" (auto-computed); collapsible **"Change details (optional)"** with: Title (max 100), Description (8-row textarea pre-filled with description + chapters), Tags, Visibility dropdown (Public/Unlisted/Private), "Goes public at" datetime, checkboxes "Add English subtitles from the script" and "Mark as altered or synthetic content", and a **thumbnail picker** — a row of frame thumbnails as radio tiles (first tile "YouTube picks").

**Manual upload** card — hint "Always works…", download buttons (↓ final_short.mp4, ↓ subtitles.srt), read-only fields Title / Description / Tags each with a small **"copy"** link (turns into "Copied"), and a row of downloadable thumbnail images.

---

### 4.4 Stats — `/stats`
Header "Stats", subtitle "Your connected channel's numbers as one text block. Copy it and paste it into the Claude chat…".
One state card depending on setup: *Not set up* · *Not connected* (button "Connect YouTube") · *One more permission* (2 steps + "Reconnect YouTube") · *Connected* (card titled with the channel name + green chip; a row "Channel totals for the last [28 ▾] days" + primary **"Get statistics"** + inline "Reading YouTube…" loader; hint that CTR is not available via the API).
Below: **Report** card — timestamp, small primary **"Copy"** button, and a large read-only monospace text box with the report (starts with `CHANNEL: Human Unknowns (UC…)`, then one line per video: type S/L, age, views, % viewed, likes…).

### 4.5 Templates — `/templates`
Header "Templates", subtitle "The scenes a beat can use…". A responsive **grid of cards**, one per scene (~30), each: mono scene name as title, a chip on the right — blue **"Short-ready"** or dim **"16:9 drawing"**, a one-line description (e.g. "Big brain with one region lighting up, sparks and a label"), and a compact key → default-value list of its settings (or "No settings."). Ideal place for future preview thumbnails.

### 4.6 Settings — `/settings`
Grid of cards:
- **YouTube** — chip Connected / Not connected / Not set up; "Uploads go to **Human Unknowns**…"; hint "Credentials are stored in `/home/…/.beatframe`, never inside a project."
- **AI review** — chip Ready / Not set; explanation that AIs are tried in order (Gemini first, OpenRouter backup); two sub-sections separated by hairlines: **"1. Gemini"** and **"2. OpenRouter (backup)"**, each with a Key set / Not set chip, a link "free key: aistudio.google.com/apikey", a password field "Paste your API key" / "Replace the saved key" and a small primary **"Save key"**; footer hint about where keys are stored.
- **Studio** — version chip "v0.1.0"; key–value list: Projects folder (mono path), Formats (Long 16:9 (1920×1080), Short 9:16 (1080×1920)), Preview (480p, 15 fps); hint about the command line.

---

## 5. Shared components and states (design these once)
- Cards (with optional header row: title left, chip/action right).
- Buttons (primary gradient / secondary / ghost; small / normal / big / full-width; disabled).
- Chips (neutral, blue, green, red, yellow, dim, live-pulsing).
- Tabs (underline style) and filter pills with counts.
- Segmented control (Short/Long).
- Format selector cards with shape drawings and corner checkmark.
- Form fields: label above in small muted text, dark inputs with strong hairline border, blue focus ring; textareas; mono code editors; dropdowns; checkboxes; radio cards; file drop zone; character counters.
- Alerts: success (green), error (red, with mono details), warning (yellow, with bullet list), info (blue).
- Progress: thin bar, percentage, numbered checklist with states, spinner, pulsing "Rendering" dot.
- Empty states: rounded tile with a glowing gradient dot + title + one line + button.
- Video player frames: vertical phone-shaped and horizontal 16:9, black.
- Thumbnail tiles (radio-selectable, with selected ring).
- Copy-to-clipboard links/buttons with "Copied" feedback.

---

## 6. Responsive behaviour
- **≥ 1180px:** everything as described (two-column forms and result cards).
- **< 1180px:** Studio's right column drops under the form; the video result card stacks player above details; vertical player is centred.
- **< 900px (tablet/phone):** the sidebar becomes an off-canvas drawer opened by a ☰ button in a slim top bar (top bar shows ☰ + logo); a dark scrim covers the page while it is open.
- **< 560px:** smaller titles (22px), tighter card padding, format cards stack vertically, radio cards in one column. No horizontal scrolling anywhere.

---

## 7. Design goals for the redesign (the brief)
Keep the **dark navy theme, blue→violet gradient, Figtree** — the redesign is a *polish*, not a new brand.
1. Make the **workflow obvious**: Script → Preview → AI review → Final → Publish. On the project page show where the video is in this flow (e.g. a 5-step progress strip) and what to do next (e.g. a "Next step" card: "Fix 1 hook problem, then render the final" with the right button).
2. Make the **AI review** feel central and scannable: a score (ring or big number), issues grouped by severity, each linked to its beat with a small frame thumbnail of that beat.
3. Cleaner hierarchy: consistent spacing (8px grid), one primary button per area, calmer secondary text, aligned card headers.
4. Projects list: room for the AI score and a "Published / Not published" state in each row.
5. Everything must stay usable at phone width (the creator sometimes checks on a phone).

Please draw: **(1) Project page — Video tab** with a Short video, an AI review of 7/10 with 3 issues and the job card hidden; **(2) Studio page — Create tab**; **(3) Studio page — Import tab**; **(4) Projects list**; **(5) Project page — Edit beats tab** with two beat cards; **(6) the Project page at phone width (375px)**.

---

## 8. Realistic sample content to use in the drawings
- Channel: **Human Unknowns** (avatar "HU").
- Project: **You've Never Heard Your Real Voice** — Short 9:16, 7 beats, 0:25, voice `am_michael`, 2.9 MB.
- Beats: 1 `stick_scene` "You've never heard your real voice." · 2 `kinetic_text` "That's why recordings sound so wrong." · 3 `kinetic_text` "Try it. Plug your ears and hum." · 4 `body_map` "Louder, right? That sound is travelling through your skull." · 5 `brain_light` "Your bones add a deep bass only you can hear." · 6 `kinetic_text` "The voice on the recording? That's the one everyone hears." · 7 `statement` "What else isn't what it seems?"
- Video frames look like: bright pastel backgrounds (mint, pink, lilac, peach) with simple black stick figures, a white human-body outline, a pink cartoon brain with orange sparks, bold coloured word blocks ("Plug", "Hum.", "THAT"), and large white captions with dark outline where the spoken word turns orange; the last frame is dark navy with serif text "What else isn't what it seems?".
- AI review: 7/10, Fix first. Summary: "Video ovoz haqidagi qiziqarli faktni yaxshi ochib bergan, lekin boshlanishi sekin va vizual qotib qolgan." Issues: [high] beat 1 · 0:00 · hook — "Birinchi soniyalarda harakat yo'q." → "Birinchi freymdanoq harakat qo'shing." "Your own skull is tricking you every day." · [medium] beat 3 · 0:06 · pacing — "Tajriba qismi kech boshlanadi." → "'Try it' beatini oldinroqqa suring." · [low] whole video · captions — "Subtitr bir joyda rasm ustiga tushadi." Model line: "gemini-3.5-flash-lite · 11:22".
- Other projects: see 4.2.
