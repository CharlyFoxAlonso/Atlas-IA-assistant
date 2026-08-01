# SDD — Indexación incremental de Atlas 4.1

**Estado del documento:** ACTIVA (gobernante para la rama `atlas-v4.1-incremental-indexing`)
**Revisión:** SDD-0 (corte documental)
**Ruta:** `docs/spec/atlas-v4.1-incremental-indexing-sdd.md`
**Firmada por:** plan de cierre de la rama `atlas-v4.1-incremental-indexing`

Esta es la **especificación de diseño autoritativa** de la indexación incremental de
Atlas 4.1. Congela los contratos de comportamiento y consistencia que gobiernan los
cortes de implementación restantes (IDX-C1 a INT-C7 de la sección 13). Ningún otro
documento define estos contratos.

Documentos relacionados:

- `docs/architecture/incremental-indexing.md` — descripción de la implementación actual (descriptiva, no gobernante).
- `docs/architecture/system-subsystem.md` — descripción de `core/system` (descriptiva).
- `docs/TECHNICAL_DEBT.md` — registro de deuda técnica (fuente de verdad de deuda).
- `docs/rfcs/RFC-0008..0011` — decisiones históricas; RFC-0011 está `Superseded`.
- `README.md` — identidad pública y roadmap.

---

## Modelo de estado de comportamiento

Todo comportamiento material de esta SDD lleva exactamente una marca:

| Marca | Significado |
|---|---|
| `CURRENT` | Comportamiento verificado en el código y los tests actuales de la rama. |
| `TARGET_REQUIRED_FOR_V4.1` | Comportamiento contractual obligatorio para declarar Atlas 4.1 completo. **No está implementado todavía**; no debe describirse como implementado. |
| `DEFERRED` | Decidido pero fuera del alcance de v4.1; requiere corte propio. |
| `OUT_OF_SCOPE` | Explícitamente fuera de esta rama y de esta especificación. |
| `UNVERIFIED` | Comportamiento declarado en documentación o inferido, sin evidencia ejecutada en la revisión actual. |

Regla: ninguna sección puede describir comportamiento `TARGET_REQUIRED_FOR_V4.1`
como ya implementado. Los verbos futuros (`debe`, `podrá`, `se verificará`) marcan
contratos, no hechos.

---

## 1. Propósito y alcance

### 1.1 Qué significa "completar Atlas 4.1"

Completar Atlas 4.1 significa que la rama `atlas-v4.1-incremental-indexing` queda
lista para integrarse en `origin/main` con los siguientes atributos:

1. La indexación incremental local y web funciona según los contratos congelados en
   esta SDD (identidad estable, manifiesto atómico, sincronización por diferencias,
   reconstrucción explícita sin vaciado).
2. La consistencia entre fuentes, manifiesto y ChromaDB es **verificable en modo
   solo lectura** (IDX-C1) y **reparable de forma conservadora** (IDX-C2).
3. Las operaciones de escritura están protegidas contra escritores concurrentes
   (IDX-C3).
4. El estado del índice es observable desde superficies de solo lectura (IDX-C4) y la
   reparación conservadora tiene una superficie explícita con confirmación (IDX-C5).
5. La documentación identifica esta SDD como gobernante (DOC-C6).
6. La integración final pasa la puerta de validación INT-C7.

### 1.2 Alcance de esta SDD

- Identidad de documentos y chunk IDs.
- Manifiesto de indexación (formato `schema_version=1`, publicación atómica).
- Ubicación autoritativa del almacenamiento vectorial.
- Detección de divergencias, estados de consistencia y reparación conservadora.
- Contrato de escritor único.
- Superficies operativas de estado y reparación.

### 1.3 Fuera del alcance de esta rama

`OUT_OF_SCOPE`:

- Migración automática de almacenamiento legacy o reposicionamiento de memoria.
- Purga automática de vectores huérfanos (ver sección 9).
- Cambios al esquema del manifiesto (`schema_version` permanece en 1 durante v4.1).
- Seguimientos de crawler (ATLAS-TD-001/002/003), perfiles (ATLAS-TD-014),
  licencia (ATLAS-TD-018), rutas OCR/PDF (ATLAS-TD-021), dashboard avanzado,
  Chat Session Exporter y todo lo listado como v4.2 en el roadmap del README.
