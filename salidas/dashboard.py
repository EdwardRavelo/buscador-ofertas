"""Genera el dashboard HTML a partir de la base.

Escribe dos copias del mismo render:
  index.html      lo que sirve GitHub Pages
  dashboard.html  la misma pagina, para abrir local con doble clic

Las etiquetas visibles y el agrupamiento salen de config/temas.yaml, no de aca:
agregar un tema tiene que seguir siendo editar un YAML y nada mas.

La pagina tiene tres niveles: ZONA (pestana) > familia > tema. Las zonas se
declaran en el bloque `zonas:` del mismo YAML.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

from nucleo.almacen import conectar
from nucleo.modelo import normalizar
from nucleo.urls import enlace_respaldo

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
SALIDA_WEB = RAIZ / "index.html"
SALIDA_LOCAL = RAIZ / "dashboard.html"
RUTA_TEMAS = RAIZ / "config" / "temas.yaml"

# Cuanto dura el LED de "recien agregada" en una tarjeta.
HORAS_NUEVA = 48


def _config_temas() -> list[dict]:
    datos = yaml.safe_load(RUTA_TEMAS.read_text(encoding="utf-8")) or {}
    return datos.get("temas", [])


def _config_zonas() -> list[dict]:
    datos = yaml.safe_load(RUTA_TEMAS.read_text(encoding="utf-8")) or {}
    return datos.get("zonas", [])


def _extra(crudo: str | None) -> dict:
    """El JSON de la columna `extra`. Si viene roto, la tarjeta cae al formato
    de siempre en vez de tumbar la generacion entera."""
    if not crudo:
        return {}
    try:
        datos = json.loads(crudo)
    except (ValueError, TypeError):
        return {}
    return datos if isinstance(datos, dict) else {}


def _fecha_corta(iso: str | None) -> str:
    """'2026-10-27' -> '27/10'. La fecha exacta es mas util que 'en 1 mes'."""
    if not iso:
        return ""
    try:
        return datetime.fromisoformat(iso).strftime("%d/%m")
    except ValueError:
        return ""


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


def _urgencia(dias: int | None, vence_en: int | None = None) -> str:
    """Cuanto apura. Con vigencia declarada mide lo que falta para que venza;
    sin ella, solo puede medir RECENCIA de publicacion.

    Para las fuentes que no declaran vencimiento seguimos sin decir "cierra
    pronto": prometer un plazo que no conocemos seria peor que no decir nada.
    """
    if vence_en is not None:
        if vence_en <= 3:
            return "caliente"
        return "semana" if vence_en <= 10 else "normal"
    if dias is None:
        return "sin-fecha"
    if dias <= 2:
        return "caliente"
    return "semana" if dias <= 7 else "normal"


def _vigencia(vence_en: int | None) -> str:
    if vence_en is None:
        return ""
    if vence_en < 0:
        return "vencida"
    if vence_en == 0:
        return "último día"
    if vence_en == 1:
        return "vence mañana"
    if vence_en < 30:
        return f"vence en {vence_en} días"
    meses = vence_en // 30
    return "vence en %d mes%s" % (meses, "es" if meses > 1 else "")


def _nivel(score: float) -> str:
    if score >= 9.0:
        return "alto"
    return "medio" if score >= 8.0 else "bajo"


def recolectar(con: sqlite3.Connection) -> dict:
    # 48 horas desde que la oferta ENTRO a la base (`primera_vez`), que es
    # distinto de cuando se publico la nota. Es la ventana en la que la tarjeta
    # lleva el LED de "recien agregada"; pasada esa, se ve como las demas.
    corte = (datetime.now(timezone.utc) - timedelta(hours=HORAS_NUEVA)).isoformat()
    config = _config_temas()
    # Se listan de mas reciente a mas viejo. El puntaje se sigue mostrando, pero
    # ya no decide el orden: para una agenda, lo que llego ultimo importa mas que
    # lo que puntuo mejor hace tres semanas.
    filas = con.execute(
        "SELECT * FROM ofertas ORDER BY tema, fecha_pub IS NULL, fecha_pub DESC"
    ).fetchall()

    # Cuantos dias se sigue mostrando cada tema. Distinto de max_antiguedad_dias,
    # que decide que entra. Un festival de hace 21 dias ya paso; un curso online
    # gratis de hace 4 meses probablemente sigue abierto.
    vida_util = {c["nombre"]: c.get("vida_util_dias") for c in config}

    # Temas que hoy existen en el YAML. Al eliminar un tema, sus filas se quedan
    # en la base (y en Google Sheets) pero no tienen donde renderizarse: si se
    # contaran, la zona mostraria un total mas alto que la suma de sus familias.
    temas_validos = {c["nombre"] for c in config}

    por_tema: dict[str, list] = {}
    todas: list[dict] = []
    vencidas = 0
    huerfanas = 0
    for f in filas:
        if f["tema"] not in temas_validos:
            huerfanas += 1
            continue
        dias = _dias(f["fecha_pub"])
        # Dias que FALTAN para vencer. Solo lo saben las fuentes que lo declaran.
        vence_en = None
        if f["vence"]:
            vence_en = -_dias(f["vence"])

        if vence_en is not None:
            # Vigencia declarada: manda ella y vida_util_dias no corre. Una promo
            # que arranco hace nueve meses pero vence manana tiene que verse.
            if vence_en < 0:
                vencidas += 1
                continue
        else:
            limite = vida_util.get(f["tema"])
            if limite is not None and dias is not None and dias > limite:
                # Se queda en la base y en Google Sheets; solo sale de la pagina.
                vencidas += 1
                continue
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
            # Con vigencia declarada se muestra lo que falta, no lo que paso: a
            # nadie le importa cuando se publico una promo, sino hasta cuando vale.
            "edad": _vigencia(vence_en) if vence_en is not None else _edad(dias),
            "vence_en": vence_en,
            "urgencia": _urgencia(dias, vence_en),
            # Se omiten los motivos que repiten la etiqueta de tiempo que ya va
            # al lado: "reciente (<7d)" junto a "hace 3 días", o "vence en 13d"
            # junto a "vence en 13 días".
            "motivos": [
                m.strip() for m in (f["motivos"] or "").split("|")
                if m.strip() and not m.strip().startswith(("reciente", "vence"))
            ],
            "nuevo": f["primera_vez"] >= corte,
            "tema_clave": f["tema"],
            # Datos estructurados de la fuente. La plantilla de oferta los usa
            # como jerarquia principal; la de agenda los ignora.
            "extra": _extra(f["extra"]),
            "hasta": _fecha_corta(f["vence"]),
            # Solo se usa en el dorso de la tarjeta: en el frente, cuando empezo
            # la promo no le importa a nadie; al leer la letra chica, si.
            "desde": _fecha_corta(f["fecha_pub"]),
        }
        por_tema.setdefault(f["tema"], []).append(oferta)
        todas.append(oferta)

    # El carrusel es la tesis de la pagina: lo mejor de la semana, hasta 5.
    # Aca SI manda el puntaje: es un destaque, no una agenda.
    # Se calcula POR ZONA: si fuera global, la agenda (cinco temas) se quedaria
    # siempre con los cinco lugares y la zona de ofertas nunca tendria destacada.
    zona_de_tema = {c["nombre"]: c.get("zona") for c in config}
    for o in todas:
        o["zona"] = zona_de_tema.get(o["tema_clave"])

    def ofertas_de_zona(nombre):
        return [o for o in todas if o["zona"] == nombre]

    destacadas_por_zona: dict[str | None, list] = {}
    for o in todas:
        o["es_destacada"] = False
    for nombre_zona in {o["zona"] for o in todas}:
        # Entra lo recien publicado y tambien lo que esta por vencer: en una zona
        # de ofertas, "se termina el viernes" es mas urgente que "salio ayer".
        candidatas = [
            o for o in todas
            if o["zona"] == nombre_zona and (
                (o["vence_en"] is not None and o["vence_en"] <= 21)
                or (o["vence_en"] is None and o["dias"] is not None and o["dias"] <= 7)
            )
        ]
        candidatas.sort(key=lambda o: (-o["score"], o["vence_en"] if o["vence_en"] is not None else o["dias"]))

        # Una misma oferta puede estar en dos temas a proposito (el hash incluye
        # el tema: "Nike 6 cuotas" es del catalogo BBVA Y sirve para la pelota).
        # Dentro de la zona eso es un duplicado visible, asi que el carrusel se
        # queda con una sola copia. La otra deja de ser destacada y por lo tanto
        # aparece en la lista de su tema, que si no quedaria vacio.
        # Nunca mas de la mitad de la zona: con 3 avisos, 5 destacadas se llevaban
        # todo y el acordeon de abajo quedaba vacio diciendo "esta arriba".
        # Siempre queda al menos una destacada si hay candidatas.
        tope_destacadas = max(1, min(5, len(ofertas_de_zona(nombre_zona)) // 2))

        elegidas: list[dict] = []
        vistas: set[tuple[str, str]] = set()
        for o in candidatas:
            clave_visual = (o["titulo"], o["fuente"])
            if clave_visual in vistas:
                continue
            vistas.add(clave_visual)
            elegidas.append(o)
            if len(elegidas) == tope_destacadas:
                break

        for o in elegidas:
            o["es_destacada"] = True
        destacadas_por_zona[nombre_zona] = elegidas

    # Agrupar por familia respetando el orden del YAML.
    familias: list[dict] = []
    for cfg in config:
        clave = cfg["nombre"]
        ofertas = [o for o in por_tema.get(clave, []) if not o["es_destacada"]]
        # Con vigencia declarada ordena lo que vence primero; sin ella, lo mas
        # reciente primero. Las que no traen ninguna fecha van al final.
        ofertas.sort(key=lambda o: (
            o["vence_en"] is None and o["dias"] is None,
            o["vence_en"] if o["vence_en"] is not None else (o["dias"] if o["dias"] is not None else 0),
        ))
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
            familias.append({
                "nombre": nombre_familia,
                "zona": cfg.get("zona"),
                "temas": [tema],
            })
        else:
            existente["temas"].append(tema)

    for fam in familias:
        fam["total"] = sum(t["total"] for t in fam["temas"])
        fam["nuevos"] = sum(t["nuevos"] for t in fam["temas"])

    zonas = _armar_zonas(familias, todas, destacadas_por_zona)

    ultima = con.execute("SELECT MAX(ultima_vez) AS u FROM ofertas").fetchone()["u"]
    return {
        "zonas": zonas,
        "total": len(todas),
        "vencidas": vencidas,
        "huerfanas": huerfanas,
        "nuevos": sum(1 for o in todas if o["nuevo"]),
        "actualizado": datetime.fromisoformat(ultima).astimezone().strftime("%d/%m/%Y %H:%M")
        if ultima else "nunca",
    }


def _armar_zonas(familias: list[dict], todas: list[dict],
                 destacadas_por_zona: dict) -> list[dict]:
    """Arma las pestanas en el orden de `zonas:` del YAML.

    Una zona sin temas igual se emite: la pestana vacia dice "esto existe y
    todavia no trajo nada", que es informacion. Una pestana que aparece y
    desaparece segun el dia es peor que una vacia.

    Los temas cuya `zona` no coincide con ninguna declarada caen en la primera,
    para que un error de tipeo en el YAML no borre un tema de la pagina.
    """
    config_zonas = _config_zonas()
    if not config_zonas:  # sin `zonas:` declaradas, todo va a una sola
        config_zonas = [{"nombre": "Todo", "acento": "teal"}]

    validas = {z["nombre"] for z in config_zonas}
    predeterminada = config_zonas[0]["nombre"]

    zonas: list[dict] = []
    for cfg in config_zonas:
        nombre = cfg["nombre"]
        propias = [
            f for f in familias
            if (f["zona"] if f["zona"] in validas else predeterminada) == nombre
        ]
        ofertas_zona = [
            o for o in todas
            if (o["zona"] if o["zona"] in validas else predeterminada) == nombre
        ]
        zonas.append({
            "nombre": nombre,
            "clave": normalizar(nombre).replace(" ", "-") or "zona",
            "eyebrow": cfg.get("eyebrow", ""),
            "acento": cfg.get("acento", "teal"),
            # Que plantilla de tarjeta usa la zona: "agenda" (puntaje + medio +
            # antiguedad) u "oferta" (beneficio + tope + vigencia). Una nota de
            # prensa y una promo bancaria no tienen los mismos datos.
            "tarjeta": cfg.get("tarjeta", "agenda"),
            "vacia": cfg.get("vacia", "Todavia nada por aca. Se revisa en cada corrida."),
            "familias": propias,
            "destacadas": destacadas_por_zona.get(nombre, []),
            "total": len(ofertas_zona),
            "nuevos": sum(1 for o in ofertas_zona if o["nuevo"]),
            "calientes": sum(1 for o in ofertas_zona if o["urgencia"] == "caliente"),
            "vencen_pronto": sum(
                1 for o in ofertas_zona
                if o["vence_en"] is not None and o["vence_en"] <= 7
            ),
        })
    return zonas


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
