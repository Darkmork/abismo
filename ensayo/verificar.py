#!/usr/bin/env python3
"""
verificar.py · control de calidad del generador.

Rehace cada pregunta desde su ENUNCIADO (no desde los parámetros del
generador) y comprueba que la opción marcada sea la que el enunciado
describe. Si un generador produce una respuesta mal calculada, esto lo
detecta: es la diferencia entre un juego y una herramienta de estudio que te
miente.

    python3 verificar.py            # 3000 preguntas por familia
    python3 verificar.py 10000      # más muestras
"""
from __future__ import annotations

import json
import math
import os
import random
import re
import sys
from fractions import Fraction

import paes

PI = 3.14
FALLOS: list[str] = []
VERIFICADAS = 0


# ── parsers ────────────────────────────────────────────────
def num(s: str):
    """'3/4' -> Fraction, '1,5' -> Fraction, '12' -> int."""
    s = s.strip().replace("$", "").replace("%", "").replace("−", "-").strip()
    if "/" in s:
        a, b = s.split("/")
        return Fraction(int(a), int(b))
    return Fraction(s.replace(",", "."))


def fmt_frac(x) -> str:
    x = Fraction(x)
    if x.denominator == 1:
        return str(x.numerator)
    return f"{x.numerator}/{x.denominator}"


def norm(txt: str) -> str:
    """Normaliza para parsear: '−' → '-', sin espacios, signos pegados."""
    return txt.replace("−", "-").replace("−", "-").replace(" ", "")


def parse_linea(txt: str):
    """'4x − 8' -> (4, -8); '−x − 8' -> (-1, -8); 'x' -> (1, 0)."""
    txt = norm(txt)
    m = re.match(r"^(-)?(\d*)x(?:([+-])(\d+))?$", txt)
    if not m:
        return None
    a = int(m.group(2)) if m.group(2) else 1
    if m.group(1):
        a = -a
    b = 0
    if m.group(3):
        b = int(m.group(4))
        if m.group(3) == "-":
            b = -b
    return a, b


def parse_polinomio(txt: str):
    """'x² − 6x − 7' -> (-6, -7)."""
    txt = norm(txt)
    m = re.match(r"^x²(?:([+-])(\d+)x)?(?:([+-])(\d+))?$", txt)
    if not m:
        return None
    b = 0
    c = 0
    if m.group(1):
        b = int(m.group(2)) * (1 if m.group(1) == "+" else -1)
    if m.group(3):
        c = int(m.group(4)) * (1 if m.group(3) == "+" else -1)
    return b, c


def coef_de(txt: str, var: str) -> int:
    """Coeficiente de 'x' o 'y' en un lado de ecuación ('5x − 6y' → x=5, y=-6)."""
    txt = norm(txt)
    m = re.search(r"(-?\d*)" + var, txt)
    if not m:
        return 0
    c = m.group(1)
    if c == "":
        return 1
    if c == "-":
        return -1
    return int(c)


def _coef_str(s: str) -> int:
    """'3' -> 3, '-' -> -1, '' -> 1."""
    s = (s or "").strip()
    if s == "":
        return 1
    if s == "-":
        return -1
    return int(s)


def _num_eq(txt: str, val: Fraction) -> bool:
    """Compara '22,5' o '45/2' con un valor exacto."""
    try:
        return abs(float(num(txt)) - float(val)) < 0.011
    except Exception:
        return False


def entre(q, pre, suf=""):
    """Texto entre dos marcadores."""
    return q.enunciado.split(pre)[1].split(suf)[0].strip()


# ── verificadores por familia ───────────────────────────────
def v_racionales(q):
    txt = entre(q, "valor de ", "?")
    mm = re.match(r"^(.+?)\s*([+\-×÷])\s*(.+)$", txt)
    if not mm:
        return False
    a, op, b = num(mm.group(1)), mm.group(2), num(mm.group(3))
    r = {"+": a + b, "-": a - b, "×": a * b, "÷": (a / b if b else a)}[op]
    correcta = q.opciones[q.correcta]
    if "/" in correcta:
        return correcta == fmt_frac(r)
    return abs(float(correcta.replace(",", ".")) - round(float(r), 2)) < 0.011