- Cambios de dependencias, instalador o distribución.
- Cambios de contrato público de `core/indexer.py`, `core/index_manifest.py`,
  `core/vector_store.py` y `core/config.py` (los contratos actuales se preservan;
  la verificación y reparación se construyen alrededor de ellos).

---

## 2. Glosario

| Término | Definición |
|---|---|
| **Source document** | Archivo de la biblioteca (`BASE_MEMORIA`) con extensión soportada (`INDEX_SUPPORTED_EXTENSIONS`) y contenido indexable. Su existencia y contenido son propiedad del filesystem. |
| **Relative document identity** | Ruta del source document relativa a `BASE_MEMORIA`, normalizada con `/`. Es la identidad estable del documento (`doc_id`) en v4.1. `CURRENT`. |
| **Manifest entry** | Registro del manifiesto para un documento: `content_sha256`, `size_bytes`, `modified_time_ns`, `indexed_at`, `chunk_count`, `last_operation`, `last_error`. `CURRENT`. |
| **Chroma document** | Conjunto de chunks en la colección `atlas_rag` asociados a una identidad de documento (metadata `doc_id`, o `ruta` en el esquema legacy). |
| **Chunk** | Fragmento de texto indexado con ID determinista `{doc_id}:chunk:{i}` (esquema v4.1) o `{doc_id}_chunk_{i}` (esquema legacy). `CURRENT`. |
| **Synchronization** | `sincronizar_indice()`: procesa solo diferencias contra el manifiesto (nuevos, modificados por SHA-256, sin cambios por atajo size+mtime, eliminados, fallidos). `CURRENT`. |
| **Rebuild** | `reconstruir_indice_completo()` (alias histórico `construir_indice()`): reindexa todo por identidad sin vaciar la colección y retira documentos ausentes. `CURRENT`. |
| **Divergence** | Diferencia observable entre las capas fuente / manifiesto / Chroma que el modelo de estados clasifica (sección 6). `CURRENT` (concepto) / verificación `TARGET_REQUIRED_FOR_V4.1`. |
| **Orphan vector** | Chunk(s) en Chroma sin entrada de manifiesto y sin source document en disco. Se detecta y reporta; nunca se purga automáticamente (sección 9). `TARGET_REQUIRED_FOR_V4.1` (detección). |
| **Unindexed source** | Source document presente en disco sin estado de indexación vigente (sin entrada de manifiesto y/o sin chunks). `CURRENT` (estado real alcanzable) / tratamiento `TARGET_REQUIRED_FOR_V4.1`. |
| **Configured storage** | Ubicación del almacenamiento vectorial derivada de la política central de rutas (`get_paths()`, `ATLAS_DATA_DIR`/`ATLAS_MEMORY_DIR`), validada por `validate_vector_store_path`. `CURRENT`. |
| **Legacy storage** | Ubicación `cwd/vector_db` distinta de la configurada. Su coexistencia ambigua produce error duro, nunca fusión ni fallback silencioso. `CURRENT`. |
| **Consistency check** | Verificación de solo lectura que clasifica el estado del índice en uno de los estados de la sección 5. `TARGET_REQUIRED_FOR_V4.1`. |
| **Conservative repair** | Operación separada que restaura la convergencia reindexando documentos presentes en disco, sin borrar vectores, sin mover almacenamiento y sin purgar datos legacy. `TARGET_REQUIRED_FOR_V4.1`. |
| **Committed indexing operation** | Operación de escritura del índice (sección 11) que adquiere el contrato de escritor único antes de mutar manifiesto o Chroma. `CURRENT` (operaciones) / exclusividad `TARGET_REQUIRED_FOR_V4.1`. |

---

## 3. Modelo de autoridad

Ninguna capa es, por sí sola, la fuente de verdad completa. La verdad es la
**relación** entre las capas, y la autoridad se distribuye así:

