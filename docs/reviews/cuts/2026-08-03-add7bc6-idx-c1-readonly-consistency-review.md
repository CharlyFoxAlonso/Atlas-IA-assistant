# Informe de Auditoría — IDX-C1 Verificación de Consistencia Read-Only

**Archivo:** `docs/reviews/cuts/2026-08-03-add7bc6-idx-c1-readonly-consistency-review.md`
**Fecha:** 2026-08-03
**Repositorio:** Atlas
**Rama:** `atlas-v4.1-incremental-indexing`
**HEAD auditado:** `add7bc65b15ee0e2b638f31f9e0a06f7b06b04ab`
**Baseline (commit previo al corte):** `add7bc6` (mismo — el corte no ha sido commiteado)
**Rol:** Auditor (Workflow 2.0)
**SDD gobernante:** `docs/spec/atlas-v4.1-incremental-indexing-sdd.md` (secciones 5–7, 10–11)

---

## Objetivo y alcance

Determinar si el microcorte **IDX-C1** implementa fielmente el contrato de verificación de consistencia de solo lectura definido en la SDD, sin efectos de escritura, creación, reparación, embeddings, proveedores ni superficies operativas.

**Alcance autorizado (4 archivos):**
- `core/index_consistency.py` (nuevo)
- `core/vector_store.py` (aditivo: adaptador `ChromaReadAccess` + `_abrir_coleccion_existente`)
- `tests/test_index_consistency.py` (nuevo)
- `tests/test_vector_paths.py` (aditivo: `ChromaReadAccessAdapterTests`)

---

## Estado Git

### Inicial (baseline confirmado)
```
 M .agents/workflow-2/context-profiles.json
 M .agents/workflow-2/install-state.json
 M .agents/workflow-2/rule-ownership.json
 D .opencode/agents/atlas-auditor.md
 D .opencode/agents/atlas-plan-to-codex.md
 D .opencode/agents/atlas-plan-to-kimik3.md
 M .opencode/agents/workflow-auditor.md
 M core/vector_store.py
 M tests/test_vector_paths.py
 M tests/test_workflow_2.py
?? core/index_consistency.py
?? tests/test_index_consistency.py
```
- 8 cambios preexistentes de gobernanza (`.agents/`, `.opencode/`, `tests/test_workflow_2.py`) — **no pertenecen al corte**.
- 4 archivos del corte: 2 nuevos (`??`), 2 modificados (`M`).

### Final (idéntico al inicial)
- El Builder **no tocó** los 8 cambios de usuario.
- No hay stage, commit ni push del corte.
- `git diff --check`: limpio (solo warnings de CRLF preexistentes).

---

## Comandos ejecutados y resultados

| Comando | Exit code | Contadores |
|---|---|---|
| `.venv\Scripts\python.exe -m unittest tests.test_index_consistency tests.test_vector_paths -v` | 0 | **37 tests OK** (0 failures, 0 errors) |
| `.venv\Scripts\python.exe -m unittest discover -s tests -v` | 0 | **186 tests OK** (1 skipped preexistente: symlinks en Windows sin privilegio) |
| `.venv\Scripts\python.exe -m compileall core/index_consistency.py core/vector_store.py tests/test_index_consistency.py tests/test_vector_paths.py` | 0 | Sin salida (compilación limpia) |
| `git diff --check` | 0 | Limpio |
| `git status --short --untracked-files=all` | 0 | Estado confirmado arriba |

---

## Criterios de aceptación (SDD §5, §6, §7, §10, §11.2)

