# Auditoría técnica de corte — Integración inicial de rutas

- **Tipo**: `cut`
- **Fecha**: 2026-07-25
- **Repositorio**: `C:\Users\delfa\Documents\Atlas`
- **Rama**: `atlas-v4.1-incremental-indexing`
- **Commit base**: `10812cb079c3ad5a632a6c38d07c142943fc27ce`
- **Commit final**: `e45727731f6ad328ef108ba0cd455dbd50390234`
- **Rango auditado**: `10812cb..e457277`
- **Auditor**: agente de auditoría de corte (opencode)

---

## A. Modo

AUDITORÍA DE CORTE

## B. Veredicto

ACCEPT

## C. Objetivo

Conectar las constantes `BASE_MEMORIA`, `BASE_ESTUDIO` y `BASE_PROMPTS` de `core/config.py` con la política central de rutas definida en `core/system/paths.py`, conservándolas como `str`, resolviéndolas mediante una única llamada a `get_paths()` durante el import, respetando `ATLAS_DATA_DIR` cuando se configura antes del import, preservando el layout lógico de desarrollo, sin fallback silencioso, sin modificar ChromaDB, sin mover ni crear datos reales, y sin ampliar el alcance a otros módulos.

## D. Alcance

- `core/config.py` — modificación de las tres constantes y agregado del import de `get_paths`.
- `tests/test_path_integration.py` — archivo nuevo (165 líneas, 5 tests).
- Inspección de consumidores directos: `core/brain.py`, `core/indexer.py`, `core/web_crawler.py`, `core/security.py`.
- Inspección de entry points: `atlas_chat.py`, `atlas_ui.py`, `main_api.py`, `core/exam_mode.py`.
- Verificación de ausencia de ciclos de importación entre `core.config` y `core.system.paths`.
- Ejecución de suites relacionadas y variantes de orden.
- Consulta al grafo de Codebase Memory (no disponible).

## E. Fuera de alcance

- `core/security.py`, `core/vector_store.py`, `core/web_crawler.py` (no modificados por el diff).
- `core/system/paths.py` (no modificado por el diff).
- `CHROMA_PATH` y demás constantes de `core/config.py`.
- Datos reales en `memory/`, `vector_db/`, `.env`.
- Reporte preexistente `docs/reviews/general/2026-07-25-10812cb-general-codebase-audit.md`.

## F. Estado Git

- Rama activa: `atlas-v4.1-incremental-indexing`
- HEAD: `e45727731f6ad328ef108ba0cd455dbd50390234`
- Tracking remoto: `origin/atlas-v4.1-incremental-indexing` (ahead 1 — commit local sin push)
- Sin cambios rastreados pendientes; permanece un reporte preexistente no rastreado y fuera del corte.

## G. Commit base

`10812cb079c3ad5a632a6c38d07c142943fc27ce` — `docs(review): add Atlas portability audit`

## H. Commit final

`e45727731f6ad328ef108ba0cd455dbd50390234` — `fix(paths): connect core config to centralized Atlas paths`

## I. Rango auditado

`10812cb079c3ad5a632a6c38d07c142943fc27ce..e45727731f6ad328ef108ba0cd455dbd50390234`

Commits en el rango: 1 (solo el commit final).
Parent verificado: `git rev-parse e457277^` = `10812cb` ✅

## J. Instrucciones aplicables

- `AGENTS.md` en el repositorio: no se encontró ningún `AGENTS.md` (búsqueda recursiva sin resultados).
- `.opencode/project-identity.md`: leído. Establece principios (local-first, modularidad, dry-run por defecto, type hints en `core/system/`). El corte respeta estos principios.
- No se encontraron instrucciones específicas bajo `core/` o `tests/`.

## K. Entorno reproducido

- Intérprete: `.venv\Scripts\python.exe`
- Versión: Python 3.13.14
- SO: Windows (win32)
- Directorio de trabajo: `C:\Users\delfa\Documents\Atlas`

## L. Diff inspeccionado

`git diff --name-status` confirma exactamente dos archivos:

```
M       core/config.py
A       tests/test_path_integration.py
```

`git diff --check` no reporta problemas de espacios.

### L.1 `core/config.py`

```diff
+from core.system.paths import get_paths
...
-BASE_MEMORIA = "memory/Atlas_Memory"
-BASE_ESTUDIO = "memory/Atlas_Memory/03_Conocimiento"
-BASE_PROMPTS = "memory/Atlas_Memory/00_Sistema/Prompts"
+_ATLAS_PATHS = get_paths()
+BASE_MEMORIA = str(_ATLAS_PATHS.private_memory_dir)
+BASE_ESTUDIO = str(_ATLAS_PATHS.private_memory_dir / "03_Conocimiento")
+BASE_PROMPTS = str(_ATLAS_PATHS.private_memory_dir / "00_Sistema" / "Prompts")
 CHROMA_PATH = "./vector_db"
```

