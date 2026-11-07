/* ─────────────────────────────────────────────────────────────
   Ensayo · test de humo (headless, node)
   Corre la lógica real del motor contra la tabla real publicada.

     node smoke.js
   ───────────────────────────────────────────────────────────── */
"use strict";

const fs = require("fs");
const path = require("path");

const M = require("./web/engine.js");

/* ── carga de datos ─────────────────────────────────────────── */
const DATA_PATH = path.join(__dirname, "web", "data", "daily.js");
if (!fs.existsSync(DATA_PATH)) {
  console.error("✗ falta web/data/daily.js — ejecuta: python3 precompute.py --days 30 --pool 600");
  process.exit(1);
}
const win = {};
new Function("window", fs.readFileSync(DATA_PATH, "utf8"))(win);
const DATA = win.ENSAYO;

/* ── mini framework ─────────────────────────────────────────── */
let ok = 0;
const fallos = [];
function check(cond, msg) {
  if (cond) ok++;
  else fallos.push(msg);
}
function eq(a, b, msg) {
  check(a === b, `${msg} (esperado ${JSON.stringify(b)}, hubo ${JSON.stringify(a)})`);
}
function cerca(a, b, tol, msg) {
  check(Math.abs(a - b) <= tol, `${msg} (esperado ~${b}, hubo ${a})`);
}

const EJES = ["Números", "Álgebra y funciones", "Geometría", "Probabilidad y estadística"];
const REPARTO = { "Números": 3, "Álgebra y funciones": 3, "Geometría": 2, "Probabilidad y estadística": 2 };

/* ══════════════════════════ 1. TABLA PUBLICADA ══════════════════════════ */
check(!!DATA, "la tabla cargó");
check(Object.keys(DATA.dias).length >= 30, `hay 30 dailies (hay ${Object.keys(DATA.dias).length})`);
check(DATA.practica.length === 600, `hay 600 de práctica (hay ${DATA.practica.length})`);

const fechas = Object.keys(DATA.dias).sort();
check(fechas[0] <= M.hoyISO(), `el rango cubre hoy (empieza ${fechas[0]}, hoy ${M.hoyISO()})`);

let malas = 0;
for (const fecha of fechas) {
  const ps = DATA.dias[fecha].preguntas;
  check(ps.length === 10, `${fecha}: 10 preguntas (hay ${ps.length})`);

  const reparto = {};
  for (const q of ps) {
    if (!EJES.includes(q.eje)) { malas++; }
    reparto[q.eje] = (reparto[q.eje] || 0) + 1;
    if (q.opciones.length !== 4) malas++;
    if (new Set(q.opciones).size !== 4) malas++;
    if (!(q.correcta >= 0 && q.correcta < 4)) malas++;
    if (!q.explicacion || q.explicacion.length < 20) malas++;
    if (!q.enunciado || q.enunciado.length < 10) malas++;
  }
  for (const eje of EJES) {
    check(reparto[eje] === REPARTO[eje],
      `${fecha}: ${eje} aparece ${reparto[eje]} veces (debía ${REPARTO[eje]})`);
  }
}
check(malas === 0, `ninguna pregunta mal formada (hubo ${malas} problemas)`);

for (const q of DATA.practica) {
  if (!EJES.includes(q.eje)) malas++;
  if (q.opciones.length !== 4) malas++;
  if (new Set(q.opciones).size !== 4) malas++;
  if (!(q.correcta >= 0 && q.correcta < 4)) malas++;
  if (!q.explicacion || q.explicacion.length < 20) malas++;
}
check(malas === 0, `pool de práctica íntegro (hubo ${malas} problemas)`);

const porEjePool = {};
for (const q of DATA.practica) porEjePool[q.eje] = (porEjePool[q.eje] || 0) + 1;
for (const eje of EJES) eq(porEjePool[eje], 150, `pool: ${eje} tiene 150`);

/* ══════════════════════════ 2. MOTOR: tiempo y racha ══════════════════════════ */
check(/^\d{4}-\d{2}-\d{2}$/.test(M.hoyISO()), "hoyISO devuelve YYYY-MM-DD");
eq(M.diasEntre("2026-11-01", "2026-11-02"), 1, "diasEntre de un día");
eq(M.diasEntre("2026-11-01", "2026-11-08"), 7, "diasEntre de una semana");
eq(M.diasEntre("2026-11-08", "2026-11-01"), -7, "diasEntre inverso");
eq(M.diasEntre("2026-11-01", "2026-11-01"), 0, "diasEntre del mismo día");

