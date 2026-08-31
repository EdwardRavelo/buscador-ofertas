---
description: Investiga y propone fuentes RSS nuevas para un tema de vigilancia
argument-hint: <nombre del tema o descripción>
---

Investigá qué fuentes nuevas conviene sumar para: **$ARGUMENTS**

Contexto: buscador personal con base en **Buenos Aires, Argentina**, presupuesto de
APIs **$0**. Las fuentes tienen que ser gratis y sin API key.

## Cómo proceder

1. Buscá qué sitios, blogs, organismos y medios cubren ese tema en Argentina.
   Priorizá los que publican avisos de inscripción o de oferta, no los que
   comentan el tema en abstracto.

2. **Probá cada candidato de verdad**, no lo supongas. Para cada uno:
   - Buscá el feed: `/feed`, `/rss`, `/feeds/posts/default` (Blogger),
     `/?feed=rss2` (WordPress).
   - Traelo y confirmá que devuelve ítems reales y recientes.
   - Anotá cuántos ítems trae y de qué fecha es el más nuevo.

3. **Descartá lo que no sirve** y decí por qué. Un feed muerto, uno que no se
   actualiza hace un año, o uno lleno de contenido afiliado es un descarte, no un
   candidato dudoso que sumás igual.

4. Verificá que no sea redundante con lo que ya está en `config/feeds.yaml`.

## Al terminar

Entregá las líneas YAML listas para pegar en `config/feeds.yaml`, cada una con un
comentario de qué aporta y con qué frecuencia publica. Separá claramente los feeds
verificados de las fuentes que existen pero **no** tienen RSS (esas van a una lista
aparte de "revisar a mano", no al archivo de config).
