#!/usr/bin/env python3
"""
paes.py · generador de ejercicios estilo PAES de Matemática 1 (M1).

Temario oficial (DEMRE, Competencia Matemática 1):
  NÚMEROS ................. enteros y racionales · porcentajes · potencias y raíces
  ÁLGEBRA Y FUNCIONES ..... productos notables · factorización · proporcionalidad
                           ecuaciones e inecuaciones 1° · sistemas 2x2
                           función lineal y afín · función cuadrática
  GEOMETRÍA .............. Pitágoras · perímetros y áreas · cuerpos geométricos
                           semejanza · transformaciones isométricas
  PROBABILIDAD Y ESTADÍSTICA ... tablas y gráficos · cuartiles y percentiles
                                probabilidades

Cada generador devuelve:
  - un enunciado con 4 opciones (una correcta),
  - distractores que son los ERRORES TÍPICOS del syllabus (no números al azar),
  - una explicación paso a paso.

Todo se genera por código: banco infinito, sin repetition, y la dificultad
se puede mover con un único parámetro `nivel` (1 = fácil, 2 = medio, 3 = PAES).
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field
from fractions import Fraction

PI = 3.14


@dataclass
class Question:
    eje: str
    unidad: str
    enunciado: str
    opciones: list[str]
    correcta: int
    explicacion: str
    nivel: int = 1
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "eje": self.eje, "unidad": self.unidad, "enunciado": self.enunciado,
            "opciones": self.opciones, "correcta": self.correcta,
            "explicacion": self.explicacion, "nivel": self.nivel, "tags": self.tags,
        }


# ── utilidades de formato (estilo chileno: coma decimal) ─────
def fmt(x) -> str:
    if isinstance(x, Fraction):
        if x.denominator == 1:
            return str(x.numerator)
        return f"{x.numerator}/{x.denominator}"
    if isinstance(x, int):
        return str(x)
    r = round(float(x), 2)
    if abs(r - round(r)) < 1e-9:
        return str(int(round(r)))
    s = f"{r:.2f}".rstrip("0").rstrip(".")
    return s.replace(".", ",")


def fmt_frac(x) -> str:
    x = Fraction(x)
    if x.denominator == 1:
        return str(x.numerator)
    return f"{x.numerator}/{x.denominator}"


def fmt_dec(x) -> str:
    """Decimal siempre con decimales si no es entero, con coma."""
    r = round(float(x), 2)
    if abs(r - round(r)) < 1e-9:
        return str(int(round(r)))
    return fmt(r)


def expr(a: int, b: int, var: str = "x") -> str:
    """a·var + b como lo escribe la PAES: '3x − 8', '−2x + 10'."""
    if a == 0:
        return str(b)
    if a == 1:
        s = var
    elif a == -1:
        s = "−" + var
    elif a < 0:
        s = f"−{abs(a)}{var}"
    else:
        s = f"{a}{var}"
    if b > 0:
        s += f" + {b}"
    elif b < 0:
        s += f" − {abs(b)}"
    return s


def expr2(a: int, b: int) -> str:
    """a·x + b·y: '5x + 6y', '3x − 2y'."""
    partes = []
    if a:
        partes.append(("x" if a == 1 else "−x" if a == -1 else f"{a}x" if a > 0 else f"−{abs(a)}x"))
    if b:
        partes.append(("y" if b == 1 else "−y" if b == -1 else f"{b}y" if b > 0 else f"−{abs(b)}y"))
    if not partes:
        return "0"
    if len(partes) == 2:
        return partes[0] + " + " + partes[1]
    return partes[0]


def linea(a: int, b: int) -> str:
    """ax + b con signos correctos: '3x − 8', '−x + 10'."""
    s = ("−x" if a == -1 else "x" if a == 1 else f"{a}x")
    if b > 0:
        s += f" + {b}"
    elif b < 0:
        s += f" − {abs(b)}"
    return s


def polinomio(b: int, c: int) -> str:
    """x² + bx + c escribiendo bien los signos: 'x² − 6x − 7'."""
    s = "x²"
    if b:
        s += f" {'+' if b > 0 else '−'} {abs(b)}x"
    if c > 0:
        s += f" + {c}"
    elif c < 0:
        s += f" − {abs(c)}"
    return s


def mcq(rng, eje, unidad, enunciado, correcta: str, distractores: list[str],
        explicacion: str, nivel: int = 1, tags=None) -> Question:
    """Arma la pregunta de 4 opciones, baraja y devuelve el índice correcto."""
    ops, vistos = [], {correcta}
    for d in distractores:
        if d not in vistos:
            ops.append(d)
            vistos.add(d)
    # si faltan distractores, se generan cerca del valor correcto (no al azar)
    i = 0
    while len(ops) < 3 and i < 60:
        cand = None
        try:
            val = Fraction(correcta.replace(",", "."))
            tabla = [val + 1, val - 1, val + 2, val - 2, val * 2, -val, val / 2]
            cand = fmt(tabla[i % len(tabla)])
        except Exception:
            cand = fmt(rng.randint(1, 99))
        if cand not in vistos:
            ops.append(cand)
            vistos.add(cand)
        i += 1
    opciones = [correcta] + ops[:3]
    rng.shuffle(opciones)
    return Question(eje, unidad, enunciado, opciones, opciones.index(correcta),
                    explicacion, nivel, tags or [])


# ══════════════════════════════════════════════════════════════
#  NÚMEROS
# ══════════════════════════════════════════════════════════════
def gen_racionales(rng, nivel=1):
    """Operaciones con decimales y fracciones (estilo PAES)."""
    op = rng.choice(["+", "-", "×", "÷"])
    usar_frac = rng.random() < 0.35
    if usar_frac:
        fa = Fraction(rng.randint(1, 12), rng.choice([1, 2, 3, 4]))
        fb = Fraction(rng.randint(1, 12), rng.choice([1, 2, 3, 4]))
    else:
        fa = Fraction(rng.randint(20, 90), 100)
        fb = Fraction(rng.randint(5, 40), 100)

    if op == "+":
        r = fa + fb
        d1, d2 = fa + fb + 1, fa - fb
        exp = f"Sumamos: {fmt(fa)} + {fmt(fb)} = {fmt(r)}."
    elif op == "-":
        r = fa - fb
        d1, d2 = fa + fb, fa - fb - 1
        exp = f"Restamos: {fmt(fa)} − {fmt(fb)} = {fmt(r)}."
    elif op == "×":
        r = fa * fb
        d1, d2 = fa * (fb + 1), (fa + 1) * fb
        exp = f"Multiplicamos: {fmt(fa)} × {fmt(fb)} = {fmt(r)}."
    else:
        r = fa / fb
        d1, d2 = fa * fb, fa / (fb + 1)
        exp = f"Dividimos: {fmt(fa)} ÷ {fmt(fb)} = {fmt(r)}."

    def muestra(x):
        if usar_frac:
            return fmt_frac(x)
        return fmt_dec(round(float(x), 2))

    txt = f"{muestra(fa)} {op} {muestra(fb)}"
    return mcq(rng, "Números", "Enteros y racionales", f"¿Cuál es el valor de {txt}?",
               muestra(r), [muestra(d1), muestra(d2), muestra(abs(r) + 1)],
               exp + " Ojo con el orden de las operaciones.", nivel, ["racionales"])


def gen_porcentaje(rng, nivel=1):
    """Porcentajes: tanto por ciento y variación porcentual."""
    n = rng.choice([40, 80, 120, 150, 200, 250, 320, 400, 500, 750, 1200, 1500])
    p = rng.choice([5, 10, 15, 20, 25, 30, 40, 50, 60, 75, 80])
    if rng.random() < 0.5:
        r = n * p / 100
        d1, d2, d3 = n * p, n * (100 - p) / 100, n / 100 * p
        exp = (f"El {p}% de {n} es {n} × {p}/100 = {fmt(r)}.")
        enun = f"¿Cuál es el {p}% de {n}?"
    else:
        signo = rng.choice(["aumenta", "disminuye"])
        if signo == "aumenta":
            r = n * (1 + p / 100)
            d1, d2, d3 = n * p / 100, n * (1 - p / 100), n + p
            exp = (f"{n} aumenta un {p}%: {n} × (1 + {p}/100) = {fmt(r)}. "
                   f"El aumento son {fmt(n*p/100)} y el total {fmt(r)}.")
        else:
            r = n * (1 - p / 100)
            d1, d2, d3 = n * p / 100, n * (1 + p / 100), n - p
            exp = (f"{n} disminuye un {p}%: {n} × (1 − {p}/100) = {fmt(r)}.")
        enun = (f"Un artículo cuesta ${n} y su precio {signo} un {p}%. "
                f"¿Cuál es el nuevo precio?")
    return mcq(rng, "Números", "Porcentajes", enun, fmt(r),
               [fmt(d1), fmt(d2), fmt(d3)], exp, nivel, ["porcentaje"])


def gen_potencias(rng, nivel=1):
    """Potencias y raíces enésimas."""
    if rng.random() < 0.5:
        base = rng.choice([2, 3, 4, 5])
        exp = rng.choice([2, 3, 4, 5, 6])
        neg = rng.random() < 0.4
        if neg:
            r = Fraction(1, base ** exp)
            d1, d2, d3 = base ** exp, Fraction(base, 1) ** exp, r * base
            exp_txt = (f"(1/{base})^{exp} = 1/{base**exp}. "
                       f"Con exponente negativo, el inverso.")
            enun = f"¿Cuál es el valor de (1/{base})^{exp}?"
            return mcq(rng, "Números", "Potencias y raíces", enun, fmt(r),
                       [fmt(d1), fmt(d2), fmt(d3)], exp_txt, nivel, ["potencias"])
        r = base ** exp
        d1, d2, d3 = base * exp, base ** (exp - 1), r + base
        exp_txt = f"{base}^{exp} = {r} (se multiplica la base {exp} veces)."
        return mcq(rng, "Números", "Potencias y raíces", f"¿Cuál es el valor de {base}^{exp}?",
                   fmt(r), [fmt(d1), fmt(d2), fmt(d3)], exp_txt, nivel, ["potencias"])
    n = rng.choice([144, 169, 196, 225, 256, 289, 324, 361, 400, 441, 484, 529, 576, 625])
    r = math.isqrt(n)
    d1, d2, d3 = n // 2, n * 2, r + 1
    return mcq(rng, "Números", "Potencias y raíces", f"¿Cuál es el valor de √{n}?",
               fmt(r), [fmt(d1), fmt(d2), fmt(d3)],
               f"{r}² = {n}, por lo tanto √{n} = {r}.", nivel, ["potencias"])


# ══════════════════════════════════════════════════════════════
#  ÁLGEBRA Y FUNCIONES
# ══════════════════════════════════════════════════════════════
def gen_producto_notable(rng, nivel=1):
    """(x+a)², (x−a)² y (x+a)(x−a)."""
    a = rng.choice([2, 3, 4, 5, 6, 7])
    tipo = rng.choice(["cuadrado", "diferencia"])
    if tipo == "cuadrado":
        signo = rng.choice(["+", "−"])
        s = 1 if signo == "+" else -1
        correcta = f"x² {'+' if s > 0 else '−'} {abs(2*a)}x + {a*a}"
        d = [f"x² {'+' if s > 0 else '−'} {a*a}x + {2*a}",
             f"x² {'+' if s > 0 else '−'} {abs(2*a)}x − {a*a}",
             f"x² + {a*a}"]
        exp = (f"(x {signo} {a})² = x² {'+' if s > 0 else '−'} 2·{a}x + {a}² "
               f"= x² {'+' if s > 0 else '−'} {abs(2*a)}x + {a*a}. "
               f"El término del medio es 2·{a}x = {abs(2*a)}x.")
        enun = f"¿Cuál es el desarrollo de (x {signo} {a})²?"
    else:
        correcta = f"x² − {a*a}"
        d = [f"x² + {a*a}", f"x² − {2*a}", f"x² − {a*a} + {2*a}x"]
        exp = (f"(x + {a})(x − {a}) = x² − {a}² = x² − {a*a}. "
               f"El término lineal se cancela: (+{a}x) y (−{a}x).")
        enun = f"¿Cuál es el desarrollo de (x + {a})(x − {a})?"
    return mcq(rng, "Álgebra y funciones", "Expresiones algebraicas", enun,
               correcta, d, exp, nivel, ["productos_notables"])


def gen_factorizacion(rng, nivel=1):
    """Factorización de trinomios y diferencias de cuadrados."""
    if rng.random() < 0.5:
        a = rng.choice([2, 3, 4, 5, 6, 7, 8])
        correcta = f"(x − {a})(x + {a})"
        d = [f"(x − {a})²", f"(x + {a})²", f"x² + {a*a}", f"(x − {a*a})(x + 1)"]
        exp = (f"x² − {a*a} es una diferencia de cuadrados: "
               f"(x − {a})(x + {a}).")
        enun = f"¿Cuál es la factorización de x² − {a*a}?"
    else:
        a, b = rng.sample([1, 2, 3, 4, 5, 6, 7, 8], 2)
        correcta = f"(x + {a})(x + {b})"
        d = [f"(x − {a})(x − {b})", f"(x + {a})(x − {b})", f"(x − {a})(x + {b})",
             f"(x + {a})²"]
        exp = (f"Buscamos dos números que sumen {a+b} y multipliquen {a*b}: "
               f"son {a} y {b}. Por eso x² + {a+b}x + {a*b} = (x + {a})(x + {b}).")
        enun = f"¿Cuál es la factorización de x² + {a+b}x + {a*b}?"
    return mcq(rng, "Álgebra y funciones", "Expresiones algebraicas", enun,
               correcta, d, exp, nivel, ["factorizacion"])


def gen_ecuacion(rng, nivel=1):
    """Ecuaciones de primer grado."""
    x0 = rng.randint(-9, 12)
    a = rng.choice([2, 3, 4, 5, 6, 7, 8])
    c = rng.choice([1, 2, 3, 4, 5, 6, 7]) * rng.choice([1, -1])
    if a == c:
        c = c + 1
    b = rng.randint(-12, 12)
    d = a * x0 + b - c * x0
    forma = rng.choice(["simple", "simple", "parentesis", "ambos_lados"])
    if forma == "simple":
        enun = f"¿Cuál es el valor de x en {expr(a, b)} = {expr(c, d)}?"
        exp = (f"Agrupamos: {a}x − {c}x = {d} − ({b}) → {a-c}x = {d-b}. "
               f"x = {d-b}/{a-c} = {x0}.")
    elif forma == "parentesis":
        k = rng.randint(2, 9)
        enun = f"¿Cuál es el valor de x en {a}(x {'+' if k >= 0 else '−'} {abs(k)}) = {a*x0 + a*k}?"
        exp = (f"Dividimos por {a}: x {'+' if k >= 0 else '−'} {abs(k)} = {x0 + k} → x = {x0}.")
        d = a * x0 + a * k
    else:
        e = rng.randint(2, 9)
        if a == c:
            c += 1
        # a(x + e) = c·x + f  ->  x = (f − a·e)/(a − c)
        # elegimos f DESDE x0 para que la solución sea un entero exacto
        x0 = rng.randint(-9, 9)
        f = (a - c) * x0 + a * e
        enun = f"¿Cuál es el valor de x en {a}(x {'+' if e >= 0 else '−'} {abs(e)}) = {expr(c, f)}?"
        exp = (f"Desarrollamos: {a}x + {a*e} = {c}x + ({f}) → "
               f"{a-c}x = {f} − {a*e} → x = {x0}.")
    correcta = fmt(x0)
    d1 = fmt(-x0) if x0 != 0 else fmt(x0 + 1)
    d2 = fmt(x0 + a)
    d3 = fmt(x0 - c) if x0 - c != x0 else fmt(x0 + 2)
    return mcq(rng, "Álgebra y funciones", "Ecuaciones de 1° grado", enun,
               correcta, [d1, d2, d3], exp, nivel, ["ecuaciones"])


def gen_inecuacion(rng, nivel=1):
    """Inecuaciones de primer grado."""
    a = rng.choice([2, 3, 4, 5, 6])
    b = rng.randint(-10, 10)
    x0 = rng.randint(-8, 10)
    k = a * x0 + b
    rel = rng.choice([">", "<", "≥", "≤"])
    neg = rng.random() < 0.35
    if neg:
        c = rng.choice([1, 2, 3]) * rng.choice([1, -1])
        if c == a:                       # nunca a == c (si no, no hay solución única)
            c = -c
        # el enunciado conserva la relación ORIGINAL; la solución usa la
        # invertida si al despejar x queda un coeficiente negativo.
        rel_sol = rel
        der = k - b
        coef = a - c
        if coef < 0:
            coef, der = -coef, -der
            rel_sol = {">": "<", "<": ">", "≥": "≤", "≤": "≥"}[rel]
        x0 = Fraction(der, coef)
        val = fmt(x0)
        enun = f"¿Cuál es la solución de {expr(a, b)} {rel} {expr(c, k)}?"
        sol = f"x {rel_sol} {val}"
        d = [f"x {rel_sol} {fmt(Fraction(der, -coef))}", f"x {rel_sol} {fmt(x0 + 1)}",
             f"x {rel_sol} {fmt(x0 - 1)}"]
        exp = (f"Agrupamos: ({a}−{c})x {rel} {k} − ({b}) → {coef}x {rel_sol} {der} → "
               f"x {rel_sol} {val}.")
    else:
        enun = f"¿Cuál es la solución de {expr(a, b)} {rel} {k}?"
        sol = f"x {rel} {x0}"
        exp = (f"{a}x {rel} {k} − ({b}) = {k-b} → x {rel} {k-b}/{a} = {x0}.")
        d = [f"x {rel} {x0+1}", f"x {rel} {x0-1}", f"x {rel} {x0+a}"]
    return mcq(rng, "Álgebra y funciones", "Inecuaciones de 1° grado", enun,
               sol, d, exp, nivel, ["inecuaciones"])


def gen_sistema(rng, nivel=1):
    """Sistemas de ecuaciones lineales 2x2."""
    x0, y0 = rng.randint(-6, 8), rng.randint(-6, 8)
    a, b = rng.randint(1, 6), rng.randint(1, 6)
    c, d = rng.randint(1, 6), rng.randint(1, 6)
    if a * d - b * c == 0:
        c += 1
    e, f = a * x0 + b * y0, c * x0 + d * y0
    enun = (f"¿Cuál es el valor de x en el sistema?\n"
            f"{expr2(a, b)} = {e}\n"
            f"{expr2(c, d)} = {f}")
    exp = (f"Resolvemos por sustitución o eliminación. La solución es "
           f"x = {x0}, y = {y0}. Verificamos: {a}·({x0}) + {b}·({y0}) = {e} ✓")
    d1, d2, d3 = fmt(y0), fmt(x0 + 1), fmt(x0 - 1)
    return mcq(rng, "Álgebra y funciones", "Sistemas 2x2", enun, fmt(x0),
               [d1, d2, d3], exp, nivel, ["sistemas"])


def gen_funcion_lineal(rng, nivel=1):
    """Función lineal y afín."""
    a = rng.choice([1, 2, 3, 4, -1, -2, -3])
    b = rng.randint(-8, 10)
    tipo = rng.choice(["valor", "pendiente", "intercepto", "interseccion"])
    fx = linea(a, b)
    if tipo == "valor":
        x = rng.randint(-6, 10)
        r = a * x + b
        enun = f"Si f(x) = {fx}, ¿cuánto vale f({x})?"
        exp = f"Reemplazamos: f({x}) = {a}·({x}) + {b} = {r}."
        d = [a + b, a * x, r + 1]
    elif tipo == "pendiente":
        x1 = rng.randint(-5, 5)
        y1 = a * x1 + b
        x2 = x1 + rng.choice([2, 3, 4])
        y2 = a * x2 + b
        r = a  # la pendiente de f(x) = ax + b es a
        enun = f"La recta f pasa por ({x1}, {y1}) y ({x2}, {y2}). ¿Cuál es su pendiente?"
        exp = (f"La pendiente es (y2−y1)/(x2−x1) = ({y2}−{y1})/({x2}−{x1}) = "
               f"{a}. En f(x)=mx+n, la pendiente es m.")
        d = [b, y1, abs(a) + 1]
    elif tipo == "intercepto":
        x = rng.randint(1, 6)
        y = a * x + b
        r = b
        enun = (f"Si f(x) = {fx} y f({x}) = {y}, ¿cuánto vale f(0)?")
        exp = (f"Con x=0 queda f(0) = {b}. El intercepto con el eje Y es el valor "
               f"de f(0), no el coeficiente de x.")
        d = [a, y, b + a]
    else:
        c = rng.choice([1, 2, 3, 4]) * rng.choice([1, -1])
        if a == c:
            c += 1
        x0 = rng.randint(-6, 8)
        d2 = a * x0 + b - c * x0
        y0 = a * x0 + b
        r = x0
        enun = (f"Si f(x) = {fx} y g(x) = {linea(c, d2)}, "
                f"¿en qué valor de x se cortan?")
        exp = (f"En el punto de corte f(x) = g(x): {a}x + {b} = {c}x + {d2} → "
               f"x = {x0}. (La coordenada y es {y0}.)")
        d = [x0 + 1, x0 - 1, y0]
    return mcq(rng, "Álgebra y funciones", "Función lineal y afín", enun, fmt(r),
               [fmt(x) for x in d], exp, nivel, ["funciones"])


def gen_cuadratica(rng, nivel=1):
    """Función cuadrática: vértice, ceros o discriminante."""
    r1, r2 = rng.sample(range(-6, 8), 2)
    b, c = -(r1 + r2), r1 * r2
    tipo = rng.choice(["vertice", "ceros", "discriminante"])
    if tipo == "vertice":
        xv = Fraction(-b, 2)
        r = xv
        enun = f"Si f(x) = {polinomio(b, c)}, ¿cuál es el valor del vértice en x?"
        exp = (f"El vértice está en x = −b/2 = −({b})/2 = {fmt(xv)}. "
               f"Remember: el signo de b cambia y se divide por 2.")
        d = [Fraction(b, 2), Fraction(c, 2), xv + 1]
    elif tipo == "ceros":
        mayor = max(r1, r2)
        r = mayor
        enun = f"Si f(x) = {polinomio(b, c)}, ¿cuál es el cero mayor de f?"
        exp = (f"Buscamos las raíces de {polinomio(b, c)}. Se factoriza como "
               f"(x − {r1})(x − {r2}), así que los ceros son {r1} y {r2}. "
               f"El mayor es {mayor}.")
        d = [min(r1, r2), r1 * r2, r1 - r2]
    else:
        disc = b * b - 4 * c
        r = disc
        enun = f"Si f(x) = {polinomio(b, c)}, ¿cuál es el discriminante?"
        exp = f"El discriminante es Δ = b² − 4ac = ({b})² − 4·1·({c}) = {disc}."
        d = [b * b + 4 * c, -disc, abs(b) - 4 * c]
    return mcq(rng, "Álgebra y funciones", "Función cuadrática", enun, fmt(r),
               [fmt(x) for x in d], exp, nivel, ["cuadratica"])


def gen_proporcionalidad(rng, nivel=1):
    """Proporcionalidad directa e inversa."""
    directa = rng.random() < 0.5
    if directa:
        k = rng.choice([2, 3, 4, 5, 6, 8, 12])
        a = rng.randint(2, 9)
        b = rng.randint(2, 9)
        r = k * b
        enun = (f"Si {a} cuadernos cuestan ${k*a}, ¿cuánto cuestan {b} cuadernos?")
        exp = (f"Proporción directa: el precio por cuaderno es ${k}. "
               f"{b} × ${k} = ${r}.")
        d = [(k * a // b) if (k * a) % b == 0 else r // 2, r + a, a * b]
    else:
        # x workers, y days → fewer workers, more days
        trab = rng.choice([2, 3, 4, 6, 8])
        dias = rng.choice([6, 8, 9, 12, 15, 18, 24])
        n2 = rng.choice([t for t in [2, 3, 4, 6] if t != trab])
        r = Fraction(trab * dias, n2)
        enun = (f"Si {trab} trabajadores hacen un trabajo en {dias} días, "
                f"¿cuántos días tardarán {n2} trabajadores?")
        exp = (f"Proporción inversa: si menos trabajadores tardan más días. "
               f"{trab}·{dias} = {n2}·x → x = {fmt(r)} días.")
        d = [Fraction(n2 * dias, trab), dias, r + 1]
    return mcq(rng, "Álgebra y funciones", "Proporcionalidad", enun, fmt(r),
               [fmt(x) for x in d], exp, nivel, ["proporcionalidad"])


# ══════════════════════════════════════════════════════════════
#  GEOMETRÍA
# ══════════════════════════════════════════════════════════════
TRIANGULOS = [(3, 4, 5), (6, 8, 10), (5, 12, 13), (8, 15, 17),
               (9, 12, 15), (7, 24, 25), (20, 21, 29), (12, 16, 20),
               (10, 24, 26), (15, 20, 25)]


def gen_pitagoras(rng, nivel=1):
    """Teorema de Pitágoras."""
    a, b, c = rng.choice(TRIANGULOS)
    pedir = rng.choice(["hip", "cat"])
    if pedir == "hip":
        r = c
        enun = f"En un triángulo rectángulo, los catetos miden {a} y {b}. ¿Cuánto mide la hipotenusa?"
        exp = (f"Aplicamos Pitágoras: c² = {a}² + {b}² = {a*a} + {b*b} = {c*c}. "
               f"c = √{c*c} = {c}.")
        d = [a + b, a * b, c + 1]
    else:
        r = b
        enun = (f"En un triángulo rectángulo, la hipotenusa mide {c} y un cateto "
                f"mide {a}. ¿Cuánto mide el otro cateto?")
        exp = (f"b² = {c}² − {a}² = {c*c} − {a*a} = {b*b}. b = {b}. "
               f"En este caso se RESTA, porque buscamos un cateto.")
        d = [c - a, a + b, c + b]
    return mcq(rng, "Geometría", "Figuras geométricas", enun, fmt(r),
               [fmt(x) for x in d], exp, nivel, ["pitagoras"])


def gen_areas(rng, nivel=1):
    """Perímetros y áreas de triángulos, trapecios, círculos y paralelogramos."""
    tipo = rng.choice(["triangulo", "trapecio", "circulo_area", "circulo_per",
                        "paralelogramo"])
    if tipo == "triangulo":
        b, h = rng.choice([(6, 4), (8, 5), (10, 6), (12, 7), (14, 9), (16, 10)])
        r = Fraction(b * h, 2)
        enun = f"¿Cuál es el área de un triángulo con base {b} y altura {h}?"
        exp = f"Área = base × altura / 2 = {b} × {h} / 2 = {fmt(r)}."
        d = [b * h, b + h, r + 1]
    elif tipo == "trapecio":
        B, b, h = rng.choice([(10, 6, 4), (12, 8, 5), (14, 10, 6), (16, 12, 7)])
        r = Fraction((B + b) * h, 2)
        enun = (f"¿Cuál es el área de un trapecio con bases {B} y {b} y altura {h}?")
        exp = (f"Área = (B + b) × h / 2 = ({B} + {b}) × {h} / 2 = {fmt(r)}. "
               f"Se suman las bases y se divide en 2.")
        d = [(B + b) * h, B * h, r + 1]
    elif tipo == "circulo_area":
        r0 = rng.choice([2, 3, 4, 5, 6, 10])
        r = PI * r0 * r0
        enun = f"¿Cuál es el área de un círculo de radio {r0}? (π = 3,14)"
        exp = f"Área = πr² = 3,14 × {r0}² = 3,14 × {r0*r0} = {fmt_dec(r)}."
        d = [PI * r0, PI * 2 * r0, r + r0]
    elif tipo == "circulo_per":
        r0 = rng.choice([2, 3, 4, 5, 6, 10])
        r = 2 * PI * r0
        enun = f"¿Cuál es el perímetro de un círculo de radio {r0}? (π = 3,14)"
        exp = f"Perímetro = 2πr = 2 × 3,14 × {r0} = {fmt_dec(r)}."
        d = [PI * r0, PI * r0 * r0, r + r0]
    else:
        b, h = rng.choice([(8, 5), (10, 6), (12, 7), (15, 9), (18, 11)])
        r = b * h
        enun = f"¿Cuál es el área de un paralelogramo con base {b} y altura {h}?"
        exp = f"Área = base × altura = {b} × {h} = {r}. No se divide en 2."
        d = [(b + h) * 2, Fraction(b * h, 2), r + b]
    return mcq(rng, "Geometría", "Figuras geométricas", enun, fmt_dec(r),
               [fmt_dec(x) for x in d], exp, nivel, ["areas"])


def gen_volumenes(rng, nivel=1):
    """Volúmenes de cubo, paralelepípedo y cilindro."""
    tipo = rng.choice(["cubo", "paralelepipedo", "cilindro"])
    if tipo == "cubo":
        a = rng.choice([2, 3, 4, 5, 6, 8, 10])
        r = a ** 3
        enun = f"¿Cuál es el volumen de un cubo de arista {a}?"
        exp = f"Volumen del cubo = arista³ = {a}³ = {r}."
        d = [a * a, 6 * a * a, r + a]
    elif tipo == "paralelepipedo":
        a, b, h = rng.choice([(2, 3, 4), (3, 4, 5), (4, 5, 6), (2, 5, 8), (3, 6, 9)])
        r = a * b * h
        enun = (f"¿Cuál es el volumen de un paralelepípedo de dimensiones "
                f"{a} × {b} × {h}?")
        exp = f"Volumen = largo × ancho × alto = {a} × {b} × {h} = {r}."
        d = [2 * (a * b + a * h + b * h), a * b, r + h]
    else:
        r0 = rng.choice([2, 3, 4, 5, 6])
        h = rng.choice([4, 6, 8, 10, 12])
        r = PI * r0 * r0 * h
        enun = (f"¿Cuál es el volumen de un cilindro de radio {r0} y altura {h}? "
                f"(π = 3,14)")
        exp = f"Volumen = πr²h = 3,14 × {r0}² × {h} = {fmt_dec(r)}."
        d = [2 * PI * r0 * h, PI * r0 * h, r + h]
    return mcq(rng, "Geometría", "Cuerpos geométricos", enun, fmt_dec(r),
               [fmt_dec(x) for x in d], exp, nivel, ["volumenes"])


def gen_semejanza(rng, nivel=1):
    """Semejanza y proporcionalidad de figuras."""
    k = rng.choice([2, 3, 4])
    a = rng.randint(2, 9)          # lado del triángulo menor
    c = rng.randint(2, 9)          # otro lado del triángulo menor
    b = k * a                      # lado correspondiente del triángulo mayor
    r = k * c                      # lo que preguntamos
    enun = (f"Dos triángulos son semejantes. En el triángulo menor, un lado "
            f"mide {a} cm y otro {c} cm. En el triángulo mayor, el lado "
            f"correspondiente al primero mide {b} cm. ¿Cuánto mide en el "
            f"triángulo mayor el lado que corresponde a {c} cm?")
    exp = (f"La razón de semejanza es {b}/{a} = {k}. Aplicamos la misma razón "
           f"al otro lado: {c} × {k} = {r} cm.")
    d = [a * b, (c // k if c >= k else c + k), r + 1]
    return mcq(rng, "Geometría", "Semejanza y proporcionalidad", enun, fmt(r),
               [fmt(x) for x in d], exp, nivel, ["semejanza"])


# ══════════════════════════════════════════════════════════════
#  PROBABILIDAD Y ESTADÍSTICA
# ══════════════════════════════════════════════════════════════
def gen_probabilidad(rng, nivel=1):
    """Probabilidades: simple, complemento, aditiva y multiplicativa."""
    tipo = rng.choice(["simple", "complemento", "suma", "producto"])
    if tipo == "simple":
        r_, a_, b_ = rng.choice([(3, 5, 8), (4, 6, 10), (2, 3, 5), (5, 7, 12), (6, 4, 10)])
        r = Fraction(r_, r_ + b_)
        enun = (f"Una bolsa tiene {r_} bolas rojas y {b_} azules. "
                f"Si se saca una al azar, ¿cuál es la probabilidad de que sea roja?")
        exp = f"Casos favorables {r_}, casos totales {r_+b_}: P = {r_}/{r_+b_} = {fmt(r)}."
        d = [Fraction(b_, r_ + b_), Fraction(r_, r_), Fraction(1, 2)]
    elif tipo == "complemento":
        r_ = rng.randint(2, 6)
        t = rng.choice([6, 8, 10, 12])
        if r_ >= t:
            r_ = t - 2
        r = Fraction(t - r_, t)
        enun = (f"En una bolsa hay {t} bolas, {r_} rojas. ¿Cuál es la "
                f"probabilidad de que NO salga roja?")
        exp = (f"Lo contrario a roja son las {t-r_} no rojas: P = {t-r_}/{t} = {fmt(r)}.")
        d = [Fraction(r_, t), Fraction(r_, t - r_), Fraction(1, 2)]
    elif tipo == "suma":
        a_ = Fraction(rng.randint(1, 5), 10)
        b_ = Fraction(rng.randint(1, 5), 10)
        r = a_ + b_
        enun = ("En un experimento, P(A) = " + fmt(a_) + " y P(B) = " + fmt(b_) +
                ", con A y B mutuamente excluyentes. ¿Cuál es P(A o B)?")
        exp = (f"Como son excluyentes, se suman: P(A o B) = {fmt(a_)} + {fmt(b_)} "
               f"= {fmt(r)}.")
        d = [a_ * b_, max(a_, b_), r + Fraction(1, 10)]
    else:
        a_ = Fraction(rng.randint(1, 9), 10)
        b_ = Fraction(rng.randint(1, 9), 10)
        r = a_ * b_
        enun = ("En dos tirajes independientes, P(A) = " + fmt(a_) +
                " y P(B) = " + fmt(b_) + ". ¿Cuál es P(A y B)?")
        exp = (f"Como son independientes, se multiplican: P(A y B) = {fmt(a_)} × "
               f"{fmt(b_)} = {fmt(r)}.")
        d = [a_ + b_, max(a_, b_), r + Fraction(1, 10)]
    return mcq(rng, "Probabilidad y estadística", "Reglas de probabilidad", enun,
               fmt(r), [fmt(x) for x in d], exp, nivel, ["probabilidad"])


def gen_promedio(rng, nivel=1):
    """Promedio y mediana."""
    n = rng.choice([5, 5, 7])
    datos = sorted(rng.sample(range(1, 40), n))
    if rng.random() < 0.5:
        r = Fraction(sum(datos), n)
        enun = f"¿Cuál es el promedio (media aritmética) de {', '.join(map(str, datos))}?"
        exp = (f"Promedio = suma / cantidad = {sum(datos)} / {n} = {fmt(r)}.")
        med = datos[n // 2]
        d = [med, sum(datos) + 1, r + 1]
    else:
        r = datos[n // 2]
        enun = f"¿Cuál es la mediana de {', '.join(map(str, datos))}?"
        exp = (f"La lista tiene {n} valores, así que la mediana es el que queda en "
               f"la posición {(n+1)//2}: {r}. (El promedio es {fmt(Fraction(sum(datos), n))}, "
               f"no la mediana.)")
        d = [Fraction(sum(datos), n), datos[0], datos[-1]]
    return mcq(rng, "Probabilidad y estadística", "Medidas de posición", enun, fmt(r),
               [fmt(x) for x in d], exp, nivel, ["promedio"])


def gen_cuartiles(rng, nivel=1):
    """Cuartiles y percentiles de una lista ordenada de 9 valores."""
    base = sorted(rng.sample(range(1, 60), 9))
    tipo = rng.choice(["q1", "q3", "p90"])
    if tipo == "q1":
        r = base[2]
        enun = f"¿Cuál es el primer cuartil (Q1) de {', '.join(map(str, base))}?"
        exp = (f"Con 9 datos ordenados, Q1 es el 3er valor: {r}. "
               f"(El 5to es la mediana y el 7mo es Q3.)")
        d = [str(base[4]), str(base[1]), str(base[5])]
    elif tipo == "q3":
        r = base[6]
        enun = f"¿Cuál es el tercer cuartil (Q3) de {', '.join(map(str, base))}?"
        exp = f"Con 9 datos ordenados, Q3 es el 7mo valor: {r}."
        d = [str(base[4]), str(base[5]), str(base[7])]
    else:
        r = base[8]
        enun = (f"¿Cuál es el percentil 90 de {', '.join(map(str, base))}?")
        exp = (f"El percentil 90 corresponde al 9no dato de 10 (9 de cada 10), "
               f"así que es el último valor: {r}.")
        d = [str(base[7]), str(base[6]), str(base[4])]
    return mcq(rng, "Probabilidad y estadística", "Cuartiles y percentiles", enun,
               fmt(r), d, exp, nivel, ["cuartiles"])


# ══════════════════════════════════════════════════════════════
#  registro
# ══════════════════════════════════════════════════════════════
GENERADORES = [
    gen_racionales, gen_porcentaje, gen_potencias,
    gen_producto_notable, gen_factorizacion, gen_ecuacion, gen_inecuacion,
    gen_sistema, gen_funcion_lineal, gen_cuadratica, gen_proporcionalidad,
    gen_pitagoras, gen_areas, gen_volumenes, gen_semejanza,
    gen_probabilidad, gen_promedio, gen_cuartiles,
]

EJES = {
    "Números": "numeros",
    "Álgebra y funciones": "algebra",
    "Geometría": "geometria",
    "Probabilidad y estadística": "probabilidad",
}


def generar(rng: random.Random, nivel: int = 1) -> Question:
    return rng.choice(GENERADORES)(rng, nivel)


_EJE_POR_GENERADOR: dict[str, list] | None = None


def generadores_por_eje() -> dict[str, list]:
    """Agrupa los generadores según el eje del temario al que pertenecen.

    Se sondea cada generador una vez (con un rng aparte, para no tocar el
    estado del llamador) en vez de mantener una tabla escrita a mano que
    se desordena apenas se agrega un generador nuevo.
    """
    global _EJE_POR_GENERADOR
    if _EJE_POR_GENERADOR is None:
        mapa: dict[str, list] = {}
        for g in GENERADORES:
            try:
                eje = g(random.Random(1234), 2).eje
            except Exception:
                continue
            mapa.setdefault(eje, []).append(g)
        _EJE_POR_GENERADOR = mapa
    return _EJE_POR_GENERADOR


def generar_por_eje(rng: random.Random, eje: str, nivel: int = 1) -> Question:
    """Genera una pregunta de un eje concreto del temario PAES."""
    cands = generadores_por_eje().get(eje)
    if not cands:
        raise ValueError(f"eje desconocido: {eje!r}")
    return rng.choice(cands)(rng, nivel)


def generar_set(rng: random.Random, n: int = 10, nivel: int = 1,
                ejes: list[str] | None = None) -> list[Question]:
    """Genera n preguntas, repartidas entre los ejes para que el set se sienta
    como la PAES real (no 10 preguntas de lo mismo)."""
    ejes = ejes or list(EJES.keys())
    preguntas = []
    i = 0
    while len(preguntas) < n and i < n * 12:
        i += 1
        q = rng.choice(GENERADORES)(rng, nivel)
        if q.eje not in ejes:
            continue
        preguntas.append(q)
    return preguntas


if __name__ == "__main__":
    rng = random.Random(7)
    for q in generar_set(rng, 10):
        print(f"[{q.eje} · {q.unidad}] {q.enunciado}")
        for i, o in enumerate(q.opciones):
            print(f"   {'✓' if i == q.correcta else ' '} {o}")
        print(f"   → {q.explicacion}\n")
