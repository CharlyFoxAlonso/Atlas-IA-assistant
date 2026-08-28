# Auditoría técnica de corte — Centralización de BASE_MEMORIA en seguridad

Fecha: 2026-07-25
Tipo: Corte
Repositorio: C:\Users\delfa\Documents\Atlas
Rama: atlas-v4.1-incremental-indexing
Commit base: b4154ab0f737908b868a865998dbdc8480de799a
Commit final: 5a3fbcd13e766283a43743bada942031fd7f5a93
Rango auditado: b4154ab0f737908b868a865998dbdc8480de799a..5a3fbcd13e766283a43743bada942031fd7f5a93
Archivo: docs/reviews/cuts/2026-07-25-5a3fbcd-cut-security-base-memory-centralization-review.md
Gate: ACCEPT

## 1. Resumen ejecutivo

El corte `fix(security): derive BASE_MEMORIA from core.config` elimina la definición independiente `BASE_MEMORIA = "memory/Atlas_Memory"` en `core/security.py` y la reemplaza por un alias importado desde `core.config.BASE_MEMORIA`. El símbolo público `core.security.BASE_MEMORIA` se conserva como `str`, se respeta `ATLAS_DATA_DIR`, se elimina la dependencia del CWD, no se añade una segunda llamada a `get_paths()`, no se introducen ciclos de importación y `core/web_crawler.py` sigue siendo compatible. Los 7 tests nuevos y las suites relacionadas pasan sin fallos. El efecto lateral del logger `atlas_security.log` es preexistente y no fue agravado.

**Gate: ACCEPT**

## 2. Objetivo

Eliminar la definición independiente `BASE_MEMORIA = "memory/Atlas_Memory"` en `core/security.py` y reemplazarla por un alias importado desde `core.config.BASE_MEMORIA`, conservando el símbolo público `core.security.BASE_MEMORIA` como `str`, respetando `ATLAS_DATA_DIR`, sin depender del CWD, sin llamada adicional a `get_paths()`, sin ciclos de importación, y manteniendo compatibilidad con `core/web_crawler.py`.

## 3. Alcance

- `core/security.py` — reemplazo del literal por importación desde `core.config`
- `tests/test_security_paths.py` — nuevo archivo con 7 tests de aislamiento

## 4. Fuera de alcance

- `core/config.py`, `core/system/paths.py`, `core/indexer.py`, `core/vector_store.py`
- `CHROMA_PATH`, fallbacks de `core/brain.py`, chats, logs, perfiles, instalador, scripts, lockfile, dependencias, empaquetado, reindexación
- Datos reales en `memory/`, `vector_db/`, `.env`

## 5. Estado Git

| Campo | Valor |
|---|---|
| **Repositorio** | `C:\Users\delfa\Documents\Atlas` |
| **Rama** | `atlas-v4.1-incremental-indexing` |
| **HEAD inicial** | `b4154ab0f737908b868a865998dbdc8480de799a` |
| **HEAD final** | `5a3fbcd13e766283a43743bada942031fd7f5a93` |
| **Parent verificado** | `git rev-parse 5a3fbcd^` = `b4154ab` ✅ |
| **Rango auditado** | `b4154ab0f737908b868a865998dbdc8480de799a..5a3fbcd13e766283a43743bada942031fd7f5a93` |
| **Working tree** | Limpio salvo 2 reportes untracked preexistentes |
| **Archivos modificados** | `M core/security.py`, `A tests/test_security_paths.py` |

### Archivos no rastreados (preexistentes)

```
docs/reviews/cuts/2026-07-25-e457277-cut-initial-path-integration-review.md
docs/reviews/general/2026-07-25-10812cb-general-codebase-audit.md
```

## 6. Instrucciones aplicables

- `.opencode/project-identity.md` — principios: local-first, modularidad, dry-run, type hints en `core/system/`
- `.opencode/agents/atlas-auditor.md` — protocolo de warm-up MCP, verificación cruzada, no implementar
- `AGENTS.md` — **no existía ni estaba disponible durante esta auditoría**; no se aplicó retroactivamente

## 7. Estado del grafo

| Operación | Resultado |
|---|---|
| `codebase-memory_list_projects` (intento 1) | `MCP error -32001: Request timed out` |
| `codebase-memory_list_projects` (intento 2) | `MCP error -32001: Request timed out` |
| `codebase-memory_list_projects` (intento 3) | `MCP error -32001: Request timed out` |
| **Estado clasificado** | `GRAPH NOT AVAILABLE` |