| Dominio | Componente autoritativo | Estado |
|---|---|---|
| Existencia y contenido de los source documents | El filesystem (disco). El manifiesto solo lo referencia por huella, no lo reemplaza. | `CURRENT` |
| Identidad del documento | Ruta relativa normalizada con `/` respecto de `BASE_MEMORIA` (derivada por el indexador; nunca el basename ni la ruta absoluta). | `CURRENT` |
| Última huella indexada con éxito | Entrada del manifiesto (`content_sha256`, `size_bytes`, `modified_time_ns`). El manifiesto registra el último estado bueno conocido; no prueba disponibilidad vectorial. | `CURRENT` |
| Disponibilidad vectorial | ChromaDB (colección `atlas_rag`): presencia y retiro de chunks por identidad. Chroma no conoce el contenido fuente; solo la materialización vectorial. | `CURRENT` |
| Ubicación de almacenamiento configurada | `core.system.paths.get_paths()` (política central), expuesta por `core.config` (`CHROMA_PATH`, `INDEX_MANIFEST_PATH`), protegida por `validate_vector_store_path`. | `CURRENT` |
| Estado operativo visible | Estado derivado del consistency check (sección 5). Ninguna capa individual puede declararse "el estado del índice". | `TARGET_REQUIRED_FOR_V4.1` |

Consecuencia contractual: un manifiesto presente no implica vectores presentes, y
vectores presentes no implican fuente presente. Cualquier superficie que afirme el
estado del índice debe derivarlo de la verificación, no de una sola capa.

---

## 4. Invariantes actuales

Solo invariantes respaldados por el código y los tests actuales de la rama.

- **INV-1 — Contención de rutas (`CURRENT`).** Todo archivo indexado debe resolverse
  como descendiente de `BASE_MEMORIA` (resolución de symlinks/junctions y `..`; rechazo
  de prefijos similares tipo `Atlas_Memory_Evil`; la base misma no es indexable). El
  rechazo ocurre antes de tocar loader, backend vectorial o manifiesto. Evidencia:
  `core/indexer.py` `_resolver_contenida_en_base`; tests de rechazo en
  `tests/test_incremental_indexing.py`.
- **INV-2 — Identidad relativa normalizada (`CURRENT`).** La identidad es la ruta
  relativa con `/`, estable e independiente de la ubicación absoluta. Chunk IDs
  deterministas `{doc_id}:chunk:{i}`. Evidencia: `core/indexer.py`; `core/vector_store.py`;
  tests de determinismo y de no-duplicación.
- **INV-3 — Publicación atómica del manifiesto (`CURRENT`).** El manifiesto solo se
  publica por `os.replace` tras `.tmp` + flush + fsync; nunca se lee un JSON parcial.
  Un manifiesto corrupto se respalda como `.bak` y se reconstruye vacío sin tocar
  ChromaDB. Evidencia: `core/index_manifest.py`; tests dedicados.
- **INV-4 — Raíz vectorial autoritativa única (`CURRENT`).** Chroma y manifiesto
  comparten raíz. Si la ruta configurada no existe pero hay un `cwd/vector_db` distinto,
  la inicialización se detiene con error duro: no hay fallback, movimiento ni
  combinación automática. Evidencia: `core/system/paths.py` `validate_vector_store_path`;
  `tests/test_vector_paths.py`, `tests/test_backup_paths.py`.
- **INV-5 — Reindexación deduplicante (`CURRENT`).** Antes de insertar la versión
  nueva, se eliminan los chunks previos del documento (esquema `doc_id` y variantes
  legacy `ruta`). Reindexar o reconstruir nunca duplica permanentemente. Evidencia:
  `core/vector_store.py` `agregar_documento`/`eliminar_documento`; tests de
  no-duplicación y de recuperación tras delete→add fallido.
- **INV-6 — Recuperación actual tras éxito en Chroma y fallo de manifiesto
  (`CURRENT`).** Si el `add` en Chroma tiene éxito pero `manifest.save` falla, el
  resultado se reporta como fallido ("indexado en ChromaDB pero falló el manifiesto"),
  el desfase converge en una sincronización posterior (stat/hash difieren → reindexa con
  deduplicación). Limitación conocida: en `eliminar_documento_indexado` un fallo de
  `manifest.save` solo se registra en el log y el resultado conserva su estado
  (`deleted`/`not_found`) — asimetría aceptada y registrada como deuda (ver 14.4).
  Evidencia: `core/indexer.py`; test de regresión en `tests/test_incremental_indexing.py`.

