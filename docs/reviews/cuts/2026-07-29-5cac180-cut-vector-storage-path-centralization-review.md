# Auditoría técnica de corte — fix(paths): centralize and protect vector storage paths

Fecha: 2026-07-29
Tipo: Corte
Repositorio: C:\Users\delfa\Documents\Atlas
Rama: atlas-v4.1-incremental-indexing
Commit base: 004961a06195d907ab8640193f548fb0894baec2
Commit final: 5cac180e2a784fca59b8d64f778fe2104c3a9913
Rango auditado: 004961a..5cac180
Archivo: docs/reviews/cuts/2026-07-29-5cac180-cut-vector-storage-path-centralization-review.md
Gate: ACCEPT

## 1. Resumen ejecutivo

El commit `5cac180` centraliza la ruta de almacenamiento vectorial de Atlas en `core.system.paths`, elimina la definición duplicada en `core/vector_store.py`, protege contra división silenciosa entre legacy y configurado mediante `validate_vector_store_path`, actualiza el script de backup para usar la fuente autoritativa con raíz ZIP estable, y añade tests exhaustivos que cubren los 5 casos legacy, CWD-independencia, override `ATLAS_DATA_DIR`, lazy initialization y aislamiento de backup. La suite completa pasa (133 passed, 1 skipped). No se observaron modificaciones en los datos protegidos durante la validación. El contenido real de esos recursos no fue abierto por el auditor. No se realizó push.

## 2. Objetivo

Centralizar y proteger las rutas de almacenamiento vectorial de Atlas: `CHROMA_PATH`, `vector_db`, persistencia Chroma y sus consumidores verificados.

## 3. Alcance

- `core/system/paths.py`
- `core/config.py`
- `core/vector_store.py`
- `scripts/backup_atlas.py`
- `tests/test_vector_paths.py` (nuevo)
- `tests/test_backup_paths.py` (nuevo)
- `tests/test_path_integration.py` (extendido)
- `docs/ARCHITECTURE.md`
- `docs/architecture/incremental-indexing.md`

## 4. Fuera de alcance

- Algoritmos de chunking, modelos de embedding, esquemas de colección
- Semántica de indexación incremental, comportamiento de crawler/ingestión
- Rediseño UI, routing de proveedores, arquitectura de logger
- Dependencias, empaquetado, Xilas, Frontier
- Migración automática de `vector_db` legacy

## 5. Estado Git

- **Rama**: `atlas-v4.1-incremental-indexing`
- **HEAD**: `5cac180e2a784fca59b8d64f778fe2104c3a9913`
- **Working tree**: limpio
- **Tracking**: `origin/atlas-v4.1-incremental-indexing: ahead 1` (no push)
- **Commit base**: `004961a06195d907ab8640193f548fb0894baec2`
- **Commit final**: `5cac180e2a784fca59b8d64f778fe2104c3a9913`
- **Rango auditado**: `004961a..5cac180` (1 commit)

## 6. Instrucciones aplicables

- `AGENTS.md` (secciones 1, 4, 6, 9, 10)
- `.agents/policies/git-safety.md`
- `.agents/policies/testing.md`
- `.agents/playbooks/audit.md`

## 7. Entorno reproducido

- Python: `.venv\Scripts\python.exe`
- SO: Windows (win32)
- Working directory: `C:\Users\delfa\Documents\Atlas`

## 8. Diff inspeccionado

### `core/config.py`
- `CHROMA_PATH = str(_ATLAS_PATHS.chroma_dir)` (antes: `"./vector_db"`)
- `INDEX_MANIFEST_PATH = str(_ATLAS_PATHS.chroma_dir / "index_manifest.json")` (antes: `os.path.join(CHROMA_PATH, ...)`)

### `core/system/paths.py`
- Nueva excepción `LegacyVectorStoreError`
- Nueva función `validate_vector_store_path(configured_path, legacy_path=None)` — valida que la ruta configurada sea la autoritativa; lanza error si existe solo legacy y la configurada no existe; permite cuando ambas existen (configurada gana) o ninguna existe (configurada se crea).

