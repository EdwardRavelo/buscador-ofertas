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


def _aplanar(terminos) -> list[str]:
    """Aplana un nivel de anidamiento.

    YAML no concatena listas, asi que para reusar un anchor y ademas agregar
    terminos propios queda algo como [[...lista compartida...], "extra1", "extra2"].
    Sin aplanar, _contiene() recibiria una lista donde espera un string.
    """
    planos: list[str] = []
    for t in terminos or []:
        if isinstance(t, (list, tuple)):
            planos.extend(str(x) for x in t)
        else:
            planos.append(str(t))
    return planos


def _contiene(texto: str, terminos: list[str]) -> list[str]:
    """Coincidencias con limite de palabra al inicio.

    Sin el limite, "ingles" matchea "El Corte Ingles" y "ia" matchea "materia".
    Se ancla solo el inicio para que un prefijo como "porten" siga tomando
    "portenas".
    """
    hallados = []
    for t in _aplanar(terminos):
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

    # --- Vigencia declarada. Cuando la fuente dice hasta cuando vale (la API de
    # un banco lo dice; una nota de prensa no), esa fecha manda y el filtro de
    # antiguedad no corre: una promo que arranco hace nueve meses y vence manana
    # sigue sirviendo hoy, y `max_antiguedad_dias` la mataria sin motivo.
    restan = oferta.dias_para_vencer
    if restan is not None:
        if restan < 0:
            oferta.score = DESCARTADA
            oferta.motivos = [f"vencida hace {-restan:.0f}d"]
            return oferta
        motivos.append("vence en %.0fd" % restan if restan >= 1 else "vence hoy")
        # Lo que esta por vencer sube: es lo que hay que aprovechar ya.
        if restan <= 3:
            score += 1.0
        elif restan <= 10:
            score += 0.5

    # --- Correccion 2: recencia. Google News mezcla 2018 con 2026.
    limite = tema.get("max_antiguedad_dias")
    edad = oferta.antiguedad_dias
    if restan is None and limite and edad is not None and edad > limite:
        oferta.score = DESCARTADA
        oferta.motivos = [f"viejo ({edad:.0f}d > {limite}d)"]
        return oferta
    if restan is None and edad is not None:
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
            faltantes = _aplanar(grupo)[:3]
            oferta.motivos = [f"le falta: {'/'.join(faltantes)}..."]
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

    # Senales propias del tema: suman sin ser obligatorias. Para cuando interesa
    # todo un rubro pero algo en particular va primero (el banco donde tenes la
    # cuenta entre todas las promos bancarias). Si fuera `requerir`, el tema se
    # quedaria sin resultados los dias que ese banco no publica nada.
    propias = _contiene(cuerpo, tema.get("senales") or [])
    if propias:
        score += min(2.0, 1.0 * len(propias))
        motivos.append(f"clave: {', '.join(propias[:3])}")

    oferta.score = max(0.0, min(10.0, score))
    oferta.motivos = motivos
    return oferta


def filtrar_y_ordenar(ofertas: list[Oferta], tema: dict) -> list[Oferta]:
    """Aplica el umbral del tema, ordena por score y limita por dominio.

    Correccion 3: un content farm (qpasa.com) aporto 5 de 25 resultados en la Fase 0.
    """
    minimo = tema.get("score_minimo", 6)
    tope = tema.get("max_por_dominio", 2)
    # El filtro de casi-repetidas asume titulares de PRENSA, donde dos textos casi
    # iguales del mismo medio son la misma nota. En un CATALOGO es al reves: los
    # titulos son formularios ("X 20% y 6 cuotas") y lo unico que los distingue es
    # el nombre del comercio, que suele ser corto y lo pierde el stemmer.
    # Medido: colapsaba "Top Sport 20% y 6 cuotas" con "Sport 78 6 cuotas".
    agrupar = tema.get("agrupar_casi_repetidas", True)
    # Distinto de `_es_casi_repetida`, que solo compara notas del MISMO medio.
    # Aca se descarta el mismo titulo EXACTO venga de donde venga: las agendas de
    # fin de semana se sindican y la nota de Clarin aparecia tres veces, con
    # fmalpina.com.ar y todobasquet.com.ar republicandola palabra por palabra.
    # Sigue sin tocarse el caso de dos medios cubriendo el mismo evento con
    # titulos distintos, que son dos fuentes utiles.
    unico_titulo = tema.get("unico_por_titulo", False)
    titulos_vistos: set[str] = set()

    vivas = [o for o in ofertas if o.score >= minimo]
    # Mayor score primero; a igual score, lo mas nuevo. Sin fecha va al final.
    vivas.sort(key=lambda o: (-o.score, o.antiguedad_dias if o.antiguedad_dias is not None else 1e9))

    vistos: Counter[str] = Counter()
    resultado: list[Oferta] = []
    for o in vivas:
        if vistos[o.fuente] >= tope:
            continue
        if agrupar and _es_casi_repetida(o, resultado):
            continue
        if unico_titulo:
            clave = normalizar(titulo_limpio(o.titulo))
            if clave in titulos_vistos:
                continue
            titulos_vistos.add(clave)
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