| Criterio | Verificación | Resultado |
|---|---|---|
| **Alcance Git correcto** | Solo 4 archivos autorizados modificados/nuevos; working tree de usuario intacto | ✅ |
| **Contrato read-only** | Sin `IndexManifest.load`, sin `.bak`, sin escrituras, sin `get_or_create`, sin embeddings, sin `log_seguridad`, sin `__main__`/CLI/UI/API | ✅ |
| **Adaptador Chroma** | Solo abre existente; distingue raíz ausente / colección ausente / backend inaccesible / colección presente | ✅ |
| **Estados (5)** | `HEALTHY`, `HEALTHY_EMPTY`, `INCONSISTENT`, `DEGRADED`, `UNAVAILABLE` presentes | ✅ |
| **Categorías (16)** | 16 identificadores estables de la SDD §6 presentes en `DivergenceCategory` | ✅ |
| **Reporte** | `observed_state`, `published_state`, flags writer, conteos, categorías, `orphan_sample`, errores estructurados | ✅ |
| **Publicación §11.2** | `HEALTHY`/`HEALTHY_EMPTY` nominales → `DEGRADED` (writer_state_known=False); `INCONSISTENT`/`UNAVAILABLE` conservan prioridad | ✅ |
| **Manifiesto** | Ausente / corrupto / incompatible distinguidos; corrupto no genera `.bak`; malformadas aislables → `DEGRADED`; schema incompatible ≠ corrupción | ✅ |
| **Fuentes y hashes** | Política `core.config` (extensiones/ignorados); identidad normalizada `/`; atajo size+mtime; SHA-256 si difieren; distingue contenido vs metadata | ✅ |
| **Categorías y contadores** | Multi-label; conteos no exclusivos; `orphan_count` chunks huérfanos; `source_absent_chroma_present` cuenta identidades; `orphan_sample` ≤10 determinista; sin purga | ✅ |

---

## Verificación del contrato read-only (SDD §7)

| Prohibición | Evidencia en código |
|---|---|
| No `IndexManifest.load` | `_leer_manifiesto_sin_mutacion` usa `json.load` crudo + validación propia; `IndexManifest.load` nunca importado/llamado |
| No `.bak` | Test `test_manifest_corrupt_sin_backup` verifica `os.listdir` sin archivos `.corrupt-` |
| No escrituras (`os.replace`, rename, delete) | Ninguna llamada a `os.replace`, `os.rename`, `os.remove`, `shutil`, `open(..., 'w')` en `index_consistency.py` |
| No `get_or_create_collection` | Adaptador usa exclusivamente `cliente.get_collection(name)` |
| No `add`/`delete`/`query_texts`/embeddings | Solo `collection.get(include=["metadatas"])` |
| No `log_seguridad` | No importado; test `test_no_escribe_ni_crea_ni_embebe` espía y confirma `assert_not_called` |
| No `__main__`, Doctor, Healer, CLI, UI, API | Archivo no tiene bloque `if __name__ == "__main__"`; no importa módulos de superficies |

**Conclusión:** Contrato read-only **demostrado** por inspección de código y tests de contrato.

---

## Revisión del adaptador Chroma (`core/vector_store.py`)

| Comportamiento | Implementación | Test |
|---|---|---|
| Raíz ausente → no construye cliente | `if not root_present or not (root/"chroma.sqlite3").is_file(): return ChromaReadAccess(root_present=root_present)` | `test_root_missing_reports_absent_without_client` ✅ |
| Raíz existe sin `chroma.sqlite3` → colección ausente | Mismo branch; `PersistentClient` no instanciado | `test_root_without_sqlite_reports_collection_absent_without_client` ✅ |
| Raíz + sqlite → `get_collection` (nunca `get_or_create`) | `cliente.get_collection(name=collection_name)` | `test_existing_root_opens_existing_collection_read_only` ✅ (0 `get_or_create_calls`) |
| `ValueError` (colección inexistente) → `collection_present=False` | `except ValueError: return ChromaReadAccess(root_present=True)` | `test_value_error_maps_to_collection_absent` ✅ |
| Otro error → `unavailable=True`, `collection_present=True` | `except Exception: return ChromaReadAccess(root_present=True, collection_present=True, unavailable=True, error=...)` | `test_other_error_maps_to_unavailable` ✅ |

**Semántica `unavailable=True` + `collection_present=True`:** Justificada. Cuando el backend falla tras confirmar que la raíz existe, la colección *fue solicitada* y el fallo es de acceso, no de ausencia. El flag `unavailable` es la señal autoritativa; `collection_present=True` evita clasificar erróneamente como "colección ausente". Consistente con el catch interno de `verificar_consistencia` (líneas 388–396) que hace lo mismo.

**Acoplamiento a layout Chroma:** Verifica existencia de `chroma.sqlite3` — detalle de implementación de Chroma 0.5.x, no contrato público. Aceptable como heurística de "raíz inicializada" dado que el adaptador es interno y testeado con fakes.

---

## Estados, categorías y contadores — coherencia con SDD