### `core/vector_store.py`
- Elimina definiciones locales `CHROMA_PATH = "./vector_db"` y `COLLECTION_NAME = "atlas_rag"`
- Importa desde `core.config`: `from core.config import CHROMA_PATH, COLLECTION_NAME`
- Importa `validate_vector_store_path` de `core.system.paths`
- En `_get_collection()`: `resolved_chroma_path = str(validate_vector_store_path(CHROMA_PATH))` antes de crear `PersistentClient`
- Mensajes de error y backup usan `resolved_chroma_path`

### `scripts/backup_atlas.py`
- Nueva función `_authoritative_vector_source()` que llama `validate_vector_store_path(CHROMA_PATH)`
- `carpetas_backup` ahora usa tuplas `(source, archive_root)` para separar fuente real de ruta en ZIP
- Vector DB se archiva bajo `vector_db/` en el ZIP (sin ruta absoluta de máquina)
- Importa `core.config` y `core.system.paths` solo al ejecutar backup, no al importar

### Tests nuevos
- `tests/test_vector_paths.py`: 8 tests — política de rutas (4), configuración vectorial (4)
- `tests/test_backup_paths.py`: 4 tests — backup usa fuente configurada, raíz ZIP estable, cuando existen la ruta configurada y una ruta legacy diferente la ruta configurada gana, legacy-only detiene sin archivo ni migración
- `tests/test_path_integration.py`: extendido con aserciones para `CHROMA_PATH` e `INDEX_MANIFEST_PATH` absolutos y consistentes

### Documentación
- `docs/ARCHITECTURE.md`: actualiza descripción de Vector DB
- `docs/architecture/incremental-indexing.md`: documenta política de rutas, manifiesto, detección legacy, backup

## 9. Criterios de aceptación

| # | Criterio | Resultado | Evidencia |
|---|---|---|---|
| 1 | Exactamente 9 archivos cambiados | PASS | `git diff --stat` → 9 archivos |
| 2 | Vector storage tiene una política de rutas autoritativa | PASS | `core/system/paths.py` define `chroma_dir` y `validate_vector_store_path`; `core/config.py` deriva de ahí; `core/vector_store.py` valida antes de usar |
| 3 | `CHROMA_PATH` permanece `str` público | PASS | `core/config.py:190` → `str(_ATLAS_PATHS.chroma_dir)`; tests verifican tipo `str` |
| 4 | Manifiesto y Chroma comparten raíz autoritativa | PASS | `INDEX_MANIFEST_PATH = str(_ATLAS_PATHS.chroma_dir / "index_manifest.json")`; test verifica `Path(INDEX_MANIFEST_PATH).parent == Path(CHROMA_PATH)` |
| 5 | Aliases de vector-store permanecen compatibles | PASS | `core/vector_store.py` importa `CHROMA_PATH`, `COLLECTION_NAME` desde `core.config`; tests verifican igualdad |
| 6 | No quedan definiciones independientes | PASS | `git grep` en `core/vector_store.py` no encuentra asignaciones locales |
| 7 | Inicialización Chroma permanece lazy | PASS | `PersistentClient` creado dentro de `_get_collection()` solo al primer uso; tests confirman `chromadb` no importado al importar `core.vector_store` |
| 8 | No se introdujo ciclo de importación | PASS | `core/config.py` → `core.system.paths`; `core/vector_store.py` → `core.config` + `core.system.paths`; `core/system/paths.py` no importa `core.config` ni `core/vector_store` |
| 9 | Los 5 casos legacy se comportan según especificación | PASS | `test_vector_paths.py::VectorPathPolicyTests` cubre: mismo path, configurado existe, ninguno existe, solo legacy (error), ambos existen (configurado gana) |
| 10 | Detección legacy ocurre antes de construir Chroma | PASS | `test_legacy_only_detection_precedes_chroma_construction` verifica `PersistentClient` nunca llamado cuando solo existe legacy |
| 11 | No hay migración/movimiento/borrado automático | PASS | `validate_vector_store_path` lanza `LegacyVectorStoreError` sin tocar FS; backup detiene sin crear ZIP; tests verifican que legacy permanece intacto |
| 12 | Backup usa fuente configurada | PASS | `test_backup_paths.py::test_backup_uses_configured_source_and_stable_vector_zip_root` |
| 13 | Miembros ZIP nunca exponen ruta absoluta de máquina | PASS | `test_backup_paths.py` verifica `absolute_member=False`, `source_name_exposed=False` |
| 14 | Backup funciona bajo `cp1252` | PASS | Test fuerza `PYTHONIOENCODING=cp1252` y verifica `stdout_encoding` |
| 15 | Documentación coincide con comportamiento implementado | PASS | `docs/ARCHITECTURE.md` y `docs/architecture/incremental-indexing.md` actualizados y consistentes con código |
| 16 | Suite: 134 ejecutados, 133 passed, 1 skipped | PASS | `unittest discover` → 134 tests, 1 skipped (symlink), 0 failures |
| 17 | No se observaron modificaciones en los datos protegidos durante la validación | PASS | Los tests inspeccionados usan TemporaryDirectory, mocks y dotenv falso. El contenido real de .env, memory/, vector_db/ y atlas_security.log no fue abierto por el auditor. |
| 18 | No se realizó push | PASS | `git branch -vv` muestra `ahead 1` |

