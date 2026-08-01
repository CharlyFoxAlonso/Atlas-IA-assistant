# Auditoría técnica de corte — SDD-0 incremental indexing contracts

Fecha: 2026-08-01
Tipo: Corte
Repositorio: Atlas
Rama: atlas-v4.1-incremental-indexing
Commit base: 2a4700d30231b44f6d17027333f2a994a46e2386
Commit final: aba2d437a6ceeb29a960b6af9a6f7c2b07111307
Rango auditado: 2a4700d..aba2d43
Archivo: docs/spec/atlas-v4.1-incremental-indexing-sdd.md
Gate: ACCEPT WITH NON-BLOCKING FINDINGS

---

## 1. Resumen ejecutivo

La SDD-0 (`docs/spec/atlas-v4.1-incremental-indexing-sdd.md`) es la especificación gobernante para la indexación incremental de Atlas 4.1. El corte documental (commits `e3f428f` y `aba2d43`, mismo mensaje) introduce **solo** la SDD y dos enlaces descriptivos en `README.md` y `docs/architecture/incremental-indexing.md`. No hay cambios en código de producción ni tests.

La SDD es **coherente con el código y la evidencia existente** y **puede gobernar los cortes IDX-C1 a INT-C7**. Los contratos de comportamiento (`CURRENT`/`TARGET_REQUIRED_FOR_V4.1`/`DEFERRED`/`OUT_OF_SCOPE`/`UNVERIFIED`) están bien separados; los estados y categorías de divergencia son consistentes con la implementación actual; el contrato read-only de IDX-C1 es estricto y verificable; el orden IDX-C1 → IDX-C2 → IDX-C3 se respeta; la purga de huérfanos está explícitamente fuera de v4.1; la política configured/legacy y la separación `ATLAS_DATA_DIR`/`ATLAS_MEMORY_DIR` coinciden con `core/system/paths.py` y `core/config.py`.

Un hallazgo LOW no bloqueante (F-06) documentado como seguimiento; el resto de observaciones menores se descartaron por confirmar coherencia.

---

## 2. Objetivo

Determinar si la SDD-0 es coherente con el código y la evidencia existente, y si puede gobernar los cortes IDX-C1 a INT-C7.

---

## 3. Alcance

- Rango de commits: `2a4700d..aba2d43` (3 archivos: SDD + 2 enlaces descriptivos)
- Artefacto principal: `docs/spec/atlas-v4.1-incremental-indexing-sdd.md`
- Verificación de coherencia con: `core/indexer.py`, `core/index_manifest.py`, `core/vector_store.py`, `core/config.py`, `core/system/paths.py`, tests `test_incremental_indexing.py`, `test_vector_paths.py`, `test_backup_paths.py`

---

## 4. Fuera de alcance

- Implementación de IDX-C1..INT-C7 (futuros cortes)
- Validación de comportamiento en entorno de usuario real (fuera de tests)
- Decisiones de merge/push (requieren autorización explícita)

---

## 5. Estado Git

- Rama: `atlas-v4.1-incremental-indexing`
- HEAD: `aba2d437a6ceeb29a960b6af9a6f7c2b07111307`
- Working tree: no había archivos modificados ni staged. El único untracked al finalizar era el propio reporte: `docs/reviews/cuts/2026-08-01-aba2d43-sdd0-incremental-indexing-contracts-review.md`.
- Commits en rango:
  - `e3f428f` — docs(spec): define Atlas 4.1 incremental indexing contracts (SDD + 2 enlaces)
  - `aba2d43` — docs(spec): define Atlas 4.1 incremental indexing contracts (mismo mensaje, sin cambios funcionales adicionales)
- Base: `2a4700d30231b44f6d17027333f2a994a46e2386` (commit previo: docs(reviews): add vector storage path audit)

---

## 6. Instrucciones aplicables

- `AGENTS.md` (raíz)
- `.agents/playbooks/audit.md`
- `.agents/policies/git-safety.md`
- `.agents/policies/testing.md`

---

## 7. Entorno reproducido

- Repositorio: `C:\Users\delfa\Documents\Atlas`
- Python: `.venv\Scripts\python.exe` (3.13)
- Tests inspeccionados (no ejecutados por política de auditoría): `test_incremental_indexing.py` (35 tests), `test_vector_paths.py` (8 tests), `test_backup_paths.py` (4 tests) — todos usan fakes y directorios temporales, sin datos reales.

---

## 8. Diff inspeccionado

| Archivo | Cambios |
|---|---|
| `docs/spec/atlas-v4.1-incremental-indexing-sdd.md` | +546 líneas (nuevo archivo) |
| `README.md` | +2 líneas (enlace a SDD como especificación gobernante) |
| `docs/architecture/incremental-indexing.md` | +1 línea (autoridad descriptiva, remite a SDD) |

