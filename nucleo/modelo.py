"""Modelo de datos comun a todas las fuentes."""
from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import datetime

# Google News agrega " - Medio" al final de cada titulo.
_SUFIJO_MEDIO = re.compile(r"\s+-\s+[^-]{2,40}$")


def normalizar(texto: str) -> str:
    """Minusculas, sin tildes ni puntuacion: base para comparar y deduplicar."""
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"[^a-z0-9 ]+", " ", texto.lower())
    return re.sub(r"\s+", " ", texto).strip()


def titulo_limpio(titulo: str) -> str:
    """Quita el sufijo del medio que agrega Google News."""
    return _SUFIJO_MEDIO.sub("", titulo or "").strip()


@dataclass
class Oferta:
    titulo: str
    url: str
    fuente: str  # dominio del medio, ej. "clarin.com"
    tema: str
    origen: str = "google_news"  # plugin que la trajo
    snippet: str = ""
    fecha_pub: datetime | None = None
    url_final: str | None = None
    precio: float | None = None
    score: float = 0.0
    motivos: list[str] = field(default_factory=list)

    @property
    def id(self) -> str:
        """Hash estable.

        Se basa en titulo + medio y NO en la URL: los enlaces de Google News son
        opacos (news.google.com/rss/articles/CBMi...) y un mismo articulo puede
        llegar con URLs distintas desde queries distintas.
        """
        base = f"{normalizar(titulo_limpio(self.titulo))}|{self.fuente}"
        return hashlib.sha1(base.encode("utf-8")).hexdigest()

    @property
    def antiguedad_dias(self) -> float | None:
        if self.fecha_pub is None:
            return None
        return (datetime.now(self.fecha_pub.tzinfo) - self.fecha_pub).total_seconds() / 86400
