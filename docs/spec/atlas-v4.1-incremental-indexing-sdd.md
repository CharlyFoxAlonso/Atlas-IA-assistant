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
| `CURRENT` | Comportamiento implementado en el código actual y respaldado por tests existentes o evidencia previa; la ejecución fresca se registra en cada auditoría y gate. |
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
   solo lectura** (IDX-C1) y **reparable de forma conservadora** (IDX-C3).
3. Las operaciones de escritura están protegidas contra escritores concurrentes
   (IDX-C2).
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
| **Configured storage** | Ubicación del almacenamiento vectorial derivada de la raíz de datos configurada. `ATLAS_DATA_DIR` controla esa raíz y, por lo tanto, `CHROMA_PATH` e `INDEX_MANIFEST_PATH`. `ATLAS_MEMORY_DIR` controla exclusivamente la raíz de los source documents (`BASE_MEMORIA`) y no modifica la ubicación vectorial. La ruta configurada se valida mediante `validate_vector_store_path`. `CURRENT`. |
| **Legacy storage** | Ubicación `cwd/vector_db` distinta de la configurada. Política (`CURRENT`): si configured y legacy resuelven al mismo path, continúa normalmente; si difieren, se usa configured (configured existente, o legacy inexistente); legacy-only (configured inexistente y legacy distinto existente) produce error duro. Nunca fallback, fusión ni migración automática. |
| **Consistency check** | Verificación de solo lectura que clasifica el estado del índice en uno de los estados de la sección 5. `TARGET_REQUIRED_FOR_V4.1`. |
| **Conservative repair** | Operación separada que restaura la convergencia: reindexa fuentes soportadas presentes en disco; retira chunks y entrada de manifiesto de fuentes conocidas que ya no existen; nunca borra vectores sin fuente ni manifiesto; nunca mueve ni migra almacenamiento. `TARGET_REQUIRED_FOR_V4.1`. |
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
  comparten raíz. Política legacy de `validate_vector_store_path`: si configured y
  legacy resuelven al mismo path, continúa normalmente; si difieren, se usa configured
  (configured existente o legacy inexistente); si configured no existe y legacy es
  distinto y existente (legacy-only), error duro `LegacyVectorStoreError` sin
  fallback, movimiento, fusión ni migración automática. Evidencia:
  `core/system/paths.py` `validate_vector_store_path`; `tests/test_vector_paths.py`,
  `tests/test_backup_paths.py`.
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
| `HEALTHY` | Manifiesto presente, válido y compatible; Chroma responde; todo source document soportado tiene chunks y coincide con la huella vigente del manifiesto. `size_bytes` y `modified_time_ns` coinciden, o fueron reconciliados mediante SHA-256; no hay fuentes sin indexar, vectores registrables, vectores huérfanos ni entradas de manifiesto correspondientes a fuentes ausentes. |
| `HEALTHY_EMPTY` | Las capas están lógicamente vacías: no existen source documents soportados; el manifiesto está ausente o es válido y contiene cero entradas; y la colección `atlas_rag` está ausente o existe con cero chunks. Un manifiesto corrupto o incompatible, o un backend Chroma inaccesible, nunca producen `HEALTHY_EMPTY`. |
| `INCONSISTENT` | Existe al menos una divergencia accionable de la sección 6: chunks faltantes, fuentes sin indexar, contenido modificado, metadatos del filesystem desactualizados, vectores sin entrada de manifiesto, entradas sin fuente, vectores huérfanos, manifiesto ausente con otras capas no vacías, o almacenamiento/colección Chroma ausente con fuentes o entradas de manifiesto presentes. |
| `DEGRADED` | La verificación no pudo confirmar completamente un estado saludable y no existe una divergencia con mayor prioridad. Incluye entradas parcialmente malformadas que pueden aislarse, candidatos legacy no confirmables, limitaciones activas de verificación y estado del escritor desconocido. Mientras `writer_state_known=False`, un resultado nominal `HEALTHY` o `HEALTHY_EMPTY` se publica como `DEGRADED`. |
| `UNAVAILABLE` | El manifiesto está presente pero es estructuralmente corrupto; el manifiesto es legible pero usa un `schema_version` incompatible; o el backend Chroma es inaccesible y no permite determinar la consistencia. Nunca se convierte en `HEALTHY_EMPTY`. |

Reglas de derivación (`TARGET_REQUIRED_FOR_V4.1`):

