# Buscador de ofertas, cursos y talleres

Vigila talleres, cursos, festivales, teatro gratis y promociones bancarias, y publica
los hallazgos en un sitio estático. La página tiene dos pestañas: **Agenda** (cultura y
formación) y **Ofertas** (descuentos).

**Sitio:** https://edwardravelo.github.io/buscador-ofertas/

## Cómo funciona

1. `fuentes/` consulta Google News RSS, feeds propios (`config/feeds.yaml`) y la API
   pública de beneficios de BBVA, que además declara hasta cuándo vale cada promo
2. `nucleo/puntuador.py` filtra por zona, actividad, recencia y tope por dominio
3. `nucleo/almacen.py` deduplica en SQLite (hash de título + medio)
4. `nucleo/sheets.py` sincroniza a Google Sheets, una pestaña por tema
5. `salidas/dashboard.py` genera el `index.html` que sirve GitHub Pages

Agregar un tema, una zona o una fuente es editar YAML. No requiere tocar código.

## Buscar ahora

Pestaña **Actions** → **Buscar ofertas** → **Run workflow**.

## Credenciales

Nunca se versionan. Viven en GitHub Secrets (`GOOGLE_SERVICE_ACCOUNT`, `GOOGLE_SHEET_ID`)
y, para uso local, en `config/.env` y `config/service_account.json`, ambos ignorados por git.
