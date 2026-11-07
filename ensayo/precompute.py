#!/usr/bin/env python3
"""
precompute.py · genera los dailies y el pool de práctica del sitio.

El sitio no calcula nada: consume tablas ya hechas. Eso lo deja offline,
sin backend y sin depender de la red en tiempo de juego.

    python3 precompute.py --days 30 --pool 600
    → web/data/daily.js
"""
from __future__ import annotations

import argparse
import json
import os
import random
from datetime import date, timedelta

import paes

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "web", "data", "daily.js")

# reparto de ejes en un dive de 10 (como en la PAES real)
REPARTO = {"Números": 3, "Álgebra y funciones": 3, "Geometría": 2,
           "Probabilidad y estadística": 2}


def build(days: int, pool: int, start: date) -> dict:
    tabla = {"generado": date.today().isoformat(), "dias": {}, "practica": []}

    rng = random.Random(20261107)
    # pool de práctica: equilibrado por eje (25% cada uno) y barajado, para que
    # cada sesión sea distinta y el cuaderno de errores tenga cobertura pareja.
    preguntas_pool: list = []
    por_eje = max(1, pool // len(REPARTO))
    for eje in REPARTO:
        for _ in range(por_eje):
            preguntas_pool.append(paes.generar_por_eje(rng, eje, nivel=2))
    rng.shuffle(preguntas_pool)
    tabla["practica"] = [q.to_dict() for q in preguntas_pool[:pool]]
    tabla["pool_por_eje"] = por_eje

    for i in range(days):
        d = start + timedelta(days=i)
        r = random.Random(d.toordinal())
        # 10 preguntas: 3 números, 3 álgebra, 2 geometría, 2 probabilidad.
        # Se genera POR EJE: si se usara paes.generar() el eje se perdería.
        plan = [eje for eje, n in REPARTO.items() for _ in range(n)]
        r.shuffle(plan)
        preguntas = [paes.generar_por_eje(r, eje, nivel=2).to_dict() for eje in plan]
        tabla["dias"][d.isoformat()] = {"preguntas": preguntas}
        ejes = {}
        for q in preguntas:
            ejes[q["eje"]] = ejes.get(q["eje"], 0) + 1
        print(f"  {d.isoformat()}  {len(preguntas)} preguntas  {ejes}")
    return tabla


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--pool", type=int, default=600)
    ap.add_argument("--start", type=str, default=None)
    args = ap.parse_args()

    start = date.fromisoformat(args.start) if args.start else date.today()
    print(f"precomputando {args.days} dailies + pool de {args.pool} desde {start}")
    tabla = build(args.days, args.pool, start)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("// Generado por precompute.py — no editar a mano.\n")
        fh.write("window.ENSAYO = ")
        json.dump(tabla, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write(";\n")
    print(f"escrito {OUT} ({os.path.getsize(OUT)/1024:.1f} KB)")


if __name__ == "__main__":
    main()
