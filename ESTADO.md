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

#### Corrida silenciosa (2026-09-10)

La tarea llamaba a `actualizar.bat` directo, así que a las 09:00 aparecía una consola
negra en primer plano, encima de lo que el usuario estuviera haciendo. Ahora la acción
de la tarea es:

    wscript.exe "...\actualizar-silencioso.vbs"

El .vbs hace `WScript.Shell.Run` del .bat con estilo de ventana **0** (oculta) y
`bWaitOnReturn = True`, para devolver el código de salida: sin esperar, la tarea
informaría éxito siempre. Verificado: corre sin ventana y propaga el exit code.

Lo que NO se hizo, a propósito: cambiar la tarea a "Ejecutar aunque el usuario no haya
iniciado sesión". También oculta la ventana, pero el `git push` usa la credencial del
Credential Manager de la sesión del usuario y el deploy se rompería. La tarea sigue
siendo `Interactive` / `LogonType: Interactive`, igual que antes.

Deuda conocida: VBScript está deprecado en Windows 11 (hoy es una Feature on Demand
instalada por defecto). Si algún día `wscript.exe` deja de existir, el reemplazo es
`conhost.exe --headless cmd /c actualizar.bat` como acción de la tarea.

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

Por eso `vida_util_dias` es POR TEMA: festivales 10, teatro 30, talleres 35,
ingles 90, cursos-ia 150.

Festivales bajo de 21 a 10 dias el 2026-09-10. La ventana de INGESTA sigue en 21: el
anuncio previo del festival sigue entrando, pero a los 10 dias de publicado lo mas
probable es que el evento ya haya pasado y la tarjeta solo ocupe lugar.

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

## Zonas: se amplio el nicho a ofertas (2026-09-10)

La pagina era solo agenda cultural y formacion. Se sumo un espacio de OFERTAS,
separado con pestanas. Jerarquia nueva: **zona > familia > tema**.

Las zonas se declaran en el bloque `zonas:` de `config/temas.yaml` y cada tema
dice a cual pertenece. Sigue valiendo la promesa: agregar un tema es editar YAML.
La unica excepcion es el ACENTO de color: `teal` y `ambar` estan definidos en el
CSS de la plantilla, asi que una zona con un acento nuevo si obliga a tocarlo.

### Por que pestanas y no una familia mas

Se leen distinto. La agenda se hojea ("que hay para hacer este finde"); la oferta
se consulta ("que descuento tengo hoy"). Apiladas en una sola lista, la promo de
hoy queda enterrada entre talleres de hace tres semanas. Ademas la zona de ofertas
va a crecer con subtemas por banco, y una tercera familia no hubiera escalado.

Detalles de implementacion:
- El acento se define en el contenedor de la zona (`[data-acento]`), no en `:root`.
  Asi TODO lo de adentro (tarjetas, riel de recencia, foco, marcas) cambia de color
  solo, sin duplicar una regla por zona.
- Las destacadas se calculan POR ZONA. Con un carrusel global, la agenda (cinco
  temas) se quedaba siempre con los cinco lugares y ofertas nunca destacaba nada.
- La zona elegida se recuerda en localStorage: si entras a mirar las promos todos
  los dias, no tenes que volver a elegir la pestana.
- Sin JS las pestanas se ocultan y las zonas quedan apiladas (`<noscript>`).
- Una zona sin resultados igual emite su pestana. Una pestana que aparece y
  desaparece segun el dia confunde mas que una vacia que explica por que lo esta.

## Promos bancarias: lo que el sondeo dijo y como cambio el plan (2026-09-10)

El pedido original fue "promociones con el Banco Frances". Se sondeo Google News
antes de escribir el tema (mismo criterio que la Fase 0) y el resultado obligo a
cambiar el enfoque:

| Lo que se asumia | Lo que se midio |
|---|---|
| BBVA/Frances tiene flujo propio de promos | Todo viejo: el item BBVA mas fresco tenia 43 dias |
| El rubro se renueva a diario | Se renueva MENSUAL: "los descuentos de septiembre", publicados el dia 1 |
| Una ventana corta (7-10d) es lo correcto | Con 10 dias pasaban 4 de 424; con 45 entraban promos de AGOSTO ya vencidas |

Decisiones que salieron de ahi:
- El tema es el RUBRO (`promos-bancarias`), no el banco. BBVA entra como `senales`,
  un campo nuevo: suma hasta +2.0 pero no es obligatorio. Si fuera `requerir`, el
  tema quedaria vacio todas las semanas que BBVA no publica nada.
- `max_antiguedad_dias: 21`, medido: es donde entra el mes en curso y nada expirado.
- `vida_util_dias: 21` tambien, IGUAL a la ingesta y a diferencia del resto de los
  temas. Los dos relojes coinciden aca porque la promo no vence a los N dias de
  publicada sino a fin de mes, y ningun reloj rodante modela eso. Con 14 entraban
  8 avisos y 4 nacian invisibles: lo peor de los dos mundos.
- Domina Banco Nacion, no BBVA. Es fiel a la realidad del rubro, no un bug.

Feeds nuevos verificados el 2026-09-10: `sirchandler.com.ar` (20 items, del dia,
es el que mejor cubre BBVA) e `infoviajera.com` (10, del dia). `bbva.com` NO tiene
RSS de Argentina usable (`/es/ar/feed` da 404; `/es/feed` responde 200 con 0 items).

## Fuente BBVA y vigencia declarada (2026-09-10)

RESUELTO lo anterior: BBVA Go tiene una **API publica** que responde JSON sin login
y desde el servidor. `fuentes/bbva.py` la consume.

    https://go.bbva.com.ar/willgo/fgo/API/v3/communications