**Solo documentación.** Sin cambios en `core/`, `tests/`, `scripts/`, dependencias, ni configuración.

---

## 9. Criterios de aceptación evaluados

| Criterio | Resultado | Evidencia |
|---|---|---|
| Separación clara de marcas de estado (`CURRENT`, `TARGET_REQUIRED_FOR_V4.1`, `DEFERRED`, `OUT_OF_SCOPE`, `UNVERIFIED`) | **PASS** | Sección 2 (Modelo de estado) define 5 marcas con regla explícita: "ninguna sección puede describir comportamiento `TARGET_REQUIRED_FOR_V4.1` como ya implementado". Todas las tablas usan marcas consistentemente. |
| Coherencia de estados y categorías de divergencia | **PASS** | 5 estados (HEALTHY, HEALTHY_EMPTY, INCONSISTENT, DEGRADED, UNAVAILABLE) con 10 reglas de derivación. 16 categorías de divergencia con identificadores estables, estado resultante y acción prevista. Coinciden con comportamiento de `core/indexer.py` (sync: size+mtime → SHA-256; rebuild; delete). |
| Contrato read-only estricto de IDX-C1 | **PASS** | Sección 7: 7 reglas. Prohíbe escritura, `IndexManifest.load` mutante, creación de almacenamiento Chroma, embeddings/modelos, conversión a `HEALTHY_EMPTY`. Exige lectura no mutante de manifiesto (JSON crudo + validación propia) y distinción `chroma_collection_absent` vs `chroma_unavailable`. |
| Orden IDX-C1 → IDX-C2 → IDX-C3 | **PASS** | Sección 13 roadmap: 1=SDD-0, 2=IDX-C1 (verificación), 3=IDX-C2 (lock), 4=IDX-C3 (reparación). Dependencias: "IDX-C1 antes de IDX-C3; IDX-C2 antes de IDX-C3 y de IDX-C5". Sección 11.6: "la implementación del bloqueo es su propio corte (IDX-C2)". |
| Ausencia de purga de huérfanos en v4.1 | **PASS** | Sección 9: `DEFERRED` para purga; `TARGET_REQUIRED_FOR_V4.1` solo para detección. "Nunca purgarlos automáticamente", "no exponer opción `purgar_huérfanos=True`", "la purga queda diferida". Sección 8 "No puede": "Borrar vectores huérfanos". Sección 12: "Purga destructiva" = `DEFERRED`. |
| Política configured/legacy | **PASS** | Glosario `Configured storage` (L100): `ATLAS_DATA_DIR` controla raíz vectorial (`CHROMA_PATH`, `INDEX_MANIFEST_PATH`); `ATLAS_MEMORY_DIR` controla exclusivamente `BASE_MEMORIA`. `Legacy storage`: 4 casos (mismo path → continúa; difieren → configured; legacy-only → error duro `LegacyVectorStoreError`; nunca fallback/fusión/migración). Coincide con `core/system/paths.py` `validate_vector_store_path` (L48-73) y tests `test_vector_paths.py` (4 casos). |
| Separación `ATLAS_DATA_DIR` vs `ATLAS_MEMORY_DIR` | **PASS** | Glosario y `core/config.py` L186-191: `BASE_MEMORIA = private_memory_dir` (derivado de `ATLAS_MEMORY_DIR`); `CHROMA_PATH = chroma_dir` (derivado de `ATLAS_DATA_DIR`). `core/system/paths.py` L95-96 y L106-108 confirman independencia. |
| Consistencia de referencias de cortes | **PASS** | Todas las referencias IDX-C1..INT-C7, DOC-C6, SDD-0 son consistentes en secciones 1.1, 7, 8, 9, 11, 12, 13, 14. No hay referencias cruzadas rotas. |
| Rango solo cambia SDD (no producción ni tests) | **PASS** | `git diff --name-only 2a4700d..aba2d43` → solo 3 archivos de documentación. |

---

## 10. Hallazgos

### BLOCKER
*(ninguno)*

### HIGH
*(ninguno)*

### MEDIUM
*(ninguno)*

### LOW

| ID | Severidad | Archivo | Líneas | Problema | Evidencia | Impacto | Corrección mínima | Prueba de aceptación | Estado |
|---|---|---|---|---|---|---|---|---|---|
| F-06 | LOW | SDD §13 | 472-475 | Dependencias: "IDX-C1 antes de IDX-C3 (el post-check de la reparación usa la verificación); IDX-C2 antes de IDX-C3 (la reparación es escritora) y de IDX-C5 (superficie de reparación)". Correcto. Pero IDX-C4 (superficies de estado) no depende explícitamente de IDX-C1; se asume. | Sección 12: IDX-C4 expone estado derivado de §5. | Añadir "IDX-C1 antes de IDX-C4" en dependencias para claridad. No invalida la SDD ni requiere modificarla antes de comenzar IDX-C1. | Añadir explícitamente la dependencia `IDX-C1 antes de IDX-C4` en la tabla de dependencias de §13. | IDX-C4 implementado tras IDX-C1. | CONFIRMED |