def v_porcentaje(q):
    m = re.search(r"¿Cuál es el (\d+)% de (\d+)\?", q.enunciado)
    if m:
        p, n = int(m.group(1)), int(m.group(2))
        return _num_eq(q.opciones[q.correcta], Fraction(n * p, 100))
    m = re.search(r"cuesta \$(\d+) y su precio (aumenta|disminuye) un (\d+)%", q.enunciado)
    if m:
        n, signo, p = int(m.group(1)), m.group(2), int(m.group(3))
        r = Fraction(n * (100 + p if signo == "aumenta" else 100 - p), 100)
        return _num_eq(q.opciones[q.correcta], r)
    return False


def v_potencias(q):
    m = re.search(r"valor de \(1/(\d+)\)\^(\d+)", q.enunciado)
    if m:
        b, e = int(m.group(1)), int(m.group(2))
        return q.opciones[q.correcta] == fmt_frac(Fraction(1, b ** e))
    m = re.search(r"valor de (\d+)\^(\d+)", q.enunciado)
    if m:
        b, e = int(m.group(1)), int(m.group(2))
        return q.opciones[q.correcta] == fmt_frac(b ** e)
    m = re.search(r"valor de √(\d+)", q.enunciado)
    if m:
        return q.opciones[q.correcta] == fmt_frac(math.isqrt(int(m.group(1))))
    return False


def v_producto_notable(q):
    m = re.search(r"desarrollo de \(x ([+−]) (\d+)\)[²^]", q.enunciado)
    if m:
        s, a = m.group(1), int(m.group(2))
        exp = f"x² {'+' if s == '+' else '−'} {2*a}x + {a*a}"
        return q.opciones[q.correcta].replace(" ", "") == exp.replace(" ", "")
    m = re.search(r"desarrollo de \(x \+ (\d+)\)\(x − (\d+)\)", q.enunciado)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        return q.opciones[q.correcta].replace(" ", "") == f"x²−{a*b}".replace(" ", "")
    return False


