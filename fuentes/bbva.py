"""Fuente: promociones de BBVA Argentina, desde la API publica de BBVA Go.

Contrato igual al de las demas fuentes: buscar(tema, cliente) -> list[Oferta]

Por que existe: la prensa NO cubre las promos semanales de BBVA. Medido el
2026-09-10 sobre 424 notas de Google News, el item mas fresco que nombraba al
banco tenia 43 dias. Lo que si existe es la API que alimenta la pagina de
beneficios (go.bbva.com.ar), que responde JSON sin login y desde el servidor.

Lo que aporta y ninguna otra fuente da:
  - `fechaHasta`: la promo dice cuando deja de valer. Todo el resto del proyecto
    estima vigencia con relojes rodantes sobre la fecha de publicacion; aca no
    hace falta estimar nada.
  - `montoTope` y `grupoTarjeta`: el tope de reintegro y con que plastico aplica.

El parametro de paginacion es `pager` (0-based, 20 items por pagina). No se puede
adivinar: se capturo espiando `window.fetch` en la pagina del banco mientras se
hacia clic en "Consultar todas las promociones". Con una sola pagina se ven 20
promos; con todas, 926. La diferencia no es cosmetica: las 22 promos de comercios
deportivos (Dexter, Open Sports, Stock Center...) estan TODAS fuera de la primera
pagina.

Un tema puede pedir solo las destacadas con `bbva_paginas: 1` en config/temas.yaml.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from html import unescape

import httpx

from nucleo.modelo import Oferta

NOMBRE = "bbva"
API = "https://go.bbva.com.ar/willgo/fgo/API/v3/communications"
PAGINA = "https://www.bbva.com.ar/beneficios/"

# La API rechaza clientes sin Referer del sitio del banco.
CABECERAS = {
    "Accept": "application/json",
    "Referer": "https://www.bbva.com.ar/",
}


def _fecha(texto: str | None) -> datetime | None:
    """Las fechas vienen como '2026-09-30' o ISO con zona horaria."""
    if not texto:
        return None
    try:
        d = datetime.fromisoformat(texto.strip())
    except ValueError:
        return None
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


# "Dexter 20% y 6 cuotas" -> comercio "Dexter", beneficio "20% y 6 cuotas".
# El corte es el primer numero seguido de % o de "cuotas": todo lo de antes es el
# nombre del comercio. "Supermercados Vea QR Modo" no tiene numeros y queda entero.
_INICIO_BENEFICIO = re.compile(r"\d+\s*(?:%|x\d|cuotas?)", re.I)
# Tres digitos: con dos, "Cabify 100% OFF" daba "00%".
_PORCENTAJE = re.compile(r"(\d{1,3})\s*%")
_CUOTAS = re.compile(r"(\d{1,2})\s*cuotas?", re.I)


def _estructura(item: dict, titulo: str) -> dict:
    """Separa lo que la plantilla necesita mostrar por separado.

    Existe porque la tarjeta tenia todo esto aplastado en una linea de texto que
    no se renderizaba nunca: el tope de reintegro y la tarjeta que aplica son
    justamente lo que decide si la promo sirve.
    """
    m = _INICIO_BENEFICIO.search(titulo)
    comercio = (titulo[:m.start()] if m else titulo).strip(" -–·,")
    beneficio = titulo[m.start():].strip() if m else ""

    datos: dict = {}
    if comercio:
        datos["comercio"] = comercio
    if beneficio:
        datos["beneficio"] = beneficio

    sub = unescape((item.get("subcabecera") or ""))
    texto = f"{titulo} {sub}"
    pct = _PORCENTAJE.search(texto)
    if pct:
        datos["descuento"] = f"{pct.group(1)}%"
    cuo = _CUOTAS.search(texto)
    if cuo:
        datos["cuotas"] = int(cuo.group(1))
        datos["sin_interes"] = "sin inter" in texto.lower()

    tope = (item.get("montoTope") or "").strip()
    if tope.isdigit() and int(tope) > 0:
        datos["tope"] = f"${int(tope):,}".replace(",", ".")

    grupo = (item.get("grupoTarjeta") or "").strip()
    if grupo:
        datos["tarjeta"] = grupo

    imagen = (item.get("imagen") or "").strip()
    # Solo se acepta la imagen del banco: la plantilla la sirve desde un host que
    # no controlamos, asi que al menos que sea el esperado.
    if imagen.startswith("https://go.bbva.com.ar/"):
        datos["imagen"] = imagen

    dias = (item.get("diasPromo") or "").strip()
    if dias and set(dias.split(",")) != {"1"}:
        cuantos = sum(1 for d in dias.split(",") if d == "1")
        if cuantos:
            datos["dias_limitados"] = cuantos
    return datos


def _detalle(item: dict) -> str:
    """Arma el snippet con lo que la prensa nunca trae: tope, tarjeta, vigencia."""
    partes = []
    sub = unescape((item.get("subcabecera") or "").strip())
    # El subcabecera suele venir como ". .Promocion valida desde X hasta Y".
    sub = sub.lstrip(". ").strip()
    if sub:
        partes.append(sub)
    tope = (item.get("montoTope") or "").strip()
    if tope and tope.isdigit():
        partes.append(f"Tope de reintegro ${int(tope):,}".replace(",", "."))
    grupo = (item.get("grupoTarjeta") or "").strip()
    if grupo:
        partes.append(grupo)
    # `diasPromo` es un patron de siete flags ("0,0,0,1,0,0,0"). No esta
    # documentado que dia es el primero, asi que NO se traduce a nombres: decir
    # "solo los jueves" cuando puede ser miercoles es peor que no decir nada.
    dias = (item.get("diasPromo") or "").strip()
    if dias and set(dias.split(",")) != {"1"}:
        cuantos = sum(1 for d in dias.split(",") if d == "1")
        if cuantos:
            partes.append(f"Solo {cuantos} dia(s) de la semana: ver el detalle")
    return " | ".join(partes)[:500]


# Tope duro de paginas. Hoy son 47; el tope evita que un cambio en la API deje el
# bucle girando para siempre.
MAX_PAGINAS = 80
POR_PAGINA = 20


def _paginas(tema: dict, cliente: httpx.Client) -> list[dict]:
    """Recorre el catalogo entero. `bbva_paginas` lo acota a las destacadas."""
    tope = tema.get("bbva_paginas") or MAX_PAGINAS
    items: list[dict] = []
    vistos: set[str] = set()

    for pagina in range(min(tope, MAX_PAGINAS)):
        try:
            r = cliente.get(API, params={"pager": pagina}, headers=CABECERAS, timeout=25.0)
            r.raise_for_status()
            lote = r.json().get("data") or []
        except (httpx.HTTPError, ValueError) as e:
            print(f"    ! BBVA, pagina {pagina}: {type(e).__name__}")
            break
        if not lote:
            break
        for item in lote:
            # La API repite items entre paginas cuando cambia el orden entre
            # pedidos; el id desempata.
            clave = str(item.get("id"))
            if clave in vistos:
                continue
            vistos.add(clave)
            items.append(item)
        if len(lote) < POR_PAGINA:
            break  # ultima pagina

    return items


def buscar(tema: dict, cliente: httpx.Client) -> list[Oferta]:
    items = _paginas(tema, cliente)
    if not items:
        return []

    ahora = datetime.now(timezone.utc)
    ofertas: list[Oferta] = []

    for item in items:
        titulo = unescape((item.get("cabecera") or "").strip())
        if not titulo:
            continue
        vence = _fecha(item.get("fechaHasta"))
        # Se descarta en la fuente lo que ya vencio: el banco deja comunicaciones
        # viejas en la respuesta y no tiene sentido guardarlas para filtrarlas
        # despues.
        if vence is not None and vence < ahora:
            continue
        ofertas.append(
            Oferta(
                titulo=titulo,
                url=PAGINA,
                fuente="bbva.com.ar",
                tema=tema["nombre"],
                origen=NOMBRE,
                snippet=_detalle(item),
                fecha_pub=_fecha(item.get("fechaDesde")),
                vence=vence,
                extra=_estructura(item, titulo),
            )
        )
    return ofertas
