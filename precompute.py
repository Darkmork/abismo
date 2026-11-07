#!/usr/bin/env python3
"""
precompute.py · genera la tabla de dailies para el sitio.

El juego publicado NO habla con Wikipedia ni con ningún servicio: todo se
calcula aquí, una vez, y se escribe como un .js estático. Por eso el sitio
funciona offline, no tiene backend y no puede romperse por un rate limit.

    python3 precompute.py --days 14
    → web/data/daily.js
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import date, timedelta

import abismo
import fama

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "web", "data", "daily.js")

# Familias cuyo conjunto de respuestas es demasiado grande para hornearlo
# entero en el navegador: el cliente las valida y puntúa con la fórmula.
DENSE = {"legendre"}


def build(days: int, start: date) -> dict:
    tabla = {"generated": date.today().isoformat(), "days": {}}
    for i in range(days):
        d = start + timedelta(days=i)
        rounds = abismo.daily(d)
        prompts = []
        for r in rounds:
            fam = r["fam"]
            p = {
                "key": fam.key,
                "stratum": fam.stratum,
                "text": fam.prompt,
                "maxv": r["maxv"],
                "gem": r["answers"][-1][0],
                "count": len(r["answers"]),
            }
            if fam.key in DENSE:
                p["kind"] = "dense"
            else:
                p["answers"] = {str(a): [name, pts] for a, _, name, pts in r["answers"]}
            prompts.append(p)
        tabla["days"][d.isoformat()] = {"prompts": prompts}
        print(f"  {d.isoformat()}  {len(prompts)} prompts  "
              f"({', '.join(p['key'] for p in prompts)})")
    return tabla


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=14)
    ap.add_argument("--start", type=str, default=None, help="YYYY-MM-DD")
    args = ap.parse_args()

    start = date.fromisoformat(args.start) if args.start else date.today()
    print(f"precomputando {args.days} dailies desde {start.isoformat()}...")
    tabla = build(args.days, start)

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write("// Generado por precompute.py — no editar a mano.\n")
        fh.write("window.ABISMO = ")
        json.dump(tabla, fh, ensure_ascii=False, separators=(",", ":"))
        fh.write(";\n")
    size = os.path.getsize(OUT)
    print(f"escrito {OUT} ({size/1024:.1f} KB)")


if __name__ == "__main__":
    main()