## 10. Evidencia reproducida

### Tests enfocados
```text
.venv\Scripts\python.exe -m unittest tests.test_vector_paths -v
Result: OK (8 tests, 0 failures, 0 errors)

.venv\Scripts\python.exe -m unittest tests.test_backup_paths -v
Result: OK (4 tests, 0 failures, 0 errors)

.venv\Scripts\python.exe -m unittest tests.test_path_integration -v
Result: OK (5 tests, 0 failures, 0 errors)

.venv\Scripts\python.exe -m unittest tests.test_incremental_indexing -v
Result: OK (35 tests ejecutados: 34 passed, 1 skipped, 0 failures y 0 errors)

.venv\Scripts\python.exe -m unittest tests.test_system_foundations -v
Result: OK (18 tests)

.venv\Scripts\python.exe -m unittest tests.test_security_paths -v
Result: OK (7 tests)
```

### Suite completa
```text
.venv\Scripts\python.exe -m unittest discover -s tests -v
Result: OK (134 tests ejecutados: 133 passed, 1 skipped, 0 failures, 0 errors, 0 _FailedTest)
```

### Compilación
```text
.venv\Scripts\python.exe -m compileall core scripts tests
Result: OK (no syntax errors)
```

### Git checks
```text
git diff --check 004961a..5cac180 → sin errores de whitespace
git status --short --untracked-files=all → limpio
git branch -vv → ahead 1, no push
```

### Verificación de definiciones independientes
```text
git grep -n -E '^(CHROMA_PATH|COLLECTION_NAME)[[:space:]]*=' -- core/vector_store.py → vacío (CONFIRMED)
```

## 11. Claims confirmados

