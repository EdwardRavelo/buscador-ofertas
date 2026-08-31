"""Limpieza de URLs y resolucion de los enlaces opacos de Google News."""
from __future__ import annotations

import base64
import re
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import httpx

_RASTREO = re.compile(r"^(utm_|fbclid|gclid|mc_|ref$|ref_|igshid|_ga)")
_URL_EMBEBIDA = re.compile(rb"https?://[a-zA-Z0-9._~:/?#@!$&'()*+,;=%-]{12,}")


def dominio(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def canonicalizar(url: str) -> str:
    """Quita parametros de rastreo y fragmentos."""
    p = urlparse(url)
    query = urlencode([(k, v) for k, v in parse_qsl(p.query) if not _RASTREO.match(k)])
    return urlunparse((p.scheme, p.netloc, p.path.rstrip("/") or "/", "", query, ""))


def es_google_news(url: str) -> bool:
    return dominio(url) == "news.google.com"


def resolver_google_news(url: str, cliente: httpx.Client) -> str | None:
    """Intenta recuperar la URL real del medio. Devuelve None si no se puede.

    Google cambio el formato varias veces y hoy muchos enlaces vienen cifrados,
    asi que esto es best-effort a proposito: el dedup NO depende de esta funcion
    (ver Oferta.id, que usa titulo + medio).
    """
    # 1) Formato viejo: el payload base64 contiene la URL en claro.
    m = re.search(r"/(?:articles|read)/([A-Za-z0-9_\-]{20,})", url)
    if m:
        crudo = m.group(1)
        relleno = crudo + "=" * (-len(crudo) % 4)
        try:
            datos = base64.urlsafe_b64decode(relleno)
        except Exception:
            datos = b""
        encontrada = _URL_EMBEBIDA.search(datos)
        if encontrada:
            try:
                return canonicalizar(encontrada.group(0).decode("utf-8"))
            except UnicodeDecodeError:
                pass

    # 2) Seguir la redireccion.
    try:
        r = cliente.get(url, follow_redirects=True, timeout=10.0)
        if not es_google_news(str(r.url)):
            return canonicalizar(str(r.url))
    except httpx.HTTPError:
        pass

    return None


def enlace_respaldo(titulo: str, medio: str = "") -> str:
    """Busqueda en Google por el titulo exacto.

    Red de seguridad: los enlaces de Google News no se pueden resolver del lado
    del servidor (Google cifra el payload), asi que si el enlace directo falla,
    este siempre lleva a la nota.
    """
    from urllib.parse import quote_plus

    consulta = f'"{titulo.strip()}"'
    if medio:
        consulta += f" site:{medio}"
    return f"https://www.google.com/search?q={quote_plus(consulta)}"