1. `UNAVAILABLE` tiene prioridad sobre cualquier otro estado.
2. `INCONSISTENT` tiene prioridad sobre `DEGRADED`.
3. `DEGRADED` tiene prioridad sobre `HEALTHY` y `HEALTHY_EMPTY`.
4. Manifiesto ausente:
   - con fuentes o Chroma presentes → `INCONSISTENT`;
   - con las capas lógicamente vacías → `HEALTHY_EMPTY`.
5. Manifiesto presente pero corrupto o incompatible → `UNAVAILABLE`.
6. Almacenamiento Chroma o colección `atlas_rag` ausentes:
   - con fuentes o entradas de manifiesto presentes → `INCONSISTENT`;
   - con fuentes vacías y manifiesto ausente o válido vacío → `HEALTHY_EMPTY`.
7. Backend Chroma inaccesible → `UNAVAILABLE`.
8. Una fuente con `size_bytes` o `modified_time_ns` diferentes exige calcular SHA-256:
   - SHA-256 diferente → contenido desactualizado;
   - SHA-256 idéntico → contenido vectorial vigente, pero metadatos del manifiesto desactualizados.
9. Mientras `writer_state_known=False`, un resultado nominal `HEALTHY` o `HEALTHY_EMPTY` se publica como `DEGRADED`, con `writer_active=False` y `possibly_transient=True`.
10. El estado se calcula desde cero en cada verificación y no se persiste.

---

## 6. Categorías de divergencia requeridas

Identificadores estables en inglés, aptos para campos de dataclass futuros.
Para cada categoría se indica el estado resultante y la acción prevista.

| Identificador | Condición | Estado resultante | Acción prevista |
|---|---|---|---|
| `source_and_manifest_and_chroma_present` | Fuente, entrada y chunks presentes; `size_bytes` y `modified_time_ns` coinciden con el manifiesto | `HEALTHY` nominal | Ninguna |
| `source_and_manifest_present_chroma_absent` | Fuente y entrada presentes; chunks ausentes | `INCONSISTENT` | Reindexar la fuente mediante el flujo deduplicante |
| `source_present_manifest_stale_chroma_present` | Fuente, entrada y chunks presentes; size/mtime difieren y el SHA-256 actual también difiere del manifiesto | `INCONSISTENT` | Reindexar la fuente; el contenido cambió |
| `source_present_manifest_metadata_stale_content_same` | Fuente, entrada y chunks presentes; size/mtime difieren, pero el SHA-256 actual coincide con `content_sha256` | `INCONSISTENT` | Actualizar únicamente los metadatos del manifiesto mediante el comportamiento de sincronización existente; no reembedir ni reescribir chunks |
| `source_present_manifest_absent_chroma_present` | Fuente presente; chunks presentes sin entrada de manifiesto | `INCONSISTENT` | Reindexar para registrar el estado mediante el flujo existente |
| `source_present_manifest_absent_chroma_absent` | Fuente presente sin entrada ni chunks | `INCONSISTENT` | Indexar la fuente |
| `source_absent_manifest_present` | Entrada conocida cuyo source document ya no existe | `INCONSISTENT` | Retirar chunks y entrada mediante la operación pública existente |
| `source_absent_chroma_present` | Chunks sin entrada de manifiesto y sin source document | `INCONSISTENT` | Detectar y reportar; nunca purgar en Atlas 4.1 |
| `manifest_absent` | Archivo de manifiesto inexistente | `INCONSISTENT` si existen fuentes o Chroma; `HEALTHY_EMPTY` si las capas están lógicamente vacías | Reportar; permitir reparación conservadora si existen fuentes |
| `manifest_corrupt` | Manifiesto presente con JSON inválido o estructura no conforme | `UNAVAILABLE` | Reportar sin crear `.bak`, renombrar ni reconstruir durante el check |
| `manifest_schema_incompatible` | JSON legible y estructuralmente válido con `schema_version` no soportado | `UNAVAILABLE` | Reportar como incompatibilidad, no como corrupción |
| `chroma_absent` | La raíz de almacenamiento vectorial configurada no existe | `INCONSISTENT` si existen fuentes o entradas; `HEALTHY_EMPTY` si las demás capas están lógicamente vacías | Reportar; reconstruir conservadoramente desde fuentes cuando corresponda |
| `chroma_collection_absent` | La raíz configurada existe, pero la colección `atlas_rag` no existe; se detecta sin `get_or_create_collection` | `INCONSISTENT` si existen fuentes o entradas; `HEALTHY_EMPTY` si fuentes y manifiesto están lógicamente vacíos | Reportar; reconstruir conservadoramente desde fuentes cuando corresponda |
| `chroma_unavailable` | El backend o la colección existente no pueden abrirse por un error de acceso o funcionamiento | `UNAVAILABLE` | Reportar sin crear ni modificar almacenamiento |
| `manifest_and_chroma_empty_sources_present` | Manifiesto ausente o válido vacío, Chroma ausente o vacío, y existen fuentes soportadas | `INCONSISTENT` | Indexar las fuentes |
| `all_layers_empty` | No hay fuentes soportadas; el manifiesto está ausente o válido vacío; la colección está ausente o contiene cero chunks | `HEALTHY_EMPTY` nominal | Ninguna |

