#!/usr/bin/env python3
"""
abismo · daily de matemáticas por rareza.

Misma idea base que krillion.io: cada prompt define un conjunto de
respuestas VÁLIDAS; no importa si aciertas, importa qué tan RARA es tu
respuesta. Rara = más puntos = más profundidad.

La diferencia clave: en trivia los conjuntos de respuesta se curan a mano
(caro, finito). Acá se GENERAN con aritmética, así que el juego es
infinito, objetivo y reproducible (mismo seed → mismos prompts).

Python 3.9+, solo stdlib.
"""
from __future__ import annotations

import math
import random
import signal
import sys
from datetime import date

import fama

fama._load()

# ---------------------------------------------------------------- rareza
# Modo absoluto (prior estructural, para conjuntos densos)
TIERS = [
    ("Común",       10, 0.66),
    ("Curioso",     15, 0.54),
    ("Raro",        30, 0.42),
    ("Profundo",    60, 0.30),
    ("Abisal",      85, 0.20),
    ("Legendario", 100, 0.00),
]

# Modo cuantil (rank dentro del prompt, para conjuntos dispersos).
# o = 0 es la respuesta más conocida, o = 1 la más oscura.
OBSCURITY = [
    (0.16, "Común",       10),
    (0.32, "Curioso",     15),
    (0.50, "Raro",        30),
    (0.68, "Profundo",    60),
    (0.86, "Abisal",      85),
    (1.01, "Legendario", 100),
]

PTS_PER_M = 10
ROUNDS = 7
WIKI_LIMIT = 600


def tier_for(g: float) -> tuple[str, int]:
    for name, pts, thr in TIERS:
        if g >= thr:
            return name, pts
    return TIERS[-1][0], TIERS[-1][1]


def tier_for_obscurity(o: float) -> tuple[str, int]:
    for thr, name, pts in OBSCURITY:
        if o <= thr:
            return name, pts
    return OBSCURITY[-1][1], OBSCURITY[-1][2]


# ---------------------------------------------------------------- helpers
def is_triangular(n: int) -> bool:
    r = math.isqrt(8 * n + 1)
    return r * r == 8 * n + 1


def is_hexagonal(n: int) -> bool:
    # n = k(2k-1)  <=>  8n+1 = (4k-1)^2, o sea raíz ≡ 3 (mod 4)
    r = math.isqrt(8 * n + 1)
    return r * r == 8 * n + 1 and r % 4 == 3


def is_square(n: int) -> bool:
    r = math.isqrt(n)
    return r * r == n


def is_cube(n: int) -> bool:
    if n < 0:
        return False
    c = round(n ** (1 / 3))
    return any(cand >= 0 and cand ** 3 == n for cand in (c - 1, c, c + 1))


def is_pentagonal(n: int) -> bool:
    # n = k(3k-1)/2  <=>  24n+1 = (6k-1)^2
    r = math.isqrt(24 * n + 1)
    return r * r == 24 * n + 1 and r % 6 == 5


def is_legendre_form(n: int) -> bool:
    """n NO es suma de tres cuadrados  <=>  n = 4^a (8b+7)"""
    while n % 4 == 0:
        n //= 4
    return n % 8 == 7


def is_prime(n: int) -> bool:
    if n < 2:
        return False
    for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if n % p == 0:
            return n == p
    d, s = n - 1, 0
    while d % 2 == 0:
        d //= 2
        s += 1
    for a in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True


_SIEVE_CACHE: dict[int, list[int]] = {}