Verificaciones:

| Aspecto | Resultado |
|---|---|
| Import exacto | `from core.system.paths import get_paths` (línea 23) |
| Llamadas a `get_paths()` durante import | Una sola (línea 186) |
| Propiedad usada para memoria | `private_memory_dir` |
| Derivación de estudio | `private_memory_dir / "03_Conocimiento"` |
| Derivación de prompts | `private_memory_dir / "00_Sistema" / "Prompts"` |
| Tipo resultante | `str(...)` aplicado a cada constante |
| `try/except` alrededor de `get_paths()` | Ausente |
| Fallback relativo | Ausente |
| `CHROMA_PATH` modificado | No (`"./vector_db"` intacto) |
| Otras modificaciones funcionales | Ninguna |

### L.2 `tests/test_path_integration.py`

Archivo nuevo de 165 líneas. Contiene:

- **Context manager `isolated_config_import`** (42 líneas): guarda y restaura `os.environ`, `Path.cwd()`, `sys.modules["core.config"]`, `sys.modules["dotenv"]`, y el atributo `core.config` del paquete `core`. Inyecta un `dotenv` falso cuyo `load_dotenv` retorna `False` sin leer archivos.

- **5 tests**:

| Test | Lo que verifica |
|---|---|
| `test_environment_mapping_respects_temporary_data_override` | `ATLAS_DATA_DIR` se respeta; `get_paths` no crea directorios |
| `test_successive_calls_reflect_environment_changes_without_cache` | Dos llamadas consecutivas con distinto `ATLAS_DATA_DIR` devuelven `data_dir` distintos |
| `test_development_layout_is_preserved_independent_of_cwd` | Cambia CWD a temporal; `private_memory_dir` sigue siendo `project_root / "memory" / "Atlas_Memory"` |
| `test_config_constants_are_captured_at_import_time` | Importa `core.config` con `ATLAS_DATA_DIR=initial`, captura las constantes, luego cambia el entorno y verifica que las constantes no se recalculan |
| `test_isolated_config_import_uses_central_path_policy` | Importa `core.config` aislado y compara contra `get_paths` calculado independientemente |

## M. Evidencia reproducida

### M.1 Test específico

| Comando | `.venv\Scripts\python.exe -m unittest tests.test_path_integration -v` |
|---|---|
| Resultado | Ran 5 tests in 0.029s — OK |
| Failures | 0 |
| Errors | 0 |
| Skipped | 0 |

### M.2 Suites relacionadas (52 tests)

| Comando | `.venv\Scripts\python.exe -m unittest tests.test_system_foundations tests.test_system_cli tests.test_launcher tests.test_healer tests.test_operational_log tests.test_configuration_hygiene -v` |
|---|---|
| Resultado | Ran 52 tests in 1.280s — OK |
| Failures | 0 |
| Errors | 0 |
| Skipped | 0 |

### M.3 Orden alternativo (8 ejecuciones acumuladas)

**Variante A — path_integration → configuration_hygiene:**

| Comando | `.venv\Scripts\python.exe -m unittest tests.test_path_integration tests.test_configuration_hygiene -v` |
|---|---|
| Resultado | Ran 8 tests in 0.578s — OK |
| Failures/Errors | 0 |

**Variante B — configuration_hygiene → path_integration:**

| Comando | `.venv\Scripts\python.exe -m unittest tests.test_configuration_hygiene tests.test_path_integration -v` |
|---|---|
| Resultado | Ran 8 tests in 0.581s — OK |
| Failures/Errors | 0 |

### M.4 Compilación

| Comando | `.venv\Scripts\python.exe -m compileall core tests` |
|---|---|
| Resultado | Sin errores |

### M.5 Working tree post-tests

```
?? docs/reviews/general/2026-07-25-10812cb-general-codebase-audit.md
```

Sin cambios rastreados pendientes. No se crearon archivos en `memory/`, `vector_db/` ni `.env`.

### M.6 Resumen de ejecuciones

| Conjunto | Tests ejecutados | Acumulado | Resultado |
|---|---|---|---|
| Test específico | 5 | 5 | OK |
| 6 suites relacionadas | 52 | 57 | OK |
| Variante A | 8 (5 repetidos + 3) | 65 | OK |
| Variante B | 8 (5 repetidos + 3) | 73 | OK |
| Compileall | — | — | Sin errores |

Los 8 tests de las variantes de orden incluyen casos repetidos respecto al test específico y a la ejecución cruzada. No se trata de 73 tests únicos sino de 73 ejecuciones acumuladas.

## N. Evaluación de criterios de aceptación