| Elemento | SDD | Implementación | Test |
|---|---|---|---|
| `ConsistencyState` (5) | §5 | Enum con 5 valores exactos | `EstadosNominalesTests`, `EstadosUnavailableTests`, `EstadosDegradedTests` |
| `DivergenceCategory` (16) | §6 tabla | Enum con 16 identificadores idénticos | `CategoriasInconsistentTests` (13 tests, uno por categoría accionable) |
| Prioridad `UNAVAILABLE` > `INCONSISTENT` > `DEGRADED` > `HEALTHY` | §5 reglas 1–3 | Orden en `manager_consistencia` líneas 470–491 | `test_manifest_corrupt_sin_backup` (UNAVAILABLE), `test_source_present_manifest_stale_chroma_present` (INCONSISTENT), `test_entradas_malformadas_aislables` (DEGRADED), `test_healthy_observado_y_publicado_degraded` (HEALTHY→DEGRADED publicado) |
| `HEALTHY_EMPTY` solo si capas lógicamente vacías | §5 reglas 4, 6 | `elif not fuentes and capas_sin_datos: pass` (no registra divergencia) | `test_healthy_empty_observado_y_publicado_degraded` ✅ |
| `MANIFEST_AND_CHROMA_EMPTY_SOURCES_PRESENT` precede a `MANIFEST_ABSENT`/`CHROMA_ABSENT` | §6 tabla | Lógica `capas_sin_datos` evaluada antes que ramas individuales | `test_manifest_and_chroma_empty_sources_present` ✅; 3 tests ajustados por Builder confirman precedencia |
| `orphan_sample` ≤ 10, orden determinista | §6, §9 | `tuple(huérfanos[:ORPHAN_SAMPLE_LIMIT])` con `huérfanos` lista ordenada por iteración de dict (Python 3.7+ insertion-order) | `test_orphan_sample_limited` ✅ |
| Sin purga | §9 | Ninguna operación de borrado en código | `test_nunca_lanza_ante_errores_de_coleccion` no purga; `test_source_absent_chroma_present_orphans` solo reporta |

---

## Evaluación de las 3 desviaciones declaradas por el Builder

| Desviación | Descripción | Compatibilidad con SDD |
|---|---|---|
| **1. Wrapper `ChromaReadAccess` en fixtures** | `_parchear_chroma` envuelve `FakeCollection` en `ChromaReadAccess(root_present=True, collection_present=True, collection=fake)` para que el verificador lea los atributos esperados. | ✅ **Compatible**. Detalle exclusivo de fixtures de test; no afecta código de producción. El verificador espera un objeto con la interfaz `ChromaReadAccess`; el fake la cumple vía envoltorio. |
| **2. `collection_present=True` cuando backend unavailable** | Adaptador devuelve `collection_present=True` en el branch `except Exception` (líneas 485–489). | ✅ **Compatible y correcto**. Semántica: la colección *existe* (se intentó abrir) pero el backend no responde. `unavailable=True` es la señal autoritativa; `collection_present=True` evita falsa categoría `CHROMA_COLLECTION_ABSENT`. Consistente con catch interno (líneas 391–396). |
| **3. Precedencia `manifest_and_chroma_empty_sources_present` en 3 tests ajustados** | Tests `test_manifest_absent_with_sources`, `test_chroma_absent_with_sources`, `test_chroma_collection_absent_with_sources` ahora configuran la otra capa con datos para que la categoría individual se registre (si ambas capas vacías, SDD manda la categoría combinada). | ✅ **Compatible y necesario**. Los tests originales tenían setup incorrecto respecto a la SDD: con fuentes presentes y ambas capas vacías, la categoría correcta es `MANIFEST_AND_CHROMA_EMPTY_SOURCES_PRESENT`, no la individual. El ajuste alinea los tests al contrato. |

**Conclusión:** Las tres desviaciones son **compatibles con la SDD**; ninguna constituye cambio contractual no aprobado.

---

## Hallazgos por severidad

### 🟢 Sin hallazgos bloqueantes (CRITICAL / HIGH)

### 🟡 Observaciones (MEDIUM / LOW)

