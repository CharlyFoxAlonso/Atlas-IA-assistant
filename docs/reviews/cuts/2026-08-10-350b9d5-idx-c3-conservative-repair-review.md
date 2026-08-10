# Auditoría de corte — IDX-C3 reparación conservadora

Fecha: 2026-08-10
Repositorio: Atlas
Rama: atlas-v4.1-incremental-indexing
Baseline auditado: 350b9d56a477beb6b147d05b4707de279b511281
Gate: PASS WITH OBSERVATIONS

## Contrato, base y diff auditado

- **Contrato**: Plan IDX-C3 (reparación conservadora del índice) aprobado por Plan Reviewer con veredicto `APPROVED`, sin condiciones ni hallazgos. Gobernanza Workflow 2.0/2.1; SDD activa `docs/spec/atlas-v4.1-incremental-indexing-sdd.md` (§8 contrato de reparación, §9 huérfanos, §11.2 writer-state/lock).
- **Base**: rama `atlas-v4.1-incremental-indexing`, HEAD `350b9d56a477beb6b147d05b4707de279b511281` (sin commits nuevos; sin stage/commit/push — correcto).
- **Diff auditado** (working tree, coincide con el Builder Report):
  - ` M core/index_consistency.py` — refactor: +86/−23 (`_ConsistencySnapshot`, `_capturar_snapshot_consistencia`, `_clasificar_fuente` → `Optional[str]`).
  - `?? core/index_repair.py` — nuevo, 713 líneas (`RepairItem`, `RepairReport`, `reparar_indice` + helpers).
  - `?? tests/test_index_repair.py` — nuevo, 779 líneas (matriz completa + regresión metadata-stale).

## Alcance y exclusiones

- **In scope**: `core/index_consistency.py` (modificado, refactor), `core/index_repair.py` (nuevo), `tests/test_index_repair.py` (nuevo). `tests/test_index_consistency.py` quedó autorizado por el plan pero sin cambios finales: Git confirma que no aparece en el diff.
- **Excluded (verificado intacto)**: `core/indexer.py`, `core/vector_store.py`, `core/index_manifest.py`, `core/config.py`, `core/system/**`, `core/index_writer_lock.py`, Doctor, Healer, CLI, UI, API, SDD, docs, dependencias.

## Evidencia inspeccionada y comandos ejecutados

- Lectura completa de `core/index_repair.py` (713 líneas), `tests/test_index_repair.py` (779 líneas), diff de `core/index_consistency.py`, `core/index_writer_lock.py`, `core/indexer.py`, `core/index_manifest.py`, `core/vector_store.py`, SDD §8/§9/§11.
- `git status` → coincide con el reporte del Builder: 3 archivos con cambios reales en el diff (`core/index_consistency.py` modificado, `core/index_repair.py` y `tests/test_index_repair.py` nuevos), sin stage. `tests/test_index_consistency.py` autorizado por el plan pero sin cambios finales.
- `git show HEAD:core/index_consistency.py` → firma de `verificar_consistencia(memoria_base, manifest_path, chroma_path, collection_name, lock_path) -> ConsistencyReport` **idéntica** a HEAD.
- `IndexManifest.get` (línea 175), `remove` (línea 181), `save` (línea 148) confirmados en `core/index_manifest.py`.
- Suites ejecutadas (todas reproducidas por el Auditor):
  - `python -m unittest tests.test_index_repair tests.test_index_consistency -v` → **Ran 63 tests, OK**.
  - `python -m unittest tests.test_incremental_indexing tests.test_index_writer_lock tests.test_path_integration tests.test_vector_paths -v` → **Ran 75 tests, OK (1 skipped)**.
  - `python -m unittest discover -s tests -v` → **Ran 247 tests, OK (1 skipped)**.
  - `python -m compileall core tests` → **exit 0**.
  - `git diff --check` → **exit 0**.
  - Único skip: creación de symlinks sin privilegios en Windows (`WinError 1314`), preexistente y fuera de alcance.

## Criterios de aceptación