Invariante complementario (comportamiento actual, no defecto declarado):

- **INV-7 — Fallos de archivos nuevos no se persisten (`CURRENT`).** Un documento
  nunca indexado que falla no crea entrada en el manifiesto (`_marcar_error_en_manifest`
  solo anota entradas conocidas). El reintento ocurre en cada sincronización. La
  persistencia de estados de fallo es `DEFERRED` (sección 14.4).

---

## 5. Estados de consistencia objetivo

Modelo explícito de estados. Un booleano de conveniencia (p. ej., `ok`) podrá
exponerse más adelante, pero **debe derivarse** del estado explícito, nunca
reemplazarlo.

| Estado | Cuándo aplica |
|---|---|
| `HEALTHY` | Manifiesto presente y legible; Chroma responde; todo source document soportado tiene chunks; no hay vectores registrables ni huérfanos; no hay entradas sin archivo pendientes de retiro. |
| `HEALTHY_EMPTY` | Las tres capas están vacías (adopción inicial sin fuentes, sin manifiesto ni Chroma). |
| `INCONSISTENT` | Existe al menos una divergencia accionable (sección 6): faltantes en Chroma con fuente presente, vectores sin entrada ni fuente, entradas sin archivo, fuentes sin indexar, o manifest/Chroma ausente con la otra capa no vacía. |
| `DEGRADED` | La verificación no pudo evaluarse por completo sin evidencia de divergencia accionable: entradas malformadas ignoradas al leer el manifiesto, candidatos huérfanos legacy no confirmables, o limitaciones de verificación activas (p. ej., verificación profunda de conteos diferida). |
| `UNAVAILABLE` | Manifiesto corrupto (ilegible estructuralmente) o Chroma inaccesible de modo que impide determinar la consistencia. **Nunca se convierte en `HEALTHY_EMPTY`.** |

Reglas de derivación (`TARGET_REQUIRED_FOR_V4.1`):

1. `UNAVAILABLE` tiene prioridad sobre cualquier otro estado.
2. `INCONSISTENT` tiene prioridad sobre `DEGRADED`.
3. `HEALTHY_EMPTY` aplica solo cuando las tres capas están vacías; si existen fuentes,
   aplica `INCONSISTENT` (fuentes sin indexar), aunque el manifiesto y Chroma estén vacíos.
4. El estado se calcula desde cero en cada verificación; no se persiste.

---

## 6. Categorías de divergencia requeridas

Identificadores estables en inglés, aptos para campos de dataclass futuros.
Para cada categoría se indica el estado de consistencia resultante y la acción prevista.

| Identificador | Condición | Estado resultante | Acción prevista |
|---|---|---|---|
| `source_and_manifest_and_chroma_present` | Fuente en disco, entrada de manifiesto y chunks presentes | `HEALTHY` (nominal) | Ninguna |
| `source_and_manifest_present_chroma_absent` | Fuente y entrada presentes; chunks ausentes | `INCONSISTENT` | Reparación conservadora: reindexar la fuente (dedup-safe) |
| `source_present_manifest_absent_chroma_present` | Fuente presente; chunks sin entrada (vectores no registrados) | `INCONSISTENT` | Reparación: re-registrar reindexando la fuente |
| `source_present_manifest_absent_chroma_absent` | Fuente sin indexar | `INCONSISTENT` | Reparación: indexar la fuente |
| `source_absent_manifest_present` | Entrada sin archivo (pendiente de retiro) | `INCONSISTENT` | Sincronización/reparación: retirar chunks y entrada |
| `source_absent_chroma_present` | Vectores huérfanos reales (sin entrada, sin archivo) | `INCONSISTENT` | Detectar y reportar; **nunca** purgar en v4.1 (sección 9) |
| `manifest_absent_or_corrupt` | Manifiesto ausente o ilegible | `UNAVAILABLE` (corrupto) / ver reglas de ausencia | Reportar; no convertir en vacío saludable; reparación por re-registro si hay fuentes |
| `chroma_absent_or_unavailable` | Almacenamiento vectorial inexistente con entradas en manifiesto, o backend inaccesible | `INCONSISTENT` (vectores perdidos → reindexar) / `UNAVAILABLE` (sin acceso para verificar) | Reportar; reparación por reindexación |
| `manifest_and_chroma_empty_sources_present` | Manifiesto y Chroma vacíos con fuentes en disco | `INCONSISTENT` | Reparación: indexar todas las fuentes |
| `all_layers_empty` | Las tres capas vacías | `HEALTHY_EMPTY` | Ninguna |

