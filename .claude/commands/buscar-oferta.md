---
description: Busca una oferta puntual de un producto en Argentina y la registra
argument-hint: <qué querés comprar> [presupuesto opcional]
---

Buscá la mejor oferta disponible para: **$ARGUMENTS**

Contexto fijo del usuario: compra desde **Buenos Aires, Argentina**. Precios en ARS.
Este es el modo puntual del buscador: una consulta efímera, no un tema de vigilancia.

## REQUISITO: usar Chrome, no WebFetch

Probado el 2026-08-30: MercadoLibre, Fullh4rd, Hardcore Computación, Argenprint,
Compra Gamer y Precialo devuelven **HTTP 403 a WebFetch**. Bloquean los pedidos
hechos desde un servidor. La única que respondió fue Langtecnología.

Entonces: para leer precios usá las herramientas `mcp__claude-in-chrome__*`, que
navegan desde el Chrome del usuario (su IP, su sesión). Invocá antes la skill
`claude-in-chrome`.

Si la extensión no está conectada, **decílo y pará**. No armes una comparación de
precios con una sola tienda verificada ni cites precios de snippets de búsqueda:
es peor que no dar nada, porque parece verificado y no lo está.

## Cómo proceder

1. **Entendé qué se necesita realmente** antes de buscar. Si el pedido es genérico
   ("parlantes para PC"), identificá los 2-3 ejes que cambian la recomendación
   (uso, rango de precio, si necesita subwoofer, conectividad) y asumí valores
   razonables en vez de frenar a preguntar. Declará los supuestos en la respuesta.

2. **Buscá en varias fuentes**, no en una sola. Para Argentina:
   - MercadoLibre Argentina (el grueso del mercado)
   - Tiendas especializadas: Compra Gamer, Venex, Full H4rd, Maximus, Mexx
   - Retail: Frávega, Musimundo, Garbarino
   - Sitios de cupones/ofertas argentinos por si hay promo bancaria vigente

3. **Verificá el precio antes de reportarlo.** No cites un precio de un snippet de
   búsqueda sin abrir la página. Si no lo pudiste confirmar, decilo explícitamente
   en vez de dar un número que parezca verificado.

4. **Detectá el descuento falso.** Un "50% OFF" sobre un precio de lista inflado no
   es una oferta. Compará contra el precio típico de mercado del mismo modelo.

5. **Recomendá, no enumeres.** Dale una opción principal con el motivo, una
   alternativa más barata y una superior. No un catálogo de 15 productos.

## Reglas

- No compres nada, no completes checkouts, no ingreses datos personales ni de pago.
- Solo reportás y recomendás; la decisión y la compra son del usuario.
- Si los precios varían mucho entre fuentes, mostralo: suele indicar stock viejo o
  publicaciones dudosas.

## Al terminar

Presentá un cuadro comparativo con: producto, precio verificado, tienda, link y una
observación. Cerrá con una recomendación en una o dos frases.

Si existe `config/.env` con `GOOGLE_SHEET_ID` configurado (Fase 2), agregá el
resultado a la pestaña `compras-puntuales` junto con la consulta que lo originó.
Si no existe todavía, anotalo al final de `datos/compras-puntuales.md`.
