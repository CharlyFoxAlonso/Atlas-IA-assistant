# Auditoría de corte — IDX-C2 contrato de escritor único

Fecha: 2026-08-04
Repositorio: Atlas
Rama: atlas-v4.1-incremental-indexing
Commit auditado: 4f2d7db
Gate: PASS WITH OBSERVATIONS

## Alcance de la auditoría

Esta auditoría revisó el corte IDX-C2 sobre el contrato de escritor único para indexación incremental. El contrato aplicable proviene de la SDD activa `docs/spec/atlas-v4.1-incremental-indexing-sdd.md`, especialmente:

- Sección 11: exclusividad de escritor, fail-fast, compatibilidad Windows sin primitivas POSIX-only y recuperación stale basada en evidencia de inactividad.
- Sección 11.2: publicación de `writer_state_known`, `writer_active` y `possibly_transient`.
- Sección 5, regla 9: degradación de estados nominales cuando el estado del escritor no es confiable o hay escritura activa.
- Sección 13: dependencia de IDX-C2 antes de los cortes de reparación y superficies de reparación.

También se consideró OBS-05 del reaudit IDX-C1, que dejaba la resolución del estado del escritor para IDX-C2.

## Base y diff auditado

- Baseline de implementación: rama `atlas-v4.1-incremental-indexing`, commit base `bde4a3c5da9c7ae7945807c05434017a3b71a4dd`.
- Commit auditado: `4f2d7db`.
- Working tree auditado: sin stage.
- Superficie auditada: `core/index_writer_lock.py`, `core/config.py`, `core/index_consistency.py`, `core/indexer.py`, `core/vector_store.py`, `core/system/paths.py`, `tests/test_index_writer_lock.py`, `tests/test_incremental_indexing.py`, `tests/test_index_consistency.py`, `tests/test_path_integration.py` y `tests/test_vector_paths.py`.
- Tamaño del corte auditado: 403 inserciones, 70 eliminaciones y 2 archivos nuevos, según el informe de auditoría fuente.

## Fuera de alcance verificado

La auditoría no identificó cambios en superficies excluidas del corte:

- `core/index_manifest.py`.
- CLI, UI y superficies operativas IDX-C4/IDX-C5.
- Purga de huérfanos.
- Cambios de dependencias o packaging.
- Datos reales de `memory/`, `vector_db/`, `.env` o logs.

## Evidencia ejecutada por la auditoría

| Comando o fuente | Resultado |
|---|---|
| `git status` y `git rev-parse HEAD` | Rama, HEAD y working tree auditado consistentes con el corte; nada staged. |
| `git diff --check` | Sin errores de whitespace; solo avisos LF/CRLF del entorno Windows. |
| `.venv\Scripts\python.exe -m unittest tests.test_index_writer_lock -v` | 12 tests OK, exit code 0. |
| `.venv\Scripts\python.exe -m unittest tests.test_incremental_indexing tests.test_index_consistency tests.test_path_integration tests.test_vector_paths` | 101 tests OK, 1 skip preexistente por symlink sin privilegio en Windows, exit code 0. |
| `.venv\Scripts\python.exe -m unittest discover -s tests` | 222 tests OK, 1 skip preexistente, exit code 0. |
| `.venv\Scripts\python.exe -m compileall core tests` | Sin errores. |
| Codebase Memory | Usado solo como apoyo para callers ya indexados en HEAD; el análisis material se confirmó contra fuente y tests actuales. |

## Criterios auditados

