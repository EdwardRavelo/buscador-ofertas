"""Avisos por Telegram. Manda solo lo que todavia no se notifico."""
from __future__ import annotations

import os
import sqlite3
from html import escape
from pathlib import Path

import httpx
from dotenv import load_dotenv

from nucleo.almacen import marcar_notificadas, sin_notificar

RUTA_ENV = Path(__file__).resolve().parent.parent / "config" / ".env"
API = "https://api.telegram.org/bot{token}/sendMessage"

ETIQUETAS = {
    "talleres-lectura-caba": "Talleres y lectura en CABA",
    "cursos-ia": "Cursos de IA",
    "ingles": "Ingles",
}


def _credenciales() -> tuple[str, str]:
    load_dotenv(RUTA_ENV)
    token = os.getenv("TELEGRAM_TOKEN", "").strip()
    chat = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    if not token or not chat:
        raise SystemExit(
            "Faltan credenciales. Cree config/.env con:\n"
            "  TELEGRAM_TOKEN=...\n"
            "  TELEGRAM_CHAT_ID=...\n"
            "Ver config/.env.ejemplo"
        )
    return token, chat


def _mensaje(filas: list[sqlite3.Row]) -> str:
    """Un solo mensaje agrupado por tema. Varios mensajes sueltos molestan mas."""
    partes = ["<b>Novedades del radar</b>"]
    tema_actual = None
    for f in filas:
        if f["tema"] != tema_actual:
            tema_actual = f["tema"]
            partes.append(f"\n<b>{escape(ETIQUETAS.get(tema_actual, tema_actual))}</b>")
        url = f["url_final"] or f["url"]
        partes.append(
            f'{f["score"]:.1f} · <a href="{escape(url, quote=True)}">'
            f'{escape(f["titulo"][:110])}</a>'
            f'\n<i>{escape(f["fuente"])}</i>'
        )
    return "\n".join(partes)


def notificar(minimo: float = 7.0, en_seco: bool = False) -> int:
    """Envia las ofertas no notificadas por encima del umbral. Devuelve cuantas."""
    from nucleo.almacen import conectar

    con = conectar()
    filas = sin_notificar(con, minimo)
    if not filas:
        print("No hay novedades por encima del umbral.")
        con.close()
        return 0

    texto = _mensaje(filas)
    if en_seco:
        print("--- se enviaria esto ---")
        print(texto)
        print(f"--- {len(filas)} ofertas, NO se marcaron como notificadas ---")
        con.close()
        return len(filas)

    token, chat = _credenciales()
    r = httpx.post(
        API.format(token=token),
        json={
            "chat_id": chat,
            "text": texto,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        },
        timeout=25.0,
    )
    if r.status_code != 200:
        raise SystemExit(f"Telegram rechazo el envio: {r.status_code} {r.text[:300]}")

    # Solo se marcan despues de que el envio salio bien, para no perder avisos.
    marcar_notificadas(con, [f["id"] for f in filas])
    con.close()
    print(f"Enviadas {len(filas)} ofertas a Telegram.")
    return len(filas)
