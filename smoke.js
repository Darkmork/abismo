#!/usr/bin/env node
/**
 * smoke.js · test de humo del cliente.
 *
 * Corre el app.js REAL contra un DOM mínimo simulado y juega una partida
 * completa. Es la red de seguridad: si el scoring o la máquina de estados se
 * rompen, esto falla (no hace falta abrir el navegador).
 *
 *     node smoke.js
 */
const fs = require("fs");
const path = require("path");
const vm = require("vm");

const WEB = path.join(__dirname, "web");

/* ── DOM mínimo ─────────────────────────────────────────── */
class El {
  constructor(id, tag = "div") {
    this.id = id;
    this.tag = tag;
    this._html = "";
    this.textContent = "";
    this.value = "";
    this.disabled = false;
    this.style = {};
    this.classList = {
      _s: new Set(),
      add(c) { this._s.add(c); },
      remove(c) { this._s.delete(c); },
      contains(c) { return this._s.has(c); },
    };
    this._ls = {};
  }
  set innerHTML(v) {
    this._html = String(v);
    // el <select> toma el valor de la opción marcada "selected" (o la primera)
    const opts = [...String(v).matchAll(/<option value="([^"]+)"([^>]*)>/g)];
    const sel = opts.find((o) => /selected/.test(o[2]));
    const chosen = sel || opts[0];
    if (chosen) this.value = chosen[1];
  }
  get innerHTML() { return this._html; }
  addEventListener(ev, fn) { (this._ls[ev] = this._ls[ev] || []).push(fn); }
  insertAdjacentHTML(_pos, html) { this._html += html; }
  focus() {}
  fire(ev, arg) {
    (this._ls[ev] || []).forEach((f) => f(arg || { preventDefault() {} }));
    const handler = this["on" + ev];
    if (typeof handler === "function") handler(arg || { preventDefault() {} });
  }
}

const els = {};
function el(id, tag) {
  if (!els[id]) els[id] = new El(id, tag);
  return els[id];
}
["answer-form", "answer-input", "btn-answer", "btn-start", "btn-copy", "btn-home",
 "sel-day", "feedback", "breakdown", "gems", "end-depth", "end-pts", "end-date",
 "end-best", "depth-now", "zone-now", "pts-now", "diver", "round-label",
 "strat-label", "timer-label", "timer-fill", "prompt-text", "hint", "tierlist",
 "stratalist", "abyss-marks", "best-line"].forEach((id) => el(id));

const screens = [new El("scr-intro"), new El("scr-game"), new El("scr-end")];
screens.forEach((s) => { els[s.id] = s; });   // misma instancia que getElementById
screens[0].classList.add("is-active");

const doc = {
  getElementById: (id) => els[id] || null,
  querySelectorAll: () => screens,
};
const store = {};
const localStorage = {
  getItem: (k) => (k in store ? store[k] : null),
  setItem: (k, v) => { store[k] = String(v); },
};

/* ── timers encolados (para avanzar de ronda a demanda) ──── */
const timers = [];
const sandbox = {
  window: { ABISMO: undefined, scrollTo() {} },
  document: doc,
  localStorage,
  location: { hash: "" },
  navigator: { clipboard: { writeText: async () => {} } },
  alert: (m) => { throw new Error("alert inesperado: " + m); },
  setInterval: () => 0,                 // el timer de 25 s no corre en el test
  clearInterval: () => {},
  setTimeout: (fn) => { timers.push(fn); return timers.length; },
  clearTimeout: () => {},
  console,
};
sandbox.globalThis = sandbox;
vm.createContext(sandbox);

function flush() {
  let guard = 0;
  while (timers.length && guard++ < 50) timers.shift()();
}

/* ── carga ───────────────────────────────────────────────── */
vm.runInContext(fs.readFileSync(path.join(WEB, "data", "daily.js"), "utf8"), sandbox);
if (!sandbox.window.ABISMO) throw new Error("daily.js no define window.ABISMO");
vm.runInContext(fs.readFileSync(path.join(WEB, "app.js"), "utf8"), sandbox);

/* ── asserts ─────────────────────────────────────────────── */
let fails = 0;
function check(name, cond, extra) {
  const ok = !!cond;
  if (!ok) fails++;
  console.log(`  ${ok ? "✓" : "✗"} ${name}${extra !== undefined && extra !== "" ? "  → " + extra : ""}`);
}
const plain = (h) => h.replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();

console.log("\nabismo · smoke test\n");

/* ── la tabla ────────────────────────────────────────────── */
const days = Object.keys(sandbox.window.ABISMO.days).sort();
check("hay dailies en la tabla", days.length > 0, `${days.length} días`);
check("la tabla tiene 14 días", days.length === 14, days.length + " días");