| Criterio | Resultado | Evidencia |
|---|---|---|
| Adquisición atómica del lock | PASS | `os.open` con `O_CREAT | O_EXCL | O_WRONLY`, modo `0o600`, metadata JSON con `flush` y `fsync`, y test real de competencia entre dos procesos. |
| Reentrancia por identidad exacta de `lock_path` resuelto | PASS | Contexto thread-local asociado a `Path.resolve()`: mismo path incrementa profundidad; path distinto falla con `lock_path_mismatch`. |
| Protección de escritores públicos | PASS | `indexar_archivo`, `eliminar_documento_indexado`, `sincronizar_indice`, `reconstruir_indice_completo`, `construir_indice`, `vector_store.agregar_documento` y `vector_store.eliminar_documento` quedan bajo el lock. |
| Recuperación stale | PASS | La recuperación ocurre solo ante `psutil.NoSuchProcess`, con segunda lectura y comparación de PID, create time y token antes de borrar; no depende del tiempo transcurrido. |
| Estados dudosos no recuperables | PASS | PID reutilizado, metadata corrupta o parcial, `AccessDenied`, `ZombieProcess` y estados ambiguos bloquean la recuperación automática. |
| Liberación solo por owner | PASS | `release()` compara identidad antes de eliminar el lock; test de no-owner conserva el archivo. |
| Liberación garantizada | PASS | El context manager libera en `finally` y restaura el contexto thread-local. |
| Integración IDX-C1 read-only | PASS | `inspect_index_writer_state()` inspecciona sin crear, borrar, recuperar ni loguear. Estados nominales solo degradan si el lock está activo o el estado es desconocido. |
| Prioridad de estados | PASS | `UNAVAILABLE` e `INCONSISTENT` conservan prioridad sobre la degradación por writer activo. |
| OBS-04 | PASS | Orden determinista de `orphan_sample` preservado. |
| Contrato `busy` | PASS | `STATUS_BUSY`, campos `busy` aditivos y mensajes allowlisted sin token, path, CWD, command line ni metadata cruda. `construir_indice` eleva `IndexWriterBusyError`. |
| Alcance | PASS | Diff restringido al lock, integración de writers, paths centralizados y tests del corte. |

## Hallazgos bloqueantes

Ninguno.

## Observaciones no bloqueantes

1. `sincronizar_indice` produce un `SyncResult` con `busy=True`, pero las superficies `!indexar sync` todavía pueden renderizarlo como una sincronización con contadores en cero. No invalida IDX-C2 porque el estado estructurado existe y la presentación pertenece a cortes posteriores, pero conviene tratarlo en IDX-C4/IDX-C5.

2. La SDD enumera explícitamente los casos post-IDX-C2 de escritor ausente y escritor activo. El caso de lock stale observado por `inspect_index_writer_state()` se publica como `writer_state_known=True`, `writer_active=False`, `possibly_transient=False`, coherente con "no hay escritor activo". No hay impacto funcional; puede precisarse en DOC-C6.

3. El grafo de Codebase Memory usado por la auditoría estaba indexado sobre HEAD anterior al working tree del corte, por lo que no contenía nodos nuevos de `index_writer_lock.py`. La auditoría mitigó esto confirmando contra fuente, grep y tests actuales.

4. No había Builder Report o plan IDX-C2 persistido en el repositorio. La auditoría reconstruyó el contrato desde la SDD activa y verificó con las suites ejecutadas.

## Áreas no verificadas

- Ejecución del lock en Linux o macOS. El contrato auditado exige Windows y la evidencia del corte se ejecutó con procesos reales en Windows.
- Chroma real y datos reales. La auditoría respetó la política de no tocar `memory/`, `vector_db/`, `.env` ni logs reales; los tests usan fakes y temporales.
- Renderizado final de busy en CLI/UI, diferido a superficies posteriores.

## Remediación mínima

No hay remediación requerida para aceptar el corte.

Acciones opcionales registradas:

- Renderizar explícitamente `busy` en CLI/UI durante IDX-C4 o IDX-C5.
- Precisar el caso stale de `inspect_index_writer_state()` en DOC-C6.
- Refrescar Codebase Memory después de integrar el corte.

## Gate final

PASS WITH OBSERVATIONS

IDX-C2 cumple el contrato de escritor único de la SDD: adquisición atómica, reentrancia por identidad exacta, fail-fast, protección de escritores, recuperación stale conservadora, rechazo de estados ambiguos, liberación por owner, integración read-only con IDX-C1, contratos `busy` públicos y preservación de OBS-04. Las observaciones registradas son no bloqueantes y corresponden a presentación futura, precisión documental o tooling auxiliar.