| Criterio | Resultado | Evidencia |
|---|---|---|
| `core/index_repair.py` nuevo con solo `RepairItem`, `RepairReport`, `reparar_indice` | PASS | Módulo de 713 líneas; helpers internos con prefijo `_`; sin símbolos públicos extra |
| `core/index_consistency.py` refactor con `_ConsistencySnapshot`, `_capturar_snapshot_consistencia`, `_clasificar_fuente_por_documento` | PASS | Diff +86/−23; snapshot frozen; clasificación devuelve `Optional[str]` |
| `verificar_consistencia()` API pública sin cambios | PASS | Firma y tipo de retorno idénticos a HEAD |
| `tests/test_index_repair.py` nuevo | PASS | 779 líneas nuevas; `test_index_consistency.py` autorizado por el plan pero sin cambios finales en el diff |
| Archivos prohibidos intactos | PASS | `git status` y diff limitados a los 4 archivos autorizados (`core/index_consistency.py` modificado, `core/index_repair.py` y `tests/test_index_repair.py` nuevos) |
| Categorías reparables: `source_and_manifest_present_chroma_absent`, `source_present_manifest_stale_chroma_present`, `source_present_manifest_absent_chroma_present`, `source_present_manifest_absent_chroma_absent`, `manifest_absent`, `chroma_absent`, `chroma_collection_absent`, `manifest_and_chroma_empty_sources_present` | PASS | `_REINDEX_CATEGORIES` (líneas 67-78 de `core/index_repair.py`, verificadas contra `DivergenceCategory` en `core/index_consistency.py`); `_METADATA_STALE_CATEGORY` para `source_present_manifest_metadata_stale_content_same`; tests por categoría |
| Fix metadata-stale: manifiesto vivo primero, validación `stat → SHA-256 → stat`, derivación a `indexar_archivo` si cambió, nunca guardar contra SHA anterior | PASS | `_reparar_metadata_stale()` línea 250; regresión `test_metadata_stale_cambio_durante_carga_reindexa_sin_guardar` línea 200: `save` no llamado, `indexar` una vez, `action="reindex"`, categoría `SOURCE_PRESENT_MANIFEST_STALE_CHROMA_PRESENT` |
| Diagnóstico bloqueado (sin escrituras): path_error, manifest_corrupt, manifest_schema_incompatible, chroma_unavailable, DEGRADED, UNAVAILABLE, entradas malformadas, verification_limitation, fallo de lectura de colección → `blocked=True`, razón allowlisted, cero items inventados, liberar lock, post-check, `success=False` | PASS | `_blocked_reason()`; `_ALLOWED_BLOCKED_REASONS` (10 entradas); tests de bloqueo sin escrituras |
| Excepción `own_writer_degraded`: HEALTHY/HEALTHY_EMPTY + published DEGRADED + writer_state_known + writer_active → lock propio, no bloquea | PASS | Lógica verificada en `_blocked_reason()`; lock reentrante (`_IndexWriterLockContext`) |
| Post-check siempre fuera del lock; busy único camino con `post_check_performed=False` | PASS | Estructura `with acquire_index_writer_lock(...)`; `except IndexWriterBusyError` retorna sin post-check |
| `RepairReport.__post_init__`: `success=True` solo con post_check_performed + post_state HEALTHY/HEALTHY_EMPTY + no blocked + no busy + sin items `failed`/`still_inconsistent` | PASS | Validación verificada; `busy_message` contra `PUBLIC_BUSY_MESSAGES.values()` |
| Confirmación por identidad desde el mismo snapshot | PASS | `_confirm_items_from_snapshot`: fuente presente → repaired/still_inconsistent; sin fuente + manifest → `source_absent_manifest_present`; sin fuente + chunks → `source_absent_chroma_present`; sin nada → repaired; `cannot_confirm` → todos `still_inconsistent` |
| Sin errores crudos en `core/index_repair.py` | PASS | Sin `str(exc)`, `repr(exc)`, `f"{exc}"`, `sys.exc_info`, `traceback`, `format_exc` (matches en `core/system/*` preexistentes y fuera de alcance) |
| `IndexManifest.get/remove/save` existen | PASS | Líneas 175/181/148 de `core/index_manifest.py` |
| Huérfanos nunca se purgan (OBS-04) | PASS | `_report_orphans` → `action="skip"`, `status="skipped"`, muestra limitada a 10, `orphan_count` total |
| Suites verdes | PASS | 63/75/247 OK, compileall exit 0, diff --check exit 0 |

## Hallazgos bloqueantes

Ninguno.

## Hallazgos no bloqueantes

1. **`writer_target_mismatch` y `degraded_diagnosis` amplían la lista de razones de bloqueo del plan aprobado.** El plan enumeraba explícitamente las razones de bloqueo; la implementación añade `writer_target_mismatch` (bloqueo cuando los destinos de escritura no coinciden con los defaults de config) y el mapeo DEGRADED→`degraded_diagnosis`. Es conservador (bloquea sin escribir), está cubierto por tests (`test_target_de_escritura_incoherente_bloquea_sin_escrituras`) y no cambia ningún contrato público. Recomendación opcional: documentar ambas razones en SDD §8 para trazabilidad.
2. **El claim histórico "regresión antes de corregir: exit 1; 1 test, 1 failure" no es reproducible ahora** (el fix ya está aplicado en el working tree). No es un defecto: el test de regresión existe y pasa, y el claim es consistente con el estado actual.

## Áreas no verificadas y cheques de dispositivo/manuales

- No se ejecutó integración con ChromaDB real ni Ollama (los tests usan `_FakeCollection`/mocks) — consistente con la política de testing (sin proveedores reales ni red no controlada).
- No se validó instalación en PC limpio ni portabilidad de paquete — fuera del alcance del corte.
- El skip de symlinks en Windows es preexistente y no relacionado con este corte.

## Remediación mínima

- Ninguna requerida. Opcional: añadir `writer_target_mismatch` y `degraded_diagnosis` a la lista de razones de bloqueo documentadas en SDD §8.

## Veredicto

`PASS WITH OBSERVATIONS`

El corte IDX-C3 cumple el contrato aprobado en todos los criterios, con evidencia reproducida (63/75/247 tests OK, compileall y diff --check exit 0), API pública de IDX-C1 intacta, fix de metadata-stale correctamente implementado y cubierto por regresión, y sin hallazgos bloqueantes. Las dos observaciones son no bloqueantes y no requieren corrección para aceptar el corte.