| # | Claim | Evidencia |
|---|-------|-----------|
| 1 | Exactamente 9 archivos cambiados | `git diff --stat` → 9 archivos |
| 2 | Vector storage tiene una política de rutas autoritativa | `core/system/paths.py` define `chroma_dir` y `validate_vector_store_path`; `core/config.py` deriva de ahí; `core/vector_store.py` valida antes de usar |
| 3 | `CHROMA_PATH` permanece `str` público | `core/config.py:190` → `str(_ATLAS_PATHS.chroma_dir)`; tests verifican tipo `str` |
| 4 | Manifiesto y Chroma comparten raíz autoritativa | `INDEX_MANIFEST_PATH = str(_ATLAS_PATHS.chroma_dir / "index_manifest.json")`; test verifica `Path(INDEX_MANIFEST_PATH).parent == Path(CHROMA_PATH)` |
| 5 | Aliases de vector-store permanecen compatibles | `core/vector_store.py` importa `CHROMA_PATH`, `COLLECTION_NAME` desde `core.config`; tests verifican igualdad |
| 6 | No quedan definiciones independientes | `git grep` en `core/vector_store.py` no encuentra asignaciones locales |
| 7 | Inicialización Chroma permanece lazy | `PersistentClient` creado dentro de `_get_collection()` solo al primer uso; tests confirman `chromadb` no importado al importar `core.vector_store` |
| 8 | No se introdujo ciclo de importación | `core/config.py` → `core.system.paths`; `core/vector_store.py` → `core.config` + `core.system.paths`; `core/system/paths.py` no importa `core.config` ni `core/vector_store` |
| 9 | Los 5 casos legacy se comportan según especificación | `test_vector_paths.py::VectorPathPolicyTests` cubre: mismo path, configurado existe, ninguno existe, solo legacy (error), ambos existen (configurado gana) |
| 10 | Detección legacy ocurre antes de construir Chroma | `test_legacy_only_detection_precedes_chroma_construction` verifica `PersistentClient` nunca llamado cuando solo existe legacy |
| 11 | No hay migración/movimiento/borrado automático | `validate_vector_store_path` lanza `LegacyVectorStoreError` sin tocar FS; backup detiene sin crear ZIP; tests verifican que legacy permanece intacto |
| 12 | Backup usa fuente configurada | `test_backup_paths.py::test_backup_uses_configured_source_and_stable_vector_zip_root` |
| 13 | Miembros ZIP nunca exponen ruta absoluta de máquina | `test_backup_paths.py` verifica `absolute_member=False`, `source_name_exposed=False` |
| 14 | Backup funciona bajo `cp1252` | Test fuerza `PYTHONIOENCODING=cp1252` y verifica `stdout_encoding` |
| 15 | Documentación coincide con comportamiento implementado | `docs/ARCHITECTURE.md` y `docs/architecture/incremental-indexing.md` actualizados y consistentes con código |
| 16 | Suite: 134 ejecutados, 133 passed, 1 skipped | `unittest discover` → 134 tests, 1 skipped (symlink), 0 failures |
| 17 | No se observaron modificaciones en los datos protegidos durante la validación. Los tests inspeccionados usan TemporaryDirectory, mocks y dotenv falso. El contenido real de .env, memory/, vector_db/ y atlas_security.log no fue abierto por el auditor. | Tests usan `TemporaryDirectory`, mocks, `fake_dotenv`; `git status --ignored` sin cambios en `memory/`, `vector_db/`, `.env` |
| 18 | No se realizó push | `git branch -vv` muestra `ahead 1` |

## 12. Reglas de protección legacy implementadas

- **configured-only**: usa la ruta configurada;
- **configured + legacy diferente**: usa la configurada;
- **legacy-only**: detiene antes de construir Chroma;
- **neither**: permite creación lazy en la configurada;
- **same resolved path**: continúa normalmente;
- **no existe migración automática**.

## 13. Hallazgos

### BLOCKER
Ninguno.

### HIGH
Ninguno.

### MEDIUM
Ninguno.

### LOW
Ninguno.

## 14. Falsos positivos descartados
Ninguno.

## 15. Cambios obligatorios
Ninguno.

## 16. Seguimientos no bloqueantes
Ninguno.

## 17. Estado final del working tree
- Branch: `atlas-v4.1-incremental-indexing`
- HEAD: `5cac180e2a784fca59b8d64f778fe2104c3a9913`
- Working tree: limpio
- Untracked files: ninguno
- Staged changes: ninguno
- Push: no realizado

## 18. Gate
**ACCEPT**

El commit centraliza correctamente la ruta vectorial en `core.system.paths`, elimina la definición duplicada en `core/vector_store.py`, protege contra división silenciosa entre legacy y configurado mediante `validate_vector_store_path`, actualiza el backup para usar la fuente autoritativa con raíz ZIP estable, y añade tests exhaustivos que cubren los 5 casos legacy, CWD-independencia, override `ATLAS_DATA_DIR`, lazy initialization, y aislamiento de backup. La suite completa pasa (133 passed, 1 skipped). No se observaron modificaciones en los datos protegidos durante la auditoría, y el auditor no abrió su contenido real. No se hizo push.