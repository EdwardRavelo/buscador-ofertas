# Estado del proyecto

## Fase 0 — Validación: COMPLETA (ver FASE0-resultados.md)
Google News RSS pasa el umbral en los tres temas. 36% / 80% / 40% de relevancia.

## Fase 1 — Núcleo: COMPLETA

Instalado: Python 3.13.15 + venv en `.venv`. Dependencias en `requirements.txt`.

Uso:

    .venv\Scripts\python.exe run.py buscar          # todos los temas, guarda en la base
    .venv\Scripts\python.exe run.py buscar --seco   # sin escribir (para tunear filtros)
    .venv\Scripts\python.exe run.py buscar -t ingles
    .venv\Scripts\python.exe run.py listar

Resultado de la corrida del 2026-08-30: 665 resultados crudos -> 17 guardados.
Segunda corrida: 0 nuevas, 17 ya conocidas (dedup verificado).

### Filtros que surgieron de mirar resultados reales

1. `requerir` = lista de GRUPOS, AND de ORs. Un solo grupo no alcanzaba:
   solo-zona dejaba pasar "agenda cultural"; solo-actividad dejaba pasar cursos de Madrid.
2. `max_antiguedad_dias`: Google News mezcla notas de 2018 con las de 2026.
3. `max_por_dominio`: qpasa.com metió 5 de 25 resultados en el tema de IA.
4. `excluir_dominios`: por sufijo de TLD. Más general que listar ciudades una por una.
   OJO: solo sufijo. ".co" como subcadena matchea ".com" y borra todo.
5. Coincidencia con límite de palabra al inicio: sin eso "inglés" matcheaba
   "El Corte Inglés" y colaba ofertas de notebooks.

## Limitación conocida: los enlaces de Google News

Google cifra el payload de `news.google.com/rss/articles/CBMi...`. `resolver_google_news()`
falla en el 100% de los casos probados y un fetch del lado del servidor solo devuelve una
página de redirección con JavaScript.

Consecuencias y mitigaciones:
- El DEDUP NO depende de esto: `Oferta.id` usa título normalizado + medio. Verificado.
- El MEDIO sí lo tenemos siempre, del `<source url>` del feed (clarin.com, eldestapeweb.com...).
- Para la entrega existe `nucleo.urls.enlace_respaldo(titulo, medio)`, que arma una búsqueda
  en Google por el título exacto restringida al sitio. Siempre funciona.
- FALTA VERIFICAR: si el enlace de Google News abre bien al hacerle clic en un navegador
  real. No se pudo probar porque la extensión de Chrome no está conectada.

## Fase 3 — Modo puntual: COMPLETA

Resuelto conectando la extensión de Chrome. MercadoLibre y las demás tiendas responden
sin problema desde el navegador del usuario. Primera búsqueda real registrada en
`datos/compras-puntuales.md` (parlantes para PC, 2026-08-30).

### Historial: por qué NO se puede hacer con WebFetch

Hechos los comandos `.claude/commands/buscar-oferta.md` y `sugerir-fuentes.md`.

### Supuesto del plan que resultó falso

El plan asumía que la búsqueda puntual se resolvía con búsqueda web del lado del
servidor. NO FUNCIONA. Probado el 2026-08-30 buscando parlantes para PC:

| Tienda | Resultado |
|---|---|
| MercadoLibre AR | 403 |
| Fullh4rd | 403 |
| Hardcore Computación | 403 |
| Argenprint | 403 |
| Compra Gamer | 403 (shell vacío) |
| Precialo | 403 |
| Venex | responde, sin precios en la categoría |
| Langtecnología | OK |

Además WebSearch está indexado en EE.UU. y devolvió listados de MercadoLibre **Perú**
al pedir precios de Argentina.

Único dato verificado: Logitech Z313 en Langtecnología a $330.566 ARS, anunciado como
35% off sobre $508.563. El precio de lista está inflado: el Z313 es un 2.1 de entrada
de 25W RMS. Es justo el "descuento falso" que el comando dice detectar.

### Qué falta para que funcione

