"""Fuente: Google News RSS. Sin API key y sin limite practico.

Contrato de toda fuente: buscar(tema, cliente) -> list[Oferta]
"""
from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import quote_plus

import feedparser
import httpx

from nucleo.modelo import Oferta
from nucleo.urls import dominio

NOMBRE = "google_news"
BASE = "https://news.google.com/rss/search"


def _url_consulta(consulta: str, tema: dict) -> str:
    gl = tema.get("gl", "AR")
    hl = tema.get("hl", "es-419")
    return f"{BASE}?q={quote_plus(consulta)}&hl={hl}&gl={gl}&ceid={gl}:{hl}"


def _fecha(entrada) -> datetime | None:
    t = entrada.get("published_parsed")
    if not t:
        return None
    return datetime(*t[:6], tzinfo=timezone.utc)


def _medio(entrada, titulo: str) -> str:
    """El medio viene en <source url="...">; si falta, se deduce del titulo."""
    fuente = entrada.get("source")
    if fuente:
        href = fuente.get("href") if isinstance(fuente, dict) else None
        if href:
            return dominio(href)
        titulo_fuente = fuente.get("title") if isinstance(fuente, dict) else str(fuente)
        if titulo_fuente:
            return titulo_fuente.strip().lower()
    if " - " in titulo:
        return titulo.rsplit(" - ", 1)[-1].strip().lower()
    return "desconocido"


def buscar(tema: dict, cliente: httpx.Client) -> list[Oferta]:
    ofertas: list[Oferta] = []
    for consulta in tema.get("keywords", []):
        try:
            r = cliente.get(_url_consulta(consulta, tema), timeout=20.0)
            r.raise_for_status()
        except httpx.HTTPError as e:
            print(f"    ! fallo la consulta '{consulta}': {e}")
            continue

        for entrada in feedparser.parse(r.text).entries:
            titulo = entrada.get("title", "").strip()
            enlace = entrada.get("link", "").strip()
            if not titulo or not enlace:
                continue
            ofertas.append(
                Oferta(
                    titulo=titulo,
                    url=enlace,
                    fuente=_medio(entrada, titulo),
                    tema=tema["nombre"],
                    origen=NOMBRE,
                    snippet=entrada.get("summary", "")[:500],
                    fecha_pub=_fecha(entrada),
                )
            )
    return ofertas
