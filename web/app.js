/* ─────────────────────────────────────────────────────────────
   Abismo · el descenso diario — lógica del juego
   Todo corre en el cliente: sin backend, sin red (salvo la fuente).
   ───────────────────────────────────────────────────────────── */
(function () {
  "use strict";

  const DATA = window.ABISMO;
  const ROUND_SECONDS = 25;
  const M_PER_PT = 10;
  const MAX_DEPTH = 7000;

  const TIERS = [
    ["Común", 10, 0.66, "⬜"],
    ["Curioso", 15, 0.54, "🟩"],
    ["Raro", 30, 0.42, "🟦"],
    ["Profundo", 60, 0.30, "🟪"],
    ["Abisal", 85, 0.20, "🟥"],
    ["Legendario", 100, 0.00, "🟨"],
  ];

  const STRATA = [
    ["Aritmética", 0, 400, "#2c3c5c"],
    ["Recurrencias", 400, 1200, "#123b4d"],
    ["Aritmética profunda", 1200, 3000, "#1a2154"],
    ["Teoría de números", 3000, 7000, "#2a1139"],
  ];

  const $ = (id) => document.getElementById(id);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));

  /* ── estado ─────────────────────────────────────────────── */
  let dayKey = null;
  let prompts = [];
  let idx = 0;
  let points = 0;
  let depth = 0;
  let log = [];
  let timerId = null;
  let deadline = 0;
  let locked = false;

  /* ── utilidades ─────────────────────────────────────────── */
  const pad = (n) => String(n).padStart(2, "0");
  const todayKey = () => {
    const d = new Date();
    return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
  };

  function zoneFor(m) {
    for (const s of STRATA) if (m < s[2]) return s[0];
    return STRATA[STRATA.length - 1][0];
  }

  // Misma fórmula que el motor Python (familias densas).
  function structuralFame(n, maxv) {
    const s = String(n);
    let g = 0;
    if (n % 1000 === 0) g += 0.30;
    else if (n % 100 === 0) g += 0.20;
    else if (n % 10 === 0) g += 0.09;
    if (s === s.split("").reverse().join("")) g += 0.14;
    if (new Set(s).size === 1) g += 0.16;
    if (n < 100) g += 0.22;
    else if (n < 1000) g += 0.10;
    g += 0.30 * (1 - Math.log10(Math.max(n, 2)) / Math.log10(maxv + 1));
    return Math.min(g, 1);
  }

  function tierFor(g) {
    for (const t of TIERS) if (g >= t[2]) return [t[0], t[1]];
    return ["Legendario", 100];
  }

  // Legendre: n no es suma de tres cuadrados <=> n = 4^a (8b+7)
  function isDenseValid(n, maxv) {
    if (n <= 0 || n >= maxv) return false;
    let m = n;
    while (m % 4 === 0) m /= 4;
    return m % 8 === 7;
  }

  function scoreAnswer(p, n) {
    if (p.kind === "dense") {
      if (!isDenseValid(n, p.maxv)) return null;
      const t = tierFor(structuralFame(n, p.maxv));
      return { tier: t[0], pts: t[1] };
    }
    const hit = p.answers[String(n)];
    if (!hit) return null;
    return { tier: hit[0], pts: hit[1] };
  }

  /* ── pantallas ──────────────────────────────────────────── */
  function show(id) {
    $$(".screen").forEach((s) => s.classList.remove("is-active"));
    $(id).classList.add("is-active");
    window.scrollTo({ top: 0, behavior: "instant" });
  }

  /* ── intro ──────────────────────────────────────────────── */
  function buildIntro() {
    $("abyss-marks").innerHTML = STRATA.map(
      (s) => `<span style="top:${(s[1] / MAX_DEPTH) * 100}%">${s[1]} m</span>`
    ).join("");

    $("tierlist").innerHTML = TIERS.map(
      (t) => `<li><span class="n t-${t[0]}">${t[0]}</span><span class="p">${t[1]} pts · ${t[1] * M_PER_PT} m</span></li>`
    ).join("");

    $("stratalist").innerHTML = STRATA.map(
      (s) => `<li><i style="background:${s[3]}"></i>${s[0]}<b>${s[1]}–${s[2]} m</b></li>`
    ).join("");

    const sel = $("sel-day");
    const keys = Object.keys(DATA.days).sort().reverse();
    sel.innerHTML = keys.map((k) => {
      const sel0 = k === todayKey() ? " selected" : "";
      return `<option value="${k}"${sel0}>${formatDate(k)}</option>`;
    }).join("");
    if (!keys.includes(todayKey())) {
      sel.insertAdjacentHTML("afterbegin",
        `<option value="${todayKey()}" selected>${formatDate(todayKey())} — hoy</option>`);
    }

    sel.onchange = () => { dayKey = sel.value; paintBest(); };
    dayKey = sel.value;

    $("btn-start").onclick = () => startRun(dayKey);
    paintBest();
  }

  function formatDate(k) {
    const [y, m, d] = k.split("-");
    return `${d}/${m}/${y}`;
  }

  function paintBest() {
    const best = localStorage.getItem("abismo.best." + dayKey);
    const runs = localStorage.getItem("abismo.runs") || 0;
    $("best-line").textContent = best
      ? `tu mejor marca en este dive: ${best} pts · ${runs} descenso(s) en total`
      : `todavía no te has sumergido en este dive · ${runs} descenso(s) en total`;
  }

  /* ── partida ────────────────────────────────────────────── */
  function startRun(key) {
    const day = DATA.days[key];
    if (!day) { alert("No hay dive para esa fecha todavía."); return; }
    prompts = day.prompts;
    idx = 0; points = 0; depth = 0; log = [];
    $("feedback").innerHTML = "";
    $("end-best").textContent = "";
    show("scr-game");
    paintDepth();
    renderRound();
  }

  function renderRound() {
    const p = prompts[idx];
    locked = false;
    $("round-label").textContent = `pregunta ${idx + 1} / ${prompts.length}`;
    $("strat-label").textContent = p.stratum;
    $("prompt-text").textContent = p.text;
    $("feedback").innerHTML = "";
    $("hint").textContent = p.count
      ? `${p.count.toLocaleString("es-CL")} respuestas válidas para esta pregunta`
      : "conjunto de respuestas válido muy grande";
    const inp = $("answer-input");
    inp.value = "";
    inp.disabled = false;
    inp.focus();
    startTimer();
  }

  function startTimer() {
    clearInterval(timerId);
    deadline = Date.now() + ROUND_SECONDS * 1000;
    const tick = () => {
      const left = Math.max(0, deadline - Date.now()) / 1000;
      $("timer-label").textContent = left.toFixed(left < 3 ? 1 : 0);
      $("timer-fill").style.transform = `scaleX(${left / ROUND_SECONDS})`;
      if (left <= 0) { clearInterval(timerId); submit(true); }
    };
    tick();
    timerId = setInterval(tick, 100);
  }

  function submit(timedOut) {
    if (locked) return;
    locked = true;
    clearInterval(timerId);
    $("answer-input").disabled = true;

    const p = prompts[idx];
    const raw = $("answer-input").value.trim();
    const fb = $("feedback");

    if (timedOut || !raw) {
      fb.innerHTML = `<div class="fb fb--miss"><span class="tier">⏱ tiempo</span>
        <span class="pts">0 pts</span><span class="why">se acabó el tiempo: 0 puntos, el descenso sigue</span></div>`;
      log.push({ p, ans: null, tier: null, pts: 0 });
      return advance();
    }
    if (!/^-?\d+$/.test(raw)) {
      fb.innerHTML = `<div class="fb fb--miss"><span class="tier">✗</span>
        <span class="pts">0 pts</span><span class="why">eso no es un número entero</span></div>`;
      log.push({ p, ans: raw, tier: null, pts: 0 });
      return advance();
    }

    const n = parseInt(raw, 10);
    const hit = scoreAnswer(p, n);
    if (!hit) {
      fb.innerHTML = `<div class="fb fb--miss"><span class="tier">✗ no válida</span>
        <span class="pts">0 pts</span><span class="why">ese número no cumple la condición del prompt</span></div>`;
      log.push({ p, ans: n, tier: null, pts: 0 });
      return advance();
    }

    points += hit.pts;
    depth = Math.min(MAX_DEPTH, points * M_PER_PT);
    const same = String(n) === String(p.gem);
    fb.innerHTML = `<div class="fb fb--ok">
        <span class="tier t-${hit.tier}">${hit.tier}</span>
        <span class="pts">+${hit.pts} pts · +${hit.pts * M_PER_PT} m</span>
        <span class="why">${same ? "esa era la gema: la respuesta más rara de todas"
          : `la gema de esta pregunta era <b>${p.gem}</b>`}</span>
      </div>`;
    log.push({ p, ans: n, tier: hit.tier, pts: hit.pts });
    paintDepth();
    advance();
  }

  function advance() {
    setTimeout(() => {
      if (idx + 1 < prompts.length) { idx++; renderRound(); }
      else finish();
    }, 1500);
  }

  function paintDepth() {
    $("depth-now").innerHTML = `${depth.toLocaleString("es-CL")}<small>m</small>`;
    $("zone-now").textContent = depth === 0 ? "superficie" : zoneFor(depth);
    $("pts-now").textContent = `${points} pts`;
    const pct = Math.min(100, (depth / MAX_DEPTH) * 100);
    $("diver").style.top = pct + "%";
  }

  /* ── resultado ──────────────────────────────────────────── */
  function finish() {
    const key = dayKey;
    const best = parseInt(localStorage.getItem("abismo.best." + key) || "0", 10);
    const isBest = points > best;
    if (isBest) localStorage.setItem("abismo.best." + key, String(points));
    localStorage.setItem("abismo.runs", String(parseInt(localStorage.getItem("abismo.runs") || "0", 10) + 1));

    $("end-date").textContent = `abismo · ${formatDate(key)}`;
    $("end-depth").textContent = depth.toLocaleString("es-CL");
    $("end-pts").textContent = `${points} puntos`;

    $("breakdown").innerHTML = log.map((l) => {
      const tier = l.tier ? `<span class="t-${l.tier}">${l.tier}</span>` : "—";
      const ans = l.ans === null ? "sin respuesta" : l.ans;
      return `<li><span class="q">${l.p.text}</span><span class="a">${ans}</span>${tier}
        <span class="p">${l.pts} pts</span></li>`;
    }).join("");

    const gemas = prompts.map((p) => `<li><span>${p.text.replace(/^Un número/, "")}</span> <b>${p.gem}</b></li>`).join("");
    $("gems").innerHTML = `<h3>las gemas del día</h3><ul>${gemas}</ul>`;

    $("end-best").textContent = isBest
      ? `nuevo récord en este dive: ${points} pts`
      : `tu mejor en este dive: ${best} pts`;

    $("btn-copy").onclick = copyResult;
    $("btn-home").onclick = () => { paintBest(); show("scr-intro"); };
    show("scr-end");
  }

  function copyResult() {
    const emoji = log.map((l) => {
      const t = TIERS.find((x) => x[0] === l.tier);
      return t ? t[3] : "⬛";
    }).join("");
    const txt = `Abismo · ${formatDate(dayKey)}\n${emoji}\n${points} pts · ${depth.toLocaleString("es-CL")} m`;
    navigator.clipboard?.writeText(txt).then(
      () => { $("btn-copy").textContent = "✓ copiado"; setTimeout(() => ($("btn-copy").textContent = "Copiar resultado"), 1600); },
      () => { $("btn-copy").textContent = "no se pudo copiar"; }
    );
  }

  /* ── arranque ───────────────────────────────────────────── */
  // Nada de submit nativo: el form no navega nunca.
  $("answer-form").addEventListener("submit", (e) => { e.preventDefault(); });
  $("btn-answer").addEventListener("click", () => submit(false));
  $("answer-input").addEventListener("keydown", (e) => {
    if (e.key === "Enter") { e.preventDefault(); submit(false); }
  });

  if (!DATA || !DATA.days) {
    document.getElementById("app").innerHTML =
      `<div style="max-width:560px;margin:14vh auto;padding:0 22px;font-family:system-ui;color:#c6d0e6">
         <h1 style="color:#ff5c8a">Falta la tabla de dives</h1>
         <p>Corre <code style="font-family:monospace">python3 precompute.py --days 14</code>
         en la carpeta del proyecto y recarga la página.</p></div>`;
    return;
  }
  buildIntro();
  if (location.hash === "#auto") startRun(dayKey);
})();
