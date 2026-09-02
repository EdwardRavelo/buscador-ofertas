"""Persistencia local en SQLite. Es la fuente de verdad del dedup."""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from nucleo.modelo import Oferta

RUTA_DB = Path(__file__).resolve().parent.parent / "datos" / "ofertas.db"

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS ofertas (
    id            TEXT PRIMARY KEY,
    titulo        TEXT NOT NULL,
    url           TEXT NOT NULL,
    url_final     TEXT,
    fuente        TEXT NOT NULL,
    tema          TEXT NOT NULL,
    origen        TEXT NOT NULL,
    snippet       TEXT,
    precio        REAL,
    score         REAL NOT NULL,
    motivos       TEXT,
    fecha_pub     TEXT,
    primera_vez   TEXT NOT NULL,
    ultima_vez    TEXT NOT NULL,
    notificado    INTEGER NOT NULL DEFAULT 0,
    sincronizado  INTEGER NOT NULL DEFAULT 0,
    estado        TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_tema ON ofertas(tema);
CREATE INDEX IF NOT EXISTS idx_pendientes ON ofertas(notificado, score);

-- Lapidas. Cuando se purga una oferta vieja queda su hash aca, ocupando unos
-- pocos bytes. Sin esto, borrar una fila hace que la proxima corrida la vuelva a
-- "descubrir" y te la anuncie como novedad.
CREATE TABLE IF NOT EXISTS vistos (
    id       TEXT PRIMARY KEY,
    purgada  TEXT NOT NULL
);
"""


def conectar(ruta: Path = RUTA_DB) -> sqlite3.Connection:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(ruta)
    con.row_factory = sqlite3.Row
    con.executescript(_ESQUEMA)
    return con


def guardar(con: sqlite3.Connection, ofertas: list[Oferta]) -> tuple[int, int]:
    """Inserta las nuevas y refresca las ya vistas. Devuelve (nuevas, repetidas)."""
    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    nuevas = repetidas = 0

    for o in ofertas:
        fila = con.execute("SELECT id FROM ofertas WHERE id = ?", (o.id,)).fetchone()
        if fila:
            # Ya la vimos: solo actualizamos la marca de tiempo. No se re-notifica.
            con.execute("UPDATE ofertas SET ultima_vez = ? WHERE id = ?", (ahora, o.id))
            repetidas += 1
            continue
        if con.execute("SELECT 1 FROM vistos WHERE id = ?", (o.id,)).fetchone():
            # Purgada hace tiempo. No se reinserta: ya tuvo su momento.
            repetidas += 1
            continue
        con.execute(
            """INSERT INTO ofertas (id, titulo, url, url_final, fuente, tema, origen,
                                    snippet, precio, score, motivos, fecha_pub,
                                    primera_vez, ultima_vez)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (o.id, o.titulo, o.url, o.url_final, o.fuente, o.tema, o.origen,
             o.snippet, o.precio, o.score, " | ".join(o.motivos),
             o.fecha_pub.isoformat() if o.fecha_pub else None, ahora, ahora),
        )
        nuevas += 1

    con.commit()
    return nuevas, repetidas


def sin_notificar(con: sqlite3.Connection, minimo: float = 0.0) -> list[sqlite3.Row]:
    return con.execute(
        "SELECT * FROM ofertas WHERE notificado = 0 AND score >= ? ORDER BY tema, score DESC",
        (minimo,),
    ).fetchall()


def marcar_notificadas(con: sqlite3.Connection, ids: list[str]) -> None:
    con.executemany("UPDATE ofertas SET notificado = 1 WHERE id = ?", [(i,) for i in ids])
    con.commit()


def purgar(con: sqlite3.Connection, dias: int = 365) -> int:
    """Borra ofertas muy viejas dejando su hash como lapida.

    Por que hace falta: ofertas.db se versiona en git y se commitea en cada
    corrida. Sin purga, el binario crece para siempre y cada commit guarda una
    copia entera; en un ano son cientos de versiones de un archivo cada vez mas
    grande. La lapida ocupa ~40 bytes y mantiene el dedup intacto.

    El umbral por defecto (365d) esta muy por encima de cualquier vida_util_dias
    configurada, asi que nunca borra algo que la pagina todavia muestra.
    """
    ahora = datetime.now(timezone.utc).isoformat(timespec="seconds")
    corte = (datetime.now(timezone.utc) - timedelta(days=dias)).isoformat()

    viejas = con.execute(
        "SELECT id FROM ofertas WHERE primera_vez < ?", (corte,)
    ).fetchall()
    if not viejas:
        return 0

    con.executemany(
        "INSERT OR IGNORE INTO vistos (id, purgada) VALUES (?, ?)",
        [(f["id"], ahora) for f in viejas],
    )
    con.executemany("DELETE FROM ofertas WHERE id = ?", [(f["id"],) for f in viejas])
    con.commit()
    con.execute("VACUUM")
    return len(viejas)