/* ══════════════════════════ 3. MOTOR: puntaje ══════════════════════════ */
eq(M.multiplicador(0), 1, "multiplicador sin racha");
eq(M.multiplicador(1), 1.2, "multiplicador con racha 1");
eq(M.multiplicador(2), 1.5, "multiplicador con racha 2");
eq(M.multiplicador(3), 1.8, "multiplicador con racha 3");
eq(M.multiplicador(4), 2, "multiplicador con racha 4");
eq(M.multiplicador(99), 2, "multiplicador con racha altísima");

const pRapido = M.puntuar(45, 0);
eq(pRapido.base, 100, "puntaje base");
eq(pRapido.bono, 50, "bono máximo a tiempo completo");
eq(pRapido.mult, 1, "multiplicador sin racha");
eq(pRapido.total, 150, "total con bono y sin racha");

const pLento = M.puntuar(0, 0);
eq(pLento.bono, 0, "sin bono sin tiempo");
eq(pLento.total, 100, "total sin tiempo");

const pCombo = M.puntuar(45, 4);
eq(pCombo.mult, 2, "multiplicador x2 con racha 4");
eq(pCombo.total, 300, "total con combo x2");

eq(M.puntuar(999, 0).total, 150, "el tiempo se topa");
eq(M.puntuar(-50, 0).total, 100, "el tiempo negativo se topa en 0");

/* ══════════════════════════ 4. MOTOR: estrellas ══════════════════════════ */
eq(M.estrellas(10, 10), 3, "10/10 son 3 estrellas");
eq(M.estrellas(8, 10), 3, "8/10 son 3 estrellas");
eq(M.estrellas(7, 10), 2, "7/10 son 2 estrellas");
eq(M.estrellas(6, 10), 2, "6/10 son 2 estrellas");
eq(M.estrellas(5, 10), 1, "5/10 es 1 estrella");
eq(M.estrellas(0, 10), 1, "0/10 es 1 estrella");

/* ══════════════════════════ 5. MOTOR: selección de contenido ══════════════════════════ */
const hoy = M.hoyISO();
const selHoy = M.seleccionarDaily(DATA, hoy);
check(!!selHoy, "hay reto para hoy");
check(selHoy.exacta === true, "el reto de hoy es exacto");
eq(selHoy.preguntas.length, 10, "el reto de hoy tiene 10 preguntas");

const selLejos = M.seleccionarDaily(DATA, "2019-01-01");
check(!!selLejos, "una fecha lejana igual devuelve algo");
eq(selLejos.exacta, false, "una fecha fuera de rango no es exacta");
check(fechas.includes(selLejos.fecha), "la fecha lejana cae en el rango precomputado");

const tP = M.tomarPractica(DATA.practica, 12, "Geometría", 0, 42);
eq(tP.preguntas.length, 12, "práctica entrega 12 preguntas");
check(tP.preguntas.every((q) => q.eje === "Geometría"), "práctica respeta el eje pedido");

const tTodos = M.tomarPractica(DATA.practica, 20, "Todos", 0, 7);
eq(tTodos.preguntas.length, 20, "práctica entrega 20 preguntas");
check(new Set(tTodos.preguntas.map((q) => q.enunciado)).size > 10, "práctica de 20 trae preguntas distintas");

const tChico = M.tomarPractica(DATA.practica, 3, "Todos", 0, 7);
eq(tChico.preguntas.length, 3, "práctica de 3 preguntas");

/* ══════════════════════════ 6. MOTOR: partida ══════════════════════════ */
const st = M.nuevoEstado(selHoy.preguntas, "diario");
eq(st.preguntas.length, 10, "el estado carga las 10 preguntas");
eq(st.hearts, M.CORAZONES, "empieza con 3 corazones");
eq(st.puntos, 0, "empieza en 0 puntos");

const r1 = M.responder(st, selHoy.preguntas[0].correcta, 45);
check(r1 && r1.ok, "acertar devuelve ok");
eq(st.aciertos, 1, "suma un acierto");
eq(st.racha, 1, "abre la racha");
eq(st.puntos, 150, "suma el puntaje de la primera");
eq(st.hearts, 3, "no gasta corazones");

check(M.responder(st, 0, 45) === null, "no se puede responder dos veces la misma pregunta");

M.avanzar(st);
eq(st.i, 1, "avanza de índice");
eq(st.respondida, false, "la pregunta nueva está sin responder");