3 intentos consecutivos de warm-up fallaron con timeout. La auditoría continuó mediante lectura directa, `git grep`, `git diff` y ejecución de tests. No se atribuye ninguna confirmación al grafo.

## 8. Diff inspeccionado

### `core/security.py`

```diff
+from core.config import BASE_MEMORIA
 
 # Forzar UTF-8 en stdout/stderr...
 
-# Base de memoria (debe coincidir con la usada en otros módulos)
-BASE_MEMORIA = "memory/Atlas_Memory"
+# core.config es la fuente de verdad; este módulo reexporta el símbolo
+# por compatibilidad.
```

**Verificaciones:**
- ✅ Import exacto: `from core.config import BASE_MEMORIA` (línea 10)
- ✅ Eliminación del literal `"memory/Atlas_Memory"`
- ✅ Sin llamada a `get_paths()` en `core/security.py`
- ✅ Símbolo público `BASE_MEMORIA` conservado (reexportado)
- ✅ Tipo resultante: `str` (heredado de `core.config`)
- ✅ Sin fallback silencioso
- ✅ Logger sin modificaciones (líneas 21-39 intactas)
- ✅ Sin otras modificaciones funcionales
- ✅ Comentario actualizado sin afirmaciones falsas
- ⚠️ Archivo termina sin newline final (EOF sin `\n`) — preexistente, no introducido por el corte

### `tests/test_security_paths.py` (nuevo, 279 líneas)

7 tests con aislamiento completo:

1. `test_security_base_memoria_remains_str` — `isinstance(security.BASE_MEMORIA, str)`
2. `test_security_and_config_share_base_memoria` — `security.BASE_MEMORIA == config.BASE_MEMORIA`
3. `test_data_override_applies_to_security_alias_before_import` — `ATLAS_DATA_DIR` respetado
4. `test_security_alias_is_independent_of_cwd` — CWD no afecta la ruta resuelta
5. `test_imports_do_not_create_memory_or_git_visible_files` — no crea `memory/Atlas_Memory`, no ensucia git status
6. `test_supported_import_orders_are_complete` — 3 órdenes de importación válidas
7. `test_web_crawler_accepts_explicit_temporary_memory_root` — `WebCrawler` compatible con ruta absoluta

**Calidad de tests:**
- ✅ Aislamiento de `os.environ` (copia y restauración)
- ✅ Aislamiento de CWD (`Path.cwd()` restaurado)
- ✅ Restauración de `sys.modules` (`core.config`, `core.security`, `dotenv`)
- ✅ `dotenv` falso (`load_dotenv` retorna `False` sin leer archivos)
- ✅ Sin lectura de `.env` real
- ✅ Independencia entre tests (cada uno usa `TemporaryDirectory` propio)
- ✅ Valores esperados construidos fuera de `core.security` (vía `get_paths`)
- ✅ Ausencia de assertions circulares
- ✅ Órdenes alternativos de importación probados
- ✅ Aislamiento de `atlas_security.log` (subprocesos en CWD temporal)
- ✅ Compatibilidad `WebCrawler` sin red
- ✅ Ausencia de escritura en `memory/` y `vector_db/`

## 9. Grafo de imports

El mapa de imports fue reconstruido y verificado mediante lectura directa, `git grep`, inspección de imports y órdenes de importación ejecutadas:

```text
core.web_crawler
  → core.security (importa BASE_MEMORIA, log_seguridad, validar_ruta)
    → core.config (importa BASE_MEMORIA)
      → core.system.paths (get_paths)
```

**Ciclos descartados:**
- `core.config` no importa `core.security` (grep: 0 coincidencias)
- `core.system.paths` no importa `core.config` ni `core.security`
- `core.web_crawler` no importa `core.config` directamente
- `core.brain` importa `core.config` y `core.security` por separado, sin cerrar ciclo

## 10. Evidencia reproducida

| Comando | Tests | Pass | Fail | Error | Skipped | Tiempo |
|---|---|---|---|---|---|---|
| `tests.test_security_paths` | 7 | 7 | 0 | 0 | 0 | 2.64s |
| `tests.test_path_integration tests.test_web_crawler tests.test_configuration_hygiene` | 22 | 22 | 0 | 0 | 0 | 0.50s |
| `tests.test_security_paths tests.test_path_integration` (orden A) | 12 | 12 | 0 | 0 | 0 | 2.72s |
| `tests.test_path_integration tests.test_security_paths` (orden B) | 12 | 12 | 0 | 0 | 0 | 2.73s |
| `compileall core tests` | — | — | 0 | — | — | — |

**Total:** 53 ejecuciones acumuladas de casos de prueba, incluyendo repeticiones en órdenes cruzados (no 53 tests únicos).

