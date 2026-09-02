"""Buscador de ofertas, cursos y talleres. CLI de la vigilancia continua.

    python run.py buscar            corre todos los temas
    python run.py buscar -t ingles  corre un tema
    python run.py buscar --seco     no escribe en la base
    python run.py listar            muestra lo guardado
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import httpx
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))

from fuentes import REGISTRO
from nucleo import almacen
from nucleo.puntuador import filtrar_y_ordenar, puntuar
from nucleo.urls import es_google_news, resolver_google_news

RAIZ = Path(__file__).resolve().parent
CABECERAS = {"User-Agent": "BuscadorOfertas/0.1 (uso personal)"}


def cargar_temas(nombre: str | None) -> list[dict]:
    datos = yaml.safe_load((RAIZ / "config" / "temas.yaml").read_text(encoding="utf-8"))
    temas = datos.get("temas", [])
    if nombre:
        temas = [t for t in temas if t["nombre"] == nombre]
        if not temas:
            sys.exit(f"No existe el tema '{nombre}' en config/temas.yaml")
    return temas


def cmd_buscar(args) -> None:
    temas = cargar_temas(args.tema)
    con = None if args.seco else almacen.conectar()
    total_nuevas = 0

    with httpx.Client(headers=CABECERAS, follow_redirects=True) as cliente:
        for tema in temas:
            print(f"\n=== {tema['nombre']} ===")
            crudas = []
            for nombre_fuente in tema.get("fuentes", list(REGISTRO)):
                buscar = REGISTRO.get(nombre_fuente)
                if not buscar:
                    print(f"    ! fuente desconocida: {nombre_fuente}")
                    continue
                crudas += buscar(tema, cliente)

            # Dedup dentro de la corrida: la misma nota llega desde varias queries.
            unicas = {o.id: o for o in crudas}
            elegidas = filtrar_y_ordenar([puntuar(o, tema) for o in unicas.values()], tema)
            print(f"  {len(crudas)} crudas -> {len(unicas)} unicas -> {len(elegidas)} pasan el filtro")

            if args.resolver:
                for o in elegidas:
                    if es_google_news(o.url):
                        o.url_final = resolver_google_news(o.url, cliente)

            for o in elegidas:
                edad = f"{o.antiguedad_dias:.0f}d" if o.antiguedad_dias is not None else "s/f"
                print(f"  [{o.score:4.1f}] ({edad:>4}) {o.titulo[:88]}")
                print(f"          {o.fuente} | {' | '.join(o.motivos)}")

            if con is not None:
                nuevas, repetidas = almacen.guardar(con, elegidas)
                total_nuevas += nuevas
                print(f"  -> {nuevas} nuevas, {repetidas} ya conocidas")

    if con is not None:
        con.close()
        print(f"\nTotal de novedades en esta corrida: {total_nuevas}")


def cmd_listar(args) -> None:
    con = almacen.conectar()
    filas = con.execute(
        "SELECT tema, score, fecha_pub, fuente, titulo, url_final, url FROM ofertas "
        "ORDER BY tema, score DESC"
    ).fetchall()
    tema_actual = None
    for f in filas:
        if f["tema"] != tema_actual:
            tema_actual = f["tema"]
            print(f"\n=== {tema_actual} ===")
        print(f"  [{f['score']:4.1f}] {f['titulo'][:90]}")
        print(f"          {f['url_final'] or f['url']}")
    print(f"\n{len(filas)} ofertas en la base.")
    con.close()


def cmd_dashboard(args) -> None:
    from salidas.dashboard import generar

    print(f"Dashboard generado: {generar()}")


def cmd_notificar(args) -> None:
    from salidas.telegram import notificar

    notificar(minimo=args.minimo, en_seco=args.seco)


def cmd_sync(args) -> None:
    from nucleo.sheets import sincronizar

    con = almacen.conectar()
    for tema, cantidad in sincronizar(con).items():
        print(f"  {tema}: {cantidad} filas agregadas")
    con.close()


def cmd_purgar(args) -> None:
    con = almacen.conectar()
    borradas = almacen.purgar(con, args.dias)
    con.close()
    print(f"Purgadas {borradas} ofertas de mas de {args.dias} dias (queda su hash).")


def main() -> None:
    p = argparse.ArgumentParser(description="Buscador de ofertas, cursos y talleres")
    sub = p.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("buscar", help="busca y guarda novedades")
    b.add_argument("-t", "--tema", help="correr un solo tema")
    b.add_argument("--seco", action="store_true", help="no escribir en la base")
    b.add_argument("--resolver", action="store_true",
                   help="intentar resolver los enlaces de Google News (lento)")
    b.set_defaults(func=cmd_buscar)

    l = sub.add_parser("listar", help="muestra lo guardado")
    l.set_defaults(func=cmd_listar)

    d = sub.add_parser("dashboard", help="genera dashboard.html")
    d.set_defaults(func=cmd_dashboard)

    g = sub.add_parser("purgar", help="borra ofertas muy viejas dejando su hash")
    g.add_argument("--dias", type=int, default=365, help="umbral en dias (default 365)")
    g.set_defaults(func=cmd_purgar)

    n = sub.add_parser("notificar", help="manda las novedades por Telegram")
    n.add_argument("--seco", action="store_true", help="mostrar sin enviar ni marcar")
    n.add_argument("--minimo", type=float, default=7.0, help="score minimo (default 7.0)")
    n.set_defaults(func=cmd_notificar)

    s = sub.add_parser("sync", help="sincroniza con Google Sheets")
    s.set_defaults(func=cmd_sync)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
