/* ─────────────────────────────────────────────────────────────
   Ensayo · motor del juego
   Lógica pura, sin DOM: se puede testear en node (smoke.js) y
   usar en el navegador. El DOM vive en app.js.
   ───────────────────────────────────────────────────────────── */
(function (root, factory) {
  if (typeof module === "object" && module.exports) module.exports = factory();
  else root.EnsayoMotor = factory();
})(typeof self !== "undefined" ? self : globalThis, function () {
  "use strict";

  const SEGUNDOS = 45;        // segundos por pregunta en el reto diario
  const CORAZONES = 3;        // errores que terminan el intento
  const PUNTOS_BASE = 100;
  const BONO_MAX = 50;        // bono máximo por responder rápido
  const MULT = [1, 1.2, 1.5, 1.8, 2];   // multiplicador por racha de aciertos

  const EJE_CORTO = {
    "Números": "Números",
    "Álgebra y funciones": "Álgebra",
    "Geometría": "Geometría",
    "Probabilidad y estadística": "Probabilidad",
  };

  /* ── tiempo ─────────────────────────────────────────────── */
  /** Fecha de Chile (America/Santiago) en formato YYYY-MM-DD. */
  function hoyISO(fecha) {
    const f = fecha || new Date();
    try {
      const s = new Intl.DateTimeFormat("en-CA", {
        timeZone: "America/Santiago", year: "numeric", month: "2-digit", day: "2-digit",
      }).format(f);
      // en-CA entrega YYYY-MM-DD; algunos runtimes devuelven MM/DD/YYYY
      if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return s;
      const partes = s.split(/[-\/]/);
      if (partes.length === 3) {
        const [a, b, c] = partes;
        const anio = a.length === 4 ? a : c;
        const mes = a.length === 4 ? b : a;
        const dia = a.length === 4 ? c : b;
        return `${anio}-${mes.padStart(2, "0")}-${dia.padStart(2, "0")}`;
      }
    } catch (e) { /* sin Intl completo: caemos al ISO local */ }
    return `${f.getFullYear()}-${String(f.getMonth() + 1).padStart(2, "0")}-${String(f.getDate()).padStart(2, "0")}`;
  }

  /** Días de diferencia entre dos fechas YYYY-MM-DD (b - a). */
  function diasEntre(a, b) {
    const fa = Date.parse(a + "T00:00:00Z");
    const fb = Date.parse(b + "T00:00:00Z");
    if (Number.isNaN(fa) || Number.isNaN(fb)) return 0;
    return Math.round((fb - fa) / 86400000);
  }

  /* ── puntaje ────────────────────────────────────────────── */
  function multiplicador(racha) {
    if (racha <= 0) return 1;
    return MULT[Math.min(racha, MULT.length - 1)];
  }

  /** Puntaje de una respuesta correcta: base + bono de velocidad, por racha. */
  function puntuar(tiempoRestante, racha) {
    const t = Math.max(0, Math.min(SEGUNDOS, tiempoRestante || 0));
    const bono = Math.round(BONO_MAX * (t / SEGUNDOS));
    const mult = multiplicador(racha);
    return { base: PUNTOS_BASE, bono, mult, total: Math.round((PUNTOS_BASE + bono) * mult) };
  }

  /** Estrellas del reto diario: 3 = 80%+, 2 = 60%+, 1 = resto. */
  function estrellas(aciertos, total) {
    const pct = total > 0 ? aciertos / total : 0;
    if (pct >= 0.8) return 3;
    if (pct >= 0.6) return 2;
    return 1;
  }

  /* ── azar ───────────────────────────────────────────────── */
  /** PRNG determinista (mulberry32): mismo seed, mismo orden. */
  function rngMulberry32(seed) {
    let a = seed >>> 0;
    return function () {
      a |= 0; a = (a + 0x6D2B79F5) | 0;
      let t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function barajar(arr, rng) {
    const a = arr.slice();
    for (let i = a.length - 1; i > 0; i--) {
      const j = Math.floor(rng() * (i + 1));
      const tmp = a[i]; a[i] = a[j]; a[j] = tmp;
    }
    return a;
  }

  /* ── selección de contenido ─────────────────────────────── */
  /**
   * Devuelve el set de preguntas de una fecha.
   * Si la fecha está fuera del rango precomputado, usa la más cercana
   * disponible (y avisa con `exacta: false`).
   */
  function seleccionarDaily(data, fechaISO) {
    const dias = (data && data.dias) || {};
    if (dias[fechaISO]) {
      return { fecha: fechaISO, preguntas: dias[fechaISO].preguntas, exacta: true };
    }
    const claves = Object.keys(dias).sort();
    if (!claves.length) return null;
    let mejor = claves[0];
    let diff = Infinity;
    for (const k of claves) {
      const d = Math.abs(diasEntre(k, fechaISO));
      if (d < diff) { diff = d; mejor = k; }
    }
    return { fecha: mejor, preguntas: dias[mejor].preguntas, exacta: false };
  }

  /** Toma n preguntas del pool de práctica según el eje elegido. */
  function tomarPractica(pool, n, eje, cursor, seed) {
    const filtrado = (!eje || eje === "Todos")
      ? pool.slice()
      : pool.filter((q) => q.eje === eje);
    const barajado = barajar(filtrado, rngMulberry32(seed >>> 0));
    const out = [];
    let c = cursor % barajado.length;
    for (let k = 0; k < n && barajado.length; k++) {
      out.push(barajado[c % barajado.length]);
      c++;
    }
    return { preguntas: out, cursor: c % Math.max(1, barajado.length), total: barajado.length };
  }

  /* ── estado de partida ──────────────────────────────────── */
  function nuevoEstado(preguntas, modo) {
    return {
      modo: modo || "diario",
      preguntas: preguntas || [],
      i: 0,
      aciertos: 0,
      errores: 0,
      puntos: 0,
      racha: 0,          // racha de aciertos consecutivos
      mejorRacha: 0,
      hearts: modo === "practica" ? Infinity : CORAZONES,
      respondida: false,
      terminada: false,
      resultados: [],    // una entrada por pregunta respondida
    };
  }

  /**
   * Registra la respuesta a la pregunta actual.
   * Devuelve {ok, puntos, pregunta} o null si ya se había respondido.
   */
  function responder(estado, elegida, tiempoRestante) {
    if (estado.respondida || estado.terminada) return null;
    const q = estado.preguntas[estado.i];
    if (!q) return null;

    const ok = elegida === q.correcta;
    let p = null;
    if (ok) {
      // el multiplicador usa la racha ANTES de esta respuesta
      p = puntuar(tiempoRestante, estado.racha);
      estado.puntos += p.total;
      estado.aciertos += 1;
      estado.racha += 1;
      estado.mejorRacha = Math.max(estado.mejorRacha, estado.racha);
    } else {
      estado.errores += 1;
      estado.racha = 0;
      if (estado.hearts !== Infinity) estado.hearts = Math.max(0, estado.hearts - 1);
    }
    estado.respondida = true;
    estado.resultados.push({ pregunta: q, elegida, ok, puntos: p });

    if (estado.hearts === 0) estado.terminada = true;
    return { ok, puntos: p, pregunta: q };
  }

  /** Pasa a la pregunta siguiente. Marca la partida como terminada al final. */
  function avanzar(estado) {
    if (!estado.respondida) return estado;
    if (estado.terminada) return estado;
    estado.i += 1;
    estado.respondida = false;
    if (estado.i >= estado.preguntas.length) estado.terminada = true;
    return estado;
  }

  /** Resumen final de la partida. */
  function resumen(estado) {
    const total = estado.preguntas.length || estado.resultados.length;
    return {
      modo: estado.modo,
      aciertos: estado.aciertos,
      errores: estado.errores,
      puntos: estado.puntos,
      total,
      estrellas: estado.modo === "practica" ? 0 : estrellas(estado.aciertos, total),
      mejorRacha: estado.mejorRacha,
      respondidas: estado.resultados.length,
      completo: estado.resultados.length >= total,
    };
  }

  /** Aciertos por eje, para el desglose del resultado. */
  function porEje(estado) {
    const mapa = {};
    for (const r of estado.resultados) {
      const e = r.pregunta.eje;
      if (!mapa[e]) mapa[e] = { eje: e, total: 0, aciertos: 0 };
      mapa[e].total += 1;
      if (r.ok) mapa[e].aciertos += 1;
    }
    return Object.keys(mapa).map((k) => mapa[k]).sort((a, b) => a.eje.localeCompare(b.eje));
  }

  /* ── racha de días ──────────────────────────────────────── */
  /**
   * Actualiza la racha al completar el reto de una fecha.
   * Mismo día → no cambia. Día siguiente → +1. salto → vuelve a 1.
   * Fecha pasada → no toca la racha.
   */
  function actualizarRacha(stats, fechaISO) {
    const s = Object.assign({ racha: 0, mejorRacha: 0, dias: 0 }, stats || {});
    if (!s.ultimoDia) {
      s.racha = 1;
    } else {
      const d = diasEntre(s.ultimoDia, fechaISO);
      if (d === 0) {
        // repetir hoy no suma ni resta
      } else if (d === 1) {
        s.racha = (s.racha || 0) + 1;
      } else if (d > 1) {
        s.racha = 1;
      } else {
        return s;   // fecha anterior: la racha vigente no se toca
      }
    }
    s.ultimoDia = fechaISO;
    s.mejorRacha = Math.max(s.mejorRacha || 0, s.racha || 0);
    s.dias = (s.dias || 0) + 1;
    return s;
  }

  /* ── texto para compartir ───────────────────────────────── */
  function textoCompartir(res, fechaISO, racha) {
    const estrellasTxt = res.estrellas > 0
      ? "★".repeat(res.estrellas) + "☆".repeat(3 - res.estrellas)
      : `${res.aciertos}/${res.total}`;
    return `Ensayo · reto diario ${fechaISO}\n${estrellasTxt}\n`
      + `${res.aciertos}/${res.total} correctas · ${res.puntos} pts · racha ${racha} día(s)\n`
      + `#PAES #Matemática`;
  }

  /* ── utilidades ─────────────────────────────────────────── */
  function esc(s) {
    return String(s == null ? "" : s)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
  }

  return {
    SEGUNDOS, CORAZONES, PUNTOS_BASE, BONO_MAX, MULT, EJE_CORTO,
    hoyISO, diasEntre, multiplicador, puntuar, estrellas,
    rngMulberry32, barajar, seleccionarDaily, tomarPractica,
    nuevoEstado, responder, avanzar, resumen, porEje,
    actualizarRacha, textoCompartir, esc,
  };
});
