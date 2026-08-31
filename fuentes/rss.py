"""Fuente: cualquier feed RSS/Atom declarado en config/feeds.yaml.

Contrato igual al de las demas fuentes: buscar(tema, cliente) -> list[Oferta]
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import feedparser
import httpx
import yaml

from nucleo.modelo import Oferta
from nucleo.urls import canonicalizar, dominio

NOMBRE = "rss"
RUTA_FEEDS = Path(__file__).resolve().parent.parent / "config" / "feeds.yaml"

# Un mismo feed suele servir a varios temas; se baja una sola vez por proceso.
_CACHE: dict[str, list] = {}


def _feeds_del_tema(nombre_tema: str) -> list[dict]:
    if not RUTA_FEEDS.exists():
        return []
    datos = yaml.safe_load(RUTA_FEEDS.read_text(encoding="utf-8")) or {}
    return [f for f in datos.get("feeds", []) if nombre_tema in f.get("temas", [])]


def _entradas(url: str, cliente: httpx.Client) -> list:
    if url in _CACHE:
        return _CACHE[url]
    try:
        r = cliente.get(url, timeout=20.0)
        r.raise_for_status()
        entradas = feedparser.parse(r.text).entries
    except (httpx.HTTPError, Exception) as e:
        print(f"    ! feed caido {url}: {type(e).__name__}")
        entradas = []
    _CACHE[url] = entradas
    return entradas


def _fecha(entrada) -> datetime | None:
    t = entrada.get("published_parsed") or entrada.get("updated_parsed")
    return datetime(*t[:6], tzinfo=timezone.utc) if t else None


def buscar(tema: dict, cliente: httpx.Client) -> list[Oferta]:
    ofertas: list[Oferta] = []
    for feed in _feeds_del_tema(tema["nombre"]):
        for entrada in _entradas(feed["url"], cliente):
            titulo = (entrada.get("title") or "").strip()
            enlace = (entrada.get("link") or "").strip()
            if not titulo or not enlace:
                continue
            ofertas.append(
                Oferta(
                    titulo=titulo,
                    url=canonicalizar(enlace),
                    fuente=dominio(enlace) or feed["nombre"],
                    tema=tema["nombre"],
                    origen=f"{NOMBRE}:{feed['nombre']}",
                    snippet=(entrada.get("summary") or "")[:500],
                    fecha_pub=_fecha(entrada),
                )
            )
    return ofertas