Decisiones contractuales:

- `source_present_manifest_stale_chroma_present` aplica únicamente cuando el SHA-256 cambió.
- `source_present_manifest_metadata_stale_content_same` aplica cuando size/mtime cambiaron pero el SHA-256 sigue siendo idéntico.
- `HEALTHY` requiere que no exista ninguna de esas dos divergencias.
- `mismatch_chunk_counts` no es un campo requerido de Atlas 4.1. Aunque el manifiesto registra `chunk_count`, no existe todavía una semántica validada para reconciliar diferencias de conteo frente a estados intermedios, duplicados legacy o cambios de chunking. La verificación profunda de conteos queda `DEFERRED`.

---

## 7. Contrato de verificación de solo lectura

Contrato del consistency check (IDX-C1). `TARGET_REQUIRED_FOR_V4.1`.

El primer verificador de consistencia:

1. **No escribe, renombra, respalda, borra ni repara nada.** Es estrictamente de solo
   lectura sobre las tres capas.
2. **No invoca `IndexManifest.load` si esa operación puede mutar un manifiesto
   corrupto.** `IndexManifest.load` respalda el archivo corrupto (efecto de escritura);
   el verificador inspecciona el manifiesto por una vía de lectura no mutante: lectura
   del JSON crudo + validación estructural propia. La corrupción estructural se
   reporta como `manifest_corrupt` → `UNAVAILABLE`; un JSON legible con `schema_version`
   no soportado se reporta como `manifest_schema_incompatible` → `UNAVAILABLE`, sin
   clasificarlo como corrupción. El respaldo `.bak` permanece exclusivamente en la vía
   de escritura.
3. **No crea almacenamiento Chroma.** No construye el cliente ni la colección si el
   almacenamiento no existe; cuando existe, accede a la colección existente sin
   semántica de creación y sin `get_or_create` implícito (ver sección 10). El adaptador
   consulta una colección existente sin crearla y distingue colección ausente
   (`chroma_collection_absent`) de backend inaccesible (`chroma_unavailable`).
4. **No embebe, no indexa y no contacta proveedores.** La verificación utiliza únicamente identidades, metadatos, estadísticas del filesystem y metadatos de Chroma. Nunca ejecuta búsquedas que requieran embeddings ni invoca modelos. Para comparar una fuente con su entrada de manifiesto:
   - si `size_bytes` y `modified_time_ns` coinciden, considera vigente la huella sin releer el contenido;
   - si alguno difiere, calcula el SHA-256 en modo lectura;
   - si el SHA-256 difiere, reporta `source_present_manifest_stale_chroma_present`;
   - si el SHA-256 coincide, reporta `source_present_manifest_metadata_stale_content_same`.

   El check nunca extrae texto, reembebe, indexa, reescribe chunks ni modifica el source document.
5. **Reporta corrupción o indisponibilidad sin convertirlas en un estado vacío
   saludable.** `UNAVAILABLE` nunca deriva en `HEALTHY_EMPTY` (sección 5).
6. **En ejecución real, inspecciona solo almacenamiento temporal o datos configurados
   autorizados por el usuario.** Nunca explora fuera de `BASE_MEMORIA` ni de la raíz
   vectorial autoritativa.
7. **En tests, usa fakes y datos temporales.** Prohibido ejecutar contra `memory/`,
   `vector_db/` o `.env` reales.

Inspección del manifiesto sin efectos de recuperación: el verificador lee el archivo
con `json.load` (o equivalente) en modo lectura. Si el contenido no es JSON válido o no
cumple la estructura del esquema (`documents` como dict), lo clasifica como corrupto
(`manifest_corrupt`); si es JSON estructuralmente válido pero `schema_version` no es
soportado por Atlas 4.1, lo clasifica como incompatible (`manifest_schema_incompatible`).
Ambos reportan `UNAVAILABLE` y **no** crean `.bak`, no renombran y no reinician
estado. La decisión de respaldar y reconstruir sigue siendo del flujo de escritura
existente (`IndexManifest.load`), no del verificador.

