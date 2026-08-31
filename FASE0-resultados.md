# Fase 0 — Validación de señal/ruido

Fecha: 2026-08-30. Fuente probada: Google News RSS (`hl=es-419&gl=AR&ceid=AR:es-419`).
Umbral definido en el plan para continuar: >=20% de resultados relevantes.

## Resultado: PASA en los tres temas

| Tema | Query probada | Relevantes/25 | % |
|---|---|---|---|
| talleres-lectura-caba | `talleres gratuitos bibliotecas Buenos Aires inscripción` | ~9 | 36% |
| cursos-ia | `"curso gratis" inteligencia artificial certificado` | ~20 | 80% |
| ingles | `curso de inglés gratis certificado Argentina` | ~10 | 40% |

## Aciertos de máxima calidad (tema talleres)

- Clarin, 26-ago-2026 — "las bibliotecas porteñas inscriben en sus talleres"
- El Destape, 25-ago-2026 — "abrió la inscripción a los talleres en las bibliotecas de la Ciudad"
- villaortuzar.ar, 29-ago-2026 — "talleres trimestrales gratuitos de la Biblioteca Nacional"
- Noticias Urbanas, 30-ago-2026 — "La Ciudad suma nuevos cursos y talleres"

Confirma la hipótesis del plan: aunque el sitio oficial de la Red de Bibliotecas no publica
datos estructurados (remite a Instagram @bibliotecasba), las APERTURAS DE INSCRIPCIÓN sí
llegan por prensa y quedan capturadas.

## Tres correcciones al diseño que surgieron de la prueba

1. FILTRO GEOGRÁFICO (prioridad 1). El ruido no es temático sino de provincia:
   Paraná, Merlo, Mendoza, Córdoba, Salta, La Plata, y algo de Colombia/México.
   Necesario un campo `requerir_alguno` (Buenos Aires, CABA, porteñ, Ciudad) además de `excluir`.

2. FILTRO DE RECENCIA (prioridad 2). El feed mezcla 2018 con 2026. Los listicles evergreen
   ("42 cursos gratis de IA") reaparecen indefinidamente.
   Necesario `max_antiguedad_dias` por tema (sugerido: 45 para talleres, 30 para cursos).

3. TOPE POR DOMINIO. qpasa.com aportó 5 de 25 resultados en el tema de IA (content farm).
   Necesario un máximo de 2 ítems por dominio por corrida.

## Nota adicional

Hay solapamiento entre temas (un mismo curso de IA aparece en `cursos-ia` y en `ingles`).
El dedup global por URL canonicalizada ya previsto en el plan lo resuelve.
