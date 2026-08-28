# Auditoría técnica de corte — fix(brain): remove relative path fallback for study paths

Fecha: 2026-07-28
Tipo: Corte
Repositorio: C:\Users\delfa\Documents\Atlas
Rama: atlas-v4.1-incremental-indexing
Commit base: 1eef4bea7151e8ce02900842f9b3d8093fd9624b
Commit final: 4cd4a56667e36da7f239e6c96fb182737ed533a8
Rango auditado: 1eef4be..4cd4a56
Archivo: docs/reviews/cuts/2026-07-28-4cd4a56-cut-brain-study-path-fallback-review.md
Gate: ACCEPT

## 1. Resumen ejecutivo

El commit `4cd4a56` elimina el bloque `try/except Exception:` que definía `BASE_ESTUDIO`, `BASE_PROMPTS` y `MAX_HISTORIAL` como rutas relativas hardcodeadas en `core/brain.py`, reemplazándolo por un import directo desde `core.config`. La centralización ya existía en `core.config` (derivada de `core.system.paths.get_paths()`). Se agregaron 4 tests enfocados en `tests/test_brain_paths.py` que validan: equivalencia de símbolos y tipos, respeto a `ATLAS_DATA_DIR`, independencia de CWD, y propagación de fallos de importación. La suite completa pasa 122 tests (121 passed, 1 skipped, 0 failures, 0 errors, 0 _FailedTest). No se realizó push.

## 2. Objetivo

Eliminar el fallback de rutas relativas (`"memory/Atlas_Memory/03_Conocimiento"` y `"memory/Atlas_Memory/00_Sistema/Prompts"`) en `core/brain.py`, centralizando el uso de `BASE_ESTUDIO`, `BASE_PROMPTS` y `MAX_HISTORIAL` desde `core.config`.

## 3. Alcance

- `core/brain.py` (código de producción)
- `tests/test_brain_paths.py` (nuevo archivo de tests)

## 4. Fuera de alcance

- `core/config.py`
- `core/system/paths.py`
- `core/security.py`
- Otros módulos de `core/`
- Documentación
- Dependencias

## 5. Estado Git

- **Rama**: `atlas-v4.1-incremental-indexing`
- **HEAD**: `4cd4a56667e36da7f239e6c96fb182737ed533a8`
- **Working tree**: limpio (sin cambios tracked/untracked)
- **Tracking**: `origin/atlas-v4.1-incremental-indexing: ahead 1` (no push)

## 6. Instrucciones aplicables

- `AGENTS.md` (secciones 1, 4, 6, 9, 10)
- `.agents/policies/git-safety.md`
- `.agents/policies/testing.md`
- `.agents/playbooks/audit.md`

## 7. Entorno

- Python: `.venv\Scripts\python.exe`
- SO: Windows (win32)
- Working directory: `C:\Users\delfa\Documents\Atlas`

## 8. Diff inspeccionado

**`core/brain.py`** — 1 archivo modificado, -9/+1 líneas:
- Eliminado bloque `try/except Exception:` (líneas 31-39 del HEAD anterior).
- Reemplazado por import directo: `from core.config import BASE_ESTUDIO, BASE_PROMPTS, MAX_HISTORIAL` (1 línea).
- No se eliminaron archivos. No se modificaron otros archivos.

**`tests/test_brain_paths.py`** — 1 archivo nuevo, 234 líneas:
- 4 tests de comportamiento usando subprocess aislado con fake modules.
- Aislamiento de CWD, env, sys.modules, y dependencias.

**`git grep` para rutas relativas en `core/brain.py`**:
- `"memory/Atlas_Memory/03_Conocimiento"` → vacío (CONFIRMED)
- `"memory/Atlas_Memory/00_Sistema/Prompts"` → vacío (CONFIRMED)

**`git diff --check`** → sin errores de whitespace.

## 9. Criterios de aceptación

| Criterio | Resultado | Evidencia |
|---|---|---|
| Solo dos archivos cambiados | PASS | `git show --stat` → 2 archivos |
| Fallback relativo eliminado completamente | PASS | `git grep` vacío en `core/brain.py` |
| Tres símbolos públicos compatibles | PASS | Test `test_symbols_match_config_with_preserved_types_and_absolute_paths` |
| Rutas derivan exclusivamente de `core.config` | PASS | Línea 31 de `core/brain.py` (inspección directa) |
| `ATLAS_DATA_DIR` respetado | PASS | Test `test_data_override_applies_when_set_before_import` |
| Independencia de CWD demostrada | PASS | Test `test_paths_do_not_change_with_cwd` |
| Fallos de importación propagados | PASS | Test `test_config_import_failure_is_not_masked` |
| No ciclo de importación | PASS | `core/brain.py` → `core/config.py` → `core/system/paths.py` (sin ciclo) |
| Cuatro tests enfocados pasan | PASS | `test_brain_paths`: 4 OK |
| Suite completa: 122 tests (121 passed, 1 skipped, 0 failures, 0 errors, 0 _FailedTest) | PASS | `unittest discover` |
| No acceso a datos reales ni proveedores externos en pruebas observadas | PASS | Tests usan `TemporaryDirectory`, fake modules, env aislada |
| Exit code 101 fue ambiental | NOT VERIFIED — no fue reproducido ni se obtuvo evidencia suficiente para determinar su causa exacta. Las ejecuciones posteriores requeridas finalizaron correctamente. | — |
| No push realizado | PASS | `branch -vv` muestra `ahead 1` |