def sum_proper_divisors_sieve(limit: int) -> list[int]:
    if limit in _SIEVE_CACHE:
        return _SIEVE_CACHE[limit]
    s = [0] * (limit + 1)
    for d in range(1, limit // 2 + 1):
        for m in range(2 * d, limit + 1, d):
            s[m] += d
    _SIEVE_CACHE[limit] = s
    return s


def mersenne_primes(limit_p: int = 47) -> list[tuple[int, int]]:
    return [(p, 2 ** p - 1) for p in range(2, limit_p + 1)
            if is_prime(p) and is_prime(2 ** p - 1)]


def catalan_numbers(limit: int) -> list[int]:
    out, c, n = [], 1, 0
    while c <= limit:
        out.append(c)
        c = c * 2 * (2 * n + 1) // (n + 2)
        n += 1
    return out


def bell_numbers(limit: int) -> list[int]:
    out, row = [], [1]
    while True:
        out.append(sum(row))
        if out[-1] > limit:
            break
        n = len(row)
        new = [0] * (n + 1)
        for k in range(1, n + 1):
            new[k] = (row[k - 1] if k - 1 < len(row) else 0) + k * (row[k] if k < len(row) else 0)
        row = new
    return [b for b in out if b <= limit]


def fib_numbers(limit: int) -> list[int]:
    out, a, b = [], 1, 1
    while a <= limit:
        out.append(a)
        a, b = b, a + b
    return out


def pell_numbers(limit: int) -> list[int]:
    out, a, b = [], 0, 1
    while a <= limit:
        out.append(a)
        a, b = b, 2 * b + a
    return out


def lucas_numbers(limit: int) -> list[int]:
    out, a, b = [], 2, 1
    while a <= limit:
        out.append(a)
        a, b = b, a + b
    return out


def is_keith(n: int) -> bool:
    """Keith: aparece en su propia sucesión (dígitos y sumas de los últimos d)."""
    if n < 10:
        return False
    d = len(str(n))
    seq = [int(c) for c in str(n)]
    for _ in range(200):
        nxt = sum(seq[-d:])
        if nxt == n:
            return True
        if nxt > n:
            return False
        seq.append(nxt)
    return False


def narcissistic_numbers() -> list[int]:
    """Narcisistas: suma de sus dígitos elevado a la cantidad de dígitos."""
    from itertools import combinations_with_replacement
    out = set()
    for d in range(1, 9):
        for combo in combinations_with_replacement(range(10), d):
            s = sum(c ** d for c in combo)
            if s > 0 and sorted(int(c) for c in str(s)) == list(combo):
                out.add(s)
    return sorted(out)


def wieferich_primes(limit: int = 100_000) -> list[int]:
    """Primos de Wieferich: 2^(p-1) ≡ 1 (mod p²). Solo hay dos conocidos."""
    return [p for p in range(2, limit) if is_prime(p) and pow(2, p - 1, p * p) == 1]


# ---------------------------------------------------------------- familias
# valid(n): ¿es respuesta válida?   universe(maxv): muestra para puntuar
class Family:
    def __init__(self, key, stratum, prompt, valid, universe, cap):
        self.key = key
        self.stratum = stratum
        self.prompt = prompt
        self.valid = valid
        self.universe = universe
        self.cap = cap


def _iter_pentagonal(maxv):
    k = 1
    while True:
        p = k * (3 * k - 1) // 2
        if p > maxv:
            return
        yield p
        k += 1


def _iter_hexagonal(maxv):
    k = 1
    while True:
        h = k * (2 * k - 1)
        if h > maxv:
            return
        yield h
        k += 1


def _univ_filter(seq, pred, maxv):
    return [n for n in seq if n <= maxv and pred(n)]


def _univ_squares(maxv):
    k = 1
    while k * k <= maxv:
        yield k * k
        k += 1


def _univ_cubes(maxv):
    k = 1
    while k ** 3 <= maxv:
        yield k ** 3
        k += 1


def _univ_legendre(maxv):
    a = 0
    while 4 ** a <= maxv:
        base = 4 ** a
        b = 0
        while base * (8 * b + 7) <= maxv:
            yield base * (8 * b + 7)
            b += 1
        a += 1


def _univ_amicable(maxv):
    s = sum_proper_divisors_sieve(maxv)
    for n in range(2, maxv + 1):
        m = s[n]
        if m != n and 0 < m <= maxv and s[m] == n:
            yield n


_KEITH_SET = {k for k in range(10, 200_001) if is_keith(k)}
_NARCISISTA_SET = set(narcissistic_numbers())

FAMILIES = [
    Family("triangular_cuadrado", "Aritmética",
           "Un número que sea a la vez triangular y cuadrado perfecto.",
           lambda n: is_square(n) and is_triangular(n),
           lambda m: _univ_filter(_univ_squares(m), is_triangular, m),
           10 ** 9),
    Family("hexagonal_cuadrado", "Aritmética",
           "Un número que sea a la vez hexagonal y cuadrado perfecto.",
           lambda n: is_hexagonal(n) and is_square(n),
           lambda m: _univ_filter(_iter_hexagonal(m), is_square, m),
           10 ** 9),
    Family("cuadrado_pentagonal", "Aritmética",
           "Un número que sea a la vez cuadrado y pentagonal.",
           lambda n: is_square(n) and is_pentagonal(n),
           lambda m: _univ_filter(_iter_pentagonal(m), is_square, m),
           10 ** 9),
    Family("triangular_pentagonal", "Aritmética",
           "Un número que sea a la vez triangular y pentagonal.",
           lambda n: is_triangular(n) and is_pentagonal(n),
           lambda m: _univ_filter(_iter_pentagonal(m), is_triangular, m),
           10 ** 9),
    Family("fibonacci_triangular", "Recurrencias",
           "Un número que esté en la sucesión de Fibonacci y además sea triangular.",
           lambda n: is_triangular(n) and n in set(fib_numbers(10 ** 7)),
           lambda m: _univ_filter(fib_numbers(m), is_triangular, m),
           10 ** 7),
    Family("fibonacci_primo", "Recurrencias",
           "Un número de Fibonacci que además sea primo.",
           lambda n: n in {f for f in fib_numbers(10 ** 7) if is_prime(f)},
           lambda m: [f for f in fib_numbers(m) if is_prime(f)],
           10 ** 7),
    Family("pell", "Recurrencias",
           "Un número de Pell: la recurrencia que generaliza a los cuadrados alternados.",
           lambda n: n in set(pell_numbers(10 ** 7)),
           lambda m: pell_numbers(m),
           10 ** 7),
    Family("lucas", "Recurrencias",
           "Un número de Lucas.",
           lambda n: n in set(lucas_numbers(10 ** 7)),
           lambda m: lucas_numbers(m),
           10 ** 7),
    Family("keith", "Estructura",
           "Un número de Keith: aparece en su propia sucesión de dígitos.",
           lambda n: n in _KEITH_SET,
           lambda m: [k for k in _KEITH_SET if k <= m],
           200_000),
    Family("narcisista", "Estructura",
           "Un número narcisista: la suma de sus dígitos, cada uno elevado a la cantidad de dígitos, da el mismo número.",
           lambda n: n in _NARCISISTA_SET,
           lambda m: [k for k in _NARCISISTA_SET if k <= m],
           10 ** 6),
    Family("wieferich", "Estructura",
           "Un primo de Wieferich: uno que cumple 2^(p−1) ≡ 1 (mod p²).",
           lambda n: n in set(wieferich_primes()),
           lambda m: [p for p in wieferich_primes() if p <= m],
           100_000),
    Family("catalan", "Recurrencias",
           "Un número de Catalan.",
           lambda n: n in set(catalan_numbers(10 ** 7)),
           lambda m: catalan_numbers(m),
           10 ** 7),
    Family("bell", "Recurrencias",
           "Un número de Bell.",
           lambda n: n in set(bell_numbers(10 ** 6)),
           lambda m: bell_numbers(m),
           10 ** 6),
    Family("mersenne", "Recurrencias",
           "Un primo de Mersenne: 2^p − 1 con p primo.",
           lambda n: any(m == n for _, m in mersenne_primes()),
           lambda m: [m for _, m in mersenne_primes() if m <= m],
           10 ** 9),
    Family("perfectos", "Recurrencias",
           "Un número perfecto: la suma de sus divisores propios da el mismo número.",
           lambda n: any(2 ** (p - 1) * m == n for p, m in mersenne_primes()),
           lambda m: [2 ** (p - 1) * x for p, x in mersenne_primes() if 2 ** (p - 1) * x <= m],
           10 ** 9),
    Family("amicables", "Aritmética profunda",
           "Un número amigo: existe otro número distinto que comparte con él la suma de divisores propios.",
           lambda n: n in set(_univ_amicable(200_000)),
           lambda m: _univ_amicable(min(m, 200_000)),
           200_000),
    Family("legendre", "Teoría de números",
           "Un número menor que 1 000 000 que NO se pueda escribir como suma de tres cuadrados enteros.",
           lambda n: n < 10 ** 6 and is_legendre_form(n),
           lambda m: _univ_legendre(m),
           10 ** 6),
]


# ---------------------------------------------------------------- scoring
def structural_fame(n: int, maxv: int) -> float:
    """Qué tan probable es que alguien escriba este número, por su forma.

    Números redondos, chicos, palíndromos o de dígitos repetidos son los
    primeros que se le ocurren a cualquiera. Los feos, grandes y con dígitos
    raros, no.
    """
    s = str(n)
    g = 0.0
    if n % 1000 == 0:
        g += 0.30
    elif n % 100 == 0:
        g += 0.20
    elif n % 10 == 0:
        g += 0.09
    if s == s[::-1]:
        g += 0.14
    if len(set(s)) == 1:
        g += 0.16
    if n < 100:
        g += 0.22
    elif n < 1000:
        g += 0.10
    # magnitud: los números chicos seProduces más fácil
    g += 0.30 * (1 - math.log10(max(n, 2)) / math.log10(maxv + 1))
    return min(g, 1.0)


def composite_fame(n: int, maxv: int, use_wiki: bool = True) -> float:
    """Fama = corpus (pageviews) + forma del número."""
    st = structural_fame(n, maxv)
    if not use_wiki:
        return st
    return 0.75 * fama.wiki_signal(n) + 0.25 * st


def score_family(fam: Family, maxv: int) -> list[tuple[int, float, str, int]]:
    """Puntuar el conjunto de respuestas de un prompt.

    Krillion define sus tiers comparando la frecuencia "compared with the
    other possibilities for that question": son cuantiles dentro del prompt.
    Pero un cuantil puro no dice nada del número en sí. Acá se mezclan las
    dos cosas:

        g = 0.55 * fama_absoluta + 0.45 * posición_en_el_prompt

    - fama_absoluta: qué tan conocido es ese número (pageviews + forma).
    - posición: 1 para el más conocido del prompt, 0 para el más oscuro.
    """
    universe = sorted({v for v in fam.universe(maxv) if v > 0})
    if len(universe) < 2:
        return []
    use_wiki = len(universe) <= WIKI_LIMIT
    if use_wiki:
        fama.warm(universe)
    scored = [(a, composite_fame(a, maxv, use_wiki)) for a in universe]
    scored.sort(key=lambda t: t[1], reverse=True)
    last = len(scored) - 1
    out = []
    for i, (a, c) in enumerate(scored):
        q = 1 - i / last
        g = 0.55 * c + 0.45 * q
        out.append((a, g, *tier_for(g)))
    return out


def build_round(rng: random.Random, pool: list[Family]) -> dict:
    fam = rng.choice(pool)
    maxv = min(rng.choice([10 ** 5, 10 ** 6, 10 ** 7, 10 ** 8, 10 ** 9]), fam.cap)
    answers = score_family(fam, maxv)
    if len(answers) < 2:
        return build_round(rng, pool)
    return {"fam": fam, "maxv": maxv, "answers": answers,
            "map": {a: (name, pts) for a, _, name, pts in answers}}


def daily(d: date | None = None, seed: int | None = None) -> list[dict]:
    d = d or date.today()
    rng = random.Random(seed if seed is not None else d.toordinal())
    pool = FAMILIES[:]
    rng.shuffle(pool)
    rounds = []
    for fam in pool[:ROUNDS]:
        rounds.append(build_round(rng, [fam]))
    return rounds


# ---------------------------------------------------------------- salida
def show(rounds: list[dict], d: date | None = None) -> None:
    d = d or date.today()
    print(f"\n  abismo · {d.isoformat()} · {ROUNDS} prompts · 1 punto = {PTS_PER_M} m\n")
    for i, r in enumerate(rounds, 1):
        best = r["answers"][-1]
        print(f"  {i}. [{r['fam'].stratum}]  {r['fam'].prompt}")
        for a, g, name, pts in r["answers"][:6]:
            v = fama.wiki_views(a)
            tag = "  sin artículo" if v is None else f"{v:>9} v/mes"
            mark = "   ← la gema" if (a, g, name, pts) == best else ""
            print(f"       {a:>12}  {name:<11} {pts:>3} pts  {tag}{mark}")
        if len(r["answers"]) > 6:
            print(f"       ... y {len(r['answers']) - 6} respuestas válidas más")
        print()


def play(rounds: list[dict], seconds: int = 25) -> None:
    total = 0
    print("\n  abismo · 25s por prompt. Type your answer + Enter.\n")
    for i, r in enumerate(rounds, 1):
        fam = r["fam"]
        print(f"  {i}. [{fam.stratum}]  {fam.prompt}")
        raw = read_with_time_limit(seconds)
        if raw is None:
            print("       ⏱  tiempo — 0 pts\n")
            continue
        if not raw.strip().lstrip("-").isdigit():
            print("       ✗  no es un número — 0 pts\n")
            continue
        n = int(raw)
        if not fam.valid(n):
            print("       ✗  no cumple la condición — 0 pts\n")
            continue
        hit = r["map"].get(n)
        if hit is None:
            print("       ✗  fuera del rango del prompt — 0 pts\n")
            continue
        name, pts = hit
        total += pts
        print(f"       ✓  {n}  {name}  {pts} pts   (+{pts * PTS_PER_M} m)\n")
    depth = total * PTS_PER_M
    print(f"  ── {total} pts · {depth} m de profundidad ──\n")


def read_with_time_limit(seconds: int):
    def boom(signum, frame):
        raise TimeoutError
    old = signal.signal(signal.SIGALRM, boom)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        return input("   > ").strip()
    except (TimeoutError, EOFError):
        print()
        return None
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)


def main() -> None:
    mode = sys.argv[1] if len(sys.argv) > 1 else "daily"
    rounds = daily()
    if mode == "daily":
        show(rounds)
    elif mode == "play":
        play(rounds)
    elif mode == "tune":
        for r in rounds:
            print(f"{r['fam'].key:<22} n={len(r['answers']):>4}  " +
                  " ".join(f"{a}:{g:.2f}/{name[:3]}" for a, g, name, _ in r["answers"][:10]))
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
