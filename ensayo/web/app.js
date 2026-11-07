/* ─────────────────────────────────────────────────────────────
   Ensayo · capa de interfaz
   Toda la lógica de juego vive en engine.js; aquí solo el DOM.
   ───────────────────────────────────────────────────────────── */
(function () {
  "use strict";

  const M = window.EnsayoMotor;
  const DATA = window.ENSAYO || { dias: {}, practica: [] };

  const LS = {
    stats: "ensayo.stats",
    cuaderno: "ensayo.cuaderno",
    cursor: "ensayo.cursor",
  };

  const LETRAS = ["A", "B", "C", "D"];
  const $ = (id) => document.getElementById(id);
  const esc = M.esc;

  /* ── estado local ────────────────────────────────────────── */
  function leer(clave, defecto) {
    try {
      const raw = localStorage.getItem(clave);
      return raw ? JSON.parse(raw) : defecto;
    } catch (e) { return defecto; }
  }
  function guardar(clave, valor) {
    try { localStorage.setItem(clave, JSON.stringify(valor)); } catch (e) { /* modo privado */ }
  }

  let stats = Object.assign(
    { racha: 0, mejorRacha: 0, dias: 0, aciertos: 0, preguntas: 0, ultimoDia: null },
    leer(LS.stats, {})
  );

  /* ── estado de la partida ────────────────────────────────── */
  let estado = null;
  let modo = "diario";
  let diaSel = null;
  let timerId = null;
  let deadline = 0;
  let restante = M.SEGUNDOS;
  let ejePractica = "Todos";
  let nPractica = 10;
  let cmprarSalir = false;

  /* ── pantallas ───────────────────────────────────────────── */
  function mostrar(id) {
    document.querySelectorAll(".screen").forEach((s) => {
      s.classList.toggle("is-active", s.id === id);
    });
    window.scrollTo({ top: 0, behavior: "instant" in window ? "instant" : "auto" });
  }

  function toast(msg) {
    const t = $("toast");
    t.textContent = msg;
    t.hidden = false;
    clearTimeout(t._t);
    t._t = setTimeout(() => { t.hidden = true; }, 2100);
  }

  /* ── intro ───────────────────────────────────────────────── */
  function pintarStats() {
    $("st-racha").textContent = stats.racha || 0;
    $("st-mejor").textContent = stats.mejorRacha || 0;
    $("st-dias").textContent = stats.dias || 0;
    $("st-aciertos").textContent = stats.aciertos || 0;

    const sel = M.seleccionarDaily(DATA, M.hoyISO());
    if (!sel) {
      $("diario-desc").textContent = "No hay retos cargados todavía.";
    } else if (sel.exacta) {
      $("diario-desc").textContent =
        `Hoy te esperan ${sel.preguntas.length} preguntas: el mismo set para todos, `
        + "con tiempo, con corazones y con racha de días.";
    } else {
      $("diario-desc").textContent =
        `El reto de hoy aún no está publicado; te muestro el más reciente `
        + `(${sel.fecha}), con ${sel.preguntas.length} preguntas.`;
    }
  }

  /* ── arranque de partida ─────────────────────────────────── */
  function empezarDiario() {
    const sel = M.seleccionarDaily(DATA, M.hoyISO());
    if (!sel || !sel.preguntas.length) { toast("No hay retos disponibles"); return; }
    modo = "diario";
    diaSel = sel;
    estado = M.nuevoEstado(sel.preguntas, "diario");
    mostrar("scr-play");
    pintarPregunta();
  }

  function empezarPractica(preguntas) {
    modo = "practica";
    diaSel = null;
    estado = M.nuevoEstado(preguntas, "practica");
    mostrar("scr-play");
    pintarPregunta();
  }

  function empezarPracticaDesdeConfig() {
    const pool = DATA.practica || [];
    if (!pool.length) { toast("No hay preguntas cargadas"); return; }
    const cursor = leer(LS.cursor, 0);
    const sem = (Date.now() / 86400000) | 0;
    const t = M.tomarPractica(pool, nPractica, ejePractica, cursor, sem * 7919 + nPractica);
    guardar(LS.cursor, t.cursor);
    if (!t.preguntas.length) { toast("No hay preguntas para ese eje"); return; }
    empezarPractica(t.preguntas);
  }

  function empezarPracticaErrores() {
    const cuad = leer(LS.cuaderno, []);
    if (!cuad.length) { toast("No hay errores guardados"); return; }
    const preguntas = cuad.slice(-20).map((e) => ({
      eje: e.eje, unidad: e.unidad, enunciado: e.enunciado,
      opciones: e.opciones, correcta: e.correcta, explicacion: e.explicacion,
      nivel: 2, tags: e.tags || [],
    }));
    empezarPractica(preguntas);
  }

  /* ── render de la pregunta ───────────────────────────────── */
  function pintarPregunta() {
    const q = estado.preguntas[estado.i];
    if (!q) { terminar(); return; }

    $("pregunta-num").textContent =
      `Pregunta ${estado.i + 1} de ${estado.preguntas.length}`;
    $("pregunta-texto").textContent = q.enunciado;
    $("hud-eje").textContent = M.EJE_CORTO[q.eje] || q.eje;
    $("hud-unidad").textContent = q.unidad || "";

    const cont = $("opciones");
    cont.innerHTML = "";
    q.opciones.forEach((texto, i) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "opcion";
      b.innerHTML = `<span class="opcion__letra">${LETRAS[i]}</span>`
        + `<span class="opcion__texto">${esc(texto)}</span>`;
      b.addEventListener("click", () => elegir(i));
      cont.appendChild(b);
    });

    $("feedback").hidden = true;
    $("feedback").classList.remove("is-ok", "is-mal");

    pintarHUD();
    pintarRiel();
    arrancarTimer();
  }

  function pintarHUD() {
    $("hud-puntos").textContent = estado.puntos;
    let h = "";
    const corazones = estado.hearts === Infinity ? 0 : estado.hearts;
    for (let i = 0; i < M.CORAZONES; i++) {
      h += `<span class="heart${i < corazones ? "" : " heart--off"}">♥</span>`;
    }
    $("hud-corazones").innerHTML = h;
    $("hud-corazones").style.visibility = modo === "practica" ? "hidden" : "visible";
  }

  function pintarRiel() {
    const total = estado.preguntas.length;
    const avance = (estado.i + (estado.respondida ? 1 : 0)) / total;
    const pct = Math.max(0, Math.min(1, avance)) * 100;
    $("rail-fill").style.width = pct + "%";
    $("rail-lapiz").style.left = pct + "%";
  }

  /* ── temporizador ────────────────────────────────────────── */
  function arrancarTimer() {
    pararTimer();
    if (modo === "practica") {
      $("tiempo-wrap").style.visibility = "hidden";
      restante = M.SEGUNDOS;
      return;
    }
    $("tiempo-wrap").style.visibility = "visible";
    restante = M.SEGUNDOS;
    deadline = Date.now() + M.SEGUNDOS * 1000;
    pintarTiempo();
    timerId = setInterval(tick, 250);
  }

  function tick() {
    if (estado.respondida || estado.terminada) { pararTimer(); return; }
    restante = Math.max(0, (deadline - Date.now()) / 1000);
    pintarTiempo();
    if (restante <= 0) {
      pararTimer();
      elegir(-1, true);
    }
  }

  function pintarTiempo() {
    const seg = Math.ceil(restante);
    $("tiempo-num").textContent = seg;
    const pct = Math.max(0, Math.min(1, restante / M.SEGUNDOS)) * 100;
    const fill = $("tiempo-fill");
    fill.style.width = pct + "%";
    fill.classList.toggle("is-medio", restante <= 30 && restante > 15);
    fill.classList.toggle("is-bajo", restante <= 15);
  }

  function pararTimer() {
    if (timerId) { clearInterval(timerId); timerId = null; }
  }

  /* ── responder ───────────────────────────────────────────── */
  function elegir(idx, porTiempo) {
    if (!estado || estado.respondida || estado.terminada) return;
    const q = estado.preguntas[estado.i];
    const seg = modo === "practica" ? 0 : restante;
    const r = M.responder(estado, idx, seg);
    if (!r) return;
    pararTimer();

    // marcar opciones
    const btns = $("opciones").querySelectorAll(".opcion");
    btns.forEach((b, i) => {
      b.disabled = true;
      if (i === q.correcta) b.classList.add("is-ok");
      else if (i === idx) b.classList.add("is-mal");
      else b.classList.add("is-atenuada");
    });

    if (!r.ok) guardarError(q, idx);

    // feedback
    const fb = $("feedback");
    fb.hidden = false;
    fb.classList.toggle("is-ok", r.ok);
    fb.classList.toggle("is-mal", !r.ok);
    $("feedback-titulo").textContent = r.ok
      ? "¡Correcto!"
      : (porTiempo ? "Se acabó el tiempo" : "No era esa");

    let cuerpo = q.explicacion;
    if (r.ok && r.puntos) {
      cuerpo += `\n\n+${r.puntos} puntos`
        + ` (base ${r.puntos.base}`
        + (r.puntos.bono ? ` + ${r.puntos.bono} de velocidad` : "")
        + ` ×${r.puntos.mult} racha)`;
    } else if (!r.ok) {
      cuerpo += `\n\nLa respuesta correcta era ${LETRAS[q.correcta]}: ${q.opciones[q.correcta]}`;
    }
    $("feedback-cuerpo").textContent = cuerpo;

    pintarHUD();
    pintarRiel();
    $("btn-siguiente").focus();
  }

  function siguiente() {
    M.avanzar(estado);
    if (estado.terminada) { terminar(); return; }
    pintarPregunta();
  }

  /* ── resultado ───────────────────────────────────────────── */
  function terminar() {
    pararTimer();
    const res = M.resumen(estado);

    if (modo === "diario" && diaSel) {
      stats = M.actualizarRacha(stats, diaSel.fecha);
      stats.aciertos = (stats.aciertos || 0) + res.aciertos;
      stats.preguntas = (stats.preguntas || 0) + res.respondidas;
      guardar(LS.stats, stats);
    }

    $("result-estrellas").textContent = modo === "practica"
      ? `${res.aciertos}/${res.total}`
      : "★".repeat(res.estrellas) + "☆".repeat(3 - res.estrellas);

    const completo = res.respondidas >= res.total;
    $("result-titulo").textContent = modo === "practica"
      ? "Práctica terminada"
      : (!completo ? "Se acabó" : (res.estrellas === 3 ? "¡Perfecto!" : "Reto completado"));

    $("result-sub").textContent = modo === "diario"
      ? `${diaSel ? diaSel.fecha : ""} · ${res.aciertos} de ${res.total} correctas`
      : `${res.aciertos} de ${res.total} correctas`;

    $("result-aciertos").textContent = `${res.aciertos}/${res.total}`;
    $("result-puntos").textContent = res.puntos;
    $("result-racha").textContent = res.mejorRacha;

    // desglose por eje
    const dl = $("result-desglose");
    dl.innerHTML = "";
    M.porEje(estado).forEach((e) => {
      const li = document.createElement("li");
      const pct = e.total ? (e.aciertos / e.total) * 100 : 0;
      li.innerHTML = `<span class="eje-n">${esc(M.EJE_CORTO[e.eje] || e.eje)}</span>`
        + `<span class="barra"><i style="width:${pct}%"></i></span>`
        + `<span class="eje-v">${e.aciertos}/${e.total}</span>`;
      dl.appendChild(li);
    });

    $("result-nota").textContent = modo === "diario"
      ? `Racha actual: ${stats.racha} día(s). ${res.estrellas === 3
        ? "Excelente: vuelve mañana para mantenerla." : "Mañana hay un reto nuevo."}`
      : "Los errores quedaron guardados en tu cuaderno.";

    mostrar("scr-result");
    pintarStats();
  }

  /* ── compartir ───────────────────────────────────────────── */
  async function compartir() {
    const res = M.resumen(estado);
    const texto = M.textoCompartir(res, diaSel ? diaSel.fecha : M.hoyISO(), stats.racha || 0);
    try {
      if (navigator.share) {
        await navigator.share({ title: "Ensayo", text: texto });
        return;
      }
    } catch (e) { /* el usuario canceló o no hay soporte */ }
    copiar(texto);
  }

  function copiar(texto) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(texto)
        .then(() => toast("Resultado copiado"))
        .catch(() => copiarLegacy(texto));
    } else {
      copiarLegacy(texto);
    }
  }

  function copiarLegacy(texto) {
    const ta = document.createElement("textarea");
    ta.value = texto;
    ta.style.position = "fixed";
    ta.style.opacity = "0";
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand("copy"); toast("Resultado copiado"); }
    catch (e) { toast("No se pudo copiar"); }
    document.body.removeChild(ta);
  }

  /* ── cuaderno de errores ─────────────────────────────────── */
  function guardarError(q, elegida) {
    const cuad = leer(LS.cuaderno, []);
    const item = {
      eje: q.eje, unidad: q.unidad, enunciado: q.enunciado,
      opciones: q.opciones, correcta: q.correcta, explicacion: q.explicacion,
      tags: q.tags || [], elegida, fecha: M.hoyISO(),
    };
    // dedupe por enunciado: si ya estaba, se actualiza
    const i = cuad.findIndex((e) => e.enunciado === q.enunciado);
    if (i >= 0) cuad[i] = item; else cuad.push(item);
    while (cuad.length > 120) cuad.shift();
    guardar(LS.cuaderno, cuad);
  }

  function pintarCuaderno() {
    const cuad = leer(LS.cuaderno, []);
    const cont = $("cuaderno-lista");
    cont.innerHTML = "";

    if (!cuad.length) {
      cont.innerHTML = `<div class="vacio"><b>Todavía no hay errores</b>
        Juega el reto diario o practica: cada fallo queda anotado acá con su explicación.</div>`;
      $("btn-practicar-errores").hidden = true;
      $("cuaderno-lede").textContent = "Las preguntas que fallaste, con su explicación.";
      return;
    }

    cuad.slice().reverse().forEach((e) => {
      const div = document.createElement("div");
      div.className = "error-card";
      div.innerHTML =
        `<div class="error-card__eje">${esc(M.EJE_CORTO[e.eje] || e.eje)} · ${esc(e.unidad || "")}</div>`
        + `<div class="error-card__enunciado">${esc(e.enunciado)}</div>`
        + `<div class="error-card__op">Tú: <b>${esc(e.opciones[e.elegida] || "—")}</b> · `
        + `Correcta: <b>${esc(e.opciones[e.correcta])}</b></div>`
        + `<div class="error-card__exp">${esc(e.explicacion)}</div>`;
      cont.appendChild(div);
    });
    $("btn-practicar-errores").hidden = false;
    $("cuaderno-lede").textContent =
      `${cuad.length} pregunta(s) fallada(s), con su explicación.`;
  }

  /* ── eventos ─────────────────────────────────────────────── */
  function cablear() {
    $("btn-diario").addEventListener("click", empezarDiario);
    $("btn-practica").addEventListener("click", () => { mostrar("scr-config"); });
    $("btn-empezar-practica").addEventListener("click", empezarPracticaDesdeConfig);
    $("btn-otra-vez").addEventListener("click", () => {
      if (modo === "diario") empezarDiario(); else mostrar("scr-config");
    });
    $("btn-inicio").addEventListener("click", () => { pararTimer(); mostrar("scr-intro"); pintarStats(); });
    $("btn-siguiente").addEventListener("click", siguiente);
    $("btn-compartir").addEventListener("click", compartir);

    // abandonar: pide confirmación con un segundo clic
    $("btn-abandonar").addEventListener("click", () => {
      if (!cmprarSalir) {
        cmprarSalir = true;
        $("btn-abandonar").textContent = "¿Salir?";
        setTimeout(() => {
          cmprarSalir = false;
          $("btn-abandonar").textContent = "←";
        }, 2600);
        return;
      }
      cmprarSalir = false;
      $("btn-abandonar").textContent = "←";
      pararTimer();
      mostrar("scr-intro");
      pintarStats();
    });

    // chips de configuración
    document.querySelectorAll("#eje-chips .chip").forEach((c) => {
      c.addEventListener("click", () => {
        document.querySelectorAll("#eje-chips .chip").forEach((x) => x.classList.remove("is-on"));
        c.classList.add("is-on");
        ejePractica = c.dataset.eje;
      });
    });
    document.querySelectorAll("#n-chips .chip").forEach((c) => {
      c.addEventListener("click", () => {
        document.querySelectorAll("#n-chips .chip").forEach((x) => x.classList.remove("is-on"));
        c.classList.add("is-on");
        nPractica = parseInt(c.dataset.n, 10) || 10;
      });
    });

    // cuaderno
    $("btn-cuaderno").addEventListener("click", () => { pintarCuaderno(); mostrar("scr-cuaderno"); });
    $("btn-cuaderno-2").addEventListener("click", () => { pintarCuaderno(); mostrar("scr-cuaderno"); });
    $("btn-cuaderno-cerrar").addEventListener("click", () => mostrar("scr-intro"));
    $("btn-practicar-errores").addEventListener("click", empezarPracticaErrores);

    // teclado
    document.addEventListener("keydown", (ev) => {
      if (!document.getElementById("scr-play").classList.contains("is-active")) return;
      if (ev.key === "Enter") {
        if (!$("feedback").hidden) { ev.preventDefault(); siguiente(); }
        return;
      }
      const n = parseInt(ev.key, 10);
      if (n >= 1 && n <= 4) {
        if ($("feedback").hidden) { ev.preventDefault(); elegir(n - 1); }
      }
    });
  }

  /* ── arranque ────────────────────────────────────────────── */
  function init() {
    cablear();
    pintarStats();
    pintarCuaderno();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
