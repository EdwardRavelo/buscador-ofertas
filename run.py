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

from fuentes import POR_DEFECTO, REGISTRO
from nucleo import almacen
from nucleo.calendario import caducidad, es_dia_de_ingesta
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
            if not es_dia_de_ingesta(tema):
                # Agenda del finde publicada un lunes = el finde que ya paso.
                print("  (hoy no corresponde buscar para este tema)")
                continue
            crudas = []
            for nombre_fuente in tema.get("fuentes", POR_DEFECTO):
                buscar = REGISTRO.get(nombre_fuente)
                if not buscar:
                    print(f"    ! fuente desconocida: {nombre_fuente}")
                    continue
                crudas += buscar(tema, cliente)

            # Dedup dentro de la corrida: la misma nota llega desde varias queries.
            unicas = {o.id: o for o in crudas}
            elegidas = filtrar_y_ordenar([puntuar(o, tema) for o in unicas.values()], tema)
            print(f"  {len(crudas)} crudas -> {len(unicas)} unicas -> {len(elegidas)} pasan el filtro")

            # Caducidad por calendario: la agenda del finde vence el LUNES, no a
            # los N dias de publicada. Se recalcula en cada corrida, asi una nota
            # que vuelve a aparecer el sabado mueve su vencimiento al lunes que
            # corresponde en vez de quedar clavada en el de la semana pasada.
            vence = caducidad(tema)
            if vence is not None:
                for o in elegidas:
                    o.vence = vence

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


# Rubros de la API de BBVA, por nombre para no escribir numeros en la linea de
# comandos. Los ids salen de /v3/rubros/filtro.
RUBROS = {
    "viajes": 13, "gastronomia": 3, "entretenimiento": 4, "moda": 170,
    "hogar": 173, "electro": 192, "deportes": 184, "belleza": 8,
    "jugueterias": 175, "regalos": 195, "shopping": 27,
}
# Lo que suele haber en un shopping, para no tener que enumerarlo cada vez.
ATAJOS = {
    "shopping": ["moda", "deportes", "electro", "jugueterias", "gastronomia", "belleza"],
}


def _comercios_de(url: str, cliente) -> str:
    """Texto visible de una pagina, normalizado, para cruzar contra comercios.

    Se cruza AL REVES de lo intuitivo: en vez de parsear la lista de locales del
    shopping (nombres de varias palabras, sin marcado util), se toma el nombre de
    comercio que ya trae cada promo de BBVA y se busca en este texto. No hay que
    adivinar donde termina un nombre y empieza el otro.
    """
    import re
    from nucleo.modelo import normalizar

    r = cliente.get(url, timeout=25.0)
    r.raise_for_status()
    sin_codigo = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", r.text, flags=re.S)
    return normalizar(re.sub(r"<[^>]+>", " ", sin_codigo))


def cmd_ahora(args) -> None:
    """Pedido puntual: llena la zona "Ahora" y borra lo que hubiera antes.

    No lo corre la tarea diaria (el tema lleva `ingesta: manual`). Lo que trae
    vence a las 23:59: un paseo de ayer no le sirve a nadie.
    """
    from nucleo.calendario import fin_del_dia
    from nucleo.modelo import normalizar

    temas = cargar_temas("ahora")
    tema = dict(temas[0])

    pedidos = []
    for r in (args.rubros or "").split(","):
        r = r.strip().lower()
        if not r:
            continue
        pedidos.extend(ATAJOS.get(r, [r]))
    ids = []
    for r in pedidos:
        if r not in RUBROS:
            sys.exit(f"Rubro desconocido: '{r}'. Conocidos: {', '.join(sorted(RUBROS))}")
        if RUBROS[r] not in ids:
            ids.append(RUBROS[r])
    if ids:
        tema["bbva_rubros"] = ids

    marcas = [m.strip() for m in (args.marcas or "").split(",") if m.strip()]
    if marcas:
        tema.setdefault("requerir", []).append(marcas)
    if args.cuotas:
        tema.setdefault("requerir", []).append(["cuotas sin interes", "cuotas"])

    with httpx.Client(headers=CABECERAS, follow_redirects=True) as cliente:
        crudas = []
        for nombre_fuente in tema.get("fuentes", POR_DEFECTO):
            crudas += REGISTRO[nombre_fuente](tema, cliente)

    unicas = {o.id: o for o in crudas}
    elegidas = filtrar_y_ordenar([puntuar(o, tema) for o in unicas.values()], tema)

    if args.en:
        import re

        with httpx.Client(headers=CABECERAS, follow_redirects=True) as cliente:
            texto = _comercios_de(args.en, cliente)
        antes = len(elegidas)
        sobreviven = []
        for o in elegidas:
            nombre = normalizar(o.extra.get("comercio") or o.titulo)
            # Menos de 4 letras da falsos positivos: "Ver", "Cat", "Exit" y
            # "Grid" son comercios reales y aparecen dentro de otras palabras.
            if len(nombre) < 4:
                continue
            if re.search(rf"\b{re.escape(nombre)}\b", texto):
                sobreviven.append(o)
        elegidas = sobreviven
        print(f"  cruzado con el listado del lugar: {antes} -> {len(elegidas)}")

    vence = fin_del_dia()
    for o in elegidas:
        o.vence = vence
        if args.lugar:
            o.extra["contexto"] = args.lugar

    print()
    print(f"=== ahora{': ' + args.lugar if args.lugar else ''} ===")
    print(f"  rubros: {', '.join(pedidos) or 'todos'}"
          f" | marcas: {', '.join(marcas) or '-'}"
          f" | solo cuotas: {'si' if args.cuotas else 'no'}")
    print(f"  {len(crudas)} crudas -> {len(unicas)} unicas -> {len(elegidas)} pasan el filtro")
    for o in elegidas:
        print(f"  [{o.score:4.1f}] {o.titulo[:74]}")
        if o.snippet:
            print(f"          {o.snippet[:96]}")

    if args.seco:
        print()
        print("  (en seco: no se guardo nada)")
        return

    con = almacen.conectar()
    # Un pedido REEMPLAZA al anterior: la zona muestra lo que pediste recien, no
    # el historial de todos los paseos. Los ids van a `vistos` para que el dedup
    # no los trate como novedad si vuelven a aparecer en otro tema.
    viejos = con.execute("SELECT id FROM ofertas WHERE tema = 'ahora'").fetchall()
    con.executemany("DELETE FROM ofertas WHERE id = ?", [(f["id"],) for f in viejos])
    con.commit()
    nuevas, repetidas = almacen.guardar(con, elegidas)
    con.close()
    print()
    print(f"  -> {len(viejos)} del pedido anterior borradas, {nuevas} guardadas")


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

    a = sub.add_parser("ahora", help="pedido puntual: llena la zona Ahora")
    a.add_argument("--rubros", help="coma: moda,deportes,electro... o el atajo 'shopping'")
    a.add_argument("--marcas", help="coma: nike,adidas. Filtra por nombre de comercio")
    a.add_argument("--cuotas", action="store_true", help="solo lo que tenga cuotas")
    a.add_argument("--lugar", help="etiqueta del pedido, ej. 'Alto Avellaneda'")
    a.add_argument("--en", metavar="URL",
                   help="deja solo los comercios que figuren en esa pagina "
                        "(la del shopping, por ejemplo)")
    a.add_argument("--seco", action="store_true", help="mostrar sin guardar")
    a.set_defaults(func=cmd_ahora)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