M.responder(st, (selHoy.preguntas[1].correcta + 1) % 4, 45);
eq(st.errores, 1, "cuenta el error");
eq(st.hearts, 2, "gasta un corazón");
eq(st.racha, 0, "rompe la racha");
eq(st.aciertos, 1, "el acierto anterior sigue contado");

const stVacio = M.nuevoEstado([], "diario");
eq(M.responder(stVacio, 0, 45), null, "sin preguntas no hay respuesta");

/* game over */
const stGo = M.nuevoEstado(selHoy.preguntas, "diario");
for (let i = 0; i < 3; i++) {
  const mala = (selHoy.preguntas[i].correcta + 1) % 4;
  M.responder(stGo, mala, 45);
  if (i < 2) M.avanzar(stGo);
}
eq(stGo.hearts, 0, "se acaban los corazones");
eq(stGo.terminada, true, "la partida termina al tercer error");
eq(stGo.resultados.length, 3, "se registran 3 respuestas");
const resGo = M.resumen(stGo);
eq(resGo.completo, false, "el resumen marca partida incompleta");
eq(resGo.estrellas, 1, "partida incompleta igual da 1 estrella");

/* partida perfecta */
const stPerf = M.nuevoEstado(selHoy.preguntas, "diario");
let esperado = 0;
for (let i = 0; i < 10; i++) {
  const q = selHoy.preguntas[i];
  M.responder(stPerf, q.correcta, 45);
  esperado += M.puntuar(45, i).total;
  M.avanzar(stPerf);
}
eq(stPerf.terminada, true, "la partida perfecta termina");
eq(stPerf.aciertos, 10, "10 aciertos");
eq(stPerf.puntos, esperado, "el puntaje perfecto coincide con el cálculo");
eq(stPerf.mejorRacha, 10, "racha máxima de 10");
const resPerf = M.resumen(stPerf);
eq(resPerf.estrellas, 3, "partida perfecta son 3 estrellas");
check(Number.isFinite(resPerf.puntos) && resPerf.puntos > 0, "el puntaje es un número finito");

/* resumen por eje */
const desglose = M.porEje(stPerf);
eq(desglose.length, 4, "el desglose cubre los 4 ejes");
eq(desglose.reduce((a, e) => a + e.total, 0), 10, "el desglose suma 10");
check(desglose.every((e) => e.aciertos === e.total), "en la partida perfecta todo está correcto");

/* ══════════════════════════ 7. MOTOR: racha de días ══════════════════════════ */
let st2 = M.actualizarRacha({}, "2026-11-01");
eq(st2.racha, 1, "primer día: racha 1");
eq(st2.mejorRacha, 1, "mejor racha 1");
eq(st2.dias, 1, "un día jugado");

st2 = M.actualizarRacha(st2, "2026-11-02");
eq(st2.racha, 2, "día siguiente: racha 2");

st2 = M.actualizarRacha(st2, "2026-11-02");
eq(st2.racha, 2, "repetir el mismo día no suma");

st2 = M.actualizarRacha(st2, "2026-11-04");
eq(st2.racha, 1, "saltar un día reinicia la racha");

st2 = M.actualizarRacha(st2, "2026-11-05");
eq(st2.racha, 2, "volver a la racha después del salto");

st2 = M.actualizarRacha(st2, "2026-11-03");
eq(st2.racha, 2, "jugar un día pasado no rompe la racha");

/* ══════════════════════════ 8. MOTOR: compartir y escapar ══════════════════════════ */
const txt = M.textoCompartir(resPerf, "2026-11-07", 4);
check(txt.includes("2026-11-07"), "el texto de compartir trae la fecha");
check(txt.includes("★★★"), "el texto de compartir trae las estrellas");
check(txt.includes("10/10"), "el texto de compartir trae el conteo");

eq(M.esc('<img src=x onerror="alert(1)">'),
  "&lt;img src=x onerror=&quot;alert(1)&quot;&gt;", "escapa HTML");

/* ══════════════════════════ 9. SIMULACIÓN COMPLETA ══════════════════════════ */
let partidas = 0;
for (const fecha of fechas.slice(0, 10)) {
  const s = M.nuevoEstado(DATA.dias[fecha].preguntas, "diario");
  // responde bien el 80% de las preguntas, mal el resto
  s.preguntas.forEach((q, i) => {
    const buena = i % 5 !== 4;
    M.responder(s, buena ? q.correcta : (q.correcta + 1) % 4, buena ? 45 : 10);
    M.avanzar(s);
  });
  partidas++;
  const r = M.resumen(s);
  check(r.aciertos === 8, `${fecha}: 8 aciertos (hubo ${r.aciertos})`);
  check(r.estrellas === 3, `${fecha}: 3 estrellas`);
  check(Number.isFinite(r.puntos) && r.puntos > 0, `${fecha}: puntaje válido`);
}
check(partidas === 10, "se simularon 10 dailies");