Se encontro leyendo `performance.getEntriesByType('resource')` en la pagina
`bbva.com.ar/beneficios` (una SPA de Next.js) con la extension de Chrome. Los
endpoints no estan en los chunks como literales: se arman en runtime, asi que
grepear el JS no alcanza.

Devuelve 20 promos vigentes con `cabecera`, `fechaDesde`, `fechaHasta`,
`montoTope`, `grupoTarjeta` y `diasPromo`. Otros endpoints del mismo host:
`/slides` (790 banners, solo imagenes), `/v3/rubros/filtro`, `/v3/provincias`,
`/deeplink/{id}`.

Limitacion: dice "926 comunicaciones, 47 paginas" pero NO se encontro el parametro
de paginacion. Probados sin exito: page, pagina, p, offset, pageNumber, nroPagina,
pageSize, y las formas de path `/2` y `/page/2`. Se leen las 20 destacadas.

`diasPromo` viene como siete flags ("0,0,0,1,0,0,0") y NO esta documentado que dia
es el primero. Por eso el snippet dice "solo N dia(s) de la semana: ver el detalle"
en vez de nombrar el dia: decir "los jueves" cuando puede ser miercoles es peor que
no decir nada.

### Vigencia declarada: el tercer reloj

Hasta ahora el proyecto estimaba vigencia con dos relojes rodantes sobre la fecha
de publicacion (`max_antiguedad_dias`, `vida_util_dias`). La API del banco dice
`fechaHasta`, asi que para esas ofertas no hay que estimar nada.

Se agrego `Oferta.vence` y la columna `vence` en SQLite. Como `CREATE TABLE IF NOT
EXISTS` no agrega columnas a una base que ya existe --y ofertas.db se versiona en
git, con bases vivas del esquema viejo-- se agrego `_migrar()` en almacen.py con un
ALTER TABLE idempotente. Es el primer cambio de esquema del proyecto: si hacen
falta mas columnas, sumarlas a `_COLUMNAS_NUEVAS`.

Regla, en los dos lados:
- `puntuador`: si hay `vence`, NO corre el filtro de antiguedad; descarta solo lo
  ya vencido y da bonus a lo que vence pronto. Sin esto, "Jumbo QR Modo" (arranco
  hace 283 dias, vence en 19) moria por vieja estando vigente.
- `dashboard`: si hay `vence`, ignora `vida_util_dias`, ordena por lo que vence
  primero y muestra "vence en N dias" en vez de "hace N dias".
- `almacen.guardar`: al reencontrar una oferta REFRESCA `vence`. El banco prorroga
  promos; con la fecha congelada, una promo extendida desapareceria el dia que
  decia la version vieja.

El pie del sitio se corrigio: ya no dice que nunca sabemos cuando cierra.

### Se elimino el tema de prensa (2026-09-10)

Con la API del banco andando, `promos-bancarias` (prensa) quedo sin razon de ser: traia
sobre todo Banco Nacion y MODO, que no sirven sin esas tarjetas. Se elimino del YAML.

Sus 8 filas SIGUEN en ofertas.db a proposito: borrarlas es irreversible y no molestan.
Para sacarlas: `DELETE FROM ofertas WHERE tema = 'promos-bancarias'`, idealmente
moviendo antes los ids a `vistos` como hace `run.py purgar`.

Eso destapo un bug: las filas de un tema eliminado caian en la zona por defecto de
`_armar_zonas()` y se contaban, asi que Agenda mostraba 55 con familias que sumaban 47.
`recolectar()` ahora las saltea con `temas_validos` y las cuenta aparte (`huerfanas`).
El fallback a la primera zona sigue existiendo, pero solo para un tema que SI esta en el
YAML con una `zona` mal escrita, que es el caso para el que se penso.

Los feeds `sirchandler` e `infoviajera` quedaron sin tema y se sacaron de `feeds:`.
Estan anotados al pie de feeds.yaml: responden, estan frescos y se reactivan poniendoles
`temas` si alguna vez se quiere prensa sobre tarjetas.

### Mercado Pago: probado y descartado (2026-09-10)

Pedido junto con las cuotas sin interes. No hay fuente publica fresca hoy:

| Ruta | Resultado |
|---|---|
| mercadopago.com.ar/promociones | 200, pero contenido de **Hot Sale, "valido del 11 al 17 de mayo"** |
| /promociones/todas | igual: unico mes mencionado, mayo |
| /ofertas, /descuentos, /beneficios | 200 con 5.7 KB: cascara de SPA, sin datos |
| api.mercadopago.com/promotions | 404 |

Sumar una fuente que emite promos de mayo en septiembre seria peor que no tenerla.
Queda pendiente encontrar el endpoint real (probablemente detras de la app).

## Subtemas de compra puntual (2026-09-10)

Familia nueva en la zona Ofertas: **"Lo que estoy buscando"**. Temas que se agregan y
se borran segun lo que haga falta comprar. El primero: `pelota-futbol`.

QUE ES Y QUE NO ES. No busca el precio de una pelota: busca promos del banco EN
COMERCIOS donde se compra una. El banco publica "Nike 6 cuotas", nunca "pelota 20% off",
asi que el filtro va por comercio y rubro, no por producto. Para el precio del producto
esta `/buscar-oferta`, que lee MercadoLibre desde el Chrome del usuario.

Como esta armado: `fuentes: [bbva]` y dos grupos en `requerir` (comercio deportivo Y
tipo de promo). No declara ventanas de tiempo porque la fuente trae `fechaHasta`.
Resultado del dia: 1 de 20 (Nike 6 cuotas, vence 30-09). Va a estar seco seguido; es un
radar, se enciende cuando el banco publica algo del rubro.

### Paginacion encontrada: de 20 promos a 926 (2026-09-10)