---

## 8. Contrato de reparación conservadora

Operación separada de la verificación (IDX-C3). `TARGET_REQUIRED_FOR_V4.1`.

**Puede:**

1. Reparar toda fuente soportada presente cuya representación en el manifiesto o en Chroma no corresponda al estado actual, reutilizando los flujos existentes de sincronización e indexación.
2. Indexar una fuente que no tiene entrada de manifiesto ni chunks.
3. Reindexar una fuente cuando faltan sus chunks, cuando falta su entrada de manifiesto o cuando su SHA-256 actual difiere del último contenido indexado.
4. Restaurar el almacenamiento vectorial cuando la raíz configurada o la colección `atlas_rag` están ausentes y existen fuentes soportadas.
5. Actualizar únicamente `size_bytes` y `modified_time_ns` del manifiesto cuando esos metadatos cambiaron pero el SHA-256 continúa siendo idéntico. En este caso no reembebe ni reescribe chunks.
6. Retirar chunks y entrada de manifiesto cuando existe una entrada conocida y el source document correspondiente ya no existe, reutilizando la operación pública de eliminación o sincronización.
7. Aislar los fallos por documento: un documento fallido no detiene el procesamiento de los demás.
8. Ejecutar una verificación de consistencia posterior y reportar el estado resultante.

Regla general:

> Toda fuente soportada presente cuya representación en el manifiesto o en Chroma no corresponda al estado actual puede repararse reutilizando los flujos existentes de sincronización o indexación. Solo se reembebe cuando el contenido cambió o cuando faltan chunks. Si el SHA-256 coincide y únicamente cambiaron size/mtime, se actualiza solo el manifiesto.

El retiro de estado correspondiente a una fuente conocida que ya no existe es una limpieza de estado derivado obsoleto. No es una purga de vectores huérfanos: los chunks sin fuente ni entrada de manifiesto continúan siendo únicamente detectados y reportados.

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
3. **El verificador IDX-C1 y la reparación conservadora IDX-C3 no exponen ninguna
   opción de purga.** La API de reparación no acepta la purga.
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
| Inventario normalizado de fuentes | Iteración sobre `BASE_MEMORIA` con el mismo filtro de extensiones y carpetas ignoradas que el indexador | Reutilizar la política de `core/config.py`; no duplicar literales. Si `_iter_archivos`/`_ruta_relativa` se reutilizan, requieren adaptador interno explícito con tests. En estos cortes no se eleva ningún helper a API pública: una nueva API pública requiere un corte documental propio. |
| Datos del manifiesto sin mutación | Vía de lectura no mutante (JSON crudo + validación estructural) | No llamar `IndexManifest.load` si puede respaldar/reconstruir (sección 7.2). |
| Metadatos de Chroma sin crear ni modificar almacenamiento | Acceso a la colección existente (identidades + metadatos de chunks) | Adaptador interno sobre `core/vector_store.py` que evite semántica de creación (`get_or_create`, `PersistentClient` sobre rutas inexistentes) y consultas con embeddings; consulta la colección existente sin crearla y distingue colección ausente (`chroma_collection_absent`) de backend inaccesible (`chroma_unavailable`). La construcción del cliente queda en `core/vector_store.py`; el módulo de consistencia no la duplica. |
| Reindexación conservadora | Operación pública existente `indexar_archivo` (dedup-safe) | No reinventar el flujo delete-then-add ni el guard de contención. |

Módulos de producción mínimos que pueden necesitar adaptadores internos estrechos
(sin nombres de funciones especificados; se resuelven con evidencia en IDX-C1):

1. `core/indexer.py` — inventario de fuentes e invocación de reindexación por identidad.
2. `core/index_manifest.py` — lector de manifiesto no mutante.
3. `core/vector_store.py` — acceso de solo lectura a la colección existente.

Los adaptadores deben: vivir en `core/` (nunca en UI/CLI/API), ser mínimos, estar
cubiertos por tests con fakes, y no cambiar los contratos públicos existentes ni
elevar helpers privados a API pública.

---

## 11. Contrato de escritor único

`TARGET_REQUIRED_FOR_V4.1` (exclusividad); la lista de escritores es `CURRENT`.

