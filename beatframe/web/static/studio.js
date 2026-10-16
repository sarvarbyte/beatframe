/* Beatframe Studio — interactive pieces: Storyboard, Compare, Thumbnail Lab, Quality and Stats charts.
   Plain JS, no libraries. Every page loads this once; each part only runs when its element exists. */
(() => {
  if (window.__studioJs) return; window.__studioJs = true;
  const $ = (s, r = document) => r.querySelector(s), $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const css = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  const mmss = s => { s = Math.max(0, Math.round(s || 0)); return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`; };
  const say = msg => (window.toast ? window.toast(msg) : console.log(msg));

  /* ------------------------------------------------------------ segmented buttons */
  function seg(el, onPick) {
    if (!el) return;
    el.addEventListener("click", e => {
      const b = e.target.closest("button"); if (!b) return;
      $$("button", el).forEach(x => x.classList.toggle("on", x === b)); onPick(b);
    });
  }

  /* ------------------------------------------------------------ STORYBOARD */
  function storyboard() {
    const list = $("#storyboard"); if (!list) return;
    const bar = $("#sbBar"), diff = $("#sbDiff"), slug = list.dataset.slug;
    const original = $$(".sb-card", list).map(c => +c.dataset.i);
    const order = () => $$(".sb-card", list).map(c => +c.dataset.i);
    function refresh() {
      const now = order(), moved = now.filter((v, k) => v !== original[k]).length;
      bar.hidden = moved === 0;
      diff.textContent = moved ? `${moved} beat${moved > 1 ? "s" : ""} in a new place.` : "";
      $$(".sb-card", list).forEach((c, k) => { c.querySelector(".sb-num").textContent = k + 1; c.classList.toggle("moved", +c.dataset.i !== original[k]); });
    }
    // FLIP: animate cards from their old to their new position
    function flip(mutate) {
      const cards = $$(".sb-card", list), before = new Map(cards.map(c => [c, c.getBoundingClientRect()]));
      mutate();
      if (calm) return refresh();
      cards.forEach(c => {
        const a = before.get(c), b = c.getBoundingClientRect(), dx = a.left - b.left, dy = a.top - b.top;
        if (!dx && !dy) return;
        c.animate([{ transform: `translate(${dx}px, ${dy}px)` }, { transform: "none" }], { duration: 260, easing: "cubic-bezier(.22,1,.36,1)" });
      });
      refresh();
    }
    function move(card, step) {
      const sib = step < 0 ? card.previousElementSibling : card.nextElementSibling; if (!sib) return;
      flip(() => step < 0 ? list.insertBefore(card, sib) : list.insertBefore(sib, card)); card.focus();
    }
    list.addEventListener("click", e => { const b = e.target.closest("[data-move]"); if (b) move(b.closest(".sb-card"), +b.dataset.move); });
    list.addEventListener("keydown", e => {
      const card = e.target.closest(".sb-card"); if (!card || !e.altKey) return;
      if (["ArrowLeft", "ArrowUp"].includes(e.key)) { e.preventDefault(); move(card, -1); }
      if (["ArrowRight", "ArrowDown"].includes(e.key)) { e.preventDefault(); move(card, 1); }
    });
    // drag with mouse, pen or finger (pointer events): a floating ghost follows, the card slots in live
    let drag = null;
    list.addEventListener("pointerdown", e => {
      const grip = e.target.closest(".sb-grip, .sb-still"), card = e.target.closest(".sb-card");
      if (!grip || !card || e.button > 0) return;
      e.preventDefault();
      const r = card.getBoundingClientRect();
      const ghost = card.cloneNode(true); ghost.classList.add("sb-ghost");
      Object.assign(ghost.style, { width: r.width + "px", height: r.height + "px", left: r.left + "px", top: r.top + "px" });
      document.body.appendChild(ghost); card.classList.add("sb-placeholder");
      drag = { card, ghost, dx: e.clientX - r.left, dy: e.clientY - r.top, id: e.pointerId };
      list.setPointerCapture(e.pointerId);
    });
    list.addEventListener("pointermove", e => {
      if (!drag || e.pointerId !== drag.id) return;
      drag.ghost.style.left = e.clientX - drag.dx + "px"; drag.ghost.style.top = e.clientY - drag.dy + "px";
      // hit-test against layout boxes (offsetLeft/Top ignore the FLIP transforms still running)
      const lr = list.getBoundingClientRect(), px = e.clientX - lr.left, py = e.clientY - lr.top;
      const over = $$(".sb-card", list).find(c => c !== drag.card && px >= c.offsetLeft && px <= c.offsetLeft + c.offsetWidth
        && py >= c.offsetTop && py <= c.offsetTop + c.offsetHeight);
      if (over) {
        const after = (px - over.offsetLeft) / over.offsetWidth > 0.5;
        const target = after ? over.nextElementSibling : over;
        if (target !== drag.card && target !== drag.card.nextElementSibling) flip(() => list.insertBefore(drag.card, target));
      }
      // scroll the page when dragging near the edges
      if (e.clientY < 70) scrollBy(0, -12); else if (e.clientY > innerHeight - 70) scrollBy(0, 12);
    });
    const end = e => {
      if (!drag || e.pointerId !== drag.id) return;
      drag.ghost.remove(); drag.card.classList.remove("sb-placeholder"); drag = null; refresh();
    };
    list.addEventListener("pointerup", end); list.addEventListener("pointercancel", end);
    $("#sbReset").addEventListener("click", () => flip(() => original.forEach(i => list.appendChild($(`.sb-card[data-i="${i}"]`, list)))));
    $("#sbSave").addEventListener("click", async () => {
      const btn = $("#sbSave"); btn.disabled = true;
      try {
        const r = await fetch(`/p/${slug}/storyboard/order`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ order: order() }) });
        const j = await r.json();
        if (!j.ok) throw new Error(j.error || "Could not save");
        say("Order saved"); setTimeout(() => location.reload(), 500);
      } catch (err) { say(err.message); btn.disabled = false; }
    });
    refresh();
  }

  /* ------------------------------------------------------------ COMPARE */
  function compare() {
    const box = $("#compare"); if (!box) return;
    const sides = $$(".cmp-side", box).map(s => ({ el: s, pick: $(".cmp-pick", s), video: $("video", s), info: $(".cmp-info", s) }));
    const [A, B] = sides, play = $("#cmpPlay"), seek = $("#cmpSeek"), time = $("#cmpTime"), rate = $("#cmpRate"), audio = $("#cmpAudio");
    const meta = s => JSON.parse(s.pick.selectedOptions[0].dataset.meta || "{}");
    const longest = () => Math.max(A.video.duration || 0, B.video.duration || 0);
    function load(s) {
      const o = s.pick.selectedOptions[0], m = meta(s);
      const t = s.video.currentTime || 0; s.video.src = o.dataset.src; s.video.currentTime = t;
      const when = new Date(m.mtime * 1000).toLocaleString([], { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
      s.info.innerHTML = `<span>${m.width ? `${m.width}×${m.height}` : ""}</span><span>${m.duration ? mmss(m.duration) : ""}</span><span>${(m.size / 1048576).toFixed(1)} MB</span><span>${when}</span>`;
      beats();
    }
    function beats() {
      const tl = [...(meta(A).timeline || [])].sort((a, b) => a.beat - b.beat), tlb = meta(B).timeline || [];
      const el = $("#cmpBeats"); if (!tl.length) { el.innerHTML = ""; return; }
      el.innerHTML = `<span class="meta">Jump to beat</span>` + tl.map(t => `<button type="button" data-beat="${t.beat}">${t.beat}</button>`).join("");
      el.onclick = e => {
        const b = e.target.closest("[data-beat]"); if (!b) return;
        const n = +b.dataset.beat, ta = tl.find(t => t.beat === n), tb = tlb.find(t => t.beat === n) || ta;
        A.video.currentTime = ta.start; B.video.currentTime = tb.start; tick();
      };
    }
    function setAudio() { A.video.muted = audio.value !== "a"; B.video.muted = audio.value !== "b"; }
    function tick() {
      const t = A.video.currentTime || 0, d = longest();
      seek.value = d ? Math.round((t / d) * 1000) : 0; time.textContent = `${mmss(t)} / ${mmss(d)}`;
    }
    let playing = false;
    function setPlaying(on) {
      playing = on; play.innerHTML = on ? "❚❚ Pause both" : "▶ Play both";
      sides.forEach(s => on ? s.video.play().catch(() => {}) : s.video.pause());
    }
    play.addEventListener("click", () => setPlaying(!playing));
    seek.addEventListener("input", () => { const t = (seek.value / 1000) * longest(); sides.forEach(s => s.video.currentTime = Math.min(t, (s.video.duration || t))); tick(); });
    rate.addEventListener("change", () => sides.forEach(s => s.video.playbackRate = +rate.value));
    audio.addEventListener("change", setAudio);
    $("#cmpSwap").addEventListener("click", () => { const a = A.pick.value; A.pick.value = B.pick.value; B.pick.value = a; load(A); load(B); });
    sides.forEach(s => s.pick.addEventListener("change", () => load(s)));
    // keep B on A's clock: small drift is corrected by nudging B's rate, a big one by a jump
    A.video.addEventListener("timeupdate", () => {
      tick();
      if (!playing || B.video.ended) return;
      const drift = B.video.currentTime - A.video.currentTime;
      if (Math.abs(drift) > 0.35) B.video.currentTime = Math.min(A.video.currentTime, B.video.duration || 1e9);
      else B.video.playbackRate = +rate.value * (drift > 0.05 ? 0.96 : drift < -0.05 ? 1.04 : 1);
    });
    A.video.addEventListener("ended", () => { if (B.video.ended || B.video.paused) setPlaying(false); });
    B.video.addEventListener("ended", () => { if (A.video.ended) setPlaying(false); });
    sides.forEach(s => s.video.addEventListener("loadedmetadata", tick));
    load(A); load(B); setAudio(); setPlaying(false);
  }

  /* ------------------------------------------------------------ THUMBNAIL LAB */
  function lab() {
    const box = $("#lab"); if (!box) return;
    const form = $("#labForm"), img = $("#labPreview"), loading = $("#labLoading"), slug = box.dataset.slug;
    let timer = null, seq = 0;
    function params() { const fd = new FormData(form); fd.delete("replace"); return new URLSearchParams(fd); }
    function update() {
      $$(".slider", form).forEach(l => $("output", l).textContent = (+$("input", l).value).toFixed(2).replace(/\.?0+$/, ""));
      clearTimeout(timer);
      timer = setTimeout(() => {
        const p = params(); if (!p.get("source")) return;
        const n = ++seq; loading.classList.add("on");
        const url = `/p/${slug}/thumbs/preview.jpg?${p}`, pre = new Image();
        pre.onload = () => { if (n === seq) { img.src = url; loading.classList.remove("on"); } };
        pre.onerror = () => loading.classList.remove("on");
        pre.src = url;
      }, 220);
    }
    form.addEventListener("input", update); form.addEventListener("change", update);
    // editing a saved variant: load its settings into the form; saving replaces it
    $$(".variant [data-edit]").forEach(b => b.addEventListener("click", () => {
      const v = b.closest(".variant"), s = JSON.parse(v.dataset.settings);
      Object.entries(s).forEach(([k, val]) => {
        const els = $$(`[name="${k}"]`, form);
        els.forEach(el => { if (el.type === "radio") el.checked = el.value === String(val); else el.value = val; });
      });
      $("#labReplace").value = v.dataset.id; $("#labSubmit").textContent = "Update this variant"; $("#labNew").hidden = false;
      form.scrollIntoView({ behavior: calm ? "auto" : "smooth", block: "start" }); update();
    }));
    $("#labNew")?.addEventListener("click", () => { $("#labReplace").value = ""; $("#labSubmit").textContent = "Save as a new variant"; $("#labNew").hidden = true; });
    const grab = $("#grabAt");
    if (grab) {
      const lbl = $("#grabLabel"), sec = $("#grabSeconds");
      const show = () => { lbl.textContent = `${(+grab.value).toFixed(1)} s`; sec.value = grab.value; };
      grab.addEventListener("input", show); show();
    }
    seg($("#variants .seg"), b => $("#variantList").dataset.view = b.dataset.view);
    update();
  }

  /* ------------------------------------------------------------ CHARTS (plain SVG) */
  const NS = "http://www.w3.org/2000/svg";
  const svgEl = (tag, attrs = {}, parent) => { const e = document.createElementNS(NS, tag); Object.entries(attrs).forEach(([k, v]) => e.setAttribute(k, v)); parent && parent.appendChild(e); return e; };
  let tip;
  function showTip(html, x, y) {
    tip = tip || Object.assign(document.body.appendChild(document.createElement("div")), { className: "chart-tip", role: "tooltip" });
    tip.innerHTML = html; tip.hidden = false;
    const r = tip.getBoundingClientRect();
    tip.style.left = Math.min(innerWidth - r.width - 10, Math.max(10, x - r.width / 2)) + "px";
    tip.style.top = Math.max(10, y - r.height - 14) + "px";
  }
  const hideTip = () => tip && (tip.hidden = true);
  function niceMax(v) { if (v <= 0) return 1; const p = Math.pow(10, Math.floor(Math.log10(v))); return Math.ceil(v / p / (v / p > 5 ? 2 : 1)) * p * (v / p > 5 ? 2 : 1); }
  const fmtNum = v => v >= 10000 ? (v / 1000).toFixed(v >= 100000 ? 0 : 1) + "k" : Math.round(v).toLocaleString("en-US");
  function frame(el, h) {
    el.innerHTML = ""; const w = el.clientWidth || 600;
    return { w, h, svg: svgEl("svg", { viewBox: `0 0 ${w} ${h}`, width: w, height: h }, el) };
  }
  function redrawOnResize(el, draw) { let last = el.clientWidth; new ResizeObserver(() => { if (el.clientWidth !== last) { last = el.clientWidth; draw(); } }).observe(el); }

  // vertical-ish bar chart: one bar per item, sorted, hover tooltip
  function bars(el, items, { value, label, color, fmt = fmtNum, tipHtml, onClick, height = 260 }) {
    const draw = () => {
      const { w, h, svg } = frame(el, height), m = { l: 44, r: 8, t: 14, b: 28 };
      const data = items.filter(d => value(d) != null);
      if (!data.length) { el.innerHTML = `<p class="chart-empty">No numbers for this yet.</p>`; return; }
      const max = niceMax(Math.max(...data.map(value))), iw = w - m.l - m.r, ih = h - m.t - m.b;
      const step = iw / data.length, bw = Math.max(3, Math.min(34, step - 2));
      for (let k = 0; k <= 4; k++) {
        const y = m.t + ih - (ih * k) / 4;
        svgEl("line", { x1: m.l, x2: w - m.r, y1: y, y2: y, class: "grid" }, svg);
        svgEl("text", { x: m.l - 8, y: y + 4, class: "axis", "text-anchor": "end" }, svg).textContent = fmt((max * k) / 4);
      }
      data.forEach((d, k) => {
        const v = value(d), bh = Math.max(2, (v / max) * ih), x = m.l + k * step + (step - bw) / 2, y = m.t + ih - bh;
        const g = svgEl("g", { class: "mark", tabindex: 0 }, svg);
        svgEl("rect", { x: m.l + k * step, y: m.t, width: step, height: ih, fill: "transparent", stroke: "none" }, g);   // hit area
        const r = svgEl("path", { d: `M${x},${m.t + ih} V${y + 4} q0,-4 4,-4 h${bw - 8} q4,0 4,4 V${m.t + ih} Z`, fill: color(d) }, g);
        if (!calm) r.animate([{ transform: `translate(0, ${bh}px) scale(1, 0)` }, { transform: "none" }], { duration: 600, delay: k * 18, easing: "cubic-bezier(.22,1,.36,1)", fill: "backwards" });
        const show = () => { const b = r.getBoundingClientRect(); showTip(tipHtml(d), b.left + b.width / 2, b.top); };
        g.addEventListener("pointerenter", show); g.addEventListener("focus", show);
        g.addEventListener("pointerleave", hideTip); g.addEventListener("blur", hideTip);
        if (onClick) g.addEventListener("click", () => onClick(d));
        if (data.length <= 14) svgEl("text", { x: x + bw / 2, y: h - 10, class: "axis", "text-anchor": "middle" }, svg).textContent = label(d, k);
      });
    };
    draw(); redrawOnResize(el, draw);
  }

  function scatter(el, items, { x, y, color, xLabel, yLabel, yMax, tipHtml, onClick, height = 280, xTime = false, refY = null }) {
    const draw = () => {
      const { w, h, svg } = frame(el, height), m = { l: 44, r: 14, t: 26, b: 30 };
      const data = items.filter(d => x(d) != null && y(d) != null);
      if (!data.length) { el.innerHTML = `<p class="chart-empty">Nothing to plot for this filter.</p>`; return; }
      const xs = data.map(x), x0 = xTime ? Math.min(...xs) : 0, x1 = xTime ? Math.max(...xs) : niceMax(Math.max(...xs));
      const span = (x1 - x0) || 1, ymax = yMax || niceMax(Math.max(...data.map(y)));
      const iw = w - m.l - m.r, ih = h - m.t - m.b;
      const px = v => m.l + (xTime ? 16 + ((v - x0) / span) * (iw - 32) : (v / x1) * iw), py = v => m.t + ih - (v / ymax) * ih;
      const steps = ymax === 10 ? 5 : 4;
      for (let k = 0; k <= steps; k++) {
        const v = (ymax * k) / steps, yy = py(v);
        svgEl("line", { x1: m.l, x2: w - m.r, y1: yy, y2: yy, class: "grid" }, svg);
        svgEl("text", { x: m.l - 8, y: yy + 4, class: "axis", "text-anchor": "end" }, svg).textContent = fmtNum(v);
      }
      const sameDay = xTime && span < 2 * 86400;
      const ticks = xTime ? (data.length > 1 ? [x0, x0 + span / 2, x1] : [x0]) : [0, x1 / 2, x1];
      ticks.forEach((t, k) => svgEl("text", { x: px(t), y: h - 8, class: "axis", "text-anchor": ticks.length === 1 ? "middle" : k === 0 ? "start" : k === ticks.length - 1 ? "end" : "middle" }, svg).textContent =
        !xTime ? fmtNum(t) : sameDay ? new Date(t * 1000).toLocaleString([], { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })
          : new Date(t * 1000).toLocaleDateString([], { day: "2-digit", month: "short" }));
      if (!xTime) svgEl("text", { x: w - m.r, y: m.t + ih - 8, class: "axis label", "text-anchor": "end" }, svg).textContent = xLabel + " →";
      svgEl("text", { x: m.l - 36, y: 10, class: "axis label" }, svg).textContent = yLabel;
      if (refY != null) {
        svgEl("line", { x1: m.l, x2: w - m.r, y1: py(refY), y2: py(refY), class: "ref" }, svg);
        svgEl("text", { x: w - m.r, y: py(refY) - 6, class: "axis", "text-anchor": "end" }, svg).textContent = `average ${refY}`;
      }
      if (xTime && data.length > 1) {        // a quiet line through the reviews in time order
        const pts = [...data].sort((a, b) => x(a) - x(b)).map(d => `${px(x(d))},${py(y(d))}`).join(" ");
        svgEl("polyline", { points: pts, class: "trend" }, svg);
      }
      data.forEach((d, k) => {
        const g = svgEl("g", { class: "mark", tabindex: 0 }, svg), cx = px(x(d)), cy = py(y(d));
        svgEl("circle", { cx, cy, r: 14, fill: "transparent", stroke: "none" }, g);
        const c = svgEl("circle", { cx, cy, r: 6, fill: color(d), class: "dot" }, g);
        if (!calm) c.animate([{ opacity: 0, transform: "scale(.2)" }, { opacity: 1, transform: "none" }], { duration: 450, delay: 80 + k * 40, easing: "cubic-bezier(.34,1.56,.64,1)", fill: "backwards" });
        const show = () => { const b = c.getBoundingClientRect(); showTip(tipHtml(d), b.left + b.width / 2, b.top); };
        g.addEventListener("pointerenter", show); g.addEventListener("focus", show);
        g.addEventListener("pointerleave", hideTip); g.addEventListener("blur", hideTip);
        if (onClick) { g.style.cursor = "pointer"; g.addEventListener("click", () => onClick(d)); g.addEventListener("keydown", e => e.key === "Enter" && onClick(d)); }
      });
    };
    draw(); redrawOnResize(el, draw);
  }

  // horizontal stacked bars: categories x severities
  function stacked(el, rows, keys, colors) {
    const draw = () => {
      el.innerHTML = "";
      if (!rows.length) { el.innerHTML = `<p class="chart-empty">No issues found in the reviews.</p>`; return; }
      const max = Math.max(...rows.map(r => keys.reduce((s, k) => s + r.v[k], 0)));
      rows.forEach((r, i) => {
        const row = Object.assign(document.createElement("div"), { className: "hbar" });
        row.innerHTML = `<span class="hbar-label">${esc(r.name)}</span><span class="hbar-track"></span><span class="hbar-total">${keys.reduce((s, k) => s + r.v[k], 0)}</span>`;
        const track = $(".hbar-track", row);
        keys.forEach(k => {
          if (!r.v[k]) return;
          const seg = Object.assign(document.createElement("i"), { className: `sev-${k}` });
          seg.style.width = (r.v[k] / max) * 100 + "%"; seg.style.background = colors[k]; seg.tabIndex = 0;
          if (!calm) seg.animate([{ transform: "scaleX(0)" }, { transform: "none" }], { duration: 600, delay: i * 50, easing: "cubic-bezier(.22,1,.36,1)", fill: "backwards" });
          const show = () => { const b = seg.getBoundingClientRect(); showTip(`<b>${esc(r.name)}</b><br>${r.v[k]} ${k} severity`, b.left + b.width / 2, b.top); };
          seg.addEventListener("pointerenter", show); seg.addEventListener("focus", show); seg.addEventListener("pointerleave", hideTip); seg.addEventListener("blur", hideTip);
          track.appendChild(seg);
        });
        el.appendChild(row);
      });
    };
    draw();
  }

  /* ------------------------------------------------------------ QUALITY page */
  function qualityPage() {
    const dataEl = $("#qdata"); if (!dataEl) return;
    const data = JSON.parse(dataEl.textContent), el = $("#qScore");
    const draw = f => scatter(el, data.points.filter(p => f === "all" || p.fmt === f), {
      x: p => p.t, y: p => p.score, xTime: true, yMax: 10, refY: data.avg, xLabel: "review date", yLabel: "score /10",
      color: p => p.fmt === "short" ? css("--chart-short") : css("--chart-long"),
      tipHtml: p => `<b>${esc(p.title)}</b><br>${p.score}/10 · ${p.issues} issue${p.issues === 1 ? "" : "s"}${p.high ? ` (${p.high} high)` : ""}<br><span>${esc(p.date)} · ${p.fmt === "short" ? "Short" : "Long"}</span>`,
      onClick: p => location.href = `/p/${p.slug}`,
    });
    draw("all"); seg($("#qFilter"), b => draw(b.dataset.f));
    const rows = Object.entries(data.by_category).map(([name, v]) => ({ name, v })).sort((a, b) => (b.v.high * 3 + b.v.medium * 2 + b.v.low) - (a.v.high * 3 + a.v.medium * 2 + a.v.low));
    stacked($("#qIssues"), rows, ["high", "medium", "low"], { high: css("--sev-high"), medium: css("--sev-medium"), low: css("--sev-low") });
  }

  /* ------------------------------------------------------------ STATS page */
  function statsPage() {
    const dataEl = $("#adata"); if (!dataEl) return;
    const rows = JSON.parse(dataEl.textContent);
    const names = { views: "views", viewed: "% viewed", avg_view: "s average view", likes: "likes", engaged: "engaged views", subs: "subscribers gained" };
    let type = "all", metric = "views";
    const color = d => d.type === "short" ? css("--chart-short") : css("--chart-long");
    const tip = d => `<b>${esc(d.title)}</b><br>${d.views != null ? fmtNum(d.views) + " views" : "views —"} · ${d.viewed != null ? d.viewed + "% viewed" : "% viewed —"}<br>`
      + `<span>${d.type === "short" ? "Short" : "Long"} · ${esc(d.published)} · ${esc(d.status)}</span>`;
    function draw() {
      const sel = rows.filter(r => type === "all" || r.type === type);
      const sorted = [...sel].filter(r => r[metric] != null).sort((a, b) => b[metric] - a[metric]);
      bars($("#aBars"), sorted, { value: d => d[metric], label: (d, k) => k + 1, color, tipHtml: d => tip(d) + `<b>${fmtNum(d[metric])}</b> ${names[metric]}`,
        fmt: metric === "viewed" ? v => Math.round(v) + "%" : fmtNum });
      scatter($("#aScatter"), sel, { x: d => d.views, y: d => d.viewed, color, xLabel: "views", yLabel: "% viewed", tipHtml: tip });
    }
    seg($("#aType"), b => { type = b.dataset.f; draw(); });
    $("#aMetric").addEventListener("change", e => { metric = e.target.value; draw(); });
    draw();
  }

  const init = () => { storyboard(); compare(); lab(); qualityPage(); statsPage(); };
  document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", init) : init();
})();