Conectar la extensión de Chrome (https://claude.ai/chrome). Con eso la navegación sale
desde el navegador del usuario, con su IP y su sesión, y las tiendas no bloquean.
El comando ya quedó escrito para usar `mcp__claude-in-chrome__*` y para frenar si la
extensión no está.

## Fase 4 — Más fuentes: COMPLETA

`fuentes/rss.py` + `config/feeds.yaml`. Cinco feeds verificados el 2026-08-30 con el
mismo httpx+feedparser que los consume:

| Feed | Items | Aporta |
|---|---|---|
| buenosaires.gob.ar/rss.xml | 10 | OFICIAL del GCBA. Fuente primaria de CABA |
| soybibliotecario.blogspot.com | 25 | Blog especializado en bibliotecas |
| puraciudad.com.ar | 10 | Agenda y talleres porteños |
| notaalpie.com.ar | 10 | Aperturas de inscripción |
| bairessecreta.com | 10 | Agenda cultural, ruidoso |

Probados y descartados (sin RSS usable): villaortuzar.ar (403), eldestapeweb.com (404
en tres rutas), noticiasurbanas.com.ar, iprofesional.com y bcn.gob.ar (200 con 0 items).
Quedan anotados en feeds.yaml como "revisar a mano".

Beneficio no previsto: los items de RSS traen URL real y limpia, no el enlace opaco de
Google News. Resuelve el problema de los links para esa parte del flujo.

## Fase 6 — Dashboard: COMPLETA, ahora como sitio web

### Publicado en GitHub Pages

**https://edwardravelo.github.io/buscador-ofertas/**

Repo: https://github.com/EdwardRavelo/buscador-ofertas (PUBLICO)

Decision de arquitectura: `publicar/` es un repo git APARTE que contiene exactamente
tres archivos (index.html, .nojekyll, README.md). El codigo fuente y las credenciales
NO se versionan. Es deliberado: siendo el sitio publico, queremos que sea
estructuralmente imposible filtrar service_account.json, no depender de un .gitignore.

El deploy va dentro de `actualizar.bat`: hace commit y push solo si hubo cambios
(`git diff --cached --quiet`), para no acumular un commit vacio por dia.
Las credenciales quedaron en el Credential Manager de Windows, asi que la tarea
programada puede pushear sin intervencion.

### Diseno

`salidas/plantilla.html.j2`. Tipografias Piazzolla + Archivo, ambas de Omnibus-Type,
fundicion de Buenos Aires. Jerarquia: destacada grande arriba, tira de metricas,
tarjetas en grilla con riel izquierdo por recencia (rojo <=2d, teal <=7d, gris resto).

## YA NO SE USAN ARTIFACTS — y por que no se puede volver sin tocar el codigo

La plantilla ahora emite un documento HTML COMPLETO (`<!doctype html>`, `<html>`,
`<head>`, `<body>`). El sistema de Artifacts envuelve el archivo en su propio esqueleto
HTML, asi que republicar este archivo como Artifact anidaria un documento dentro de un
`<body>`: HTML invalido.

Si alguna vez hiciera falta volver a Artifacts, hay que sacar esas cuatro etiquetas de
la plantilla. NO es reversible con solo cambiar el destino.

El `<head>` no es un capricho: sin `<meta charset="utf-8">` el sitio servido suelto
mostraba "abriA3" en vez de "abrio". Dentro del Artifact no se veia porque el wrapper
lo agregaba.

## Fase 2 — Google Sheets: COMPLETA

Planilla: el ID esta en `config/.env` (local) y en el secret GOOGLE_SHEET_ID.
Service account: el email esta en `config/service_account.json` (local) y en el
secret GOOGLE_SERVICE_ACCOUNT. No se escriben aca: este repo es publico y, aunque
no son credenciales, no hay razon para exponerlos.

20 filas en tres pestañas. Segundo sync: 0 filas agregadas (idempotencia verificada).
La columna `estado` es del usuario y el sync nunca la pisa.

## Fase 5 — Automatización: COMPLETA (sin Telegram)

`actualizar.bat` corre buscar + sync + dashboard y loguea en `datos/corridas.log`.
Fija UTF-8 antes de arrancar; sin eso el log sale con caracteres rotos.

Tarea programada de Windows: **"Buscador de Ofertas"**, diaria a las 09:00.
Probada con `schtasks /Run`: corrió completa.

Ajustes de energia y recuperacion (los defaults de schtasks estaban mal):

    StartWhenAvailable      True   corre al encender si se perdio la hora
    AllowStartIfOnBatteries True   corre con notebook desenchufada
    StopIfGoingOnBatteries  False  no se corta si desenchufas a mitad
    WakeToRun               False  NO despierta la PC a proposito
    ExecutionTimeLimit      1h     corta si algo se cuelga

LA PC TIENE QUE ESTAR ENCENDIDA Y CON SESION INICIADA (LogonType Interactive).
Si esta apagada a las 09:00, la corrida se ejecuta apenas la prendas, no se pierde.
No se cambio a "correr sin sesion iniciada" a proposito: el `git push` usa la
credencial guardada en el Credential Manager de Windows, que es de la sesion del
usuario, y correr fuera de ella puede romper el deploy.

    schtasks /Query /TN "Buscador de Ofertas"      ver estado
    schtasks /Change /TN "Buscador de Ofertas" /ST 20:00   cambiar horario
    schtasks /Delete /TN "Buscador de Ofertas" /F   eliminar

### Telegram: salteado a pedido del usuario

`salidas/telegram.py` está escrito y probado en seco. Para activarlo basta completar
TELEGRAM_TOKEN y TELEGRAM_CHAT_ID en `config/.env` y agregar `run.py notificar` al .bat.

## Temas y diseno (2026-09-01)

Agregados `festivales-caba` y `teatro-gratis-caba`. Con cinco temas la pagina plana
era una ensalada, asi que:

- Campo `familia` en temas.yaml: "Cultura porteña" (talleres, festivales, teatro) y
  "Formación" (IA, ingles). Agrupa lo afin en vez de apilar todo en una lista.
- Cada tema es un acordeon `<details>` nativo. Abierto solo si trae novedades.
  Colapsado, los cinco temas entran en una pantalla con su cuenta y mejor puntaje.
- `etiqueta` y `corto` pasaron del codigo al YAML. Antes agregar un tema obligaba a
  editar dashboard.py, lo que rompia la promesa de "un tema es solo YAML".
- Renombrado a "Radar Porteño": el titulo viejo no cubria festivales ni teatro.

### Dos bugs que aparecieron al agregar los temas

1. El hash de dedup era `titulo + medio`, sin el tema. Una nota relevante para dos
   temas caia solo en el primero que corriera (la guia del FIBA es festival Y teatro).
   Ahora el hash incluye el tema. Se migraron los ids existentes conservando
   primera_vez para no marcar todo como nuevo.
2. Casi-repetidas: villaortuzar publico "Abre la inscripcion..." y "Abren las
   inscripciones..." de la misma nota. El dedup exacto no las agarra. Se agrego
   `_es_casi_repetida()` con similitud de Jaccard sobre raices de 5 letras
   (sin truncar daba 0.56 y no llegaba al umbral de 0.7). Solo compara notas del
   MISMO medio: dos medios cubriendo el mismo evento son dos fuentes utiles.

### Filtro de zona: Ciudad vs Provincia

"Buenos Aires" matchea la Ciudad Y la Provincia. Festivales traia el Festival de Cine
de la PROVINCIA, la UNLa (Lanus) y Avellaneda. Se agregaron a `_fuera_de_zona`:
Provincia de Buenos Aires, Avellaneda, Lanus, UNLa, conurbano, Quilmes, San Isidro,
Tigre, "kilometros de CABA". Bajo de 22 a 15 resultados.

## Orden cronologico (2026-09-01)

Las listas van de mas reciente a mas viejo, no por puntaje. El puntaje se sigue
mostrando en cada tarjeta y en el resumen del acordeon, pero ya no decide el orden:
para una agenda, lo que llego ultimo importa mas que lo que puntuo mejor hace tres
semanas.

Separacion deliberada entre seleccionar y mostrar:

- `puntuador.filtrar_y_ordenar()` sigue ordenando por SCORE. De ahi dependen el tope
  por dominio y el filtro de casi-repetidas: cuando hay que descartar, se conserva la
  mejor, no la mas nueva.
- `dashboard.recolectar()` reordena por fecha para mostrar. Las sin fecha van al final.

La destacada sigue siendo la de mayor puntaje de los ultimos 7 dias. Es un unico
destaque, no una lista: si fuera "la mas reciente" podria ser cualquier cosa mediocre
publicada hoy.

## Vida util y purga (2026-09-01)

Pregunta que disparo esto: hasta cuando sirve un resultado. La respuesta es que no
hay un numero unico, porque conviven tres relojes distintos:

| Que expira | Temas | Vida real |
|---|---|---|
| La inscripcion cierra | Talleres, cursos con cupo | 2-4 semanas |
| El evento pasa | Festivales, teatro | 1-3 semanas |
| Nunca cierra | Cursos online de Google, IBM, Platzi | Meses o anos |

Por eso `vida_util_dias` es POR TEMA: festivales 21, teatro 30, talleres 35,
ingles 90, cursos-ia 150.

### Dos conceptos que estaban fusionados

- `max_antiguedad_dias` decide que ENTRA (filtro de ingesta, en el puntuador).
- `vida_util_dias` decide que se SIGUE MOSTRANDO (filtro de presentacion, en el
  dashboard). La fila se queda en SQLite y en Google Sheets; solo sale de la pagina.

El pie del sitio dice cuantas se archivaron, para que no sea silencioso.

### Lapidas: por que no se borra directamente

Borrar una fila rompe el dedup: la proxima corrida la vuelve a descubrir y te la
anuncia como novedad. `run.py purgar` mueve el hash a la tabla `vistos` (unos 40
bytes) y recien ahi borra la fila.

Motivo real de la purga: ofertas.db se versiona en git y se commitea en cada corrida.
Sin purgar, en un ano hay cientos de versiones de un binario cada vez mas grande, y
git no comprime bien SQLite entre versiones. El umbral (365d) esta muy por encima de
cualquier vida_util configurada, asi que nunca borra algo todavia visible.

## Falsos positivos por polisemia (2026-09-01)

Tres clases distintas de ruido, cada una con su arreglo:

1. POLISEMIA. "taller" en espanol tambien es galpon de reparaciones (los talleres
   del subte) y atelier ("recorridos guiados por talleres y negocios", 9.5).
   Se agregaron a `excluir`: taller mecanico, talleres del subte, metrodelegados,
   recorridos guiados, taller de reparacion, talleres ferroviarios.

2. EL FILTRO NUNCA PIDIO EL TEMA REAL. El tema se llama "talleres de LECTURA" pero
   el grupo requerido era [taller, inscripcion, cupos, curso]: nada sobre leer. Por
   eso pasaba "Jorge Macri abre el Congreso Federal de Ciudades Inteligentes".
   Tercer grupo agregado: lectura, escritura, literatura, biblioteca, libro,
   escritor, poesia, narrativa, cuento, lectores, bibliotecario.

3. GEOGRAFIA POR INSTITUCION. "Escuelas Oficiales de Idiomas" (Espana), "salvadoreno"
   (Platzi El Salvador) y "UMSNH" (Michoacan) publican desde dominios .com, asi que
   el filtro de TLD no los agarraba y el titulo no nombra la ciudad.

### Regresion propia que esto destapo

Al crear el anchor compartido `_zona_caba` se habia perdido "Biblioteca Nacional",
que estaba en el grupo original del tema. Los dos avisos de la Biblioteca Nacional
(uno de ellos el mejor de todos, 10.0) murieron por "fuera de zona". Se restauro
como `[*zona_caba, "Biblioteca Nacional", "Biblioteca del Congreso"]`.

Eso obligo a agregar `_aplanar()` en el puntuador: YAML no concatena listas, asi que
reusar un anchor y sumarle terminos propios produce [[...compartida...], "extra"].
Sin aplanar, _contiene() recibia una lista donde esperaba un string.

### Reevaluacion de lo ya guardado

Endurecer un filtro no toca lo que ya esta en la base. Se reevaluaron las 48 filas
contra las reglas nuevas: 9 borradas, 6 repuntuadas. Quedan 41.

## Pendiente para la proxima sesion

1. Telegram: salteado a pedido. `salidas/telegram.py` esta escrito y probado en seco.
   Para activarlo: completar TELEGRAM_TOKEN y TELEGRAM_CHAT_ID en `config/.env` y
   agregar una linea `run.py notificar` al `actualizar.bat`.
2. Sumar fuentes con `/sugerir-fuentes <tema>`. Los feeds descartados por no tener RSS
   quedaron listados en `config/feeds.yaml`.
3. Agregar temas nuevos editando `config/temas.yaml`. No requiere tocar codigo.
4. Si alguna vez se quiere el sitio PRIVADO: Cloudflare Pages con Access lo hace gratis.
   Hoy el repo es publico; tiene `<meta name="robots" content="noindex">` pero eso es una
   convencion para buscadores, no una proteccion de acceso.

## Comandos

    .venv\Scripts\python.exe run.py buscar          busca y guarda
    .venv\Scripts\python.exe run.py buscar --seco   sin escribir, para tunear filtros
    .venv\Scripts\python.exe run.py listar          muestra lo guardado
    .venv\Scripts\python.exe run.py sync            sincroniza Google Sheets
    .venv\Scripts\python.exe run.py dashboard       regenera el HTML
    .venv\Scripts\python.exe run.py notificar --seco   Telegram, sin enviar
    actualizar.bat                                    todo junto + deploy

Slash commands: `/buscar-oferta <que comprar>` y `/sugerir-fuentes <tema>`.