| ID | Hallazgo | Severidad | Impacto | Remediación mínima |
|---|---|---|---|---|
| OBS-01 | `except Exception` defensivo en `verificar_consistencia` (línea 493) marcado `# pragma: no cover` — no testeado. | LOW | Cobertura incompleta de la red de seguridad; si se dispara, reporta `DEGRADED` con `verification_limitation=1`. | Documentar como defensivo intencional; no requiere test (por diseño `pragma: no cover`). |
| OBS-02 | Errores sanitizados en `ChromaReadAccess.error` incluyen `type(e).__name__: e` — podría filtrar rutas absolutas si la excepción las contiene (p. ej., `FileNotFoundError: /ruta/privada/...`). | LOW | Fuga potencial de rutas privadas en reporte/serialización. | Sanitizar `error` removiendo rutas absolutas antes de asignar (ej. `re.sub(r'[A-Za-z]:[\\/].*', '<path>', str(e))`). |
| OBS-03 | Dependencia implícita de `chroma.sqlite3` como heurística de "raíz inicializada". | LOW | Si Chroma cambia layout en versión futura, el adaptador podría clasificar mal. | Documentar como heurística de versión 0.5.x; test de regresión si se actualiza chromadb. |
| OBS-04 | `orphan_sample` usa orden de iteración de dict (insertion-order Python 3.7+). Determinista en una ejecución, pero no ordenado explícitamente (p. ej., por chunk_id). | LOW | Muestra no estable entre versiones de Python si cambia orden de inserción. | Ordenar `huérfanos` antes de slice: `sorted(huérfanos)[:ORPHAN_SAMPLE_LIMIT]`. |
| OBS-05 | `possibly_transient=True` y `writer_state_known=False` hardcodeados — por diseño hasta IDX-C2. | LOW | Estado publicado siempre `DEGRADED` para resultados nominales. | Resolver en IDX-C2 (contrato de escritor único). |

---

## Riesgos residuales

| Riesgo | Estado | Nota |
|---|---|---|
| `except Exception` no cubierto | **ACEPTADO** | Defensivo por contrato; `pragma: no cover` documentado. |
| Errores sin sanitizar rutas | **OBSERVADO** | OBS-02; no bloquea, bajo riesgo en contexto local single-user. |
| Heurística `chroma.sqlite3` | **ACEPTADO** | Adaptador interno, testeado; actualizable en corte futuro si chromadb cambia. |
| `orphan_sample` orden implícito | **OBSERVADO** | OBS-04; no afecta corrección, solo estabilidad de muestra. |
| Writer state desconocido hasta IDX-C2 | **POR DISEÑO** | SDD §11.2 explícito: `writer_state_known=False` → `DEGRADED` publicado. |

---

## Limitaciones de la auditoría

1. **No se ejecutó contra ChromaDB real** — por política de testing (SDD §7.7, §14.1): tests usan fakes y temporales. La integración real se validará en IDX-C3/INT-C7.
2. **No se verificó `origin/main` fresco** — `git fetch` no autorizado; frescura remota `UNVERIFIED` hasta INT-C7 (SDD §15).
3. **Cobertura de `except Exception` no medida** — `pragma: no cover` excluye de cobertura intencionalmente.
4. **Rutas privadas en errores** — no se inyectaron excepciones con rutas reales para confirmar fuga; análisis estático únicamente.
5. **Concurrencia de escritor** — fuera de alcance (IDX-C2); el verificador reporta `possibly_transient=True` por contrato.

---

## Gate final

**Veredicto: `PASS WITH OBSERVATIONS`**

### Justificación
- ✅ Alcance Git correcto (4 archivos autorizados; working tree de usuario preservado).
- ✅ Contrato read-only demostrado (código + tests de contrato).
- ✅ Adaptador Chroma cumple semántica requerida (4 estados distinguidos, tests verdes).
- ✅ 5 estados, 16 categorías, reporte completo coherentes con SDD §5, §6, §11.2.
- ✅ Manifiesto: ausente/corrupto/incompatible distinguidos; sin `.bak`; malformadas aislables → `DEGRADED`.
- ✅ Fuentes/hashes: política `core.config`, atajo size+mtime, SHA-256 condicional, distinción contenido vs metadata.
- ✅ Categorías/contadores: multi-label, `orphan_count`/`orphan_sample` correctos, sin purga.
- ✅ Suite enfocada (37) y completa (186) verdes; `compileall` limpio; `git diff --check` limpio.
- ✅ 3 desviaciones del Builder evaluadas: compatibles con SDD.
- ⚠️ 5 observaciones (OBS-01 a OBS-05) — **no bloqueantes**, documentadas para resolución en cortes futuros o como deuda conocida.

### Próximos pasos recomendados (fuera de este corte)
1. Sanitizar `error` en adaptador (OBS-02).
2. Ordenar `orphan_sample` explícitamente (OBS-04).
3. Resolver writer state en IDX-C2 (OBS-05).
4. Revisar heurística `chroma.sqlite3` si se actualiza chromadb.

---

**Fin del informe.**
No se realizaron stage, commit ni push. Working tree final idéntico al inicial.