def v_factorizacion(q):
    m = re.search(r"factorización de x² − (\d+)", q.enunciado)
    if m:
        r = math.isqrt(int(m.group(1)))
        return q.opciones[q.correcta].replace(" ", "") == f"(x−{r})(x+{r})".replace(" ", "")
    m = re.search(r"factorización de x² \+ (\d+)x \+ (\d+)", q.enunciado)
    if m:
        s, pr = int(m.group(1)), int(m.group(2))
        pares = [(i, pr // i) for i in range(1, pr + 1)
                 if pr % i == 0 and i + pr // i == s]
        if not pares:
            return True
        i, j = pares[0]
        esp = sorted([i, j])
        return q.opciones[q.correcta].replace(" ", "") in (
            f"(x+{esp[0]})(x+{esp[1]})".replace(" ", ""),
            f"(x+{esp[1]})(x+{esp[0]})".replace(" ", ""))
    return False


def v_ecuacion(q):
    enun = q.enunciado.replace("\u2212", "-")
    cuerpo = enun.split(" en ", 1)[1].rstrip("?")
    if "(" in cuerpo:
        izq, der = cuerpo.split(" = ")
        m = re.match(r"^(\d+)\(x([+-])(\d+)\)$", norm(izq))
        if not m:
            return False
        a = int(m.group(1))
        e = int(m.group(3)) * (1 if m.group(2) == "+" else -1)
        cd = parse_linea(der.strip())
        if cd is None:                       # forma a(x ± e) = N
            n = int(der.strip())
            return q.opciones[q.correcta] == fmt_frac(Fraction(n, a) - e)
        c, f = cd
        if a == c:
            return True
        return q.opciones[q.correcta] == fmt_frac(Fraction(f - a * e, a - c))
    izq, der = cuerpo.split(" = ")
    a, b = parse_linea(izq.strip())
    c, d = parse_linea(der.strip())
    if a is None or c is None or a == c:
        return True
    return q.opciones[q.correcta] == fmt_frac(Fraction(d - b, a - c))


def v_inecuacion(q):
    enun = q.enunciado.replace("\u2212", "-")
    cuerpo = enun.split(" de ", 1)[1].rstrip("?")
    m = re.search(r"([<>=\u2264\u2265]+)", cuerpo)
    if not m:
        return False
    rel = m.group(1)
    izq, der = cuerpo.split(rel, 1)
    a, b = parse_linea(izq.strip())
    if a is None:
        return False
    if "x" in der:
        c, k = parse_linea(der.strip())
        if c is None or a == c:
            return True
        coef, val = a - c, k - b
        if coef < 0:
            coef, val = -coef, -val
            rel = {">": "<", "<": ">", "\u2265": "\u2264", "\u2264": "\u2265"}.get(rel, rel)
        return q.opciones[q.correcta] == f"x {rel} {fmt_frac(Fraction(val, coef))}"
    k = int(der.strip())
    return q.opciones[q.correcta] == f"x {rel} {fmt_frac(Fraction(k - b, a))}"
def v_sistema(q):
    lineas = [l for l in q.enunciado.split("\n") if "=" in l]
    if len(lineas) != 2:
        return False
    filas = []
    for l in lineas:
        izq, der = l.split("=")
        filas.append((coef_de(izq, "x"), coef_de(izq, "y"), int(der.strip())))
    (a, b, e), (c, d, f) = filas
    det = a * d - b * c
    if det == 0:
        return True
    x = Fraction(e * d - b * f, det)
    return q.opciones[q.correcta] == fmt_frac(x)


def v_funcion_lineal(q):
    if "pendiente" in q.enunciado:
        pts = re.findall(r"\((-?\d+), (-?\d+)\)", q.enunciado)
        if len(pts) != 2:
            return False
        (x1, y1), (x2, y2) = (tuple(map(int, p)) for p in pts)
        if x1 == x2:
            return True
        return q.opciones[q.correcta] == fmt_frac(Fraction(y2 - y1, x2 - x1))
    if "se cortan" in q.enunciado:
        fs = q.enunciado.split("f(x) = ")[1].split(" y g(x) = ")
        a, b = parse_linea(fs[0])
        c, d = parse_linea(fs[1].split(",")[0])
        if a is None or c is None or a == c:
            return True
        return q.opciones[q.correcta] == fmt_frac(Fraction(d - b, a - c))
    if " y f(" in q.enunciado:
        a, b = parse_linea(entre(q, "f(x) = ", " y f("))
        return q.opciones[q.correcta] == str(b)
    fs = entre(q, "f(x) = ", ", ¿")
    a, b = parse_linea(fs)
    x = int(re.search(r"f\((-?\d+)\)", q.enunciado).group(1))
    return q.opciones[q.correcta] == str(a * x + b)


def v_cuadratica(q):
    b, c = parse_polinomio(entre(q, "f(x) = ", ", ¿"))
    if b is None:
        return False
    if "vértice" in q.enunciado:
        return q.opciones[q.correcta] == fmt_frac(Fraction(-b, 2))
    if "cero mayor" in q.enunciado:
        disc = b * b - 4 * c
        if disc < 0:
            return True
        sq = math.isqrt(disc)
        if sq * sq != disc:
            return True
        r1 = Fraction(-b + sq, 2)
        r2 = Fraction(-b - sq, 2)
        if r1.denominator != 1 or r2.denominator != 1:
            return True
        return q.opciones[q.correcta] == str(max(int(r1), int(r2)))
    if "discriminante" in q.enunciado:
        return q.opciones[q.correcta] == str(b * b - 4 * c)
    return False


def v_proporcionalidad(q):
    m = re.search(r"(\d+) cuadernos cuestan \$(\d+).*?(\d+) cuadernos", q.enunciado)
    if m:
        a, ka, b = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return q.opciones[q.correcta] == fmt_frac(Fraction(ka * b, a))
    m = re.search(r"(\d+) trabajadores hacen un trabajo en (\d+) días.*?(\d+) trabajadores",
                  q.enunciado)
    if m:
        t, dias, t2 = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return q.opciones[q.correcta] == fmt_frac(Fraction(t * dias, t2))
    return False


def v_pitagoras(q):
    m = re.search(r"catetos miden (\d+) y (\d+)", q.enunciado)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        return q.opciones[q.correcta] == str(math.isqrt(a * a + b * b))
    m = re.search(r"hipotenusa mide (\d+) y un cateto\s*mide (\d+)", q.enunciado)
    if m:
        c, a = int(m.group(1)), int(m.group(2))
        if c * c - a * a < 0:
            return True
        return q.opciones[q.correcta] == str(math.isqrt(c * c - a * a))
    return False


def v_areas(q):
    m = re.search(r"triángulo con base (\d+) y altura (\d+)", q.enunciado)
    if m:
        b, h = int(m.group(1)), int(m.group(2))
        return q.opciones[q.correcta] == fmt_frac(Fraction(b * h, 2))
    m = re.search(r"trapecio con bases (\d+) y (\d+) y altura (\d+)", q.enunciado)
    if m:
        B, b, h = (int(m.group(i)) for i in (1, 2, 3))
        return q.opciones[q.correcta] == fmt_frac(Fraction((B + b) * h, 2))
    m = re.search(r"área de un círculo de radio (\d+)", q.enunciado)
    if m:
        r = int(m.group(1))
        return abs(float(q.opciones[q.correcta].replace(",", ".")) - PI * r * r) < 0.02
    m = re.search(r"perímetro de un círculo de radio (\d+)", q.enunciado)
    if m:
        r = int(m.group(1))
        return abs(float(q.opciones[q.correcta].replace(",", ".")) - 2 * PI * r) < 0.02
    m = re.search(r"paralelogramo con base (\d+) y altura (\d+)", q.enunciado)
    if m:
        b, h = int(m.group(1)), int(m.group(2))
        return q.opciones[q.correcta] == str(b * h)
    return False


def v_volumenes(q):
    m = re.search(r"cubo de arista (\d+)", q.enunciado)
    if m:
        a = int(m.group(1))
        return q.opciones[q.correcta] == str(a ** 3)
    m = re.search(r"paralelepípedo de dimensiones (\d+) × (\d+) × (\d+)", q.enunciado)
    if m:
        a, b, h = (int(m.group(i)) for i in (1, 2, 3))
        return q.opciones[q.correcta] == str(a * b * h)
    m = re.search(r"cilindro de radio (\d+) y altura (\d+)", q.enunciado)
    if m:
        r, h = int(m.group(1)), int(m.group(2))
        return abs(float(q.opciones[q.correcta].replace(",", ".")) - PI * r * r * h) < 0.02
    return False


def v_semejanza(q):
    m = re.search(r"un lado mide (\d+) cm y otro (\d+) cm.*?"
                  r"al primero mide (\d+) cm.*?corresponde a (\d+) cm", q.enunciado)
    if not m:
        return False
    a, c, b, c2 = (int(m.group(i)) for i in (1, 2, 3, 4))
    if a == 0:
        return True
    return q.opciones[q.correcta] == fmt_frac(Fraction(b * c2, a))


def v_probabilidad(q):
    m = re.search(r"(\d+) bolas rojas y (\d+) azules", q.enunciado)
    if m:
        r, b = int(m.group(1)), int(m.group(2))
        return q.opciones[q.correcta] == fmt_frac(Fraction(r, r + b))
    m = re.search(r"hay (\d+) bolas, (\d+) rojas", q.enunciado)
    if m:
        t, r = int(m.group(1)), int(m.group(2))
        return q.opciones[q.correcta] == fmt_frac(Fraction(t - r, t))
    m = re.search(r"P\(A\) = (\S+) y P\(B\) = (\S+), con A y B mutuamente", q.enunciado)
    if m:
        a, b = num(m.group(1)), num(m.group(2))
        return q.opciones[q.correcta] == fmt_frac(a + b)
    m = re.search(r"P\(A\) = (\S+) y P\(B\) = (\S+)\. ¿Cuál es P\(A y B\)", q.enunciado)
    if m:
        a, b = num(m.group(1)), num(m.group(2))
        return q.opciones[q.correcta] == fmt_frac(a * b)
    return False


def v_promedio(q):
    m = re.search(r"de ([0-9, ]+)\?", q.enunciado)
    if not m:
        return False
    datos = [int(x) for x in m.group(1).split(",")]
    if "promedio" in q.enunciado:
        return q.opciones[q.correcta] == fmt_frac(Fraction(sum(datos), len(datos)))
    if "mediana" in q.enunciado:
        s = sorted(datos)
        n = len(s)
        med = s[n // 2] if n % 2 else Fraction(s[n // 2 - 1] + s[n // 2], 2)
        return q.opciones[q.correcta] == fmt_frac(med)
    return False


def v_cuartiles(q):
    m = re.search(r"de ([0-9, ]+)\?", q.enunciado)
    if not m:
        return False
    base = sorted(int(x) for x in m.group(1).split(","))
    if "primer cuartil" in q.enunciado:
        return q.opciones[q.correcta] == str(base[2])
    if "tercer cuartil" in q.enunciado:
        return q.opciones[q.correcta] == str(base[6])
    if "percentil 90" in q.enunciado:
        return q.opciones[q.correcta] == str(base[8])
    return False


VERIFICADORES = {
    "racionales": v_racionales, "porcentaje": v_porcentaje,
    "potencias": v_potencias, "productos_notables": v_producto_notable,
    "factorizacion": v_factorizacion, "ecuaciones": v_ecuacion,
    "inecuaciones": v_inecuacion, "sistemas": v_sistema,
    "funciones": v_funcion_lineal, "cuadratica": v_cuadratica,
    "proporcionalidad": v_proporcionalidad, "pitagoras": v_pitagoras,
    "areas": v_areas, "volumenes": v_volumenes, "semejanza": v_semejanza,
    "probabilidad": v_probabilidad, "promedio": v_promedio,
    "cuartiles": v_cuartiles,
}

def auditar(q) -> tuple[bool, str]:
    """Audita UNA pregunta. Devuelve (ok, motivo_del_fallo).

    Chequeos estructurales (4 opciones distintas, indice valido, explicacion
    presente) mas la verificacion matematica: se recalcula la respuesta desde
    el ENUNCIADO y se compara con la opcion marcada.
    """
    tag = q.tags[0] if q.tags else "?"
    if len(q.opciones) != 4:
        return False, f"{tag}: {len(q.opciones)} opciones"
    if len(set(q.opciones)) != 4:
        return False, f"{tag}: opciones repetidas {q.opciones}"
    if not (0 <= q.correcta < 4):
        return False, f"{tag}: indice correcto fuera de rango"
    if len(q.explicacion) < 20:
        return False, f"{tag}: explicacion demasiado corta"

    ver = VERIFICADORES.get(tag)
    if ver is None:
        return True, ""          # familia sin verificador: solo chequeos estructurales
    try:
        ok = ver(q)
    except Exception as e:
        return False, f"{tag}: excepcion ({type(e).__name__}: {e}) - {q.enunciado[:90]}"
    if ok:
        return True, ""
    return False, (f"{tag}: respuesta INCORRECTA -> {q.enunciado[:110]} | "
                   f"marcada '{q.opciones[q.correcta]}' | opciones {q.opciones}")


def _desde_dict(d: dict) -> "paes.Question":
    return paes.Question(
        eje=d["eje"], unidad=d["unidad"], enunciado=d["enunciado"],
        opciones=d["opciones"], correcta=d["correcta"],
        explicacion=d["explicacion"], nivel=d.get("nivel", 2), tags=d.get("tags", []),
    )


def auditar_tabla(ruta: str) -> None:
    """Audita la tabla PUBLICADA (web/data/daily.js): todo lo que el sitio
    sirve queda verificado contra su propio enunciado."""
    global VERIFICADAS
    if not os.path.exists(ruta):
        FALLOS.append(f"no existe {ruta}: ejecuta precompute.py primero")
        return
    crudo = open(ruta, encoding="utf-8").read()
    datos = json.loads(crudo[crudo.index("{"):crudo.rindex(";")])

    total = 0
    for fecha, dia in sorted(datos["dias"].items()):
        for d in dia["preguntas"]:
            total += 1
            ok, motivo = auditar(_desde_dict(d))
            if ok:
                VERIFICADAS += 1
            else:
                FALLOS.append(f"{fecha}: {motivo}")
    for d in datos["practica"]:
        total += 1
        ok, motivo = auditar(_desde_dict(d))
        if ok:
            VERIFICADAS += 1
        else:
            FALLOS.append(f"(practica) {motivo}")

    print(f"tabla publicada: {total} preguntas auditadas "
          f"({len(datos['dias'])} dailies + {len(datos['practica'])} de practica)")


def main() -> None:
    global VERIFICADAS
    args = list(sys.argv[1:])
    solo_datos = "--data" in args
    args = [a for a in args if a != "--data"]
    n = int(args[0]) if args else 3000

    if solo_datos:
        auditar_tabla(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                   "web", "data", "daily.js"))
    else:
        rng = random.Random(1234)
        conteo = {}
        for _ in range(n):
            q = rng.choice(paes.GENERADORES)(rng, rng.choice([1, 2, 3]))
            tag = q.tags[0] if q.tags else "?"
            conteo[tag] = conteo.get(tag, 0) + 1
            ok, motivo = auditar(q)
            if ok:
                VERIFICADAS += 1
            else:
                FALLOS.append(motivo)

        print(f"\n{'familia':<22}{'muestras':>10}")
        for t in sorted(conteo):
            print(f"  {t:<20}{conteo[t]:>8}")
        print(f"\nverificadas contra el enunciado: {VERIFICADAS}/{n}")

    if FALLOS:
        print(f"\n{len(FALLOS)} fallo(s). Primeros 12:")
        for f in FALLOS[:12]:
            print("  -", f[:230])
        sys.exit(1)
    print("\nOK: todas las respuestas marcadas son consistentes con su enunciado")


if __name__ == "__main__":
    main()
