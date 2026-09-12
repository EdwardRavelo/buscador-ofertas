"""Caducidad por calendario, no por reloj rodante.

El resto del proyecto mide vigencia en dias desde que algo se publico
(`max_antiguedad_dias`, `vida_util_dias`) o toma la fecha que declara la fuente
(`Oferta.vence`, que hoy solo llena la API de BBVA).

La agenda del fin de semana no encaja en ninguno de los dos: no caduca a los N
dias de publicada sino el LUNES, sea cual sea el dia en que se publico. Una nota
del jueves y una del domingo dejan de servir el mismo lunes a la manana.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

# Buenos Aires es UTC-3 fijo: el pais no cambia de hora desde 2009. Se escribe a
# mano en vez de usar zoneinfo porque `tzdata` no viene con Python en Windows y
# el runner de GitHub Actions tampoco lo garantiza; una dependencia mas por un
# offset que no se mueve no vale la pena.
ARGENTINA = timezone(timedelta(hours=-3))

# datetime.weekday(): lunes=0 ... domingo=6
JUEVES, DOMINGO = 3, 6


def fin_del_finde(ahora: datetime | None = None) -> datetime:
    """El proximo lunes a las 00:00 de Buenos Aires.

    Es el momento en que la agenda del fin de semana deja de servir. Se devuelve
    con zona horaria para que `Oferta.dias_para_vencer` compare bien.
    """
    ahora = (ahora or datetime.now(ARGENTINA)).astimezone(ARGENTINA)
    faltan = (7 - ahora.weekday()) % 7 or 7
    lunes = ahora + timedelta(days=faltan)
    return lunes.replace(hour=0, minute=0, second=0, microsecond=0)


def es_dia_de_ingesta(tema: dict, ahora: datetime | None = None) -> bool:
    """Si hoy corresponde buscar para este tema.

    Solo aplica a los temas con `ingesta: finde`. Existe porque una nota de
    agenda publicada un LUNES habla del fin de semana que ya paso: si entrara,
    sobreviviria hasta el lunes siguiente y la zona mostraria una semana entera
    de informacion vencida. De jueves a domingo es cuando los medios publican la
    agenda del finde que viene.
    """
    if tema.get("ingesta") != "finde":
        return True
    dia = (ahora or datetime.now(ARGENTINA)).astimezone(ARGENTINA).weekday()
    return JUEVES <= dia <= DOMINGO


def caducidad(tema: dict, ahora: datetime | None = None) -> datetime | None:
    """Cuando vence lo que traiga este tema, o None si no caduca por calendario."""
    if tema.get("caduca") == "finde":
        return fin_del_finde(ahora)
    return None
