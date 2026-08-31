"""Sincronizacion con Google Sheets: una pestana por tema, historico que no repite.

SQLite sigue siendo la fuente de verdad del dedup; Sheets es la capa de lectura,
la que se consulta desde el celular y donde se marca a mano el estado.
"""
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import gspread
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

RAIZ = Path(__file__).resolve().parent.parent
RUTA_ENV = RAIZ / "config" / ".env"
RUTA_CREDENCIALES = RAIZ / "config" / "service_account.json"

ALCANCES = ["https://www.googleapis.com/auth/spreadsheets"]
CABECERA = ["fecha_visto", "titulo", "tipo", "fuente", "precio", "url", "score", "estado", "notas"]

# La columna `estado` la completa el usuario a mano (me anote / descartado / pendiente).
# Nunca se pisa al re-sincronizar.
COL_URL = CABECERA.index("url")


def _cliente() -> gspread.Client:
    if not RUTA_CREDENCIALES.exists():
        raise SystemExit(
            f"Falta {RUTA_CREDENCIALES}.\n"
            "Descargue la clave JSON de la service account de Google Cloud y guardela ahi."
        )
    cred = Credentials.from_service_account_file(str(RUTA_CREDENCIALES), scopes=ALCANCES)
    return gspread.authorize(cred)


def _planilla(cliente: gspread.Client) -> gspread.Spreadsheet:
    load_dotenv(RUTA_ENV)
    sheet_id = os.getenv("GOOGLE_SHEET_ID", "").strip()
    if not sheet_id:
        raise SystemExit("Falta GOOGLE_SHEET_ID en config/.env. Ver config/.env.ejemplo")
    try:
        return cliente.open_by_key(sheet_id)
    except gspread.exceptions.APIError as e:
        raise SystemExit(
            f"No se pudo abrir la planilla: {e}\n"
            "Verifique que compartio el Sheet con el email de la service account "
            "(el campo client_email del JSON), con permiso de editor."
        )


def _pestana(planilla: gspread.Spreadsheet, nombre: str) -> gspread.Worksheet:
    try:
        hoja = planilla.worksheet(nombre)
    except gspread.exceptions.WorksheetNotFound:
        hoja = planilla.add_worksheet(title=nombre, rows=500, cols=len(CABECERA))
        hoja.append_row(CABECERA)
        hoja.freeze(rows=1)
    return hoja


def sincronizar(con: sqlite3.Connection) -> dict[str, int]:
    """Sube a Sheets lo que todavia no se subio. Idempotente."""
    cliente = _cliente()
    planilla = _planilla(cliente)
    agregados: dict[str, int] = {}

    temas = [f["tema"] for f in con.execute("SELECT DISTINCT tema FROM ofertas").fetchall()]
    for tema in temas:
        filas = con.execute(
            "SELECT * FROM ofertas WHERE tema = ? AND sincronizado = 0 ORDER BY score DESC",
            (tema,),
        ).fetchall()
        if not filas:
            agregados[tema] = 0
            continue

        hoja = _pestana(planilla, tema)
        # Segunda red contra duplicados: si la URL ya esta en la hoja, no se repite.
        # Cubre el caso de haber borrado ofertas.db sin borrar la planilla.
        try:
            ya_estan = set(hoja.col_values(COL_URL + 1)[1:])
        except gspread.exceptions.APIError:
            ya_estan = set()

        nuevas = []
        for f in filas:
            url = f["url_final"] or f["url"]
            if url in ya_estan:
                continue
            nuevas.append([
                (f["fecha_pub"] or f["primera_vez"])[:10],
                f["titulo"],
                f["origen"],
                f["fuente"],
                f["precio"] if f["precio"] is not None else "",
                url,
                round(f["score"], 1),
                "",  # estado: lo completa el usuario
                " | ".join(m for m in (f["motivos"] or "").split("|") if m.strip()),
            ])

        if nuevas:
            hoja.append_rows(nuevas, value_input_option="USER_ENTERED")

        con.executemany(
            "UPDATE ofertas SET sincronizado = 1 WHERE id = ?", [(f["id"],) for f in filas]
        )
        con.commit()
        agregados[tema] = len(nuevas)

    return agregados