## 10. Evidencia reproducida

### Tests enfocados
```text
.venv\Scripts\python.exe -m unittest tests.test_brain_paths -v
Result: OK
Exit code: 0
Evidence: 4 tests, 0 failures, 0 errors, 0 skipped
```

### Tests de integración de paths
```text
.venv\Scripts\python.exe -m unittest tests.test_path_integration -v
Result: OK
Exit code: 0
Evidence: 5 tests, 0 failures, 0 errors
```

### Tests de seguridad de paths
```text
.venv\Scripts\python.exe -m unittest tests.test_security_paths -v
Result: OK
Exit code: 0
Evidence: 7 tests, 0 failures, 0 errors
```

### Suite completa
```text
.venv\Scripts\python.exe -m unittest discover -s tests -v
Result: OK (skipped=1)
Exit code: 0
Evidence: 122 tests ejecutados: 121 passed, 1 skipped, 0 failures, 0 errors y 0 _FailedTest.
```

### Compilación
```text
.venv\Scripts\python.exe -m compileall core tests
Result: OK
Exit code: 0
Evidence: No syntax errors
```

### Verificación de no push
```text
git branch -vv
Evidence: atlas-v4.1-incremental-indexing 4cd4a56 [origin/atlas-v4.1-incremental-indexing: ahead 1]
```

## 11. Hallazgos

### BLOCKER
Ninguno.

### HIGH
Ninguno.

### MEDIUM
Ninguno.

### LOW
Ninguno.

## 12. Claims confirmados

| # | Claim | Evidencia |
|---|-------|-----------|
| 1 | Solo dos archivos cambiados | `git show --stat` → 2 archivos |
| 2 | El fallback relativo fue eliminado completamente | `git grep` vacío en `core/brain.py` |
| 3 | Los tres símbolos públicos permanecen compatibles | Test `test_symbols_match_config_with_preserved_types_and_absolute_paths` |
| 4 | Las rutas derivan exclusivamente de `core.config` | Línea 31 de `core/brain.py` (inspección directa) |
| 5 | `ATLAS_DATA_DIR` es respetado | Test `test_data_override_applies_when_set_before_import` |
| 6 | Independencia de CWD demostrada | Test `test_paths_do_not_change_with_cwd` |
| 7 | Fallos de importación de configuración se propagan | Test `test_config_import_failure_is_not_masked` |
| 8 | No se introdujo ciclo de importación | `core/brain.py` → `core/config.py` → `core/system/paths.py` (sin ciclo) |
| 9 | Cuatro tests enfocados pasan | `test_brain_paths`: 4 OK |
| 10 | Suite completa: 122 tests (121 passed, 1 skipped, 0 failures, 0 errors, 0 _FailedTest) | `unittest discover` |
| 11 | No se observaron accesos a datos reales ni proveedores externos durante las pruebas ejecutadas; los tests inspeccionados usan temporales, módulos falsos y entorno aislado | Inspección de `test_brain_paths.py`, `test_path_integration.py`, `test_security_paths.py` |
| 12 | Exit code 101 fue ambiental | NOT VERIFIED — no fue reproducido ni se obtuvo evidencia suficiente para determinar su causa exacta. Las ejecuciones posteriores requeridas finalizaron correctamente. |
| 13 | No se hizo push | `branch -vv` muestra `ahead 1` |

## 13. Claims parciales
Ninguno.

## 14. Claims no verificados
- Exit code 101 fue ambiental (ver claim 12).

## 15. Falsos positivos descartados
Ninguno.

## 16. Cambios obligatorios
Ninguno.

## 17. Seguimientos no bloqueantes
Ninguno.

## 18. Estado final del working tree
- Branch: `atlas-v4.1-incremental-indexing`
- HEAD: `4cd4a56667e36da7f239e6c96fb182737ed533a8`
- Working tree: limpio
- Untracked files: ninguno (salvo el presente reporte)
- Staged changes: ninguno
- Push: no realizado

## 19. Gate
**ACCEPT**

El commit elimina correctamente el fallback de rutas relativas, centraliza los tres símbolos desde `core.config`, preserva tipos y contratos públicos, respeta `ATLAS_DATA_DIR`, demuestra independencia de CWD, propaga fallos de importación, y pasa 122 tests (1 skip ambiental) sin regresiones. No se detectaron hallazgos de severidad BLOCKER, HIGH, MEDIUM o LOW. No se realizó push.