---

## 11. Claims confirmados

| Claim | Confirmado por |
|---|---|
| SDD es especificación gobernante única | `README.md` + `docs/architecture/incremental-indexing.md` enlazan a SDD; SDD §1 "Ningún otro documento define estos contratos" |
| 5 marcas de estado bien separadas | SDD §2 tabla + regla; uso consistente en todas las tablas |
| 5 estados de consistencia con 10 reglas de derivación | SDD §5; coherente con `core/indexer.py` sync logic |
| 16 categorías de divergencia con identificadores estables | SDD §6 tabla; mapean a comportamientos de `core/indexer.py` |
| IDX-C1 read-only estricto (7 reglas) | SDD §7; no escritura, no `IndexManifest.load` mutante, no creación Chroma, no embeddings |
| Orden IDX-C1 → IDX-C2 → IDX-C3 | SDD §13 roadmap + dependencias + §11.6 |
| Purga de huérfanos fuera de v4.1 | SDD §9 (DEFERRED), §8 (No puede), §12 (DEFERRED) |
| Política configured/legacy 4 casos | SDD Glosario + `core/system/paths.py` `validate_vector_store_path` + tests |
| Separación `ATLAS_DATA_DIR` (vectorial) / `ATLAS_MEMORY_DIR` (fuentes) | SDD Glosario `Configured storage` + `core/config.py` L186-191 + `core/system/paths.py` |
| Rango solo documentación | `git diff --name-only 2a4700d..aba2d43` |

---

## 12. Claims parciales

*(ninguno)*

---

## 13. Claims no verificados

| Claim | Por qué |
|---|---|
| IDX-C1 implementable con los contratos actuales | Requiere implementación futura; SDD define contrato, no implementación |
| Algoritmo de lock stale (IDX-C2) funcionará en Windows sin POSIX | SDD §11.5 declara "Windows obligatorio... vía compatible declarada, sin decisión final aquí"; se decide en IDX-C2 con tests de inyección |
| `mismatch_chunk_counts` DEFERRED es correcto | SDD §6 decisión contractual; código actual registra `chunk_count` pero no lo valida; coherente |

---

## 14. Falsos positivos descartados

| Posible hallazgo | Por qué se descarta |
|---|---|
| Dos commits con mismo mensaje (`e3f428f` y `aba2d43`) | Instrucción explícita: "No lo consideres un hallazgo por sí solo ni reescribas historia". No hay cambios funcionales entre ellos. |
| `core/vector_store.py` usa `get_or_create_collection` | SDD §7.3 prohíbe al verificador; `_get_collection` es vía de escritura (indexación), no de verificación. Separación correcta. |
| `IndexManifest.load` respalda corrupto (efecto escritura) | SDD §7.2 lo prohíbe al verificador; el verificador usa "lectura del JSON crudo + validación estructural propia". Correcto. |
| `reconstruir_indice_completo` no vacía colección | SDD §1 Glosario `Rebuild`: "reindexa todo por identidad sin vaciar la colección y retira documentos ausentes". Coincide con `core/indexer.py` L388-395. |
| Prioridad de estados: `UNAVAILABLE > INCONSISTENT > DEGRADED > HEALTHY/HEALTHY_EMPTY` | Correcta. SDD §5 regla 3: DEGRADED tiene prioridad sobre HEALTHY/HEALTHY_EMPTY; regla 9 degrada a DEGRADED cuando `writer_state_known=False`. Coherente con el modelo de verificación (no fue hallazgo; el propio análisis confirma coherencia). |
| Categoría `source_and_manifest_and_chroma_present` con `size_bytes` y `modified_time_ns` coincidentes | Correcta. Representa correctamente el fast path saludable: `core/indexer.py` L435-461 usa el atajo size+mtime y solo calcula SHA-256 cuando difieren. Coincidencia de size+mtime es suficiente para HEALTHY. |
| SDD §7 punto 4: huella size/mtime coincidente → vigente sin releer; si difiere → SHA-256 en modo lectura | Coherente con `core/indexer.py` L445 (`_sha256_archivo` lee bloques sin mutar). Observación redundante sin impacto ni corrección. |
| SDD §8 "Puede" ítems 1 y 5 (reparar fuentes no correspondientes; actualizar solo size/mtime cuando SHA-256 es idéntico) | Coincide con `core/indexer.py` L454-460 (actualiza entry.size_bytes y modified_time_ns sin reindexar). Observación redundante sin impacto ni corrección. |
| SDD §11 punto 2: campos `writer_state_known`, `writer_active`, `possibly_transient` congelados | Coherente con regla 9 de §5 y DEGRADED (pre-IDX-C2: `False/False/True`; post-IDX-C2: `True/False/False` o `True/True/True`). Observación redundante sin impacto ni corrección. |