const today = days[0];
const prompts = sandbox.window.ABISMO.days[today].prompts;
check("cada dive tiene 7 prompts", prompts.length === 7, prompts.length + "");

let denseCount = 0;
Object.values(sandbox.window.ABISMO.days).forEach((d) =>
  d.prompts.forEach((p) => { if (p.kind === "dense") denseCount++; }));
check("hay familias densas en la tabla", denseCount > 0, denseCount + " prompts densos");

/* ── arrancar el dive ────────────────────────────────────── */
el("sel-day").value = today;
el("sel-day").fire("change");     // la app escucha el change, no el value
el("btn-start").fire("click");
flush();
check("el dive arranca", screens[1].classList.contains("is-active"));
check("la lista de tiers se pintó", el("tierlist").innerHTML.includes("Legendario"));
check("las marcas de profundidad se pintaron", el("abyss-marks").innerHTML.includes("m"));

/* ── jugar: ronda 1 con la gema ──────────────────────────── */
const p0 = prompts[0];
el("answer-input").value = String(p0.gem);
el("btn-answer").fire("click");
let fb = el("feedback").innerHTML;
const t0 = p0.answers ? p0.answers[String(p0.gem)] : null;
check("la gema da feedback", /pts/.test(fb), plain(fb).slice(0, 60));
check("el tier se muestra", /Común|Curioso|Raro|Profundo|Abisal|Legendario/.test(fb),
      t0 ? t0[0] : "?");
check("el tier es el esperado", t0 && fb.includes(t0[0]), t0 ? t0[0] : "familia densa");
check("el depth sube", el("depth-now").textContent !== "0m", el("depth-now").textContent);
flush();

/* ── ronda 2: respuesta inválida ─────────────────────────── */
el("answer-input").value = "999999999";
el("btn-answer").fire("click");
fb = el("feedback").innerHTML;
check("una respuesta inválida no suma", /no válida|0 pts/.test(fb), plain(fb).slice(0, 50));
flush();

/* ── ronda 3: texto ──────────────────────────────────────── */
el("answer-input").value = "hola";
el("btn-answer").fire("click");
fb = el("feedback").innerHTML;
check("texto no numérico no suma", /no es un número|0 pts/.test(fb), plain(fb).slice(0, 50));
flush();

/* ── rondas 4 a 7 con las gemas ──────────────────────────── */
let expected = t0 ? t0[1] : 0;
for (let i = 3; i < prompts.length; i++) {
  const p = prompts[i];
  el("answer-input").value = String(p.gem);
  el("btn-answer").fire("click");
  const t = p.answers ? p.answers[String(p.gem)] : null;
  if (t) expected += t[1];
  flush();
}

check("la pantalla final aparece", screens[2].classList.contains("is-active"));
const endPts = parseInt(el("end-pts").textContent, 10);
check("el total de puntos cuadra", endPts === expected, `${endPts} vs esperado ${expected}`);
const endDepth = parseInt(el("end-depth").textContent.replace(/\./g, ""), 10);
check("la profundidad final cuadra", endDepth === expected * 10, `${endDepth} vs ${expected * 10}`);
check("el desglose tiene 7 filas", (el("breakdown").innerHTML.match(/<li>/g) || []).length === 7);
check("se revelan las gemas", /gema/i.test(el("gems").innerHTML));
check("se guarda el récord local", !!localStorage.getItem("abismo.best." + today),
      localStorage.getItem("abismo.best." + today));

/* ── la familia densa (Legendre): se valida en el cliente ─── */
console.log("");
const denseDay = days.find((d) =>
  sandbox.window.ABISMO.days[d].prompts.some((p) => p.kind === "dense"));
check("existe un día con familia densa", !!denseDay, denseDay || "ninguno");

if (denseDay) {
  const dp = sandbox.window.ABISMO.days[denseDay].prompts.find((p) => p.kind === "dense");
  el("sel-day").value = denseDay;
  el("sel-day").fire("change");
  el("btn-start").fire("click");
  flush();
  el("answer-input").value = "7";   // 7 = 8·0+7 → NO es suma de tres cuadrados
  el("btn-answer").fire("click");
  fb = el("feedback").innerHTML;
  check("la familia densa acepta un número válido",
        /pts/.test(fb) && !/no válida/.test(fb),
        plain(fb).slice(0, 60) + " | prompt: " + plain(el("prompt-text").textContent).slice(0, 40));
  flush();
  el("answer-input").value = "8";   // 8 sí es suma de tres cuadrados → inválido
  el("btn-answer").fire("click");
  fb = el("feedback").innerHTML;
  check("la familia densa rechaza lo que no cumple",
        /no válida|0 pts/.test(fb), plain(fb).slice(0, 50));
}

console.log(`\n${fails === 0 ? "✓ todo ok" : "✗ " + fails + " fallo(s)"}\n`);
process.exit(fails === 0 ? 0 : 1);
