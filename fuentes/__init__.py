"""Registro de fuentes. Agregar una fuente = agregar un modulo y una linea aca."""
from fuentes import google_news, rss

REGISTRO = {
    google_news.NOMBRE: google_news.buscar,
    rss.NOMBRE: rss.buscar,
}
