# Reauditoría final — IDX-C1 verificación de consistencia read-only

Fecha: 2026-08-04

Repositorio: Atlas

Rama: atlas-v4.1-incremental-indexing

HEAD auditado: add7bc65b15ee0e2b638f31f9e0a06f7b06b04ab

Gate: PASS

## Gate: PASS

Reauditoría final focalizada IDX-C1 completada en modo read-only. No modifiqué archivos, no ejecuté `mkdir`, no hice stage, commit ni push.

### Baseline Git verificado

- Rama: `atlas-v4.1-incremental-indexing`
- HEAD: `add7bc65b15ee0e2b638f31f9e0a06f7b06b04ab`
- Working tree:
  - 8 cambios preexistentes de gobernanza visibles.
  - 4 archivos IDX-C1 dentro del alcance:
    - [core/vector_store.py](C:/Users/delfa/Documents/Atlas/core/vector_store.py)
    - [core/index_consistency.py](C:/Users/delfa/Documents/Atlas/core/index_consistency.py)
    - [tests/test_vector_paths.py](C:/Users/delfa/Documents/Atlas/tests/test_vector_paths.py)
    - [tests/test_index_consistency.py](C:/Users/delfa/Documents/Atlas/tests/test_index_consistency.py)
  - Reporte histórico IDX-C1 sigue sin rastrear:
    - [2026-08-03-add7bc6-idx-c1-readonly-consistency-review.md](C:/Users/delfa/Documents/Atlas/docs/reviews/cuts/2026-08-03-add7bc6-idx-c1-readonly-consistency-review.md)

Git mostró warnings persistentes de acceso a `C:\Users\delfa/.config/git/ignore`, pero los comandos finalizaron.

### Codebase Memory

Usado para buscar/trazar `ChromaReadStatus`, `_ChromaReadAccess`, `_collection`, `_abrir_coleccion_existente`, `ConsistencyReport` y serialización/logging.

Resultado: el grafo está desactualizado. Todavía reporta `ChromaReadAccess`, `_sanitizar_error` y nombres viejos de tests. Lo registré como limitación informativa y usé fuente actual + búsquedas directas como autoridad.

### Verificación del contrato

`ChromaReadStatus`:

- Es `@dataclass(frozen=True)`.
- Contiene exclusivamente:
  - `root_present`
  - `collection_present`
  - `unavailable`
  - `error_code`
  - `error_type`
  - `error`
- No contiene `collection`.
- Los errores se normalizan por allowlist:
  - códigos en `IDX_PUBLIC_ERROR_MESSAGES`;
  - tipos en `IDX_SAFE_ERROR_TYPES`;
  - texto crudo en `error=` se transforma en `raw_chroma_error_rejected`;
  - tipos desconocidos caen a `Exception`.

`_ChromaReadAccess`:

- No es dataclass.
- Usa `__slots__ = ("status", "_collection")`.
- Mantiene el handle únicamente en `_collection`.
- No tiene `__dict__`.
- `dataclasses.asdict(_ChromaReadAccess(...))` falla con `TypeError`, cubierto por test.

`core/index_consistency.py`:

- Consume estado seguro vía `acceso_chroma.status`.
- Consume el handle solo internamente vía `acceso_chroma._collection`.
- `ConsistencyReport(...)` no recibe el handle.
- `issues` y `path_error` se renderizan desde estructuras allowlisted, no desde `_collection`.
- No hay retorno público del handle desde `verificar_consistencia`.

### Búsquedas directas

Confirmado:

- Sin campo dataclass público `collection`.
- Sin símbolo `ChromaReadAccess` en los cuatro archivos auditados.
- Sin `vars()` sobre el adaptador.
- Sin `str(access._collection)` ni `repr(access._collection)`.
- Sin logging/serialización del handle.
- Sin inclusión de `_collection` en `ConsistencyReport`, `issues` o `path_error`.

Únicas coincidencias relevantes:

- `dataclasses.asdict(access)` y `getattr(access, "__dict__", None)` aparecen solo en [tests/test_vector_paths.py](C:/Users/delfa/Documents/Atlas/tests/test_vector_paths.py:818), para demostrar que el adaptador interno no es serializable/no tiene dict.

### Prueba adversarial

Cubierta por tests ejecutados:

- [tests/test_vector_paths.py](C:/Users/delfa/Documents/Atlas/tests/test_vector_paths.py:805) inyecta en `_collection`:
  - `SYNTHETIC_SECRET_TOKEN`
  - ruta privada sintética
  - `RAW_BACKEND_MESSAGE`
- Confirma que no aparecen en `dataclasses.asdict(ChromaReadStatus)`.
- Confirma que `dataclasses.asdict(_ChromaReadAccess(...))` falla por no ser dataclass.

También en [tests/test_index_consistency.py](C:/Users/delfa/Documents/Atlas/tests/test_index_consistency.py:838):

- Inyecta una colección fake con secreto/ruta/mensaje crudo en el handle.
- Verifica que no aparece en `dataclasses.asdict(ConsistencyReport)`, `issues` ni `path_error`.
- Verifica que la fake collection sigue siendo leída internamente.

### Regresiones

Confirmado:

- Raíz ausente, colección ausente, backend inaccesible y colección presente mantienen semántica por tests enfocados.
- Allowlists de errores siguen cerradas.
- Ningún texto crudo de excepciones llega a campos públicos en el contrato IDX-C1.
- OBS-04 intacto:
  - `ORPHAN_SAMPLE_LIMIT = 10`;
  - `orphan_sample = tuple(sorted(huérfanos)[:ORPHAN_SAMPLE_LIMIT])`;
  - `orphan_count = len(huérfanos)`;
  - sin purga ni escritura.

### Validación ejecutada

1. `.venv\Scripts\python.exe -m unittest tests.test_index_consistency tests.test_vector_paths -v`

- Primer intento sin elevación: exit code `1`, `Acceso denegado`.
- Reejecución elevada: exit code `0`.
- Tests: `54`.
- Failures: `0`.
- Errors: `0`.
- Skipped: `0`.
- `_FailedTest`: `0`.

2. `.venv\Scripts\python.exe -m unittest discover -s C:\Users\delfa\Documents\Atlas\tests -v`

- Exit code: `0`.
- Tests: `203`.
- Failures: `0`.
- Errors: `0`.
- Skipped: `1` por privilegio de symlink en Windows.
- `_FailedTest`: `0`.

3. `.venv\Scripts\python.exe -m compileall core/index_consistency.py core/vector_store.py tests/test_index_consistency.py tests/test_vector_paths.py`

- Exit code: `0`.

4. `git diff --check`

- Exit code: `0`.
- Sin errores de whitespace.
- Warnings de line endings LF→CRLF en archivos ya modificados.

5. `git status --short --untracked-files=all`

- Exit code: `0`.
- Estado final consistente con baseline esperado:
  - cambios de gobernanza preexistentes;
  - archivos IDX-C1;
  - reporte histórico sin rastrear.
- Warnings de acceso a git ignore global.

### Conclusión

La separación entre estado serializable (`ChromaReadStatus`) y handle interno (`_ChromaReadAccess._collection`) cierra el hallazgo sobre `ChromaReadAccess.collection` sin ampliar el contrato. El handle no cruza superficies públicas de IDX-C1, la prueba adversarial no filtra secretos/rutas/mensajes crudos, las allowlists y OBS-04 siguen verdes, y las suites obligatorias ejecutadas están verdes.