Decisión contractual:

- **`mismatch_chunk_counts` NO es un campo requerido de v4.1.** El manifiesto registra
  `chunk_count` por documento, pero no existe semántica validada para reconciliar
  desviaciones de conteo (estados intermedios de crash, duplicados legacy, límites de
  chunking). La verificación de v4.1 se basa en presencia/ausencia de chunks por
  identidad, no en conteos exactos. La verificación profunda de conteos es
  `DEFERRED`.

---

## 7. Contrato de verificación de solo lectura

Contrato del consistency check (IDX-C1). `TARGET_REQUIRED_FOR_V4.1`.

El primer verificador de consistencia:

1. **No escribe, renombra, respalda, borra ni repara nada.** Es estrictamente de solo
   lectura sobre las tres capas.
2. **No invoca `IndexManifest.load` si esa operación puede mutar un manifiesto
   corrupto.** `IndexManifest.load` respalda el archivo corrupto (efecto de escritura);
   el verificador inspecciona el manifiesto por una vía de lectura no mutante: lectura
   del JSON crudo + validación estructural propia. La detección de corrupción se
   reporta como `manifest_absent_or_corrupt` / `UNAVAILABLE`; el respaldo `.bak`
   permanece exclusivamente en la vía de escritura.
3. **No crea almacenamiento Chroma.** No construye el cliente ni la colección si el
   almacenamiento no existe; cuando existe, accede a la colección existente sin
   semántica de creación y sin `get_or_create` implícito (ver sección 10).
4. **No embebe, no indexa y no contacta proveedores.** La verificación usa solo
   identidades y metadatos de Chroma (IDs de chunk, `doc_id`, `ruta`); nunca invoca
   consultas de texto que requieran embeddings ni ningún modelo.
5. **Reporta corrupción o indisponibilidad sin convertirlas en un estado vacío
   saludable.** `UNAVAILABLE` nunca deriva en `HEALTHY_EMPTY` (sección 5).
6. **En ejecución real, inspecciona solo almacenamiento temporal o datos configurados
   autorizados por el usuario.** Nunca explora fuera de `BASE_MEMORIA` ni de la raíz
   vectorial autoritativa.
7. **En tests, usa fakes y datos temporales.** Prohibido ejecutar contra `memory/`,
   `vector_db/` o `.env` reales.

Inspección de un manifiesto corrupto sin efectos de recuperación: el verificador lee
el archivo con `json.load` (o equivalente) en modo lectura; si la estructura no
cumple el esquema (`documents` como dict, `schema_version` compatible), lo clasifica
como corrupto, reporta `UNAVAILABLE` y **no** crea `.bak`, no renombra y no reinicia
estado. La decisión de respaldar y reconstruir sigue siendo del flujo de escritura
existente (`IndexManifest.load`), no del verificador.

---

## 8. Contrato de reparación conservadora

Operación separada de la verificación (IDX-C2). `TARGET_REQUIRED_FOR_V4.1`.

**Puede:**

1. Reindexar source documents soportados presentes en disco
   (`source_and_manifest_present_chroma_absent`, `source_present_manifest_absent_*`,
   `manifest_and_chroma_empty_sources_present`).
2. Restaurar la convergencia manifiesto/vector a través del comportamiento de
   indexación deduplicante existente (nunca vaciando la colección).