El usuario aviso que faltaban ofertas (Dexter, y comercios deportivos que el banco
clasifica en Moda). Tenia razon: `fuentes/bbva.py` leia solo la primera pagina.

El parametro es **`pager`** (0-based, 20 por pagina, 47 paginas). No se adivina: se
capturo espiando `window.fetch` en la pagina del banco mientras se hacia clic en
"Consultar todas las promociones". Notas del intento:
- La ruta del listado (`/beneficios/beneficios?rubros=170`) da 404 si se entra
  directo: es ruta de cliente, solo funciona navegando desde la SPA.
- El listado completo usa EL MISMO endpoint `/v3/communications`, con `pager`.
- La extension de Chrome censura los query strings en la salida, asi que hay que
  pedir los NOMBRES de los parametros (`searchParams.keys()`), no las URLs.

Impacto medido: 22 promos de comercios deportivos, TODAS fuera de la primera pagina.
Con una sola pagina, el tema de la pelota mostraba 1 (Nike). Ahora 21.

`bbva_paginas: N` en el tema acota la lectura. El tema `bbva` usa 1 (las 20 que el
banco destaca); los temas de compra puntual leen todo, porque filtran por comercio.
Volcar 926 promos en un acordeon no es una pagina, es un volcadero.

### Tres bugs que este subtema destapo

1. `_es_casi_repetida()` COLAPSABA COMERCIOS DISTINTOS. El heuristico asume titulares
   de PRENSA, donde dos textos casi iguales del mismo medio son la misma nota. En un
   CATALOGO es al reves: los titulos son formularios ("X 20% y 6 cuotas") y lo unico
   que los distingue es el nombre del comercio, que suele ser corto y lo pierde el
   stemmer de 5 letras. "Top Sport 20% y 6 cuotas" y "Sport 78 6 cuotas" reducian
   ambos a {sport, cuota}: similitud 1.0. Se perdian 3 de 21.
   Ahora hay `agrupar_casi_repetidas` por tema (default true, false en catalogos).
