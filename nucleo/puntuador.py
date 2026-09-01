"""Puntuacion por reglas. Deterministico y sin costo de API.

Las tres correcciones que salieron de la Fase 0 (ver FASE0-resultados.md) viven aca:
filtro geografico, filtro de recencia y tope por dominio.
"""
from __future__ import annotations

import re
from collections import Counter

from nucleo.modelo import Oferta, normalizar, titulo_limpio

SENALES_FUERTES = [
    "gratis", "gratuito", "gratuita", "sin costo", "inscripcion abierta",
    "abren inscripciones", "abrio la inscripcion", "beca", "con certificado",
    "cupo", "descuento", "promocion", "2x1",
]

DESCARTADA = -99.0


def _contiene(texto: str, terminos: list[str]) -> list[str]:
    """Coincidencias con limite de palabra al inicio.

    Sin el limite, "ingles" matchea "El Corte Ingles" y "ia" matchea "materia".
    Se ancla solo el inicio para que un prefijo como "porten" siga tomando
    "portenas".
    """
    hallados = []
    for t in terminos:
        patron = normalizar(t)
        if patron and re.search(rf"\b{re.escape(patron)}", texto):
            hallados.append(t)
    return hallados


def _grupos_requeridos(tema: dict) -> list[list[str]]:
    """Cada grupo es un OR; todos los grupos deben cumplirse (AND de ORs).

    Un solo grupo no alcanzaba: filtrar por zona dejaba pasar "agenda cultural"
    y filtrar por actividad dejaba pasar cursos de Madrid.
    """
    if tema.get("requerir"):
        return tema["requerir"]
    if tema.get("requerir_alguno"):  # forma vieja, un solo grupo
        return [tema["requerir_alguno"]]
    return []


def puntuar(oferta: Oferta, tema: dict) -> Oferta:
    """Asigna score 0-10 y los motivos. score DESCARTADA = filtrada."""
    titulo = normalizar(titulo_limpio(oferta.titulo))
    cuerpo = f"{titulo} {normalizar(oferta.snippet)}"
    motivos: list[str] = []
    score = 5.0

    # --- Correccion 2: recencia. Google News mezcla 2018 con 2026.
    limite = tema.get("max_antiguedad_dias")
    edad = oferta.antiguedad_dias
    if limite and edad is not None and edad > limite:
        oferta.score = DESCARTADA
        oferta.motivos = [f"viejo ({edad:.0f}d > {limite}d)"]
        return oferta
    if edad is not None:
        if edad <= 7:
            score += 1.5
            motivos.append("reciente (<7d)")
        elif edad <= 21:
            score += 0.75
            motivos.append("reciente (<21d)")

    # --- Correccion 1: filtro geografico y de actividad (AND de ORs).
    for grupo in _grupos_requeridos(tema):
        hallados = _contiene(cuerpo, grupo)
        if not hallados:
            oferta.score = DESCARTADA
            oferta.motivos = [f"le falta: {'/'.join(grupo[:3])}..."]
            return oferta
        score += 0.75
        motivos.append(hallados[0])

    excluidos = _contiene(cuerpo, tema.get("excluir") or [])
    if excluidos:
        oferta.score = DESCARTADA
        oferta.motivos = [f"excluido: {excluidos[0]}"]
        return oferta

    # Medios de otros paises publicando ofertas locales suyas. Excluir por dominio
    # es mas general que ir listando ciudades una por una.
    # Solo sufijo: ".co" como subcadena matchearia ".com" y borraria todo.
    for patron in tema.get("excluir_dominios") or []:
        if oferta.fuente.endswith(patron):
            oferta.score = DESCARTADA
            oferta.motivos = [f"dominio excluido: {patron}"]
            return oferta

    # Keywords del tema presentes en el titulo pesan mas que en el cuerpo.
    palabras = {p for kw in tema.get("keywords", []) for p in normalizar(kw).split() if len(p) > 3}
    if palabras:
        en_titulo = sum(1 for p in palabras if p in titulo) / len(palabras)
        score += 2.0 * en_titulo
        if en_titulo >= 0.4:
            motivos.append(f"keywords en titulo ({en_titulo:.0%})")

    senales = _contiene(cuerpo, SENALES_FUERTES)
    if senales:
        score += min(1.5, 0.5 * len(senales))
        motivos.append(f"senal: {', '.join(senales[:3])}")

    oferta.score = max(0.0, min(10.0, score))
    oferta.motivos = motivos
    return oferta


def filtrar_y_ordenar(ofertas: list[Oferta], tema: dict) -> list[Oferta]:
    """Aplica el umbral del tema, ordena por score y limita por dominio.

    Correccion 3: un content farm (qpasa.com) aporto 5 de 25 resultados en la Fase 0.
    """
    minimo = tema.get("score_minimo", 6)
    tope = tema.get("max_por_dominio", 2)

    vivas = [o for o in ofertas if o.score >= minimo]
    # Mayor score primero; a igual score, lo mas nuevo. Sin fecha va al final.
    vivas.sort(key=lambda o: (-o.score, o.antiguedad_dias if o.antiguedad_dias is not None else 1e9))

    vistos: Counter[str] = Counter()
    resultado: list[Oferta] = []
    for o in vivas:
        if vistos[o.fuente] >= tope:
            continue
        if _es_casi_repetida(o, resultado):
            continue
        vistos[o.fuente] += 1
        resultado.append(o)
    return resultado


def _palabras(oferta: Oferta) -> set[str]:
    """Raices de 5 letras: stemmer de pobre, suficiente para espanol.

    Sin truncar, "inscripcion" e "inscripciones" cuentan como palabras distintas
    y dos titulares del mismo evento dan solo 0.56 de similitud.
    """
    return {p[:5] for p in normalizar(titulo_limpio(oferta.titulo)).split() if len(p) > 3}


def _es_casi_repetida(oferta: Oferta, elegidas: list[Oferta], umbral: float = 0.7) -> bool:
    """Detecta la misma nota publicada dos veces con el titulo cambiado.

    Caso real: villaortuzar.ar publico "Abre la inscripcion a los talleres..." y
    "Abren las inscripciones a los talleres...". El dedup por hash no las agarra
    porque compara titulos exactos. Se comparan solo notas del MISMO medio: dos
    medios distintos cubriendo el mismo evento son dos fuentes utiles.
    """
    mias = _palabras(oferta)
    if not mias:
        return False
    for otra in elegidas:
        if otra.fuente != oferta.fuente:
            continue
        suyas = _palabras(otra)
        if not suyas:
            continue
        interseccion = len(mias & suyas)
        union = len(mias | suyas)
        if union and interseccion / union >= umbral:
            return True
    return False
