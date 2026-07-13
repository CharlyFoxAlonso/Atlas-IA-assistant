# RFC-0008: Reparación segura mediante Healer

**Estado:** Aceptado e implementado  
**Fecha:** 2026-07-13  
**Ámbito:** `core/system/healer.py`

## Contexto

La implementación inicial de Healer reparaba automáticamente al ejecutarse, instalaba paquetes por nombre de importación, ignoraba códigos de retorno, escribía placeholders en `.env` y mezclaba inicio de servicios con descargas inmediatas.

Ese comportamiento no era adecuado para una aplicación distribuible ni para un sistema que prioriza privacidad y control del usuario.

## Decisión

Healer se implementa como un conjunto de reparadores explícitos e idempotentes. Su comportamiento predeterminado es simulación.

```python
healer = Healer(dry_run=True)
result = healer.fix("folders")
report = healer.fix_all()
```

Componentes actuales:

- `folders`;
- `config`;
- `venv`;
- `python_packages`;
- `ollama_service`;
- `ollama_model`.

## Riesgos

| Categoría | Ejemplos | Consentimiento |
|---|---|---|
| Seguro | Crear carpetas necesarias, crear configuración inexistente | Acción explícita y `--apply` desde CLI |
| Moderado | Iniciar Ollama instalado | Acción explícita y `--apply` |
| Pesado | Instalar requirements, descargar un modelo | `--apply --allow-heavy` |

## Propiedades obligatorias

1. `dry_run=True` por defecto.
2. Ninguna acción al importar o ejecutar el módulo sin una solicitud específica.
3. Resultados mediante `RepairResult`.
4. Continuación de `fix_all()` ante fallos parciales.
5. Nuevo diagnóstico después de cambios reales.
6. Instalación desde `requirements.txt`, no desde nombres de importación.
7. Rechazo de instalaciones en Python global.
8. Conservación de `.env` existente.
9. Ausencia de placeholders de claves.
10. Espera acotada al iniciar Ollama.
11. No descargar un modelo ya presente.

## Consecuencias

### Positivas

- Las reparaciones son predecibles y auditables.
- La CLI y una futura UI pueden mostrar un plan antes de aplicarlo.
- Los componentes fallan de manera aislada.
- El usuario mantiene control sobre instalaciones y descargas.

### Costos

- Algunas reparaciones requieren más interacción.
- Los ejecutables externos todavía necesitan instalación manual.
- La configuración de fuentes y hashes queda pendiente.

## Alternativas descartadas

### Reparar automáticamente cuando la salud sea menor que 100

Descartado porque la salud incluye capacidades recomendadas u opcionales. Un sistema puede estar listo con un puntaje menor.

### Instalar cada import faltante con pip

Descartado porque import y distribución no siempre comparten nombre, y porque rompe el archivo curado de dependencias.

### Escribir claves vacías o placeholders

Descartado porque puede producir falsos positivos y modificar configuración privada sin necesidad.

## Trabajo futuro

- Reparadores de ejecutables externos basados en manifiestos.
- Descargas HTTPS con allowlist y SHA-256.
- Políticas de privilegios de administrador.
- Logs persistentes con rotación y redacción.
- Progreso estructurado para UI y bootstrapper.

