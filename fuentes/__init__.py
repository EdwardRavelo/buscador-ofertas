"""Registro de fuentes. Agregar una fuente = agregar un modulo y una linea aca."""
from fuentes import bbva, google_news, rss

REGISTRO = {
    google_news.NOMBRE: google_news.buscar,
    rss.NOMBRE: rss.buscar,
    bbva.NOMBRE: bbva.buscar,
}

# Fuentes que NO corren salvo que el tema las pida por nombre en `fuentes:`.
#
# Las de busqueda (google_news, rss) reciben las keywords del tema y devuelven
# algo acotado. Las de CATALOGO devuelven todo lo que tienen y no les importa el
# tema: bbva baja 926 promos en 47 pedidos. Sin esta lista, cada tema sin
# `fuentes:` declarado se bajaba el catalogo entero del banco para descartarlo
# despues: seis temas x 47 pedidos = ~280 pedidos al cuete por corrida, y el
# embudo pasaba de 300 a 1200 crudas.
SOLO_POR_PEDIDO = {bbva.NOMBRE}

# Lo que corre cuando el tema no declara `fuentes:`.
POR_DEFECTO = [n for n in REGISTRO if n not in SOLO_POR_PEDIDO]
