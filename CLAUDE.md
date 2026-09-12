# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

El código, los comentarios, los nombres de módulos y la documentación están **en español**.
Mantener ese idioma al escribir código nuevo o documentación.

## Comandos

Windows, venv local. Siempre con el intérprete del venv:

    .venv\Scripts\python.exe run.py buscar            # todos los temas, guarda en SQLite
    .venv\Scripts\python.exe run.py buscar --seco     # no escribe en la base: para tunear filtros
    .venv\Scripts\python.exe run.py buscar -t ingles  # un solo tema
    .venv\Scripts\python.exe run.py listar            # muestra lo guardado
    .venv\Scripts\python.exe run.py sync              # sube a Google Sheets (idempotente)
    .venv\Scripts\python.exe run.py dashboard         # regenera index.html + dashboard.html
    .venv\Scripts\python.exe run.py purgar --dias 365 # borra lo viejo dejando lápida
    .venv\Scripts\python.exe run.py notificar --seco  # Telegram, muestra sin enviar
    actualizar.bat                                     # todo junto + deploy a GitHub Pages
    wscript actualizar-silencioso.vbs                  # lo mismo, sin ventana: lo que corre la tarea

No hay suite de tests ni linter. El ciclo de trabajo real es `buscar --seco -t <tema>`,
mirar los resultados impresos con su score y sus motivos, y ajustar `config/temas.yaml`.

Dos formas de correr en producción, ambas activas:
- Tarea programada de Windows **"Buscador de Ofertas"** (09:00). Su acción es
  `wscript.exe actualizar-silencioso.vbs`, que corre el `.bat` con la ventana oculta.
  La tarea sigue siendo **Interactive** a propósito: el `git push` del deploy usa la
  credencial del Credential Manager de la sesión del usuario.
- GitHub Actions `.github/workflows/buscar.yml` (12:00 UTC + botón Run workflow).

## Arquitectura