3. Aislar fallos por documento: un documento fallido no detiene el resto.
4. Ejecutar una verificación de consistencia posterior a la reparación (post-check) y
   reportar el estado resultante.

**No puede:**

1. Borrar vectores huérfanos (sección 9).
2. Mover ni migrar almacenamiento (configured/legacy).
3. Purgar datos legacy.
4. Declarar éxito sin un post-check saludable (`HEALTHY` o `HEALTHY_EMPTY` derivado
   del modelo de estados).
5. Operar de forma concurrente con otro escritor: debe adquirir el contrato de
   escritor único o fallar con estado "ocupado" (sección 11).

**Categorías de resultado de reparación** (identificadores para dataclass):

| Identificador | Significado |
|---|---|
| `attempted` | La reparación se ejecutó para el ítem; resultado pendiente de confirmación. |
| `repaired` | El ítem convergió y el post-check lo confirma. |
| `failed` | La reparación del ítem falló (error aislado, documentado por documento). |
| `still_inconsistent` | El post-check no alcanzó `HEALTHY`/`HEALTHY_EMPTY`; queda divergencia accionable. |
| `skipped` | Ítem no procesado (p. ej., huérfano real, backend ocupado, consentimiento no otorgado). |

La reparación nunca debe presentar un resultado `repaired` sin post-check ejecutado.

---

## 9. Política de huérfanos

`DEFERRED` para la purga; `TARGET_REQUIRED_FOR_V4.1` para la detección.

1. **Detectar y reportar** vectores huérfanos reales (categoría
   `source_absent_chroma_present`): la verificación los identifica y reporta (cantidad
   y muestra), sin borrarlos.
2. **Nunca purgarlos automáticamente**, ni durante verificación ni durante reparación
   conservadora.
3. **No exponer una opción interna `purgar_huérfanos=True`** en los primeros cortes de
   implementación (IDX-C1, IDX-C2). La API de reparación no acepta la purga.
4. La purga queda **diferida** hasta que exista un flujo separado de
   vista-previa-y-confirmación, especificado en su propio corte; la purga no es una
   superficie de v4.1 (sección 12).

---

## 10. Límites de dependencia interna

Cómo obtiene el futuro módulo de consistencia (`core/index_consistency.py`, nombre
referencial) sus insumos sin forzar la importación de helpers privados ni duplicar la
construcción del cliente Chroma. `TARGET_REQUIRED_FOR_V4.1`.

| Insumo | Origen previsto | Restricción |
|---|---|---|
| Inventario normalizado de fuentes | Iteración sobre `BASE_MEMORIA` con el mismo filtro de extensiones y carpetas ignoradas que el indexador | Reutilizar la política de `core/config.py`; no duplicar literales. Si `_iter_archivos`/`_ruta_relativa` se reutilizan, requieren adaptador interno explícito o elevación a API pública con test. |
| Datos del manifiesto sin mutación | Vía de lectura no mutante (JSON crudo + validación estructural) | No llamar `IndexManifest.load` si puede respaldar/reconstruir (sección 7.2). |
| Metadatos de Chroma sin crear ni modificar almacenamiento | Acceso a la colección existente (identidades + metadatos de chunks) | Adaptador interno sobre `core/vector_store.py` que evite semántica de creación (`get_or_create`, `PersistentClient` sobre rutas inexistentes) y consultas con embeddings. La construcción del cliente queda en `core/vector_store.py`; el módulo de consistencia no la duplica. |
| Reindexación conservadora | Operación pública existente `indexar_archivo` (dedup-safe) | No reinventar el flujo delete-then-add ni el guard de contención. |

Módulos de producción mínimos que pueden necesitar adaptadores internos estrechos
(sin nombres de funciones especificados; se resuelven con evidencia en IDX-C1):

1. `core/indexer.py` — inventario de fuentes e invocación de reindexación por identidad.
2. `core/index_manifest.py` — lector de manifiesto no mutante.
3. `core/vector_store.py` — acceso de solo lectura a la colección existente.

Los adaptadores deben: vivir en `core/` (nunca en UI/CLI/API), ser mínimos, estar
cubiertos por tests con fakes, y no cambiar los contratos públicos existentes.

