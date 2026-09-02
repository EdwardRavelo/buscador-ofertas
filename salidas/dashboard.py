"""Genera el dashboard HTML a partir de la base.

Escribe dos copias del mismo render:
  index.html      lo que sirve GitHub Pages
  dashboard.html  la misma pagina, para abrir local con doble clic

Las etiquetas visibles y el agrupamiento salen de config/temas.yaml, no de aca:
agregar un tema tiene que seguir siendo editar un YAML y nada mas.
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from nucleo.almacen import conectar
from nucleo.urls import enlace_respaldo

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
SALIDA_WEB = RAIZ / "index.html"
SALIDA_LOCAL = RAIZ / "dashboard.html"
RUTA_TEMAS = RAIZ / "config" / "temas.yaml"


def _config_temas() -> list[dict]:
    datos = yaml.safe_load(RUTA_TEMAS.read_text(encoding="utf-8")) or {}
    return datos.get("temas", [])


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
    """Mide RECENCIA de publicacion, no fecha de cierre.

    No tenemos fecha de vencimiento, asi que nunca decimos "cierra pronto":
    prometer un plazo que no conocemos seria peor que no decir nada.
    """
    if dias is None:
        return "sin-fecha"
    if dias <= 2:
        return "caliente"
    return "semana" if dias <= 7 else "normal"


def _nivel(score: float) -> str:
    if score >= 9.0:
        return "alto"
    return "medio" if score >= 8.0 else "bajo"


def recolectar(con: sqlite3.Connection) -> dict:
    corte = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    config = _config_temas()
    # Se listan de mas reciente a mas viejo. El puntaje se sigue mostrando, pero
    # ya no decide el orden: para una agenda, lo que llego ultimo importa mas que
    # lo que puntuo mejor hace tres semanas.
    filas = con.execute(
        "SELECT * FROM ofertas ORDER BY tema, fecha_pub IS NULL, fecha_pub DESC"
    ).fetchall()

    por_tema: dict[str, list] = {}
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
            "score": f["score"],
            "nivel": _nivel(f["score"]),
            "dias": dias,
            "edad": _edad(dias),
            "urgencia": _urgencia(dias),
            # "reciente (<7d)" se omite: la antiguedad ya va al lado en palabras.
            "motivos": [
                m.strip() for m in (f["motivos"] or "").split("|")
                if m.strip() and not m.strip().startswith("reciente")
            ],
            "nuevo": f["primera_vez"] >= corte,
        }
        por_tema.setdefault(f["tema"], []).append(oferta)
        todas.append(oferta)

    # El carrusel es la tesis de la pagina: lo mejor de la semana, hasta 5.
    # Aca SI manda el puntaje: es un destaque, no una agenda.
    candidatas = [o for o in todas if o["dias"] is not None and o["dias"] <= 7]
    candidatas.sort(key=lambda o: (-o["score"], o["dias"]))
    destacadas = candidatas[:5]
    ids_destacados = {id(o) for o in destacadas}
    for o in todas:
        o["es_destacada"] = id(o) in ids_destacados

    # Agrupar por familia respetando el orden del YAML.
    familias: list[dict] = []
    for cfg in config:
        clave = cfg["nombre"]
        ofertas = [o for o in por_tema.get(clave, []) if not o["es_destacada"]]
        # Mas reciente primero; las que no traen fecha van al final.
        ofertas.sort(key=lambda o: (o["dias"] is None, o["dias"] if o["dias"] is not None else 0))
        nuevos = sum(1 for o in por_tema.get(clave, []) if o["nuevo"])
        tema = {
            "clave": clave,
            "nombre": cfg.get("etiqueta", clave),
            "corto": cfg.get("corto", clave),
            "ofertas": ofertas,
            "total": len(por_tema.get(clave, [])),
            "nuevos": nuevos,
            "mejor": max((o["score"] for o in por_tema.get(clave, [])), default=0),
            # Se abre solo si hay algo nuevo. Con cinco temas, abrir todo es la
            # ensalada que estamos tratando de evitar.
            "abierto": nuevos > 0,
        }
        nombre_familia = cfg.get("familia", "Otros")
        existente = next((f for f in familias if f["nombre"] == nombre_familia), None)
        if existente is None:
            familias.append({"nombre": nombre_familia, "temas": [tema]})
        else:
            existente["temas"].append(tema)

    for fam in familias:
        fam["total"] = sum(t["total"] for t in fam["temas"])
        fam["nuevos"] = sum(t["nuevos"] for t in fam["temas"])

    ultima = con.execute("SELECT MAX(ultima_vez) AS u FROM ofertas").fetchone()["u"]
    return {
        "familias": familias,
        "destacadas": destacadas,
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

    SALIDA_WEB.write_text(html, encoding="utf-8")
    SALIDA_LOCAL.write_text(html, encoding="utf-8")
    return SALIDA_WEB


if __name__ == "__main__":
    print(generar())
