# Abismo · el descenso diario

Juego matemático daily inspirado en la mecánica de
[krillion.io](https://krillion.io): cada pregunta define un **conjunto de
respuestas válidas** y no importa si aciertas — importa **qué tan rara** es tu
respuesta. Las obvias no te hunden nada; las raras te llevan al fondo.

```
Común 10 · Curioso 15 · Raro 30 · Profundo 60 · Abisal 85 · Legendario 100
1 punto = 10 metros · 7 preguntas = 7 000 m de profundidad
```

La diferencia con el original: en trivia los conjuntos de respuestas se curan a
mano (lento, caro, finito). Acá **se generan con aritmética**, así que el
contenido es infinito, la validación es exacta (`isqrt` y predicados enteros)
y no hay fuzzy matching ni aliases.

## Estructura

```
abismo.py       motor: 17 familias de preguntas, scoring, seed por fecha
fama.py         oráculo de familiaridad (pageviews de Wikipedia) + cache
precompute.py   genera la tabla de dailies para el sitio (web/data/daily.js)
DISENO.md       investigación de krillion.io y diseño completo del juego
web/            el juego (HTML + CSS + JS plano, sin build)
```

## Uso local

```bash
python3 abismo.py daily     # muestra el dive del día con sus gemas
python3 abismo.py play      # versión jugable en terminal, timer de 25 s
python3 abismo.py tune      # calibración de umbrales
```

El motor usa la red solo para calibrar la rareza (pageviews de Wikipedia).
Para trabajar sin red:

```bash
ABISMO_OFFLINE=1 python3 abismo.py daily
```

## Regenerar la tabla del sitio

```bash
python3 precompute.py --days 14      # escribe web/data/daily.js
```

Esto **sí** necesita red: baja los pageviews que faltan y los cachea en
`fama_cache.json`. El sitio publicado nunca hace eso — consume la tabla ya
calculada, así que es 100% estático.

## Desplegar

`vercel.json` ya está configurado: sitio estático, output `web/`, sin build.

```bash
npx vercel deploy web --prod     # una vez
npx vercel --prod                # cada vez que cambie algo
```

O importá el repo en Vercel y cada push a `main` despliega solo.

## Por qué no hay backend (todavía)

El diseño completo no lo necesita:

- **Los prompts**: se generan con un seed (la fecha). Los mismos 7 para todos,
  sin servidor.
- **La validación**: ocurre en el cliente contra el conjunto de respuestas
  horneado en la tabla.
- **La rareza**: sale de un oráculo estático (pageviews + forma del número).
- **El ranking**: por ahora es local (`localStorage`).

Lo que sí pediría backend, para una v2:

1. **Ranking global** del día → necesita una base de datos.
2. **Rareza por jugadores de verdad**: cuando suficientes personas responden, su
   distribución real ajusta los tiers (es lo que hace bueno a Krillion con el
   tiempo y habilita el modo duelo).
3. Cuentas, amigos, compartidos.

Ahí sí: Postgres en Railway + una API mínima. Es un módulo aparte, no cambia
el motor.

## Licencia

MIT, si el repo es público.