Tubería de cuatro etapas. Cada etapa está en su paquete y el contrato entre ellas es `Oferta`.

    fuentes/*  ->  nucleo/puntuador  ->  nucleo/almacen  ->  salidas/* y nucleo/sheets
    (ingesta)      (filtro + score)     (dedup, SQLite)      (presentación)

**fuentes/** — cada módulo expone `NOMBRE` y `buscar(tema, cliente) -> list[Oferta]` y se
registra en `fuentes/__init__.py:REGISTRO`. Las de **catálogo** (devuelven todo y no miran
el tema, como `bbva`) van además en `SOLO_POR_PEDIDO`: si no, cada tema sin `fuentes:`
declarado se baja el catálogo entero para descartarlo. Ya pasó: +280 pedidos por corrida. Ese es el único contrato. Hoy: `google_news`
(RSS de Google News, sin API key), `rss` (feeds propios de `config/feeds.yaml`) y `bbva`
(API pública de BBVA Go, la única que declara vencimiento real). Un tema puede limitar
qué fuentes corre con `fuentes: [...]`; sin esa clave corren todas.

**nucleo/modelo.py** — la dataclass `Oferta` y `Oferta.id`, el hash de dedup.
El hash es `tema|titulo_normalizado|medio`, **no la URL**: los enlaces de Google News son
opacos y una misma nota llega con URLs distintas desde queries distintas. Incluye el tema
a propósito, porque una nota puede ser relevante para dos temas.

**nucleo/puntuador.py** — reglas deterministas, sin costo de API. Asigna 0-10 y una lista
de `motivos`. `requerir` es obligatorio (AND de ORs); `senales` solo **suma** hasta +2.0,
para "me interesa todo el rubro pero esto va primero" sin vaciar el tema los días que
eso no aparece. `DESCARTADA = -99.0` marca lo filtrado. `filtrar_y_ordenar()` aplica el
umbral del tema, el tope por dominio y el filtro de casi-repetidas (Jaccard sobre raíces
de 5 letras, solo contra notas del MISMO medio).

**nucleo/almacen.py** — SQLite en `datos/ofertas.db`, fuente de verdad del dedup.
`CREATE TABLE IF NOT EXISTS` no agrega columnas a una base existente y el `.db` se
versiona, así que los cambios de esquema van en `_COLUMNAS_NUEVAS` + `_migrar()`
(ALTER TABLE idempotente), no en `_ESQUEMA`.
Dos tablas: `ofertas` y `vistos` (lápidas). `ofertas.db` **se versiona en git** a
propósito: sin él, cada corrida de Actions empezaría de cero y volvería a "descubrir" lo
mismo todos los días. De ahí la purga: mueve el hash a `vistos` y borra la fila, para que
el binario no crezca para siempre en el historial de git.

**salidas/dashboard.py + plantilla.html.j2** — renderiza Jinja2 a `index.html` (lo que
sirve GitHub Pages) y `dashboard.html` (copia local, en .gitignore).

**nucleo/sheets.py** — capa de lectura desde el celular. La columna `estado` la completa
el usuario a mano y el sync nunca la pisa.

### Dos plantillas de tarjeta

La zona declara cual usa con `tarjeta: agenda|oferta`. Una nota de prensa y una promo
bancaria no tienen los mismos datos: en Agenda el score varia y sirve; en Ofertas manda
el beneficio y la vigencia, y el score no se muestra (21 tarjetas con 2 valores).

Los datos estructurados de la fuente van en `Oferta.extra` (dict -> columna `extra`, JSON):
`comercio`, `beneficio`, `descuento`, `cuotas`, `sin_interes`, `tope`, `tarjeta`, `imagen`.
Un dict y no columnas porque son campos de una sola fuente; la plantilla usa lo que conoce
y `_extra()` devuelve `{}` si el JSON viene roto.

### Tres niveles: zona > familia > tema

`zona` es una pestaña (hoy **Agenda** y **Ofertas**), declarada en el bloque `zonas:` de
`config/temas.yaml`; cada tema dice a cuál pertenece. La separación existe porque se leen
distinto: la agenda se hojea, la oferta se consulta.

El acento de color se aplica en el contenedor de la zona (`[data-acento]`), nunca en
`:root`: así todo lo de adentro cambia de color solo. Solo hay dos acentos definidos
(`teal`, `ambar`) — una zona con acento nuevo **sí** obliga a tocar el CSS.

Las destacadas del carrusel se calculan **por zona**. Global, la agenda se quedaba con
los cinco lugares y ofertas nunca destacaba nada.

### Todo tema o fuente nueva es YAML, no código

Es la promesa central del diseño. `config/temas.yaml` lleva no solo las keywords y los
filtros sino también la presentación (`zona`, `familia`, `etiqueta`, `corto`). Si agregar
un tema obliga a editar un `.py`, la promesa se rompió — arreglar el código, no el YAML.
La única excepción aceptada es el acento de color de una zona nueva.

### Dos relojes distintos, no confundirlos

- `max_antiguedad_dias` decide qué **ENTRA**: filtro de ingesta, vive en el puntuador.
- `vida_util_dias` decide qué se **SIGUE MOSTRANDO**: filtro de presentación, vive en el
  dashboard. La fila se queda en SQLite y en Sheets; solo sale de la página.

Y un **cuarto, por calendario**: `nucleo/calendario.py`. Un tema con `caduca: finde`
vence el lunes 00:00 sin importar cuando se publico, y con `ingesta: finde` solo busca
de jueves a domingo (una agenda del finde publicada un lunes habla del finde que pasó).

Hay un **tercer reloj que gana a los dos**: `Oferta.vence` (columna `vence` en SQLite).
Cuando la fuente declara hasta cuándo vale — hoy solo `fuentes/bbva.py` — el puntuador no
aplica `max_antiguedad_dias` y el dashboard ignora `vida_util_dias`: se descarta solo lo
vencido y se muestra "vence en N días". Sin esto, una promo que arrancó hace 283 días y
vence en 19 moría por vieja estando vigente.

Si `vida_util_dias` < `max_antiguedad_dias`, parte de lo que se ingiere nace invisible.
A veces es correcto, a veces es un error de config: verificarlo al agregar un tema.

### Selección vs. presentación

`puntuador.filtrar_y_ordenar()` ordena por **score** — de ahí dependen el tope por dominio
y el descarte de casi-repetidas: cuando hay que tirar algo, se conserva lo mejor.
`dashboard.recolectar()` reordena por **fecha** para mostrar. El carrusel de destacadas es
la excepción: ahí vuelve a mandar el score, porque es un destaque, no una agenda.

## Trampas conocidas

- **Los enlaces de Google News no se pueden resolver del lado del servidor.** Google cifra
  el payload; `resolver_google_news()` es best-effort y falla casi siempre. El dedup no
  depende de eso. Para la entrega existe `nucleo.urls.enlace_respaldo()`, una búsqueda en
  Google por el título exacto restringida al sitio, que siempre funciona.
- **`excluir_dominios` matchea por SUFIJO.** `".co"` como subcadena matchearía `".com"` y
  borraría todo.
- **Los anchors de YAML no concatenan listas.** Reusar `*zona_caba` y sumarle términos da
  `[[...], "extra"]`; por eso existe `_aplanar()` en el puntuador. Al tocar un anchor
  compartido, verificar que ningún tema perdió términos que tenía antes (ya pasó).
- **"Buenos Aires" matchea la Ciudad Y la Provincia.** El anchor `_fuera_de_zona` separa
  una de otra listando el conurbano y las provincias.
- **Polisemia en español:** "taller" también es galpón de reparaciones; "inglés" matchea
  "El Corte Inglés". El puntuador ancla el inicio de palabra, y el resto se resuelve
  agregando a `excluir` del tema.
- **Los controles de la barra de herramientas actuan sobre la zona visible**, no sobre
  todos los temas. Su `aria-pressed` es DERIVADO del estado de los acordeones a la vista,
  no un toggle propio: si agregas un control ahi, decide si tiene estado y recalculalo en
  `reflejarControles()`.
- **El frente de una tarjeta de oferta NO es un enlace.** Voltea al hacerle clic, y una
  superficie no puede abrir otra pagina y darse vuelta a la vez. El enlace al banco esta
  en el dorso. El boton `i` queda como control accesible (teclado y lectores).
- **Las tarjetas de oferta tienen dos caras.** Gira `.caras`, no `.tarjeta`: el boton
  de voltear queda afuera para no irse con el giro. La cara oculta lleva `aria-hidden`
  y sus enlaces `tabindex="-1"`. El alto fijo de `.caras` no es cosmetico: el dorso es
  `position: absolute`.
- **El carrusel apaga `scroll-snap-type` y `scroll-behavior` via `.pista.viva`.** Con
  snap la deriva pelea contra el iman; con `behavior: smooth` cada `scrollLeft = x` se
  anima y el bucle infinito tiembla. No devolverlos sin sacar la deriva.
- **rAF no corre en la pestana de la extension** (`visibilityState: hidden`, 0 ticks).
  Para probar animaciones, disparar PointerEvents sinteticos o medir la logica aparte.
- **El bloque `@media (max-width: 1020px)` va al FINAL del `<style>`.** Comparte
  especificidad con las reglas de los componentes: antes de ellas, no aplica. Ya pasó.
- **`resize_window` de la extension de Chrome no cambia lo que ve la pagina.** Para
  probar un breakpoint, generar una copia del HTML con el `max-width` subido y leer
  `getComputedStyle`.
- **La barra lateral redefine tokens en su scope** (`--ink`, `--muted`, `--sunken`,
  `--border`) para ser un panel de petroleo oscuro en modo claro. Los `--panel-*` del
  bloque oscuro van con valores LITERALES: `--panel-ink: var(--ink)` con `--ink:
  var(--panel-ink)` adentro es una referencia circular y CSS tira la propiedad.
- **Los tokens oscuros estan DUPLICADOS**: en el `@media (prefers-color-scheme: dark)`
  y en `:root[data-theme="dark"]`. Tocar uno solo rompe el modo automatico o el manual.
  Lo mismo con los acentos de zona, que aparecen tres veces cada uno.
- **`--faint` esta calibrado al limite de WCAG AA** (4.5:1) en ambos modos y se usa en
  texto real. Si se aclara, deja de cumplir. Sobre `--sunken` no llega: ahi va `--muted`.
- **La plantilla emite un documento HTML COMPLETO** (`<!doctype>`, `<html>`, `<head>`).
  No es republicable como Artifact sin sacar esas etiquetas. El `<meta charset="utf-8">`
  no es opcional: sin él el sitio servido suelto muestra "abriÃ³".
- **Antes de pelear con los filtros, buscar la fuente primaria.** La prensa no cubre las
  promos semanales de un banco; la API del banco sí. Para una SPA, los endpoints se
  encuentran con `performance.getEntriesByType('resource')` en el navegador — grepear los
  chunks no sirve si las URLs se arman en runtime.
- **Medir antes de configurar un tema nuevo.** Cada rubro tiene su ritmo: la agenda
  cultural es diaria, las promos bancarias son mensuales ("los descuentos de septiembre").
  Sondear Google News y contar el embudo por causa de descarte antes de fijar ventanas.
- **`_es_casi_repetida()` es para PRENSA, no para catalogos.** Con titulos formularios
  ("X 20% y 6 cuotas") colapsa comercios distintos. Los temas de catalogo llevan
  `agrupar_casi_repetidas: false`.
- **`fuentes/bbva.py` pagina con `pager`** (0-based, 20 por pagina, 47 paginas = 926
  promos). Un tema acota con `bbva_paginas: N`. La primera pagina son solo las
  destacadas: los rubros enteros (deportes, por ejemplo) viven mas atras.
- **La misma oferta puede vivir en dos temas** (el hash incluye el tema, a proposito).
  Dentro de una zona eso son dos tarjetas iguales: las destacadas se deduplican por
  (titulo, fuente). Ojo al agregar cualquier vista de nivel zona.
- **Borrar un tema del YAML no borra sus filas.** Quedan en SQLite y en Sheets. El
  dashboard las ignora por `temas_validos` (si no, la zona mostraría un total mayor que
  la suma de sus familias); se cuentan aparte como `huerfanas`.
- **Endurecer un filtro no toca lo ya guardado.** Después de cambiar reglas hay que
  reevaluar las filas existentes de `ofertas.db` a mano si importa.
- **UTF-8 en Windows:** `actualizar.bat` fija `chcp 65001` y `PYTHONUTF8=1`; sin eso el log
  sale con caracteres rotos.
- **No apuntar la tarea programada al `.bat` directo:** abre una consola en primer plano.
  Y no resolverlo con "ejecutar sin sesión iniciada": rompe el `git push` del deploy.

## Credenciales y publicación

`config/.env` y `config/service_account.json` **nunca** se versionan (ver `.gitignore`).
En Actions vienen de los secrets `GOOGLE_SERVICE_ACCOUNT` y `GOOGLE_SHEET_ID`, se escriben
al inicio del job y se borran antes del commit.

`publicar/` es un **repo git aparte** (ignorado por este) que contiene solo el HTML.
El sitio es público, así que la separación es deliberada: que sea estructuralmente
imposible filtrar la service account, no depender de un `.gitignore` bien puesto.
Sitio: https://edwardravelo.github.io/buscador-ofertas/

## Documentos del repo

- `ESTADO.md` — bitácora de decisiones por fase, con el porqué de cada arreglo. Es el
  contexto más útil antes de tocar filtros o dashboard. Mantenerlo al día.
- `FASE0-resultados.md` — la validación de señal/ruido que originó los tres filtros.
- `datos/compras-puntuales.md` — registro del modo puntual (`/buscar-oferta`).

## Slash commands del proyecto

- `/buscar-oferta <qué comprar>` — búsqueda puntual de precios. **Requiere la extensión de
  Chrome**: MercadoLibre y casi todas las tiendas argentinas devuelven 403 a WebFetch, y
  WebSearch está indexado en EE.UU. y devuelve listados de Perú. Si la extensión no está,
  el comando manda parar, no improvisar.
- `/sugerir-fuentes <tema>` — propone feeds RSS nuevos, probándolos de verdad antes de
  proponerlos.