| # | Criterio | Estado | Evidencia |
|---|---|---|---|
| 1 | Rango y parent correctos | ✅ | `git rev-parse e457277^` = `10812cb` |
| 2 | Diff limitado a dos archivos | ✅ | `git diff --name-status`: solo `core/config.py` (M) y `tests/test_path_integration.py` (A) |
| 3 | Las tres constantes derivan de la política central | ✅ | Todas usan `_ATLAS_PATHS.private_memory_dir` |
| 4 | Propiedades semánticamente correctas | ✅ | `private_memory_dir` = `project_root / "memory" / "Atlas_Memory"` en development |
| 5 | Constantes siguen siendo `str` | ✅ | `str(...)` aplicado; test verifica `isinstance(value, str)` |
| 6 | Sin fallback | ✅ | No hay `try/except` ni valores relativos por defecto |
| 7 | `CHROMA_PATH` no cambió | ✅ | `"./vector_db"` intacto en el diff |
| 8 | Consumidores compatibles | ✅ | `os.path.join`, `os.path.exists`, `os.walk` aceptan `str` rutas absolutas |
| 9 | Tests independientes y no circulares | ✅ | Cada test usa `TemporaryDirectory` propio; valores esperados independientes |
| 10 | Pruebas pasan en distinto orden | ✅ | Variantes A y B OK |
| 11 | Suites relacionadas pasan | ✅ | 52 tests OK |
| 12 | compileall pasa | ✅ | Sin errores |
| 13 | Sin efectos sobre datos reales | ✅ | Working tree post-tests solo contiene el reporte preexistente |
| 14 | Sin cambios fuera de alcance | ✅ | Solo dos archivos modificados |
| 15 | Sin hallazgos BLOCKER ni HIGH | ✅ | Ver secciones O y P |

## O. Hallazgos BLOCKER

Ninguno.

## P. Hallazgos HIGH

Ninguno.

## Q. Hallazgos MEDIUM

Ninguno.

## R. Hallazgos LOW

### LOW-1: `core/security.py` mantiene su propio `BASE_MEMORIA` literal

- **Archivo**: `core/security.py` línea 40.
- **Problema**: `BASE_MEMORIA = "memory/Atlas_Memory"` está hardcodeado y no deriva de `core/system/paths.py`.
- **Evidencia**: `git diff` no toca `core/security.py`; el grep muestra la constante literal.
- **Impacto**: `core/web_crawler.py` importa `BASE_MEMORIA` desde `core.security`, no desde `core.config`. La integración de rutas cubre `core.config` pero `core.security` permanece con una ruta relativa independiente.
- **Corrección mínima**: en un corte futuro, reemplazar `BASE_MEMORIA` en `core/security.py` por `from core.config import BASE_MEMORIA` (o derivar de `get_paths()`).
- **Estado**: CONFIRMED — no bloqueante porque está explícitamente fuera del alcance declarado del corte.

### LOW-2: `core/brain.py` tiene fallback relativo para `BASE_ESTUDIO` y `BASE_PROMPTS`

- **Archivo**: `core/brain.py` líneas 36-39.
- **Problema**: el bloque `try/except` en `core/brain.py` define fallbacks relativos si la importación de `core.config` falla.
- **Evidencia**: lectura directa de `core/brain.py`.
- **Impacto**: si `core.config` falla al importar (ej. error en `get_paths()`), `brain.py` caería a rutas relativas en lugar de propagar el error.
- **Estado**: CONFIRMED — deuda preexistente, no introducida por este corte.

## S. Claims confirmados

1. **Solo se modificaron dos archivos** — CONFIRMED
2. **`get_paths()` se llama una sola vez durante import** — CONFIRMED
3. **Las tres constantes siguen siendo `str`** — CONFIRMED
4. **`private_memory_dir` representa correctamente la memoria de Atlas** — CONFIRMED
5. **`ATLAS_DATA_DIR` se respeta si se establece antes del import** — CONFIRMED
6. **El modo development conserva el layout lógico anterior** — CONFIRMED
7. **No existe fallback silencioso** — CONFIRMED
8. **`CHROMA_PATH` quedó intacto** — CONFIRMED
9. **Los consumidores aceptan rutas absolutas** — CONFIRMED
10. **Los cinco tests nuevos demuestran el contrato** — CONFIRMED
11. **Las 52 pruebas relacionadas permanecen verdes** — CONFIRMED
12. **No se tocaron datos privados** — CONFIRMED
13. **El reporte preexistente quedó fuera del commit** — CONFIRMED
14. **No hubo push** — CONFIRMED

## T. Claims parciales

Ninguno.

## U. Claims no verificados

Ninguno.

## V. Falsos positivos descartados

