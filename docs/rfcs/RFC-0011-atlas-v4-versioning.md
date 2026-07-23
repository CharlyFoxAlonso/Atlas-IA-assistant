Estado: Superseded

Este RFC documenta la decisión histórica de Atlas v4.
Atlas v4.1 adopta la versión técnica 4.1.0 y la identidad visible Atlas v4.1.

# RFC-0011 — Identidad de versión Atlas v4

- Estado: aceptado
- Fecha: 2026-07-13
- Alcance: identidad de producto y metadatos de versión

## Decisión

Atlas adopta `v4` como identidad visible y `4.0` como versión técnica canónica. Los títulos, interfaces, lanzadores, documentación vigente, API, empaquetado, diagnósticos y pruebas deben respetar esa convención.

## Compatibilidad

- Las entradas históricas de changelog conservan sus versiones originales.
- El cambio no altera formatos de datos, secretos, memoria del usuario ni dependencias.
- La API raíz informa `v4`; `core.config.VERSION` y Doctor informan `4.0`.
- El crawler se identifica como `AtlasBot/4.0`.

## Verificación

La migración se valida mediante búsqueda residual, compilación de Python, pruebas automatizadas y ejecución de la ayuda de la CLI técnica.