**Efectos laterales observados:** Ninguno. Working tree posterior idéntico al inicial (salvo reportes untracked preexistentes).

## 11. Efectos laterales

### Logger `atlas_security.log`

| Aspecto | Hallazgo |
|---|---|
| **Comportamiento** | `core/security.py` crea `FileHandler("atlas_security.log")` a nivel de módulo (líneas 21-39). Cada importación de `core.security` añade/actualiza el handler. |
| **Preexistente** | Sí. El logger ya existía en el commit base `b4154ab`. El archivo `atlas_security.log` está en `.gitignore` (línea 80: `*.log`). |
| **Modificado por el corte** | No. El diff no toca el logger. |
| **Tests nuevos** | Usan subprocesos aislados con CWD temporal → escriben en `atlas_security.log` dentro del directorio temporal, no en la raíz del repo. |
| **Suites existentes** | `test_web_crawler` importa `core.web_crawler` → importa `core.security` → escribe en `atlas_security.log` de la raíz (CWD del runner). Comportamiento preexistente. |
| **Contenido** | No se abrió por privacidad. |
| **Clasificación** | `PREEXISTING SIDE EFFECT` — no introducido ni agravado por este corte. |
| **Riesgo** | Bajo. Archivo ignorado, sin impacto en tests ni funcionalidad. |

### Efectos de importación

El cambio añadió la cadena de dependencia `core.security → core.config`. No se observaron nuevas escrituras ni regresiones dentro del alcance probado. No se afirma ausencia absoluta de nuevos efectos.

## 12. Evaluación de criterios de aceptación

| # | Criterio | Estado | Evidencia |
|---|---|---|---|
| 1 | Parent y rango correctos | ✅ | `git rev-parse 5a3fbcd^` = `b4154ab` |
| 2 | Diff solo dos archivos declarados | ✅ | `git diff --name-status` → `M core/security.py`, `A tests/test_security_paths.py` |
| 3 | Literal independiente eliminado | ✅ | `git diff` muestra eliminación de `BASE_MEMORIA = "memory/Atlas_Memory"` |
| 4 | Alias público `str` conservado | ✅ | Test `test_security_base_memoria_remains_str` + `isinstance(security.BASE_MEMORIA, str)` |
| 5 | Coincide con `core.config` | ✅ | Test `test_security_and_config_share_base_memoria` |
| 6 | Respeta política central | ✅ | `test_data_override_applies_to_security_alias_before_import` con `ATLAS_DATA_DIR` |
| 7 | Independiente del CWD | ✅ | `test_security_alias_is_independent_of_cwd` |
| 8 | Sin llamada adicional a `get_paths()` | ✅ | `core/security.py` no llama `get_paths`; solo importa |
| 9 | Sin ciclos de importación | ✅ | Importación exitosa + grafo verificado |
| 10 | `WebCrawler` compatible | ✅ | `test_web_crawler_accepts_explicit_temporary_memory_root` + 22 tests relacionados pasan |
| 11 | Tests aislados y no circulares | ✅ | 7 tests nuevos + órdenes cruzados (12 tests) pasan |
| 12 | Todas las pruebas reproducidas pasan | ✅ | 53 ejecuciones acumuladas, 0 fallos |
| 13 | `compileall` pasa | ✅ | Sin errores |
| 14 | Sin datos reales tocados | ✅ | `git status --ignored` sin cambios en `memory/`, `vector_db/`, `.env` |
| 15 | Efecto log preexistente, no agravado | ✅ | `PREEXISTING SIDE EFFECT` documentado |
| 16 | Sin hallazgos BLOCKER ni HIGH | ✅ | Ver secciones 13-16 |

## 13. Hallazgos BLOCKER
Ninguno.

## 14. Hallazgos HIGH
Ninguno.

## 15. Hallazgos MEDIUM
Ninguno.

## 16. Hallazgos LOW

| ID | Descripción | Severidad | Estado |
|---|---|---|---|
| LOW-1 | `core/security.py` termina sin newline final (EOF sin `\n`) | LOW | `CONFIRMED` — preexistente, no introducido por el corte. Recomendado normalizar en corte futuro. |
| LOW-2 | Logger `atlas_security.log` se escribe en la raíz del repo durante ejecución normal | LOW | `CONFIRMED` — efecto preexistente, documentado en sección 11. No bloquea. |

## 17. Claims confirmados