---

## 11. Contrato de escritor único

`TARGET_REQUIRED_FOR_V4.1` (exclusividad); la lista de escritores es `CURRENT`.

1. **Escritores (`CURRENT`):** `indexar_archivo`, `eliminar_documento_indexado`,
   `sincronizar_indice`, `reconstruir_indice_completo` (y su alias `construir_indice`).
   La reparación conservadora (IDX-C2) también es escritora y queda sujeta a este
   contrato. La sincronización de cierre de estados de la reparación (post-check) no
   es escritora.
2. **Verificación de estado:** es de solo lectura. Puede ejecutarse sin adquirir la
   exclusividad, y en ese caso puede observar estados transitorios durante una
   escritura concurrente (se reporta el estado observado, con marca de transitoriedad
   si aplica).
3. **Fail-fast:** si otro escritor está activo, la operación entrante **falla de
   inmediato** con un estado estructurado de "ocupado"; no espera, no hace cola y no
   degrada a escritura sin exclusividad.
4. **Windows obligatorio:** el mecanismo debe funcionar en Windows sin primitivas
   POSIX-only (sin `fcntl`); la exclusividad de creación de archivo
   (`O_CREAT|O_EXCL`) es la vía compatible declarada, sin decisión final aquí.
5. **Seguridad del lock stale:** el mecanismo debe incluir detección de locks
   obsoletos (proceso muerto o bloqueo colgante) con identificación (PID + timestamp)
   y política de expiración. **No se declara aquí que la detección sea trivial ni qué
   algoritmo se selecciona**: el diseño y la elección son parte de IDX-C3, con tests
   de inyección de fallos.
6. **Corte propio:** la implementación del bloqueo es su propio corte (IDX-C3); esta
   SDD fija el contrato, no la implementación.

---

## 12. Superficies operativas

Separación explícita de superficies:

| Superficie | Contenido | Requerida v4.1 | Corte |
|---|---|---|---|
| **Estado de solo lectura** | Reporte de estado derivado (sección 5) + categorías de divergencia + resumen de huérfanos; sin acciones de escritura. Expuesta como check de Doctor (`core/system/doctor.py`) y comando de estado (`!indexar status` en CLI y UI). | Sí | IDX-C4 |
| **Reparación conservadora** | Invocación explícita de la reparación (sección 8) con confirmación; dry-run por defecto (patrón Healer/CLI existente); post-check obligatorio. | Sí | IDX-C5 |
| **Purga destructiva** | Borrado de vectores huérfanos con vista previa y confirmación. | No — `DEFERRED` | corte futuro |

Restricción de arquitectura: las superficies solo orquestan; la lógica de verificación
y reparación vive en `core/`. Doctor y Healer no reimplementan detección ni reparación.

---

## 13. Roadmap de cortes (ordenado)

| # | Corte | Entregable | Estado |
|---|---|---|---|
| 1 | **SDD-0** | Esta especificación gobernante. | `CURRENT` (este corte) |
| 2 | **IDX-C1** | Verificación de consistencia de solo lectura (`core/index_consistency.py` + tests; sin superficies). | `TARGET_REQUIRED_FOR_V4.1` |
| 3 | **IDX-C2** | Reparación conservadora con post-check obligatorio. | `TARGET_REQUIRED_FOR_V4.1` |
| 4 | **IDX-C3** | Contrato de escritor único (lock fail-fast con seguridad de stale). | `TARGET_REQUIRED_FOR_V4.1` |
| 5 | **IDX-C4** | Superficies de estado de solo lectura (check de Doctor + `!indexar status`). | `TARGET_REQUIRED_FOR_V4.1` |
| 6 | **IDX-C5** | Superficie explícita de reparación conservadora (Healer + CLI, dry-run por defecto). | `TARGET_REQUIRED_FOR_V4.1` |
| 7 | **DOC-C6** | Reconciliación documental final (feature doc, README, `.env.example`, `TECHNICAL_DEBT.md`, API reference si aplica). | `TARGET_REQUIRED_FOR_V4.1` |
| 8 | **INT-C7** | Puerta de integración completa de la rama (validación total + clasificación de commits + autorización de merge). | `TARGET_REQUIRED_FOR_V4.1` |

