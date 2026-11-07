#!/usr/bin/env python3
"""
fama.py · oráculo de familiaridad.

Responde: "¿qué tan conocido es este número?".

Krillion usa "a familiarity database of how often a word or name actually
turns up in what people read and write" (su propio FAQ). Acá la fuente es
la misma idea pero con pageviews de Wikipedia sobre el artículo "N (number)":

    28  (number) →  5 414 vistas/mes     220 (number) →   637
    55  (number) →  5 010 vistas/mes     284 (number) →   173
    496 (number) →    668 vistas/mes     9801           →    69
    6   (number) →    494 vistas/mes     1184           →     1
                                     6232 / 40755      → sin artículo

Sin artículo ≈ nadie ha mirado ese número nunca ≈ raro de ver.
Con artículo pero pocas vistas ≈ existe, pero nadie lo busca.

Estrategia: primero se consulta en lote qué títulos existen (50 por request,
MediaWiki action=query) y después se piden pageviews solo de los que existen.
La mayoría de los candidatos no tienen artículo, y eso ya basta para saber
que son raros: no hace falta preguntar sus vistas.

Python 3.9+, solo stdlib. Cache en fama_cache.json.
"""
from __future__ import annotations

import json
import math
import os
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_PATH = os.path.join(HERE, "fama_cache.json")
ENDPOINT = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
            "{lang}.wikipedia/all-access/user/{title}/monthly/{start}/{end}")
EXISTS_ENDPOINT = ("https://{lang}.wikipedia.org/w/api.php?action=query&format=json"
                   "&formatversion=2&redirects=1&titles={titles}")
UA = ("abismo-proto/0.1 (juego educativo de matematicas; "
      "contacto: jorgegangale en gmail.com)")

# La API de Wikimedia limita por IP: sin este throttle el servidor devuelve
# 429 y el cache se llena de "sin artículo" falsos. 1 req/seg es seguro.
MIN_INTERVAL = 1.0
_throttle_lock = threading.Lock()
_last_call = 0.0

# Con ABISMO_OFFLINE=1 el juego no toca la red: usa solo el cache local.
# Es el modo en que correría el juego publicado (tabla precomputada).
OFFLINE = os.environ.get("ABISMO_OFFLINE") == "1"

_cache: dict[str, int | None] = {}
_dirty = False


def _throttle() -> None:
    global _last_call
    with _throttle_lock:
        wait = MIN_INTERVAL - (time.monotonic() - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.monotonic()


def _load() -> None:
    global _cache
    if os.path.exists(CACHE_PATH):
        with open(CACHE_PATH, "r", encoding="utf-8") as fh:
            _cache = json.load(fh)


def _save() -> None:
    if _dirty:
        with open(CACHE_PATH, "w", encoding="utf-8") as fh:
            json.dump(_cache, fh, ensure_ascii=False, indent=0, sort_keys=True)


def _fetch(lang: str, title: str, start: str, end: str):
    """(estado, vistas). estado: 'ok' | 'none' (no existe) | 'retry' (429/5xx)."""
    url = ENDPOINT.format(lang=lang, title=urllib.parse.quote(title, safe="()_"),
                          start=start, end=end)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    _throttle()
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return "none", None
        return "retry", None
    except (urllib.error.URLError, TimeoutError, ValueError):
        return "retry", None
    items = data.get("items") or []
    if not items:
        return "none", None
    return "ok", sum(it.get("views", 0) for it in items)


def exists_batch(lang: str, titles) -> tuple[set[str], set[str]]:
    """Cuáles de estos títulos existen en Wikipedia. 50 por request.

    Devuelve (existentes, fallados). Los fallados son títulos cuyo lote no se
    pudo consultar: NO se deben cachear como "no existe", porque envenenaría
    la rareza al revés.
    """
    found, failed, titles = set(), set(), list(titles)
    for i in range(0, len(titles), 50):
        chunk = titles[i:i + 50]
        url = EXISTS_ENDPOINT.format(lang=lang, titles=urllib.parse.quote("|".join(chunk), safe="|()_"))
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        _throttle()
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.load(resp)
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError):
            failed.update(chunk)
            continue
        q = data.get("query", {})
        redirects = {r["from"]: r["to"] for r in q.get("redirects", [])}
        normalized = {n["from"]: n["to"] for n in q.get("normalized", [])}
        real = {p["title"] for p in q.get("pages", []) if not p.get("missing") and p.get("title")}
        for t in chunk:
            key = normalized.get(t, t)
            key = redirects.get(key, key)
            if key in real:
                found.add(t)
    return found, failed