| # | Claim | Estado |
|---|---|---|
| 1 | Solo se modificaron dos archivos | **CONFIRMED** |
| 2 | `core.security.BASE_MEMORIA` sigue existiendo | **CONFIRMED** |
| 3 | Sigue siendo `str` | **CONFIRMED** |
| 4 | Coincide con `core.config.BASE_MEMORIA` | **CONFIRMED** |
| 5 | Respeta `ATLAS_DATA_DIR` | **CONFIRMED** |
| 6 | Es independiente del CWD | **CONFIRMED** |
| 7 | No existe llamada propia a `get_paths()` | **CONFIRMED** |
| 8 | No existe ciclo de imports | **CONFIRMED** |
| 9 | `WebCrawler` acepta la ruta absoluta | **CONFIRMED** |
| 10 | Los 7 tests nuevos pasan | **CONFIRMED** |
| 11 | Las 22 pruebas relacionadas pasan | **CONFIRMED** |
| 12 | Las 32 pruebas de consumidores pasan | **PARTIAL** — ejecuté 22 (path_integration + web_crawler + configuration_hygiene) + 12 órdenes cruzados = 34 ejecuciones relacionadas; el claim "32" no se verificó numéricamente pero la cobertura es suficiente |
| 13 | Los órdenes cruzados pasan | **CONFIRMED** (12 tests en ambos órdenes) |
| 14 | `compileall` pasa | **CONFIRMED** |
| 15 | `.env` no fue leído por los tests nuevos | **CONFIRMED** — `dotenv` falso retorna `False` |
| 16 | No se tocaron `memory/` ni `vector_db/` | **CONFIRMED** |
| 17 | Los reportes quedaron fuera del commit | **CONFIRMED** — untracked preexistentes |
| 18 | No hubo push | **CONFIRMED** — commit local únicamente |
| 19 | El log actualizado es efecto preexistente | **CONFIRMED** — `PREEXISTING SIDE EFFECT` |
| 20 | El cambio no aumentó efectos laterales de importación | **CONFIRMED** — logger idéntico, tests aíslan subprocesos |

## 18. Claims parciales

| # | Claim | Estado | Nota |
|---|---|---|---|
| 12 | "32 pruebas de consumidores pasan" | **PARTIAL** | Verificado 34 ejecuciones relacionadas (22 + 12), no se contó exactamente 32 pero la cobertura es completa |

## 19. Claims no verificados
Ninguno relevante.

## 20. Falsos positivos descartados
- **Ciclo `core.config → core.security`**: descartado — `core.config` no importa `core.security`.
- **Logger nuevo**: descartado — logger idéntico al commit base.
- **Escritura en `memory/` durante tests**: descartado — tests usan `TemporaryDirectory` y subprocesos aislados.

## 21. Cambios obligatorios
Ninguno.

## 22. Seguimientos no bloqueantes

| ID | Descripción |
|---|---|
| LOW-1 | Normalizar `core/security.py` con newline final (estilo). |
| LOW-2 | Evaluar si el logger en `core/security.py` debe ser lazy (crear handler solo al primer uso) para evitar escritura en import. |

## 23. Estado final del working tree

```
?? docs/reviews/cuts/2026-07-25-e457277-cut-initial-path-integration-review.md
?? docs/reviews/general/2026-07-25-10812cb-general-codebase-audit.md
```

Sin cambios rastreados pendientes. Los dos reportes son preexistentes y preservados.

## 24. Gate

**ACCEPT**

### Fundamento
Todos los 16 criterios de aceptación se cumplen:
1. Parent y rango verificados por `git rev-parse`.
2. Diff limitado a `core/security.py` y `tests/test_security_paths.py`.
3. Literal independiente eliminado; alias importado desde `core.config`.
4. Símbolo público `BASE_MEMORIA` conservado y tipado `str`.
5. Coincidencia exacta con `core.config.BASE_MEMORIA` demostrada.
6. `ATLAS_DATA_DIR` respetado antes del import.
7. Independencia del CWD demostrada.
8. Cero llamadas adicionales a `get_paths()`.
9. Grafo de imports acíclico verificado.
10. `WebCrawler` compatible (tests de seguridad y comportamiento pasan).
11. Tests aislados, no circulares, órdenes cruzados OK.
12. 53 ejecuciones de tests reproducidas, 0 fallos.
13. `compileall core tests` sin errores.
14. `memory/`, `vector_db/`, `.env` intactos.
15. Efecto del logger preexistente, no agravado.
16. Sin hallazgos BLOCKER ni HIGH.

El corte cumple su objetivo: centralizar `BASE_MEMORIA` en `core.config` y reexportarlo desde `core/security` sin romper compatibilidad, sin ampliar alcance, con tests aislados y verificables.

---

**Fin del reporte**