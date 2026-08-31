# Buscador de ofertas, cursos y talleres

Vigila talleres, cursos y ofertas formativas en Buenos Aires y publica los hallazgos
en un sitio estático.

**Sitio:** https://edwardravelo.github.io/buscador-ofertas/

## Cómo funciona

1. `fuentes/` consulta Google News RSS y feeds propios declarados en `config/feeds.yaml`
2. `nucleo/puntuador.py` filtra por zona, actividad, recencia y tope por dominio
3. `nucleo/almacen.py` deduplica en SQLite (hash de título + medio)
4. `nucleo/sheets.py` sincroniza a Google Sheets, una pestaña por tema
5. `salidas/dashboard.py` genera el `index.html` que sirve GitHub Pages

Agregar un tema o una fuente es editar YAML. No requiere tocar código.

## Buscar ahora

Pestaña **Actions** → **Buscar ofertas** → **Run workflow**.

## Credenciales

Nunca se versionan. Viven en GitHub Secrets (`GOOGLE_SERVICE_ACCOUNT`, `GOOGLE_SHEET_ID`)
y, para uso local, en `config/.env` y `config/service_account.json`, ambos ignorados por git.