**Purga de huérfanos:** `DEFERRED` (requiere flujo de vista previa y confirmación;
fuera de v4.1).

Dependencias: IDX-C1 antes de IDX-C2 (el post-check usa la verificación); IDX-C3 antes
de IDX-C5 (la reparación es escritora); IDX-C4 y IDX-C5 después de sus núcleos; DOC-C6
antes de INT-C7.

---

## 14. Definition of Done

### 14.1 Un corte de implementación

- Comportamiento del corte implementado según esta SDD, con tests enfocados verdes
  (comando, exit code, passed/failed/errors/skipped reportados).
- Sin contacto con datos protegidos (`memory/`, `vector_db/`, `.env`,
  `atlas_security.log` reales); tests con fakes y temporales.
- Sin cambios fuera del alcance declarado del corte.
- `git diff --check` limpio; revisión completa del diff; working tree final declarado.
- Informe con evidencia ejecutada; limitaciones y `NOT VERIFIED` explícitos.
- Commits locales temáticos; sin push sin autorización.

### 14.2 Atlas 4.1 (rama completa)

- IDX-C1..C5 y DOC-C6 implementados y verificados; SDD-0 vigente y referenciada.
- Estados de la sección 5 derivables; verificación y reparación operativas; sin purga
  automática ni opción interna `purgar_huérfanos` en las superficies v4.1.
- Documentación alineada (feature doc descriptiva, README, `.env.example`,
  `TECHNICAL_DEBT.md` con deudas nuevas registradas).
- Suite completa verde con contadores; sin tests debilitados ni fallos ocultos.

### 14.3 Integración final en `origin/main`

- INT-C7 ejecutado: `origin/main` verificado fresco (requiere `git fetch` autorizado);
  todos los commits únicos de la rama clasificados y su fusión conjunta declarada
  intencional (sección 15); validación total re-ejecutada sobre el HEAD final.
- Auditoría independiente (rol Atlas Auditor) del corte final e informe aceptado.
- Autorización explícita del usuario para merge/push; sin reescritura de historia
  silenciosa; el merge no se ejecuta sin esa autorización.

### 14.4 Deudas conocidas registradas para v4.1.x (`DEFERRED`)

- Persistencia de fallos de archivos nuevos (INV-7).
- Asimetría de reporte en `eliminar_documento_indexado` (INV-6).
- Limpieza de `.tmp` huérfanos del manifiesto.
- Verificación profunda de conteos (`mismatch_chunk_counts`).
- Purga de huérfanos con flujo de confirmación.
- Cambio de modelo de embeddings como disparador de reindexación (informativo hoy).

---

## 15. Riesgo de composición de la rama

La rama `atlas-v4.1-incremental-indexing` contiene, además de cambios de indexación,
commits de agencia, gobernanza y auditoría. Composición verificada de los 13 commits
únicos respecto de `origin/main` (merge-base `8aa3e378`):

- **Producto (indexación/rutas/seguridad):** `e457277`, `5a3fbcd`, `4cd4a56`, `5cac180`.
- **Gobernanza y agencia:** `9caf3af`, `c842d66`, `4bc46af`, `b4154ab`, `1eef4be`.
- **Revisión y evidencia:** `10812cb`, `3e0d184`, `004961a`, `2a4700d`.

Requisito de INT-C7: la auditoría final de integración debe **clasificar todos los
commits únicos** (estado verificado al momento de la integración, no asumido de esta
tabla) y **determinar si se fusionan intencionalmente juntos**, documentando la
decisión del usuario. La SDD no decide la estrategia de merge; registra el requisito.

---

## 16. Nota final

Esta especificación congela contratos; no describe implementaciones futuras como
hechas. Toda discrepancia entre esta SDD y el código debe reportarse y resolverse
antes de INT-C7, sin reconciliar en silencio. Los cortes IDX-C1..INT-C7 son
obligatorios para completar Atlas 4.1; cualquier cambio material a esta SDD requiere
un corte documental propio.