- **"El test podría leer `.env` real"**: descartado. El context manager inyecta un módulo `dotenv` falso cuyo `load_dotenv` retorna `False` sin leer archivos.
- **"Podría haber ciclo de importación"**: descartado. `core/system/paths.py` no importa `core.config` (0 coincidencias en grep). Los importadores de `paths` son `core/config.py`, `core/system/healer.py`, `core/system/doctor.py`, `core/system/launcher.py`, `core/system/operational_log.py` — ninguno cierra un ciclo.
- **"Los tests podrían contaminarse entre sí"**: descartado. Ambas variantes de orden pasan 8/8.

## W. Cambios obligatorios

Ninguno.

## X. Seguimientos no bloqueantes

- **LOW-1**: integrar `core/security.py` con la política central de rutas en un corte futuro.
- **LOW-2**: eliminar el fallback relativo en `core/brain.py` (deuda preexistente).

## Y. Estado final del working tree

```
?? docs/reviews/general/2026-07-25-10812cb-general-codebase-audit.md
```

Sin cambios rastreados pendientes; permanece un reporte preexistente no rastreado y fuera del corte.

## Z. Gate

**ACCEPT**

### Fundamento

Los 15 criterios de aceptación se cumplen:

1. Rango y parent verificados por `git rev-parse`.
2. Diff limitado a `core/config.py` y `tests/test_path_integration.py`.
3. Las tres constantes (`BASE_MEMORIA`, `BASE_ESTUDIO`, `BASE_PROMPTS`) derivan de `_ATLAS_PATHS.private_memory_dir`.
4. `private_memory_dir` resuelve a `project_root / "memory" / "Atlas_Memory"` en development y al directorio configurado por `ATLAS_DATA_DIR` cuando se establece.
5. Las constantes son `str` (verificado por test y por `str(...)` explícito).
6. `CHROMA_PATH` no fue modificado.
7. No existe `try/except` ni fallback silencioso en `core/config.py`.
8. Los consumidores (`brain.py`, `indexer.py`) aceptan rutas absolutas como `str`.
9. Los tests son independientes, no circulares, y construyen valores esperados independientemente.
10. Las pruebas pasan en ambos órdenes de ejecución.
11. Las 52 pruebas de las suites relacionadas pasan en su totalidad.
12. `compileall core tests` completa sin errores.
13. No se tocaron datos reales (`memory/`, `vector_db/`, `.env` intactos).
14. No hubo cambios fuera del alcance declarado.
15. No hay hallazgos BLOCKER ni HIGH. Los dos hallazgos LOW son deuda preexistente o están fuera del alcance del corte.

### Resumen de ejecuciones

| Conjunto | Ejecuciones | Resultado |
|---|---|---|
| Test específico (`test_path_integration`) | 5 tests | OK |
| 6 suites relacionadas | 52 tests | OK |
| Variante de orden A | 8 tests (con repetición) | OK |
| Variante de orden B | 8 tests (con repetición) | OK |
| compileall | core/ + tests/ | Sin errores |

### Evidencia del grafo

**GRAPH NOT AVAILABLE** — El servidor MCP de Codebase Memory no respondió a ninguna consulta (5 timeouts consecutivos en `list_projects`, `index_status`, `search_graph` × 2, `get_architecture`). La validación del impacto se realizó mediante lectura directa, `grep`, `git diff` y ejecución de tests.

**Relaciones verificadas por código directo (sustituto del grafo):**

| Relación | Método | Resultado |
|---|---|---|
| `core.config` importa `core.system.paths.get_paths` | `grep` línea 23 | CONFIRMED |
| `core.system.paths` NO importa `core.config` | `grep` recursivo en `core/system/` | CONFIRMED (0 coincidencias) |
| Consumidores de `BASE_MEMORIA` | `grep` global | CONFIRMED (`brain.py`, `indexer.py`, `web_crawler.py` vía `security.py`) |
| Consumidores de `BASE_ESTUDIO` | `grep` global | CONFIRMED (`brain.py`) |
| Consumidores de `BASE_PROMPTS` | `grep` global | CONFIRMED (`brain.py`) |
| Entry points NO consumen las tres constantes | `grep` por archivo | CONFIRMED (0 coincidencias) |
| `core/security.py`, `core/vector_store.py` NO modificados | `git diff` | CONFIRMED |
| `core/system/paths.py` NO modificado | `git diff` | CONFIRMED |
| Consumidores aceptan `str` | Lectura de `os.path.join`, `os.path.exists`, `os.walk`, `Path(...).resolve()` | CONFIRMED |

**Relaciones descartadas:**

- Ciclo `core.config → core.system.paths → core.config`: descartado — `paths.py` no importa `config.py`.
- Ciclo indirecto vía `core.system.{healer,doctor,launcher}`: descartado — importan `paths` pero no `config`.
- Contaminación entre tests: descartado — ambas variantes de orden pasan.

---

**Fin del reporte**