2. "A'S Mundodeporte" no matcheaba "Deporte": `_contiene()` ancla el INICIO de
   palabra y ahi va pegado. Se agrego el termino en vez de relajar el anclaje, que
   romperia los temas de prensa (por eso existe: sin el, "ingles" matchea "El Corte
   Ingles").
3. El banco publica "Albert Sport" dos veces con titulo identico. El dedup por hash
   lo colapsa bien: 22 items del catalogo -> 21 en la pagina. No es un bug nuestro.

### Dos bugs que este subtema destapo

1. DUPLICADO EN EL CARRUSEL. `Oferta.id` incluye el tema a proposito, asi que la misma
   promo vive en `bbva` y en `pelota-futbol`. A nivel tema esta bien; a nivel ZONA son
   dos tarjetas identicas, y el carrusel mostraba "Nike 6 cuotas" dos veces. Ahora las
   destacadas se deduplican por (titulo, fuente).
2. TEMA QUE DICE "TODAVIA NADA" TENIENDO ALGO. El cuerpo del tema excluye las
   destacadas; si TODAS sus ofertas subieron al carrusel, quedaba vacio mostrando
   "Todavia nada para este tema" mientras el resumen de al lado decia "1 nueva".
   Ahora, si `total` > 0 pero la lista quedo vacia, dice "Lo de este tema esta en los
   destacados, arriba".

## Rediseno: dos tarjetas, una por zona (2026-09-11)

Diagnostico previo, con datos y no con gusto:

| Sintoma | Medicion |
|---|---|
| El puntaje dominaba la tarjeta sin distinguir nada | `pelota-futbol`: 21 tarjetas, **2** valores de score. En `festivales-caba`, 15 valores en 26 |
| Los mejores datos no se mostraban NUNCA | tope, tarjeta y % vivian aplastados en `snippet`, que la plantilla no renderiza |
| Chips de relleno | `senal: promocion` en las 21; `Dexter` repetia el titulo |
| "vence en 1 mes" | teniendo la fecha exacta (27/10) |

### `Oferta.extra`: datos estructurados

Columna nueva `extra` (JSON) en vez de una columna por campo: son datos de UNA
fuente y la plantilla usa solo las claves que conoce. `fuentes/bbva.py` parte el
titulo en comercio + beneficio ("Dexter 20% y 6 cuotas" -> "Dexter" / "20% y 6
cuotas") y suma descuento, cuotas, sin_interes, tope, tarjeta, imagen y
dias_limitados. Medido: 52 de 60 promos traen logo, 37 traen tope.

Bug atrapado al probar: la regex de porcentaje era `\d{1,2}` y "Cabify 100% OFF"
daba "00%". Tres digitos.

### Dos plantillas de tarjeta

La zona declara cual usa (`tarjeta: agenda|oferta` en el bloque `zonas:`).
- AGENDA: puntaje + medio + antiguedad. Sin cambios, ahi el score si varia.
- OFERTA: logo + comercio + tarjeta que aplica, el beneficio como pieza central,
  y tope + vigencia al pie. Sin puntaje.

El carrusel tambien se bifurca: en Ofertas muestra el beneficio, no el "7.5".
Y la metrica "recien publicadas" (que en Ofertas daba 0 casi siempre) se cambia
por "vencen en 7 dias", que es lo que apura en una promo.

### Detalles que solo apareceron mirando la pagina

- "Coto NFC" no tiene ni % ni cuotas: la caja de beneficio quedaba dibujada y
  vacia. Ahora no se emite si no hay que poner nada.
- La caja se estiraba a todo el ancho alrededor de un "20%". `align-self:
  flex-start` para que abrace su contenido.
- "solo 1 dias por semana".
- Un separador "&middot;" huerfano en el carrusel, porque la vigencia va empujada
  a la derecha con margin-left:auto.

### Limitacion aceptada: logos blancos

Las imagenes son del banco (`go.bbva.com.ar`), hotlinkeadas. Cargan bien (0 rotas
de 33) pero 2 o 3 comercios publican el logo en blanco sobre transparente, asi que
sobre el recuadro blanco no se ven. No hay forma de detectarlo sin analizar el
pixel. Si el banco mueve las imagenes, `onerror` esconde el hueco.

## Tema visual conmutable y auditoria de contraste (2026-09-11)

Selector de tres estados en el encabezado: **Auto / Claro / Oscuro**. Tres y no un
interruptor de dos a proposito: la pagina ya seguia a `prefers-color-scheme`, y un
switch binario habria eliminado esa opcion sin avisar. "Auto" borra el atributo
`data-theme` y deja mandar a los `@media`.

Detalles que importan:
- El tema se aplica en un `<script>` del `<head>`, ANTES de pintar. Con el JS al
  final del body, quien elige "oscuro" ve un fogonazo blanco en cada carga.
- Se agrego `color-scheme` para que la barra de scroll y los controles nativos
  acompanen. Sin eso, en modo oscuro forzado la scrollbar seguia clara.
- Se guarda en localStorage (`radar:tema-visual`); "auto" borra la clave en vez de
  guardar el string, asi el default vuelve a ser el sistema.
- Sin JS el selector se oculta (`<noscript>`): un control que no hace nada es peor
  que no tenerlo. El CSS sigue respetando prefers-color-scheme igual.

### La paleta no pasaba WCAG AA, y no se veia a ojo

Se midio con un script (contraste WCAG 2.x sobre los pares que la pagina usa de
verdad, no todos contra todos). Fallas encontradas:

| Par | Antes | Ahora |
|---|---|---|
| `--faint` sobre tarjeta, CLARO | 3.11 | 4.87 |
| `--faint` sobre fondo, CLARO | 2.91 | 4.56 |
| `--faint` sobre tarjeta, OSCURO | 4.16 | 4.51 |
| `--faint` sobre `--sunken` (contadores) | 4.28 | se cambio el elemento a `--muted`: 5.23 |

`--faint` no es decorativo: lo usan `.plastico` ("Tarjetas de credito BBVA"),
`.sello` ("Actualizado..."), `.alterno` ("buscar la nota") y las pestanas inactivas.

Los valores nuevos se calcularon moviendo SOLO la luminosidad en HLS, para no
cambiar el tono de la paleta: #83959E -> #62747D (claro), #6D808B -> #738691
(oscuro). Los bordes tambien subieron un escalon (#DBE4E8 -> #C8D5DC y #26343D ->
#2B3B45): no son texto, pero a 1.21 la tarjeta no se despegaba del fondo.

El script de auditoria quedo en el scratchpad, no en el repo. Si se toca la paleta,
conviene rehacerlo: lee los tokens del `.j2`, asi que no se desactualiza.
Resultado hoy: **18 pares medidos por modo, 0 fallas**.

## Armazon de dashboard (2026-09-11)

La pagina era una columna de 1080px centrada. En un monitor ancho, medio viewport
era margen y habia que scrollear hasta arriba para cambiar de zona.

Ahora: `.envoltorio` a 1560px y un grid `.armazon` de **236px + resto**.
- BARRA LATERAL fija (`position: sticky`): titulo, selector de tema, pestanas de
  zona en vertical y los tres controles. Se cambia de zona sin scrollear.
- LIENZO: KPIs, carrusel y familias, con la grilla mas densa (minmax 272px, y 258
  para ofertas). Pasa de 3 columnas a 4-5 segun el ancho.
- Las metricas dejaron de ser una fila flex y son un panel `auto-fit`, asi no
  quedan huecos cuando una zona tiene menos familias.
- El carrusel muestra 2-3 destacadas a la vez (`flex: 0 0 clamp(300px,33%,460px)`)
  en vez de una sola a pantalla completa.
- El titulo bajo de 62px a ~34px: en la barra lateral acompana, no encabeza.

### Dos cosas que hubo que corregir

1. ORDEN DE LA CASCADA. El bloque `@media (max-width: 1020px)` estaba ANTES de las
   reglas de los componentes. Misma especificidad, asi que las reglas base ganaban
   por orden y las pestanas se quedaban verticales en pantalla angosta. Se movio al
   final del `<style>`, junto a las otras media queries. Si se agregan reglas
   responsive, van ahi.
2. Los titulares de prensa en una diapositiva de 33% ocupaban NUEVE lineas y
   estiraban el carrusel a media pantalla. `-webkit-line-clamp: 4` y tamano fijo;
   el titulo completo queda en el atributo `title`.

### Como se verifico el modo angosto

El `resize_window` de la extension informa exito pero la pagina sigue viendo
2048px, asi que no sirve para probar breakpoints. Se genero una copia de index.html
con el `max-width: 1020px` cambiado a `9999px` y se inspecciono `getComputedStyle`:
armazon a una columna, barra estatica, pestanas y controles en fila, sin desborde
horizontal. La copia se borro despues.

## Carrusel infinito, a la deriva y arrastrable (2026-09-11)

Reescrito entero. Antes era scroll-snap + flechas. Ahora las tres cosas conviven en
un unico `requestAnimationFrame` por carrusel:

- INFINITO: se clonan las diapositivas una vez. Cuando el scroll pasa el ancho de
  un ciclo se le RESTA ese ancho sin animacion; el salto no se ve porque lo que
  queda a la vista es identico. El ancho del ciclo se MIDE
  (`clones[0].offsetLeft - originales[0].offsetLeft`), no se calcula sumando gaps.
- DERIVA: `scrollLeft += VELOCIDAD * dt`, por milisegundo y no por frame, asi la
  velocidad no cambia con los Hz del monitor. `dt` se topea en 50ms porque una
  pestana en segundo plano devuelve saltos enormes al volver.
- ARRASTRE: pointer events con `setPointerCapture`. Un umbral de 4px separa el
  clic del arrastre; si hubo arrastre, el `click` posterior se cancela en fase de
  captura (si no, soltar sobre un titulo abria la nota).

Detalles que hubo que resolver:
- El CSS pelea con el JS: `scroll-snap-type` hace que el iman discuta con la
  deriva, y `scroll-behavior: smooth` ANIMA cada asignacion de `scrollLeft`, lo
  que convierte el bucle en un temblor. Los dos se apagan en `.pista.viva`, clase
  que pone el JS. Sin JS la pista conserva el snap y se sigue arrastrando.
- Los clones llevan `aria-hidden="true"` y sus enlaces `tabindex="-1"`: para un
  lector de pantalla y para el tabulador siguen siendo cinco destacadas, no diez.
- Los puntos ahora van al equivalente MAS CERCANO del indice, no al del primer
  ciclo: si no, tocar el punto 1 estando sobre los clones retrocedia todo.
- Las flechas ya no se deshabilitan: con bucle infinito no hay extremos.
- `prefers-reduced-motion: reduce` apaga la deriva (el arrastre sigue).

### Pausa

Se detiene con el mouse apretado (era el pedido) y TAMBIEN al pasar el mouse por
encima o al entrar el foco por teclado. Lo segundo no se pidio: se agrego porque
un carrusel que sigue moviendose mientras intentas hacer clic te corre el blanco.
Si molesta, son las cuatro lineas de `mouseenter/mouseleave/focusin/focusout`.

### Como se probo, ya que rAF no corre en segundo plano

La pestana manejada por la extension esta `visibilityState: "hidden"`, asi que
`requestAnimationFrame` NO dispara: 0 ticks en un segundo. La deriva no se puede
observar por ahi. Lo que si se verifico, con PointerEvents sinteticos (pasan por
el mismo `normalizar()`):

| Prueba | Resultado |
|---|---|
| Ancho del ciclo medido | 2106 px |
| Arrastrar 300 px | scrollLeft 300 |
| Arrastrar mas de un ciclo | dio la vuelta a 120 px |
| Cursor al agarrar / soltar | grabbing / grab |
| Clic despues de arrastrar | NO abre la nota |
| Clones sin foco ni lectura | 5 originales + 5 clones, todos ocultos |

## 3D en las tarjetas de oferta (2026-09-12)

Se pidio "algo de modelado 3D". Se descartaron dos caminos y se eligio el unico que
AGREGA informacion en vez de decorar:

| Idea | Por que no |
|---|---|
| Objeto/modelo girando en el encabezado | ~600 KB de three.js en una pagina de uso diario que hoy pesa 100 KB, para algo que no dice nada de las ofertas |
| Radar 3D con los datos (el sitio se llama Radar Porteno) | Sigue siendo una idea buena y pendiente; mas trabajo y si necesita libreria |

Lo hecho: **inclinacion y volteo con transformaciones CSS. Cero dependencias, 0 KB.**

### Por que habia letra chica que mostrar

No se invento contenido para justificar el efecto. Medido sobre la pagina real:
- **20 de 35** tarjetas tenian la linea "Tarjetas de credito y debito BBVA" cortada
  con puntos suspensivos.
- La fecha de INICIO de la promo (`fechaDesde`) no se mostraba en ningun lado.
- El puntaje y los motivos se habian sacado del frente en el rediseno anterior.

El dorso muestra: vigencia completa (desde al hasta), la tarjeta que aplica sin
cortar, el tope, los dias limitados y el encaje con sus motivos, mas el enlace.

### Detalles de implementacion

- Solo gira `.caras`; el boton `i` vive FUERA, en la tarjeta. Si estuviera adentro
  se voltearia con ella y no habria con que volver.
- `min-height: 248px` en `.caras`: el dorso va `position: absolute` y necesita una
  caja fija. De paso empareja la grilla, que iba de 193 a 242px.
- La cara oculta queda con `aria-hidden` y sus enlaces con `tabindex="-1"`, que se
  intercambian al voltear: si no, el tabulador cae en enlaces invisibles.
- Escape cierra la tarjeta volteada que tenga el foco adentro.
- La inclinacion (5 grados) la escribe el JS en `--rx`/`--ry` con un listener
  delegado, no uno por tarjeta. Se apaga si la tarjeta esta volteada: sumarla al
  giro de 180 grados marea e invierte los ejes.
- Nada de esto corre con `prefers-reduced-motion: reduce` ni en tactil
  (`hover: hover and pointer: fine`).

### Verificacion

Las transiciones tambien estan congeladas en la pestana de la extension, asi que se
midio el estado final con la transicion apagada:

| Que | Resultado |
|---|---|
| `.caras` volteada | `matrix3d(-1,0,0,0, 0,1,0,0, 0,0,-1,0, 0,0,0,1)` = rotateY(180) exacto |
| Tarjeta inclinada | matrix3d con perspectiva -1/900 |
| `transform-style` / `backface-visibility` | preserve-3d / hidden |
| Alturas de las 35 tarjetas | todas 250px |
| aria-expanded, aria-hidden, tabindex | se intercambian al voltear |

### Voltea la tarjeta entera, no solo el boton (2026-09-12)

El clic en cualquier parte de la tarjeta la voltea. Eso obligo a un cambio que no es
cosmetico: **el frente dejo de ser un enlace**. Antes toda la cara delantera era un
`<a>` al banco; una superficie no puede ser al mismo tiempo "abre otra pagina" y
"se da vuelta". El enlace al banco ahora vive solo en el dorso ("Ver en bbva.com.ar").

El boton `i` se mantiene aunque parezca redundante: es el control accesible. Un
`<article>` no se puede enfocar con el tabulador ni anunciarse como "mostrar la letra
chica"; el clic en la superficie es una comodidad para el mouse, no la unica via.

Reglas del handler delegado:
- Un enlace adentro hace lo suyo y NO voltea (si no, tocar "Ver en el banco" daba
  vuelta la tarjeta antes de abrir la pestana).
- Si hay texto seleccionado dentro de la tarjeta, soltar el mouse no voltea.
- El dorso tambien voltea al tocarlo, asi se vuelve sin buscar el boton.

Verificado paso a paso desde un estado limpio: clic en el cuerpo voltea; clic en el
dorso vuelve; el boton sigue funcionando; el enlace del dorso NO alterna; con texto
seleccionado no pasa nada. `aria-expanded` acompana en los cinco casos.

### Alcance

Solo las tarjetas de OFERTA. Las de agenda no tienen letra chica que esconder (sus
motivos ya se ven como chips), asi que no llevan ni volteo ni inclinacion. Si se
quiere inclinacion ahi tambien, es cambiar el selector `.tarjeta.promo` del JS.

## Zona "Este finde" y caducidad por calendario (2026-09-12)

Tercera zona, primera de la lista porque es lo mas perecedero. Un tema:
`finde-caba` (musica, teatro, arte y cualquier expresion artistica en CABA).

### El tercer reloj: caducidad por calendario

Los dos relojes anteriores son RODANTES (N dias desde que se publico) y el de la
API del banco es una FECHA DECLARADA por la fuente. La agenda del finde no es
ninguno: caduca el LUNES, se haya publicado el jueves o el domingo.

`nucleo/calendario.py`, nuevo:
- `fin_del_finde()` -> proximo lunes 00:00 de Buenos Aires. Se escribe el offset
  -3 a mano en vez de usar zoneinfo: `tzdata` no viene con Python en Windows ni
  esta garantizado en el runner de Actions, y el pais no cambia de hora desde 2009.
- `es_dia_de_ingesta()` -> el tema con `ingesta: finde` solo busca de JUEVES a
  DOMINGO. Sin esto, una agenda publicada un lunes (que habla del finde que ya
  paso) entraba y sobrevivia hasta el lunes siguiente: una semana entera de
  informacion vencida.
- `caducidad()` -> lo llama run.py y le pone `vence` a todo lo elegido. Se
  recalcula en cada corrida, asi una nota que reaparece el sabado mueve su
  vencimiento al lunes que corresponde.

El dashboard no necesito cambios: ya prefiere `vence` sobre `vida_util_dias`.

### Dos cosas que aparecieron al probar

1. SINDICACION. La misma nota de Clarin aparecia TRES veces: fmalpina.com.ar y
   todobasquet.com.ar la republican palabra por palabra. El hash no las junta
   (distinto medio) y `_es_casi_repetida` solo compara dentro del mismo medio, a
   proposito. Se agrego `unico_por_titulo`, que descarta el titulo EXACTO venga
   de donde venga. Sigue sin tocar dos medios cubriendo el mismo evento con
   titulos distintos, que son dos fuentes utiles.
   PENDIENTE: de las tres copias queda una arbitraria (hoy quedo fmalpina, no
   Clarin). No hay forma de rankear medios sin una lista de calidad.
2. "Salame, bunuelos y caballos criollos: la agenda del fin de semana en la
   Provincia" pasaba el filtro de zona. El anchor `_fuera_de_zona` pide
   "Provincia de Buenos Aires" completo; se agrego "en la Provincia".

### Acento violeta

Tercer acento, y eso SI obliga a tocar el CSS (esta documentado como la unica
excepcion a "todo es YAML"). Calculado para cumplir contraste, igual que la
paleta base: claro #7C4DDB (4.99 sobre tarjeta y fondo), oscuro #A98BE8 (6.14),
con sus tintes y sobre-acento.

## Panel izquierdo solo de categorias (2026-09-12)

- La barra lateral queda con el titulo y las tres categorias. Nada mas.
- Los filtros (Solo nuevas / Abrir todo / Cerrar todo) pasaron al cuerpo, en una
  barra de herramientas arriba del contenido.
- El tema visual dejo de ser un grupo de tres estados y es un `role="switch"`
  binario, a la derecha de esa barra. "Auto" ya no es una opcion explicita, pero
  no se perdio: quien nunca lo toca no tiene valor guardado y el CSS sigue
  resolviendo con `prefers-color-scheme`; el interruptor muestra el tema EFECTIVO
  y sigue al sistema si cambia. Verificado: sin elegir marca lo que dice el
  sistema, el primer clic guarda lo contrario, el segundo vuelve.
- Las destacadas nunca son mas de la MITAD de la zona. Con 3 avisos, las 5
  destacadas se llevaban todo y el acordeon quedaba vacio diciendo "esta arriba".

## Bug propio: el catalogo de BBVA corria en TODOS los temas (2026-09-12)

Introducido al registrar `fuentes/bbva.py`. Un tema sin `fuentes:` declarado corre
todas las fuentes registradas, asi que cada tema de prensa se bajaba las 47
paginas del catalogo del banco para descartarlas despues.

Sintoma medido: los temas pasaron de ~300 crudas a ~1200, y la corrida hacia unos
280 pedidos HTTP de mas.

Arreglo en `fuentes/__init__.py`: `SOLO_POR_PEDIDO` y `POR_DEFECTO`. Las fuentes
de BUSQUEDA (google_news, rss) reciben las keywords del tema y devuelven algo
acotado; las de CATALOGO devuelven todo y no miran el tema, asi que solo corren si
el tema las nombra. Verificado: los temas volvieron a ~300 crudas con los mismos
resultados.

## Los tres filtros ahora muestran estado (2026-09-12)

Reportado: "el click en los filtros solo permanece el cambio de estado en Solo
nuevas". Correcto, y el diagnostico importa: **abrir y cerrar SI funcionaban y SI
se guardaban** en localStorage; lo que no tenian era estado visible. Eran los
unicos controles sin `aria-pressed`, asi que al tocarlos no cambiaba nada a la
vista aunque el acordeon se hubiera movido.

Ahora los dos reflejan como esta la zona:
- "Abrir todo" se enciende cuando TODOS los temas a la vista estan abiertos.
- "Cerrar todo" cuando todos estan cerrados.
- Con unos abiertos y otros cerrados, ninguno de los dos: el estado es mixto y
  mentir seria peor.
- Se recalcula tambien al abrir o cerrar un acordeon a mano, y al cambiar de
  pestana (cada zona tiene su propio estado).

### Cambio de comportamiento que vino con esto

Los botones ahora actuan sobre la ZONA QUE SE ESTA VIENDO, no sobre los ocho temas
de las tres zonas. Antes "Abrir todo" abria tambien lo que no estabas mirando:
trabajo invisible, y ademas el estado del boton no podia significar nada porque
mezclaba zonas. Se llama `temasALaVista()` y filtra por `hidden` y `offsetParent`.

Verificado en cinco escenarios: al cargar, cerrar todo, abrir todo, cerrar uno a
mano (apaga "Abrir todo"), estado mixto (los dos apagados) y cambio de pestana
(recalcula para la zona nueva).

## Categoria "Cine": ciclos, no cartelera (2026-09-12)

Cuarta zona, acento ROSA (claro #C2185B 5.50, oscuro #E88BA8 7.07, con sus tintes;
calculado igual que los otros tres). Un tema: `cine-caba`, familia "Ciclos y
muestras". Hoy trae 11.

El pedido fue "todos los CICLOS de cine", no todos los estrenos, y el filtro lo
refleja: el segundo grupo de `requerir` exige ciclo / retrospectiva / muestra /
festival / cineclub / programacion / temporada. Sin eso entraba la cartelera
comercial entera.

Lo que trajo el sondeo del 2026-09-12 y hoy se ve en la pagina: la retrospectiva
de Frank Borzage en la Sala Lugones, el aniversario del Malba con cine al aire
libre, OFFNI Cine Fest en la Casa del Bicentenario, el Banff Mountain Film
Festival, el Festival La Mujer y el Cine, el Festival de Cine Tailandes en Atlas
Cines y el Festival de Cine y Musica del Complejo Teatral.

### Dos ajustes que salieron de mirar resultados

1. `max_por_dominio: 4`, mas alto que el 2 de todos los demas temas. El tope
   existe contra content farms, pero en cine los medios que mas publican son
   ESPECIALIZADOS (escribiendocine.com, otroscines.com). Con 2, la retrospectiva
   de la Sala Lugones --el mejor item del sondeo-- quedaba afuera porque ya habia
   dos notas del mismo medio arriba.
2. El ruido dominante NO es tematico sino geografico: el FICPBA de La Plata
   aparecia en casi todas las consultas, mas Cordoba, San Luis, Villa Gesell,
   Lujan y Mar del Plata. Se agregaron a `excluir` junto con "ley audiovisual",
   que es politica y no un ciclo.

### El primer grupo de `requerir` lista SALAS, no solo la zona

Sala Lugones, Malba, Museo del Cine, Gaumont, Casa del Bicentenario, Cine Cosmos,
Lorca, Cineclub. Mismo criterio que en talleres con la Biblioteca Nacional: un
espacio porteño no siempre nombra la ciudad en el titular.

## Limpieza de texto redundante (2026-09-12)

Con cuatro zonas quedo a la vista cuanto texto se repetia a si mismo. En la zona
Cine se leia "ciclos y muestras" TRES veces: el eyebrow, el titulo de familia y el
nombre del tema. Sacado:

| Que | Por que |
|---|---|
| Titulo de familia cuando la zona tiene UNA sola | Repetia el eyebrow de arriba. Con dos o mas familias sigue apareciendo, porque ahi si agrupa |
| "N en seguimiento - N nuevas" al lado de la familia | Los mismos numeros estaban en el panel de KPIs, dos centimetros arriba |
| KPI por familia cuando hay UNA sola | "11 CICLOS Y MUESTRAS" al lado de "11 EN SEGUIMIENTO" |
| Cuenta del tema cuando todas son nuevas | La marca decia "11 NUEVAS" y al lado un "11" suelto |
| Chips de motivos en las tarjetas de agenda | Por construccion los motivos son palabras que YA estan en el titulo: la tarjeta del festival mostraba "Buenos Aires" y "festival" debajo de un titulo que decia las dos cosas |
| Pie: de cinco frases a dos | Que lo genera run.py y lo publica Actions le importaba al que lo escribio, no al que lo lee |

Lo que se dejo en el pie son las dos frases que cambian COMO se lee la pagina: que
el puntaje mide encaje y no calidad, y la diferencia entre "hace N dias" (cuando se
publico) y "vence" (fecha real declarada por la fuente).

Los chips que SI quedan son los informativos: "solo 1 dia por semana" en las promos
bancarias, que no esta en el titulo.

## Modo claro: papel de petroleo y panel oscuro (2026-09-12)

Reportado: el modo claro era "demasiado blanco y molesto". Era cierto y medible:
`--surface` era **blanco puro** (#FFFFFF) y `--ground` casi blanco (#F5F8F9), asi
que la pantalla entera era glare sin un solo color.

### Dos cambios, no uno

1. LA PALETA SE TIÑE de petroleo. Ninguno de los dos fondos es blanco ya, y la
   tinta dejo de ser negra:

   | token | antes | ahora |
   |---|---|---|
   | `--ground` | #F5F8F9 | **#E3EDEF** |
   | `--surface` | #FFFFFF | **#F6FAFB** |
   | `--sunken` | #ECF1F3 | #D5E2E5 |
   | `--border` | #C8D5DC | #AFC5CB |
   | `--ink` | #101820 (casi negro) | **#0C2630** (petroleo profundo) |
   | `--muted` | #56666F | #3F5C66 |
   | `--faint` | #62747D | #526F78 |

2. LA BARRA LATERAL es un BLOQUE DE PETROLEO OSCURO (#123039) con texto claro.
   Esto es lo que le da color de verdad a la pagina: teñir el fondo solo la
   suaviza, pero sigue siendo una pagina de un solo tono.

### Como se hizo sin duplicar reglas

El panel redefine los tokens en su propio scope (`--ink: var(--panel-ink)`, etc.),
asi que TODO lo de adentro se adapta solo: pestañas, contadores, bordes, el sello
de "Actualizado". No hay una regla por elemento.

Los acentos de zona adentro del panel usan los valores de MODO OSCURO (el fondo es
oscuro). En modo oscuro esas reglas repiten lo que ya vale, asi que son un no-op y
no hizo falta condicionarlas por tema.

`--panel-fondo` vale `transparent` en oscuro: el panel se funde con el fondo, como
antes. OJO: los valores oscuros de `--panel-*` se escriben LITERALES y no con
`var(--ink)`, porque `--panel-ink: var(--ink)` junto al `--ink: var(--panel-ink)`
del panel es una referencia circular y CSS descarta la propiedad.

En pantalla angosta (<1020px) el panel vuelve a ser transparente: una banda oscura
a lo ancho arriba de todo seria otra cosa, no esto.

### Auditoria

37 pares por modo, incluidos los nuevos del panel (tinta, muted, borde y los cuatro
acentos sobre el petroleo). **0 fallas reales.** La unica marca es
`surface / ground` en OSCURO: 1.11 contra un umbral de 1.12 que me invente yo para
"la tarjeta se despega del fondo"; no es WCAG y el modo oscuro no se toco.

`--faint` hubo que recalcularlo: con el fondo nuevo se quedaba en 4.26 y volvio a
4.52 con #526F78.

## Logos mas grandes en Ofertas (2026-09-12)

De 48 a **72px** en la tarjeta y de 52 a **84px** en el destacado del carrusel.

El motivo no es solo estetico: muchas de esas imagenes no son un logo suelto sino
el BANNER de la promo (311x208, 317x112, 320x320 segun el comercio). A 48px con
`object-fit: contain` no se distinguia de que marca era; a 72 se lee.

Costo asumido: la grilla de ofertas subio de `minmax(258px)` a `minmax(288px)`
para que el nombre del comercio no quede en una columna de 90px. Con el ancho
actual eso pasa de 4 columnas a 3. Si se prefiere densidad sobre tamaño, el numero
a tocar es ese, no el del logo.

## LED de "recien agregada" (2026-09-12)

Pedido: que lo agregado hace poco se distinga con un punto o luz tipo LED, que dure
dos dias y despues se apague.

Dos cambios:

1. LA VENTANA PASO DE 24 A 48 HORAS (`HORAS_NUEVA` en dashboard.py). Se mide sobre
   `primera_vez` --cuando la oferta ENTRO a la base--, que no es lo mismo que
   cuando se publico la nota. El KPI se renombro de "nuevas hoy" a "nuevas (48 h)"
   porque el numero ya no es de hoy.
2. EL LED reemplaza a la etiqueta de texto "nueva" en la tarjeta de agenda, que es
   la que usan Este finde, Cine y Agenda. Avisa lo mismo sin gastar una linea.

Detalles:
- El LED toma `var(--accent)` via `currentColor`, asi que sale violeta en Este
  finde, rosa en Cine y teal en Agenda sin una regla por zona.
- Pulso suave de 2.6s. No hizo falta apagarlo a mano con prefers-reduced-motion:
  la regla global `* { animation: none !important }` ya lo cubre y el punto queda
  fijo, que sigue avisando.
- Lleva un `.solo-lectores` al lado ("Agregada hace menos de 48 horas"). Un LED es
  color puro: sin ese texto, quien no lo ve no se entera.
- En el carrusel va en la esquina superior derecha de la diapositiva.

OFERTAS quedo afuera a proposito: se pidieron las otras tres zonas, y ahi la
tarjeta de promo ya trae su marca "NUEVA". Si se quiere unificar, es usar el mismo
`.led` en la plantilla de oferta.

## Pendiente para la proxima sesion

1. Telegram: salteado a pedido. `salidas/telegram.py` esta escrito y probado en seco.
   Para activarlo: completar TELEGRAM_TOKEN y TELEGRAM_CHAT_ID en `config/.env` y
   agregar una linea `run.py notificar` al `actualizar.bat`.
2. Sumar fuentes con `/sugerir-fuentes <tema>`. Los feeds descartados por no tener RSS
   quedaron listados en `config/feeds.yaml`.
3. Agregar temas nuevos editando `config/temas.yaml`. No requiere tocar codigo.
3b. SUBTEMAS DE OFERTAS: ya hay dos (`bbva` y `promos-bancarias`) en la familia
   "Bancos y tarjetas". Para otro rubro conviene una familia nueva.
3c. Mercado Pago: falta encontrar su endpoint real de promociones (ver arriba).
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
    actualizar.bat                                    todo junto + deploy (con ventana)
    wscript actualizar-silencioso.vbs                 lo mismo, sin ventana

Slash commands: `/buscar-oferta <que comprar>` y `/sugerir-fuentes <tema>`.