---

## 15. Mapa de riesgos

| Área | Riesgo | Mitigación en SDD |
|---|---|---|
| Verificación read-only (IDX-C1) | Acceso accidental a `IndexManifest.load` mutante | §7.2: vía no mutante obligatoria; tests usan fakes |
| Lock stale (IDX-C2) | PID reuse, metadata incompleta | §11.5: "nunca se decide por tiempo transcurrido"; evidencia de inactividad requerida; estados dudosos bloquean recuperación |
| Reparación conservadora (IDX-C3) | Reembebido innecesario | §8 regla general: "Solo se reembebe cuando el contenido cambió o cuando faltan chunks" |
| Purga huérfanos | Activación accidental | §9: `DEFERRED`, sin opción interna, API no acepta purga |
| Config/legacy split | Migración silenciosa | `validate_vector_store_path` lanza `LegacyVectorStoreError` en caso legacy-only |

---

## 16. Deuda técnica candidata

| Deuda | Origen | Estado en SDD |
|---|---|---|
| Persistencia de fallos de archivos nuevos (INV-7) | `core/indexer.py` `_marcar_error_en_manifest` solo anota entradas conocidas | §14.4 `DEFERRED` |
| Asimetría reporte `eliminar_documento_indexado` (INV-6) | `manifest.save` falla solo se loguea | §14.4 `DEFERRED` |
| Limpieza `.tmp` huérfanos del manifiesto | Escritura atómica deja `.tmp` si crash antes de `os.replace` | §14.4 `DEFERRED` |
| Verificación profunda de conteos (`mismatch_chunk_counts`) | Manifiesto registra `chunk_count` pero no se valida | §6 decisión contractual `DEFERRED` |
| Purga huérfanos con flujo confirmación | Fuera de v4.1 | §9, §12, §14.4 `DEFERRED` |
| Cambio modelo embeddings como disparador reindexación | Informativo hoy | §14.4 `DEFERRED` |

---

## 17. Próximos cortes candidatos

| Corte | Entregable | Dependencia |
|---|---|---|
| IDX-C1 | `core/index_consistency.py` + tests (verificación read-only) | SDD-0 |
| IDX-C2 | Lock fail-fast + stale safety (Windows) | SDD-0 |
| IDX-C3 | Reparación conservadora + post-check | IDX-C1, IDX-C2 |
| IDX-C4 | Superficies estado read-only (Doctor + `!indexar status`) | IDX-C1 |
| IDX-C5 | Superficie reparación (Healer + CLI, dry-run) | IDX-C3 |
| DOC-C6 | Reconciliación documental final | IDX-C1..C5 |
| INT-C7 | Puerta integración completa + clasificación commits | DOC-C6 |

---

## 18. Limitaciones

- Auditoría basada en inspección de código estático y tests existentes; no se ejecutaron tests (política de solo lectura).
- No se validó comportamiento en entorno de usuario real (`memory/`, `vector_db/`, `.env` reales).
- No se observaron modificaciones en los datos protegidos durante la auditoría. El auditor no abrió su contenido real.
- `core/vector_store.py` inicialización perezosa de ChromaDB no se probó con backend real.
- La SDD congela contratos; la implementación futura (IDX-C1..INT-C7) debe ser auditada independientemente.

---

## 19. Estado final del working tree

```
?? docs/reviews/cuts/2026-08-01-aba2d43-sdd0-incremental-indexing-contracts-review.md
```

HEAD: `aba2d437a6ceeb29a960b6af9a6f7c2b07111307` (sin mover). No había archivos modificados ni staged; el único untracked era el propio reporte.

---

## 20. Conclusión

**Gate: ACCEPT WITH NON-BLOCKING FINDINGS**

La SDD-0 es **coherente con el código y la evidencia existente** y **puede gobernar los cortes IDX-C1 a INT-C7**. Hay **1 hallazgo LOW no bloqueante** (F-06): añadir explícitamente la dependencia `IDX-C1 antes de IDX-C4` es una aclaración útil; no invalida la SDD ni requiere modificarla antes de comenzar IDX-C1.

La separación de marcas de estado, el modelo de consistencia, el contrato read-only, el orden de cortes, la ausencia de purga, la política configured/legacy y la separación `ATLAS_DATA_DIR`/`ATLAS_MEMORY_DIR` están todos **verificados y consistentes**.

El rango `2a4700d..aba2d43` modifica **exclusivamente documentación** (SDD + 2 enlaces), sin tocar producción ni tests.

---

**Fin del informe.**