1. **Escritores (`CURRENT`):** `indexar_archivo`, `eliminar_documento_indexado`,
   `sincronizar_indice`, `reconstruir_indice_completo` (y su alias `construir_indice`).
   La reparación conservadora (IDX-C3) también es escritora y queda sujeta a este
   contrato. La sincronización de cierre de estados de la reparación (post-check) no
   es escritora.
2. **Verificación de estado:** es de solo lectura y puede ejecutarse sin adquirir exclusividad, por lo que puede observar un estado transitorio durante una escritura concurrente. El reporte congela:

   - `writer_state_known: bool`
   - `writer_active: bool`
   - `possibly_transient: bool`

   Antes de IDX-C2, el verificador no dispone de un mecanismo confiable para conocer el estado del escritor y debe reportar:

   ```text
   writer_state_known=False
   writer_active=False
   possibly_transient=True
   ```

   Mientras `writer_state_known=False`, un resultado nominal `HEALTHY` o `HEALTHY_EMPTY` debe publicarse como `DEGRADED`. `UNAVAILABLE` conserva la máxima prioridad e `INCONSISTENT` conserva prioridad sobre `DEGRADED`.

   Después de IDX-C2, si el mecanismo confirma que no existe un escritor activo:

   ```text
   writer_state_known=True
   writer_active=False
   possibly_transient=False
   ```

   Si confirma que existe un escritor activo:

   ```text
   writer_state_known=True
   writer_active=True
   possibly_transient=True
   ```

   En este último caso, el reporte debe advertir que el estado observado puede cambiar al terminar la operación escritora.
3. **Fail-fast:** si otro escritor está activo, la operación entrante **falla de
   inmediato** con un estado estructurado de "ocupado"; no espera, no hace cola y no
   degrada a escritura sin exclusividad.
4. **Windows obligatorio:** el mecanismo debe funcionar en Windows sin primitivas
   POSIX-only (sin `fcntl`); la exclusividad de creación de archivo
   (`O_CREAT|O_EXCL`) es la vía compatible declarada, sin decisión final aquí.
5. **Seguridad del lock stale:** el mecanismo debe detectar locks obsoletos (proceso
   muerto o bloqueo colgante) con identificación (PID + timestamp), pero la
   recuperación **nunca se decide por tiempo transcurrido**: se requiere evidencia de
   que el proceso dueño está inactivo. Estados dudosos (PID reutilizado, metadatos
   incompletos o ilegibles, condición ambigua) **bloquean la recuperación automática**
   y se reportan para tratamiento explícito. El algoritmo concreto y su compatibilidad
   Windows (sin primitivas POSIX-only) se deciden y prueban en IDX-C2 con tests de
   inyección de fallos; esta SDD fija el contrato, no el algoritmo.
6. **Corte propio:** la implementación del bloqueo es su propio corte (IDX-C2); esta
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
| 3 | **IDX-C2** | Contrato de escritor único (lock fail-fast con seguridad de stale). | `TARGET_REQUIRED_FOR_V4.1` |
| 4 | **IDX-C3** | Reparación conservadora con post-check obligatorio. | `TARGET_REQUIRED_FOR_V4.1` |
| 5 | **IDX-C4** | Superficies de estado de solo lectura (check de Doctor + `!indexar status`). | `TARGET_REQUIRED_FOR_V4.1` |
| 6 | **IDX-C5** | Superficie explícita de reparación conservadora (Healer + CLI, dry-run por defecto). | `TARGET_REQUIRED_FOR_V4.1` |
| 7 | **DOC-C6** | Reconciliación documental final (feature doc, README, `.env.example`, `TECHNICAL_DEBT.md`, API reference si aplica). | `TARGET_REQUIRED_FOR_V4.1` |
| 8 | **INT-C7** | Puerta de integración completa de la rama (validación total + clasificación de commits + autorización de merge). | `TARGET_REQUIRED_FOR_V4.1` |

**Purga de huérfanos:** `DEFERRED` (requiere flujo de vista previa y confirmación;
fuera de v4.1).

Dependencias: IDX-C1 antes de IDX-C3 (el post-check de la reparación usa la
verificación); IDX-C2 antes de IDX-C3 (la reparación es escritora) y de IDX-C5
(superficie de reparación); IDX-C4 y IDX-C5 después de sus núcleos; DOC-C6 antes de
INT-C7.

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
commits de agencia, gobernanza y auditoría. Clasificación de los 13 commits únicos
respecto de `origin/main` (merge-base `8aa3e378`), verificada durante SDD-0 contra la
referencia local. La frescura de `origin/main` respecto del remoto real permanece
`UNVERIFIED` hasta el `git fetch` autorizado de INT-C7:

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
