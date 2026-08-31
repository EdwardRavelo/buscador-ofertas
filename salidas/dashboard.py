"""Genera el dashboard HTML a partir de la base.

Escribe dos copias del mismo render:
  dashboard.html      para abrir local con doble clic
  publicar/index.html para el deploy a GitHub Pages (repo aparte, sin credenciales)
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from nucleo.almacen import conectar
from nucleo.urls import enlace_respaldo

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
# index.html en la raiz: es lo que sirve GitHub Pages.
# dashboard.html es la misma pagina, para abrir local con doble clic.
SALIDA_LOCAL = RAIZ / "dashboard.html"
SALIDA_WEB = RAIZ / "index.html"

ETIQUETAS = {
    "talleres-lectura-caba": "Talleres y lectura en CABA",
    "cursos-ia": "Cursos de inteligencia artificial",
    "ingles": "Inglés",
}
CORTAS = {
    "talleres-lectura-caba": "Talleres",
    "cursos-ia": "IA",
    "ingles": "Inglés",
}


def _dias(fecha_pub: str | None) -> int | None:
    if not fecha_pub:
        return None
    return (datetime.now(timezone.utc) - datetime.fromisoformat(fecha_pub)).days


def _edad(dias: int | None) -> str:
    if dias is None:
        return "sin fecha"
    if dias <= 0:
        return "hoy"
    if dias == 1:
        return "ayer"
    if dias < 30:
        return f"hace {dias} días"
    meses = dias // 30
    return f"hace {meses} mes" + ("es" if meses > 1 else "")


def _urgencia(dias: int | None) -> str:
    """Solo mide RECENCIA de publicacion, no fecha de cierre.

    No tenemos fecha de vencimiento de las inscripciones, asi que la etiqueta
    dice "recien publicado" y nunca "cierra pronto": prometer un plazo que no
    conocemos seria peor que no decir nada.
    """
    if dias is None:
        return "sin-fecha"
    if dias <= 2:
        return "caliente"
    if dias <= 7:
        return "semana"
    return "normal"


def _nivel(score: float) -> str:
    if score >= 9.0:
        return "alto"
    return "medio" if score >= 8.0 else "bajo"


def recolectar(con: sqlite3.Connection) -> dict:
    corte = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    filas = con.execute("SELECT * FROM ofertas ORDER BY tema, score DESC").fetchall()

    temas: dict[str, list] = {}
    todas: list[dict] = []
    for f in filas:
        dias = _dias(f["fecha_pub"])
        url = f["url_final"] or f["url"]
        oferta = {
            "titulo": f["titulo"],
            "url": url,
            "respaldo": enlace_respaldo(f["titulo"], f["fuente"]),
            "opaco": url.startswith("https://news.google.com"),
            "fuente": f["fuente"],
            "tema": f["tema"],
            "tema_corto": CORTAS.get(f["tema"], f["tema"]),
            "score": f["score"],
            "nivel": _nivel(f["score"]),
            "dias": dias,
            "edad": _edad(dias),
            "urgencia": _urgencia(dias),
            # "reciente (<7d)" se omite: la antiguedad ya se muestra en palabras
            # al lado, y el parentesis es jerga interna del puntuador.
            "motivos": [
                m.strip() for m in (f["motivos"] or "").split("|")
                if m.strip() and not m.strip().startswith("reciente")
            ],
            "nuevo": f["primera_vez"] >= corte,
        }
        temas.setdefault(f["tema"], []).append(oferta)
        todas.append(oferta)

    # El destacado es la tesis de la pagina: lo mejor que ademas es reciente.
    candidatas = [o for o in todas if o["dias"] is not None and o["dias"] <= 7]
    destacada = max(candidatas, key=lambda o: o["score"]) if candidatas else None

    ultima = con.execute("SELECT MAX(ultima_vez) AS u FROM ofertas").fetchone()["u"]
    return {
        "temas": [
            {
                "clave": clave,
                "nombre": ETIQUETAS.get(clave, clave),
                "corto": CORTAS.get(clave, clave),
                "ofertas": [o for o in ofertas if o is not destacada],
                "total": len(ofertas),
                "nuevos": sum(1 for o in ofertas if o["nuevo"]),
            }
            for clave, ofertas in temas.items()
        ],
        "destacada": destacada,
        "total": len(filas),
        "nuevos": sum(1 for o in todas if o["nuevo"]),
        "calientes": sum(1 for o in todas if o["urgencia"] == "caliente"),
        "actualizado": datetime.fromisoformat(ultima).astimezone().strftime("%d/%m/%Y %H:%M")
        if ultima else "nunca",
    }


def generar() -> Path:
    con = conectar()
    datos = recolectar(con)
    con.close()

    entorno = Environment(
        loader=FileSystemLoader(AQUI),
        autoescape=select_autoescape(["html"]),
    )
    html = entorno.get_template("plantilla.html.j2").render(**datos)

    SALIDA_LOCAL.write_text(html, encoding="utf-8")
    SALIDA_WEB.parent.mkdir(parents=True, exist_ok=True)
    SALIDA_WEB.write_text(html, encoding="utf-8")
    return SALIDA_LOCAL


if __name__ == "__main__":
    print(generar())