def views(lang: str, title: str, start: str = "20260101", end: str = "20260131") -> int | None:
    """Vistas de un artículo. None = sin artículo (o consulta saturada)."""
    global _dirty
    key = f"{lang}|{title}|{start}|{end}"
    if key not in _cache:
        if OFFLINE:
            return None  # sin red: solo lo que ya está en cache
        status, val = _fetch(lang, title, start, end)
        if status == "retry":
            return None  # transitorio: no se cachea, se reintenta después
        _cache[key] = val
        _dirty = True
    return _cache[key]


def warm(numbers, lang: str = "en", start: str = "20260101", end: str = "20260131",
         workers: int = 4) -> None:
    """Precarga la caché para una lista de números.

    1) un request de existencia por cada 50 títulos,
    2) pageviews solo para los que existen.

    Un 404 es definitivo y se cachea. Un 429 o un 5xx es transitorio: NO se
    cachea, así la próxima corrida lo reintenta.
    """
    global _dirty
    if OFFLINE:
        return  # sin red: solo se lee el cache
    titles = []
    for n in numbers:
        for t in (f"{n} (number)", str(n)):
            key = f"{lang}|{t}|{start}|{end}"
            if key not in _cache:
                titles.append(t)
    if not titles:
        return

    existing, failed = exists_batch(lang, titles)
    pending = []
    for t in titles:
        key = f"{lang}|{t}|{start}|{end}"
        if t in failed:
            continue                    # consulta caída: no cachear nada
        if t in existing:
            pending.append(t)
        else:
            _cache[key] = None  # el artículo no existe: definitivo
    _dirty = True

    def job(title):
        key = f"{lang}|{title}|{start}|{end}"
        for delay in (0, 2.0, 6.0, 15.0, 40.0):
            if delay:
                time.sleep(delay)
            status, val = _fetch(lang, title, start, end)
            if status == "ok":
                _cache[key] = val
                return "ok"
            if status == "none":
                _cache[key] = None
                return "none"
        return "retry"

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(job, pending))
    _dirty = True
    failed = sum(1 for r in results if r == "retry")
    if failed:
        print(f"  ! {failed} consultas saturadas, se reintenta en la próxima vuelta")
    _save()


def wiki_views(n: int, lang: str = "en", start: str = "20260101", end: str = "20260131") -> int | None:
    """Vistas del artículo del número.

    Primero se prueba 'N (number)'; si ese título no existe, se prueba 'N'
    pelado (a veces no existe: p. ej. 6232). None = nadie lo ha mirado nunca.
    """
    v = views(lang, f"{n} (number)", start, end)
    if v is None:
        v = views(lang, str(n), start, end)
    return v


def wiki_signal(n: int, lang: str = "en") -> float:
    """Saturado a [0,1]: cuántas veces se mira ese número al mes."""
    v = wiki_views(n, lang)
    if v is None:
        return 0.0
    return min(1.0, math.log10(v + 1) / 3.5)


if __name__ == "__main__":
    import sys
    _load()
    nums = [int(x) for x in sys.argv[1:]]
    if nums:
        warm(nums)
    for n in nums:
        v = wiki_views(n)
        print(f"{n:>14}  {'sin artículo' if v is None else f'{v:>7} vistas'}  "
              f"signal={wiki_signal(n):.2f}")
    _save()