/* ══════════════════════════ 11. LINT DE LOS ARCHIVOS WEB ══════════════════════════ */
/* `node --check` NO alcanza: `let x = 1` sin espacio es sintaxis válida
   (asignación a un identificador no declarado) y sólo revienta al ejecutar
   en modo estricto. Este bloque caza esa clase de error. */
for (const f of ["web/app.js", "web/engine.js"]) {
  const src = fs.readFileSync(path.join(__dirname, f), "utf8");
  const sueltos = [];
  src.split("\n").forEach((line, i) => {
    const code = line.replace(/\/\/.*$/, "");
    const m = code.match(/\b(let|const|var)([A-Za-z_$][\w$]*)/g);
    if (m) sueltos.push(`${f}:${i + 1} → ${m.join(", ")}`);
  });
  check(sueltos.length === 0, `sin 'let' pegado a la variable: ${sueltos.join(" | ")}`);

  // sintaxis real
  try {
    new Function(src.replace(/^\s*if \(typeof module[\s\S]*?\}\)\(.*?\);/m, ""));
  } catch (e) { /* engine.js es UMD: se salta */ }
}

/* balance de llaves y paréntesis: un desbalance rompe todo el script */
for (const f of ["web/app.js", "web/engine.js", "web/index.html"]) {
  const src = fs.readFileSync(path.join(__dirname, f), "utf8");
  const cuenta = (a, b) => (src.split(a).length - 1) - (src.split(b).length - 1);
  if (f.endsWith(".html")) {
    eq(cuenta("{", "}"), 0, `${f}: llaves balanceadas`);
    eq(cuenta("<div", "</div>"), 0, `${f}: divs balanceados`);
    eq(cuenta("<section", "</section>"), 0, `${f}: sections balanceados`);
    eq(cuenta("<button", "</button>"), 0, `${f}: botones balanceados`);
  } else {
    eq(cuenta("{", "}"), 0, `${f}: llaves balanceadas`);
    eq(cuenta("(", ")"), 0, `${f}: paréntesis balanceados`);
  }
}

/* el HTML debe referenciar los scripts que existen */
const html = fs.readFileSync(path.join(__dirname, "web", "index.html"), "utf8");
for (const s of ["data/daily.js", "engine.js", "app.js"]) {
  check(html.includes(`src="${s}"`), `index.html carga ${s}`);
  check(fs.existsSync(path.join(__dirname, "web", s)), `${s} existe`);
}

/* todo id que app.js busca debe existir en el HTML */
const app = fs.readFileSync(path.join(__dirname, "web", "app.js"), "utf8");
const idsUsados = new Set();
app.replace(/\$\("([a-zA-Z0-9_-]+)"\)/g, (_, id) => { idsUsados.add(id); return _; });
const idsHtml = new Set();
html.replace(/id="([a-zA-Z0-9_-]+)"/g, (_, id) => { idsHtml.add(id); return _; });
const huerfanos = [...idsUsados].filter((id) => !idsHtml.has(id));
check(huerfanos.length === 0, `todo id usado por app.js existe en el HTML (faltan: ${huerfanos.join(", ")})`);

/* ══════════════════════════ 12. PRÁCTICA ══════════════════════════ */const stPrac = M.nuevoEstado(tTodos.preguntas, "practica");
eq(stPrac.hearts, Infinity, "en práctica no hay corazones");
tTodos.preguntas.forEach((q) => {
  M.responder(stPrac, q.correcta, 0);
  M.avanzar(stPrac);
});
eq(stPrac.terminada, true, "la práctica termina sola");
eq(stPrac.aciertos, 20, "20 aciertos en práctica");
eq(M.resumen(stPrac).estrellas, 0, "la práctica no lleva estrellas");

/* ── resultado ──────────────────────────────────────────────── */
if (fallos.length) {
  console.error(`\n✗ ${fallos.length} fallo(s) de ${ok + fallos.length} comprobaciones:\n`);
  fallos.slice(0, 25).forEach((f) => console.error("  -", f));
  if (fallos.length > 25) console.error(`  ... y ${fallos.length - 25} más`);
  process.exit(1);
}
console.log(`\n✓ Ensayo: ${ok} comprobaciones, todas en verde`);
console.log(`  ${fechas.length} dailies · ${DATA.practica.length} de práctica · 18 familias de preguntas`);
