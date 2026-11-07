# Abismo — daily de matemáticas por rareza

Investigación + diseño de un juego matemático inspirado en la mecánica de
[krillion.io](https://krillion.io). Incluye un motor de puntaje funcionando en
`abismo.py` y el oráculo de familiaridad en `fama.py`.

---

## 1. Qué es Krillion (la mecánica real)

No es un trivia con respuesta única. Cada prompt define un **conjunto cerrado de
respuestas válidas** y lo que puntúa no es la corrección, sino la **rareza**:

- 7 prompts por día, los mismos para todos, con timer (~25 s) por prompt.
- Responder mal o dejar vencer el timer = 0 puntos en ese prompt, el juego sigue.
- Cada respuesta válida cae en una categoría de rareza:

| Tier | Puntos | Profundidad |
|---|---|---|
| Plankton | 10 | 100 m |
| Too Clever | 15 | 150 m |
| Schooler | 30 | 300 m |
| Rare | 60 | 600 m |
| Deep Cut | 85 | 850 m |
| Krillion | 100 | 1 000 m |

- 1 punto = 10 metros. Máximo 700 pts = **7 000 m**, el fondo de la fosa hadal.
- La profundidad es el score: hay zonas con nombre (resto del Titanic, territorio
  del pez abisal, hadal).
- Un "Krillion" es un literal: "one in a krillion".

**Lo importante — y lo que casi nadie menciona:** la barrera real de este juego
no es el frontend. Es la **curación**. Su FAQ lo dice explícitamente:

> *how are answer sets curated?* — aggregating datasets (dictionaries, wiki
> pages, encyclopedias...), then merging and cleaning the result into one
> answer set.

> *how is rarity determined?* — a familiarity database of how often a word or
> name actually turns up in what people read and write. Others can't be reduced
> to a number like that, so those get a combination of LLM assistance and a
> manual pass.

O sea: alguien tiene que (a) reunir el conjunto de respuestas válidas de cada
prompt y (b) estimar qué tan poco probable es que alguien escriba cada una.
Es trabajo manual, lento y que no escala. El juego lo disimula porque se ve
lindo.

---

## 2. Por qué el género ya está saturado (y por qué todavía hay espacio)

Existe una lluvia de clones: `krillion.org`, `krillion-unlimited.org`,
`krilliontoday.com`, `krilliongames.app`, `rarestanswer.com`, `cosmillion.io`
(versión de palabras), `playlin.io`. En HN hay usuarios diciendo que es "another
AI remake of a very common game type". Uno de los clones hasta abría páginas de
malware. El propio autor de Krillion dice en su FAQ que Google AI ya está
listando a "some random dude who made a copycat clone" como su creador.

Dos conclusiones:

1. **La mecánica es un género, no una invención protegida.** Se puede usar.
   Pero el nombre, el arte, los nombres de los tiers y los prompts son de él.
   Este diseño usa nombres y tiers propios: Común / Curioso / Raro / Profundo /
   Abisal / Legendario.
2. **La versión de matemáticas está poco ocupada.** Lo más cercano es
   **RNGdle** (alldle.games): daily matemático con "rarity ranks" donde
   "draft the rarest number". Pero el número es aleatorio, no tiene la
   estructura de "prompt con conjunto de respuestas válidas" + validación
   objetiva. Ahí hay terreno.

---

## 3. La idea: la rareza se puede GENERAR

Este es el insight que abre la puerta.

En trivia, la rareza de una respuesta es un **dato externo**: hay que medir
cuántas veces la escribió la gente. Es por eso que Krillion necesita un corpus,
un LLM y una pasada manual.

En matemáticas, muchas familias de números tienen un **conjunto de respuestas
válidas que es enumerable exactamente** y que tiene una **gradiente de rareza
natural**:

> "Un número que sea a la vez triangular y pentagonal."
> → 1, 210, 40755, …

El primero es obvio. El segundo exige saber la serie. El tercero es
practicamente inaccesible sin cálculo. Eso **es** la escalera de rareza de
Krillion, pero gratis, infinita y verificable con aritmética entera.

Consecuencias prácticas:

- **Contenido infinito.** No hay que curar prompts: se generan.
- **Validación objetiva.** ¿Aciertas o no? Se comprueba con `isqrt` y una
  predicado. Cero fuzzy matching, cero alias, cero falsos positivos.
- **El mismo prompt para todos, gratis.** El seed es la fecha: todos ven los
  mismos 7 prompts sin servidor.
- **Se puede jugar sin backend.** En la versión v1 no hay ni usuarios ni
  accounts: el ranking local + un leaderboard estático.

### El modelo de rareza en dos capas

**Capa 1 — Oráculo de familiaridad (offline).** Qué tan conocido es el número.
Implementado en `fama.py` con **pageviews de Wikipedia** sobre el artículo
`N (number)`:

| Número | Vistas/mes | Lectura |
|---|---|---|
| 42 | 24 532 | respond triangular y pentagonal |
| 14 | 6 520 | respond triangular y pentagonal |
| 55 | 5 010 | Fibonacci dorado |
| 31 | 3 858 | primo de Mersenne archiconocido |
| 220 | 637 | par amigo clásico |
| 284 | 173 | la otra mitad de 220 |
| 2147483647 | 156 | int máximo |
| 9801 | 69 | cuadrado y pentagonal |
| 1184 | 1 | existe el artículo, nadie lo mira |
| 6232 · 40755 · 1413721 | sin artículo | nadie los ha mirado nunca |

Sin artículo ≈ nadie lo conoce. Es exactamente la "familiarity database" que
describe el FAQ de Krillion, pero gratis y objective.

Se combina con un **prior estructural**: números redondos, chicos, palíndromos
o de dígitos repetidos son los que se le ocurren a cualquiera.

**Corolario interesante:** el corpus corrige errores del sentido común. "31" y
"127" son primos de Mersenne mucho más buscados que "7" o "3", y el modelo lo
detecta solo (3 858 y 1 475 vistas contra 543 y 420).

**Lo que se probó y se descartó: la OEIS.** La Online Encyclopedia of Integer
Sequences es la fuente obvia de "prominencia matemática": cuántos artículos la
contienen. La API funciona y devuelve el nombre de las secuencias ("Amicable
numbers", "Square triangular numbers"). Pero el servidor pagina de a 100 y
satura: 1, 6, 28 y 31 devuelven `null` por tener demasiadas coincidencias, y
todo lo demás llega al tope de 100. La resolución es justo donde se necesita
(el rango 30–90 hits: 6232 → 91, 10744 → 64, 40755 → 53, 1413721 → 33), y
precomputar un año serían ~200 000 requests a ~1 s cada uno. Se deja documentada
como la siguiente capa posible si el juego escala, pero no en la v1.

**Capa 2 — Frecuencia real de jugadores (online, para la v2).** Cuando haya
jugadores, se mezcla la frecuencia observada con el oráculo, tipo actualización
bayesiana. Es lo que hace bueno al juego con el tiempo, habilita el modo duelo
y permite elegir "la gema" con datos en vez de intuición.

### La escalera de tiers

El modelo final mezcla las dos cosas, porque ninguna sola sirve:

```
g = 0.55 · fama_absoluta + 0.45 · posición_en_el_prompt
```

- `fama_absoluta` = 0.75 · pageviews + 0.25 · forma del número. Comparable
  entre prompts: un "Legendario" es igual de raro en el prompt 3 que en el 7.
- `posición_en_el_prompt` = 1 para la respuesta más conocida del conjunto, 0
  para la más oscura. Y esto **no es inventado**: el FAQ del clon de Krillion
  describe los tiers como comparar la frecuencia "compared with the other
  possibilities for that question". Son cuantiles dentro del prompt.

El cuantil puro llenaba los tiers pero aplastaba el valor real del número
("3" como gema de un prompt Fibonacci). El absoluto puro dejaba los tiers
medios vacíos, porque la señal "tiene artículo de Wikipedia / no lo tiene" es
binaria. La mezcla arregla las dos cosas: en el daily de hoy los 6 tiers se
reparten 17/3/5/13/9/29 sobre 76 respuestas candidatas.

---

## 4. Las familias de prompts (con output real)

17 familias, todas verificadas. Ejemplos reales del motor:

| Prompt | Respuestas válidas | Gema |
|---|---|---|
| triangular y cuadrado perfecto | 1, 36, 1225, 41616, 1413721, 48024900 | 48 024 900 |
| triangular y pentagonal | 1, 210, 40755, 7906276 | 7 906 276 |
| hexagonal y cuadrado perfecto | 1, 1225, 1413721 | 1 413 721 |
| cuadrado y pentagonal | 1, 9801, 94109401 | 94 109 401 |
| Fibonacci y triangular | 1, 3, 21, 55 | 55 |
| Fibonacci y primo | 2, 3, 5, 13, 89, 233, 1597, 28657, 514229 | 514 229 |
| número de Pell | 1, 2, 5, 12, 29, 70, 169, 408, 985… | 13 860 000+ |
| número de Lucas | 1, 2, 3, 4, 7, 11, 18, 29, 47, 76… | |
| número de Keith | 14, 19, 28, 47, 61, 75, 197, 742, 1104… | |
| número narcisista | 153, 370, 371, 407, 1634, 8208, 9474, 54748… | 548 834 |
| primo de Wieferich | 1093, 3511 | 3511 |
| número de Catalan | 1, 2, 5, 14, 42, 132, 429, 1430, 4862… | 9 694 845 |
| número de Bell | 1, 2, 5, 15, 52, 203, 877, 4140, 21147… | 678 570 |
| primo de Mersenne | 3, 7, 31, 127, 8191, 131071, 524287, 2147483647 | 524 287 |
| número perfecto | 6, 28, 496, 8128, 33550336 | 33 550 336 |
| número amigo | 220, 284, 1184, 1210, 2620, 2924, 5020, 5564… | 172 976 |
| no suma de tres cuadrados | 7, 15, 23, 28, 31… (Legendre) | denso: 4^a(8b+7) |

**Una familia murió durante el diseño:** "cubo y triangular". parecía una buena
idea, pero el único cubo que es triangular es 1 (verificado por fuerza bruta
hasta k=300 000). El motor la detectaba y la cambiaba sola, pero es mejor
sacarla: una familia con una sola respuesta no es un prompt.

**Las familias densas** (Legendre, primos, etc.) son el caso interesante a
futuro: su conjunto de respuestas es casi infinito, así que el "one in a
krillion" es real —hay **166 664** respuestas válidas bajo un millón—. Ahí el
tier no puede salir de un cuantil y hay que usar el prior estructural en
absoluto.

**Las familias densas** (Legendre, primos, etc.) son el caso interesante a
futuro: su conjunto de respuestas es casi infinito, así que el "one in a
krillion" es real —hay 166 667 respuestas válidas bajo un millón—. Ahí el tier
no puede salir de un cuantil y hay que usar el prior estructural en absoluto.

---

## 5. La metáfora

Krillion usa el océano (el krill desciende). Para matemáticas hay una
alternativa mejor: **descender a través de estratos de teoría de números**.

- 0–400 m · **Aritmética** (triangular, cuadrado, hexagonal, pentagonal)
- 400–1 200 m · **Recurrencias** (Catalan, Bell, Fibonacci, Mersenne)
- 1 200–3 000 m · **Aritmética profunda** (números amigos, perfectos)
- 3 000–7 000 m · **Teoría de números** (Legendre, congruencias)

Cada vez que bajas de stratum, el juego se pone más difícil. Y a 7 000 m está
el fondo: el primer número perfecto impar, que **nadie ha encontrado nunca**
(lafamia es literalmente infinita ahí — el mismo nombre del juego). Es un
final perfecto.

---

## 6. Arquitectura recomendada

```
datos/
  familias.py     # las 17 familias, sus predicados y sus generadores
  fama.json       # tabla precomputada: número → vistas (capa 1)
  abismo.json     # los dailies del año (seed por fecha)
web/
  index.html      # el juego (estático)
scripts/
  precompute.py   # corre una vez por estación: llena fama.json y abismo.json
```

**Clave: el precompute es offline.** La API de Wikimedia devuelve **429**
(rate limit) si le pides de más — lo descubrí peleando con el motor durante
esta investigación. Con un throttle de 1 req/s la cosa funciona, pero la tabla
completa del año son ~200 000 consultas: **eso se calcula una vez, en una
máquina, y se publica como JSON estático**. El juego nunca pega a la API.

Por eso el prototipo trae `ABISMO_OFFLINE=1`: el juego lee la tabla y listo.

---

## 7. Lo que ya está hecho (no es una idea, es código)

`abismo.py` (motor):

- 17 familias con validación entera exacta (`isqrt`, predicados).
- Seed por fecha → los mismos 7 prompts para todos, sin servidor.
- Tiers por cuantil de fama, profundidad = puntos × 10 m.
- `daily` muestra el dive completo con vistas de wiki por respuesta.
- `play` es una versión jugable en terminal con timer real de 25 s
  (`signal.setitimer`), puntúa tu respuesta y te dice el tier.
- `tune` imprime la calibración para ajustar umbrales.

`fama.py` (oráculo):

- Consulta en lote qué artículos existen (50 por request) y pide pageviews solo
  de los que existen.
- Cache en `fama_cache.json`; los 404 se cachean (definitivos), los 429 no
  (transitorios, se reintentan).
- Throttle de 1 req/s y modo offline.

```
$ python3 abismo.py play
  abismo · 25s por prompt. Type your answer + Enter.

  1. [Aritmética]  Un número que sea a la vez triangular y pentagonal.
     > 210
       ✓  210  Curioso  15 pts   (+150 m)

  ── 15 pts · 150 m de profundidad ──
```

---

## 8. Riesgos abiertos (honestidad)

1. **La capa 1 es estática.** Sin jugadores, "raro" quiere decir "no muy
   conocido por Wikipedia", no "no lo escribió nadie". Con la v2 (frecuencia
   real) se arregla. Antes de eso, el juego es un daily de cultura
   matemática con rareza aproximada.
2. **Familias densas.** El conjunto de respuestas es demasiado grande para
   cuantil; hay que definir bien el tier absoluto y el bound del prompt.
3. **Google Ngram está bloqueado** desde esta máquina (`books.google.com` no
   responde), pero Wikipedia sí. En un servidor normal Ngram sería una fuente
   mejor para palabras.
4. **Sin backend no hay ranking, cuentas ni amigos.** Es un problema de scope,
   no de diseño: la v1 puede ser 100% estática.
5. **El copycat ya existe.** Todo lo que se publique tiene que verse propio:
   nombre, arte, tiers, prompts.

---

## 9. Alternativas que miré y descarté

- **Aritmética diaria clásica** (cuenta, memoria, operación mental): mercado
  saturadísimo, sin ninguna conexión con Krillion.
- **RNGdle-like** (elegir el número más raro de un rango al azar): más simple,
  pero pierde el alma de Krillion, que es el *prompt con conjunto de respuestas
  válidas*.
- **Adivinar la respuesta correcta más improbable** (estilo "pregunta de
  cultura matemática con distractores"): es quiz con scoring, no el juego de
  rareza abierta de Krillion.
- **Cambiar la rareza por la dificultad** (puntuar por cuánto te costó resolver):
  pierde la validación objetiva y el componente social de comparar respuestas.
- **Mantener el océano**: es copiar la marca. La versión con estratos de
  teoría de números es mejor justamente porque el tema y el contenido son
  propios.
