# Registro de deuda técnica — Atlas

Este documento es la fuente de verdad para las deudas técnicas, documentales y de mantenimiento de Atlas.

Una deuda no desaparece cuando se acepta el corte que la originó. Permanece abierta hasta que exista una implementación, una prueba de aceptación y un commit que demuestre su resolución.

## Estados

- `OPEN`: deuda confirmada y todavía no planificada.
- `PLANNED`: asignada a un corte futuro concreto.
- `IN_PROGRESS`: actualmente en implementación.
- `RESOLVED`: corregida y demostrada.
- `WONT_FIX`: se decidió conscientemente no resolverla.
- `SUPERSEDED`: reemplazada por otra deuda o decisión posterior.

## Severidades

- `HIGH`: riesgo funcional, de seguridad o de consistencia importante.
- `MEDIUM`: problema real que debería resolverse, pero no bloquea actualmente.
- `LOW`: mantenimiento, claridad, compatibilidad futura o cobertura.
- `INFORMATIONAL`: seguimiento sin defecto confirmado.

---

# Resumen

| ID | Título | Severidad | Estado | Componente |
|---|---|---:|---|---|
| ATLAS-TD-001 | Parámetro `reindexer` aceptado pero ignorado | LOW | OPEN | Web crawler |
| ATLAS-TD-002 | Estado acumulado al reutilizar `WebCrawler` | LOW | OPEN | Web crawler |
| ATLAS-TD-003 | Resumen ambiguo cuando todas las indexaciones fallan | LOW | OPEN | Web crawler / UI |
| ATLAS-TD-004 | Versionado distribuido y cadenas hardcodeadas | MEDIUM | RESOLVED | Configuración / UI / CLI / API |
| ATLAS-TD-005 | Ausencia de prueba central de coherencia de versión | LOW | RESOLVED | Tests / versión |
| ATLAS-TD-006 | README y changelog desalineados con el estado real | MEDIUM | RESOLVED | README |
| ATLAS-TD-007 | Roadmap mezcla funciones terminadas, parciales y pendientes | MEDIUM | RESOLVED | Roadmap |
| ATLAS-TD-008 | Documentación pública todavía identifica la versión como v4 | MEDIUM | RESOLVED | Documentación |
| ATLAS-TD-009 | Comandos y puertos documentados no siempre coinciden | MEDIUM | RESOLVED | Documentación / launchers |
| ATLAS-TD-010 | Referencia documental a `prometeo_worker.py` inexistente | LOW | RESOLVED | Guía de desarrollo |
| ATLAS-TD-011 | Uso incorrecto de “Prometheus” en lugar de “Prometeo” | LOW | RESOLVED | README |
| ATLAS-TD-012 | Rutas locales personales en archivos rastreados | MEDIUM | RESOLVED | Docs / scripts |
| ATLAS-TD-013 | Defaults y etiquetas públicas acoplados a “Charly” | MEDIUM | RESOLVED | UI / CLI / perfil |
| ATLAS-TD-014 | Identidad interna del perfil acoplada a `Perfil_Charly.md` | LOW | OPEN | Memoria / perfil |
| ATLAS-TD-015 | Manual HTML v2.0 obsoleto todavía rastreado | MEDIUM | RESOLVED | Documentación |
| ATLAS-TD-016 | Capturas de una interfaz anterior todavía rastreadas | LOW | RESOLVED | Documentación |
| ATLAS-TD-017 | RFC-0011 no marcado como reemplazado por v4.1 | MEDIUM | RESOLVED | RFC / versión |
| ATLAS-TD-018 | README enlaza una licencia inexistente | MEDIUM | OPEN | README / publicación |
| ATLAS-TD-019 | Ausencia de registro central de deuda técnica | MEDIUM | RESOLVED | Gobernanza |
| ATLAS-TD-020 | Documentos históricos no están claramente marcados | LOW | RESOLVED | Documentación histórica |
| ATLAS-TD-021 | Rutas personales en fallbacks de OCR y PDF | LOW | OPEN | OCR / PDF |
| ATLAS-TD-022 | Fallos de archivos nuevos no persisten en el manifiesto | MEDIUM | OPEN | Indexación incremental |
| ATLAS-TD-023 | Reporte asimétrico si falla el manifiesto tras eliminar | MEDIUM | OPEN | Indexador / manifiesto |
| ATLAS-TD-024 | `.tmp` huérfanos del manifiesto sin limpieza | LOW | OPEN | Manifiesto |
| ATLAS-TD-025 | Conteos de chunks sin verificación profunda | MEDIUM | OPEN | Consistencia del índice |
| ATLAS-TD-026 | Purga controlada de huérfanos diferida | INFORMATIONAL | OPEN | Operación del índice |
| ATLAS-TD-027 | Cambio de modelo no dispara reindexación | INFORMATIONAL | OPEN | Manifiesto / sincronización |

---

# Detalle de deudas

## ATLAS-TD-001 — Parámetro `reindexer` aceptado pero ignorado

- **Estado:** `OPEN`
- **Severidad:** `LOW`
- **Origen:** Auditoría Atlas v4.1 Corte 2
- **Componente:** `core/web_crawler.py`
- **Símbolo:** `WebCrawler.__init__(..., reindexer=...)`
- **Descripción:** El constructor continúa aceptando `reindexer`, pero el callback ya no se invoca. Esto preserva la firma del constructor, pero puede ocultar silenciosamente que un consumidor esperaba efectos observables.
- **Impacto:** Un consumidor externo podría pasar `reindexer=` esperando una reconstrucción completa y no recibir ninguna advertencia.
- **Corrección propuesta:** Emitir una advertencia de deprecación explícita cuando se proporcione `reindexer`.
- **Prueba de aceptación:** Un test pasa `reindexer=mock`, comprueba la advertencia y confirma que el callback no se invoca.
- **Versión objetivo sugerida:** v4.1.x.
- **Commit de resolución:** pendiente.

---

## ATLAS-TD-002 — Estado acumulado al reutilizar `WebCrawler`

- **Estado:** `OPEN`
- **Severidad:** `LOW`
- **Origen:** Auditoría Atlas v4.1 Corte 2
- **Componente:** `core/web_crawler.py`
- **Símbolo:** `WebCrawler.crawl`
- **Descripción:** Los contadores y colecciones se inicializan en el constructor, pero no se reinician al comenzar una segunda llamada a `crawl()` sobre la misma instancia.
- **Impacto:** Una instancia reutilizada podría acumular `processed_count`, `indexed_count`, `index_failed_count`, solicitudes, visitados y cola.
- **Decisión pendiente:** Definir si `WebCrawler` es explícitamente de un solo uso o si debe soportar reutilización.
- **Corrección propuesta:** Documentar el contrato de una sola ejecución o reiniciar todo el estado por corrida.
- **Prueba de aceptación:** Ejecutar dos crawls sintéticos sobre la misma instancia y verificar el comportamiento contractual elegido.
- **Versión objetivo sugerida:** v4.1.x.
- **Commit de resolución:** pendiente.

---

## ATLAS-TD-003 — Resumen ambiguo cuando todas las indexaciones fallan

- **Estado:** `OPEN`
- **Severidad:** `LOW`
- **Origen:** Auditoría Atlas v4.1 Corte 2
- **Componente:** `core/web_crawler.py`, `atlas_ui.py`
- **Descripción:** Cuando se guardan archivos pero ninguna indexación resulta exitosa, el resumen final indica “RAG sin cambios”, aunque existen artefactos pendientes.
- **Impacto:** El mensaje es técnicamente correcto, pero puede hacer que el usuario no advierta la necesidad de ejecutar recuperación o sincronización.
- **Corrección propuesta:** Mostrar “RAG sin cambios; hay archivos pendientes de indexación”.
- **Prueba de aceptación:** Simular una corrida con archivos guardados, cero indexados y al menos un fallo; verificar mensaje, contadores y estado.
- **Versión objetivo sugerida:** v4.1.x.
- **Commit de resolución:** pendiente.

---

## ATLAS-TD-004 — Versionado distribuido y cadenas hardcodeadas

- **Estado:** `RESOLVED`
- **Severidad:** `MEDIUM`
- **Origen:** Plan de cierre documental Atlas v4.1
- **Componentes:** configuración, UI, CLI, API, launchers y reportes internos.
- **Evidencia conocida:**
  - `core/config.py` declara `VERSION = "4.0"`.
  - `core/system/doctor.py` mantiene otra constante independiente.
  - UI, CLI, API y reportes contienen cadenas `v4`, `4.0` e incluso `3.8`.
- **Impacto:** La aplicación puede presentar versiones contradictorias según el punto de entrada.
- **Decisión adoptada:**
  - versión técnica: `4.1.0`;
  - identidad visible: `Atlas v4.1`;
  - `core.config.VERSION` será la fuente general;
  - `core.system.doctor.VERSION` seguirá duplicada por independencia de arranque.
- **Corrección propuesta:** Actualizar consumidores y evitar cadenas técnicas duplicadas cuando sea seguro.
- **Prueba de aceptación:** UI, CLI, API, doctor y self-awareness muestran una versión coherente.
- **Versión objetivo:** Corte 3 de Atlas v4.1.
- **Fecha de resolución:** 2026-07-22.
- **Corte:** Atlas v4.1 Corte 3.
- **Commit de resolución:** `fe199a0`.
- **Evidencia:** `core.config.VERSION` y Doctor informan `4.1.0`; UI, CLI, API, launchers, User-Agent y reportes usan la identidad v4.1; las búsquedas residuales solo muestran historia o versiones de terceros.

---

## ATLAS-TD-005 — Ausencia de prueba central de coherencia de versión

- **Estado:** `RESOLVED`
- **Severidad:** `LOW`
- **Origen:** Plan de cierre documental Atlas v4.1
- **Componente:** tests.
- **Descripción:** No existe una prueba dedicada que confirme que la versión general y la versión independiente del doctor coinciden.
- **Impacto:** Un cambio futuro puede actualizar una constante y olvidar la otra.
- **Corrección propuesta:** Crear un test de coherencia que compruebe `4.1.0` en ambas fuentes y en consumidores críticos que puedan probarse sin iniciar servicios.
- **Prueba de aceptación:** El test falla si una fuente se desvía.
- **Versión objetivo:** Corte 3 de Atlas v4.1.
- **Fecha de resolución:** 2026-07-22.
- **Corte:** Atlas v4.1 Corte 3.
- **Commit de resolución:** `fe199a0`.
- **Evidencia:** `tests/test_version_consistency.py` valida config, Doctor, título FastAPI y respuesta de versión; 4 pruebas pasan y la suite completa pasa.

---

## ATLAS-TD-006 — README y changelog desalineados con el estado real

- **Estado:** `RESOLVED`
- **Severidad:** `MEDIUM`
- **Origen:** Plan de cierre documental Atlas v4.1
- **Componente:** `README.md`
- **Descripción:** El README mezcla Atlas v4 y v4.1, presenta v4.1 como “in progress” y no refleja correctamente los Cortes 1 y 2 ya implementados, probados, auditados e integrados.
- **Impacto:** La página pública del proyecto no representa su estado real.
- **Corrección propuesta:** Reescribir la sección actual y distinguir funcionalidades implementadas, probadas, aceptadas, parciales y pendientes.
- **Prueba de aceptación:** Cada claim importante del README tiene evidencia en código, tests o documentación.
- **Versión objetivo:** Corte 3 de Atlas v4.1.
- **Fecha de resolución:** 2026-07-22.
- **Corte:** Atlas v4.1 Corte 3.
- **Commit de resolución:** `215f7ba`.
- **Evidencia:** README identifica v4.1 como release candidate y registra indexación incremental local/web, EPUB/HTML, Prompt Playground y dashboard básico sin afirmar publicación ni aceptación.

---

## ATLAS-TD-007 — Roadmap mezcla funciones terminadas, parciales y pendientes

- **Estado:** `RESOLVED`
- **Severidad:** `MEDIUM`
- **Origen:** Plan de cierre documental Atlas v4.1
- **Componente:** Roadmap dentro de `README.md`
- **Evidencia conocida:**
  - EPUB y HTML figuran como pendientes aunque existen.
  - Prompt Playground figura como pendiente aunque está implementado.
  - Dashboard mejorado está implementado parcialmente.
  - Chat Session Exporter no está implementado.
- **Impacto:** No permite saber qué trabajo queda realmente.
- **Corrección propuesta:** Separar:
  - completado en v4.1;
  - parcial;
  - seguimientos técnicos v4.1.x;
  - pendientes v4.2;
  - largo plazo.
- **Prueba de aceptación:** Cada item del roadmap tiene estado y evidencia verificables.
- **Versión objetivo:** Corte 3 de Atlas v4.1.
- **Fecha de resolución:** 2026-07-22.
- **Corte:** Atlas v4.1 Corte 3.
- **Commit de resolución:** `215f7ba`.
- **Evidencia:** roadmap separa entregado, parcial, seguimientos L1–L3 v4.1.x y pendientes reales de v4.2; Chat Session Exporter continúa pendiente.

---

## ATLAS-TD-008 — Documentación pública todavía identifica la versión como v4

- **Estado:** `RESOLVED`
- **Severidad:** `MEDIUM`
- **Origen:** Plan de cierre documental Atlas v4.1
- **Componentes conocidos:**
  - `docs/ARCHITECTURE.md`
  - `docs/USER_GUIDE.md`
  - `docs/API_REFERENCE.md`
  - `docs/DEV_GUIDE.md`
  - `docs/MODEL_CATALOG.md`
  - `requirements.txt`
  - `.env.example`
  - launchers.
- **Descripción:** Documentos actuales usan títulos o encabezados v4 aunque el producto actual es v4.1.
- **Impacto:** Identidad pública inconsistente.
- **Corrección propuesta:** Actualizar solo referencias vigentes; conservar referencias históricas.
- **Prueba de aceptación:** Las búsquedas de `Atlas v4` dejan únicamente documentos históricos o contextos explícitamente justificados.
- **Versión objetivo:** Corte 3.
- **Fecha de resolución:** 2026-07-22.
- **Corte:** Atlas v4.1 Corte 3.
- **Commit de resolución:** `215f7ba`.
- **Evidencia:** títulos públicos, SETUP, `requirements.txt` y `.env.example` usan Atlas v4.1; RFC-0011 y la bitácora v3.8 quedan marcados como históricos.

---

## ATLAS-TD-009 — Comandos y puertos documentados no siempre coinciden

- **Estado:** `RESOLVED`
- **Severidad:** `MEDIUM`
- **Origen:** Auditoría documental Atlas v4.1
- **Componentes:** README, manuales, launchers y guías.
- **Evidencia conocida:** Parte de la documentación usa el puerto `8501`, mientras `run_ui.bat` y la guía actual utilizan `8401`.
- **Impacto:** El usuario puede ejecutar un comando distinto al launcher soportado o interpretar una falla inexistente.
- **Corrección propuesta:** Definir y documentar el puerto principal, aclarando cuándo puede personalizarse.
- **Prueba de aceptación:** README, launcher y guía de desarrollo coinciden.
- **Versión objetivo:** Corte 3.
- **Antecedente del Corte 3 (2026-07-22):** la documentación vigente identificaba 8401 como puerto principal, pero no explicaba que los fallbacks sin `.venv` de `run_ui.bat` usan 8501.
- **Fecha de resolución:** 2026-07-23.
- **Corte de resolución:** Atlas v4.1 Corte 3 follow-up.
- **Commit de resolución:** `2e636b8`.
- **Evidencia:**
  - La inspección de `run_ui.bat` confirma 8401 para la ruta con `.venv` local y 8501 para las rutas de respaldo con `py` o Streamlit global.
  - README, SETUP, guía de usuario y guía de desarrollo documentan el mismo contrato sin atribuir el fallback a disponibilidad del puerto.
  - Las búsquedas de validación muestran ambos puertos únicamente con su función real.

---

## ATLAS-TD-010 — Referencia a `prometeo_worker.py` inexistente

- **Estado:** `RESOLVED`
- **Severidad:** `LOW`
- **Origen:** Auditoría documental Atlas v4.1
- **Componente:** `docs/DEV_GUIDE.md`
- **Descripción:** La guía menciona un archivo o componente que no existe en el árbol actual.
- **Impacto:** Documentación de desarrollo engañosa.
- **Corrección propuesta:** Sustituir por el componente real o eliminar la referencia.
- **Prueba de aceptación:** Toda ruta o módulo mencionado existe o está marcado explícitamente como histórico.
- **Versión objetivo:** Corte 3.
- **Fecha de resolución:** 2026-07-22.
- **Corte:** Atlas v4.1 Corte 3.
- **Commit de resolución:** `215f7ba`.
- **Evidencia:** `docs/DEV_GUIDE.md` referencia `core/digestion_worker.py`, componente existente con `ThreadPoolExecutor`; no quedan referencias activas al archivo inexistente fuera de este registro histórico.

---

## ATLAS-TD-011 — Uso incorrecto de “Prometheus”

- **Estado:** `RESOLVED`
- **Severidad:** `LOW`
- **Origen:** Auditoría documental Atlas v4.1
- **Componente:** `README.md`
- **Descripción:** Una referencia pública usa “Prometheus” cuando el nombre correcto del motor es “Prometeo”.
- **Impacto:** Inconsistencia de identidad y posible confusión con Prometheus Monitoring.
- **Corrección propuesta:** Reemplazar la referencia por “Prometeo”.
- **Prueba de aceptación:** No quedan coincidencias públicas injustificadas de “Prometheus”.
- **Versión objetivo:** Corte 3.
- **Fecha de resolución:** 2026-07-22.
- **Corte:** Atlas v4.1 Corte 3.
- **Commit de resolución:** `215f7ba`.
- **Evidencia:** la búsqueda case-insensitive de `prometheus` en README no devuelve coincidencias; la identidad vigente usa Prometeo.

---

## ATLAS-TD-012 — Rutas locales personales en archivos rastreados

- **Estado:** `RESOLVED`
- **Severidad:** `MEDIUM`
- **Origen:** Auditoría documental Atlas v4.1
- **Componentes conocidos:**
  - `README.md`
  - `SETUP.md`
  - `docs/installation/development.md`
  - `scripts/crear_distribucion.py`
  - posibles scripts auxiliares.
- **Evidencia histórica:** se detectó el ejemplo rastreado `C:\Users\delfa\Documents\Atlas` antes del Corte 3 y su follow-up.
- **Impacto:** Documentación no portable y exposición accidental del nombre de usuario local.
- **Corrección propuesta:** Reemplazar por `<ruta-del-repo>` o rutas sintéticas claramente genéricas.
- **Prueba de aceptación:** `git grep -F "C:\Users\"` no devuelve coincidencias accidentales en archivos rastreados actuales.
- **Versión objetivo:** Corte 3.
- **Antecedente del Corte 3 (2026-07-22):** `README.md`, `SETUP.md`, `docs/installation/development.md` y `scripts/crear_distribucion.py` usan `<ruta-del-repo>` desde `215f7ba`; quedaba pendiente `probar_researcher.py`.
- **Fecha de resolución:** 2026-07-23.
- **Corte de resolución:** Atlas v4.1 Corte 3 follow-up.
- **Commit de resolución:** `2e636b8`.
- **Evidencia:**
  - `probar_researcher.py` deriva la raíz portable con `Path(__file__).resolve().parent` y conserva la ruta relativa esperada del PDF.
  - `py_compile` pasa sin ejecutar el researcher real.
  - Las búsquedas de `C:\Users\` y `C:/Users/` no muestran rutas personales accidentales; solo evidencia histórica explícita y datos sintéticos de tests.

---

## ATLAS-TD-013 — Defaults y etiquetas públicas acoplados a “Charly”

- **Estado:** `RESOLVED`
- **Severidad:** `MEDIUM`
- **Origen:** Auditoría de identidad Atlas v4.1
- **Componentes conocidos:**
  - `core/profile_manager.py`
  - `atlas_ui.py`
  - `atlas_chat.py`
  - textos y prompts visibles.
- **Descripción:** “charly” aparece como valor predeterminado, etiqueta, encabezado o nombre de ejemplo.
- **Impacto:** Una instalación pública parece personalizada para una persona concreta.
- **Decisión adoptada:** Cambiar defaults, etiquetas y ejemplos visibles por “usuario” o “Perfil de ejemplo”.
- **Restricción:** No cambiar todavía rutas persistentes ni identificadores internos.
- **Prueba de aceptación:** UI y CLI no usan “charly” como valor predeterminado; tests cubren el default genérico.
- **Versión objetivo:** Corte 3.
- **Fecha de resolución:** 2026-07-22.
- **Corte:** Atlas v4.1 Corte 3.
- **Commit de resolución:** `27bd860`.
- **Evidencia:** defaults públicos usan `usuario`, etiquetas y prompts quedaron neutralizados, y `tests/test_public_identity.py` pasa. Se preservan `cargar_perfil_charly()` y `Perfil_Charly.md` por compatibilidad de ATLAS-TD-014.

---

## ATLAS-TD-014 — Identidad interna del perfil acoplada a `Perfil_Charly.md`

- **Estado:** `OPEN`
- **Severidad:** `LOW`
- **Origen:** Auditoría de identidad Atlas v4.1
- **Componentes conocidos:**
  - `core/brain.py`
  - `core/memory_manager.py`
  - ruta `Perfil_Charly.md`.
- **Descripción:** La identidad personal está incorporada en nombres internos, funciones y rutas persistentes.
- **Impacto:** Dificulta convertir Atlas en una aplicación genuinamente multiusuario o genérica.
- **Decisión actual:** Conservar estos identificadores por compatibilidad durante el Corte 3.
- **Corrección futura:** Diseñar una migración explícita de perfil y compatibilidad hacia nombres neutrales.
- **Prueba de aceptación futura:** Perfiles existentes siguen cargando y nuevas instalaciones usan identificadores neutrales.
- **Versión objetivo sugerida:** v4.2 o un corte específico de perfiles.
- **Commit de resolución:** pendiente.

---

## ATLAS-TD-015 — Manual HTML v2.0 obsoleto todavía rastreado

- **Estado:** `RESOLVED`
- **Severidad:** `MEDIUM`
- **Origen:** Auditoría documental Atlas v4.1
- **Archivo:** `Atlas_Manual_Usuario.html`
- **Descripción:** Manual correspondiente a una versión anterior, con funciones, agentes, UI y textos personales que ya no representan el producto.
- **Decisión adoptada:** Eliminar definitivamente.
- **Restricción:** No archivar, mover, restaurar ni reemplazar.
- **Prueba de aceptación:** El archivo deja de estar rastreado y no quedan enlaces vigentes hacia él.
- **Versión objetivo:** Corte 3.
- **Fecha de resolución:** 2026-07-22.
- **Corte:** Atlas v4.1 Corte 3.
- **Commit de resolución:** `cb01d45`.
- **Evidencia:** `Atlas_Manual_Usuario.html` fue eliminado y `git ls-files` confirma que ya no está rastreado; no quedan enlaces públicos vigentes.

---

## ATLAS-TD-016 — Capturas de una interfaz anterior todavía rastreadas

- **Estado:** `RESOLVED`
- **Severidad:** `LOW`
- **Origen:** Auditoría documental Atlas v4.1
- **Archivos candidatos:**
  - `docs/01_chat_ui.png`
  - `docs/02_chat_prometeo_ui.png`
  - `docs/03_help_command.png`
  - `docs/04_rag_processing.png`
- **Descripción:** Las capturas pueden pertenecer al manual obsoleto o representar una interfaz anterior.
- **Corrección propuesta:** Eliminar las que no tengan consumidores actuales y conservar solo material vigente.
- **Prueba de aceptación:** Cada imagen conservada tiene un uso actual demostrado; las eliminadas no dejan enlaces rotos.
- **Versión objetivo:** Corte 3.
- **Fecha de resolución:** 2026-07-22.
- **Corte:** Atlas v4.1 Corte 3.
- **Commit de resolución:** `cb01d45`.
- **Evidencia:** las cuatro capturas candidatas fueron eliminadas; README ya no las referencia y `git ls-files docs/*.png` no lista esos archivos.

---

## ATLAS-TD-017 — RFC-0011 no marcado como reemplazado por v4.1

- **Estado:** `RESOLVED`
- **Severidad:** `MEDIUM`
- **Origen:** Auditoría de versionado Atlas v4.1
- **Archivo:** `docs/rfcs/RFC-0011-atlas-v4-versioning.md`
- **Descripción:** El RFC establece v4 visible y 4.0 técnica, pero el cierre actual adopta v4.1 y 4.1.0.
- **Decisión adoptada:** Conservar el contenido histórico y añadir una nota de `SUPERSEDED`.
- **Corrección propuesta:** Añadir nota con la decisión vigente sin reescribir retroactivamente la decisión original.
- **Prueba de aceptación:** El lector puede distinguir la decisión histórica de la versión actual.
- **Versión objetivo:** Corte 3.
- **Fecha de resolución:** 2026-07-22.
- **Corte:** Atlas v4.1 Corte 3.
- **Commit de resolución:** `215f7ba`.
- **Evidencia:** RFC-0011 comienza con `Estado: Superseded`, explica la decisión v4.1 y conserva intacto el contenido histórico posterior.

---

## ATLAS-TD-018 — README enlaza una licencia inexistente

- **Estado:** `OPEN`
- **Severidad:** `MEDIUM`
- **Origen:** Auditoría documental Atlas v4.1
- **Componente:** `README.md`
- **Descripción:** README presenta un badge o enlace hacia `LICENSE`, pero el archivo no existe.
- **Impacto:** Enlace roto y estado legal ambiguo.
- **Decisión adoptada:** No crear una licencia automáticamente en el Corte 3.
- **Corrección propuesta:** Retirar el enlace roto y registrar la selección de licencia como decisión futura.
- **Prueba de aceptación:** README no afirma una licencia inexistente.
- **Versión objetivo:** Corte 3 para el enlace; decisión legal en corte separado.
- **Commit de resolución:** pendiente.
- **Progreso en Corte 3 (2026-07-22, `215f7ba`):**
  - Se retiró el enlace o badge roto.
  - La selección y publicación de una licencia continúa pendiente.

---

## ATLAS-TD-019 — Ausencia de registro central de deuda técnica

- **Estado:** `RESOLVED`
- **Severidad:** `MEDIUM`
- **Origen:** Gobernanza de Atlas
- **Componente:** documentación del proyecto.
- **Descripción:** Los seguimientos estaban repartidos entre auditorías, conversaciones, README y documentación técnica.
- **Impacto:** Riesgo de olvidar deudas aceptadas y repetir análisis.
- **Corrección propuesta:** Mantener este documento como fuente de verdad.
- **Prueba de aceptación:**
  - el documento existe;
  - cada deuda tiene ID;
  - los prompts lo consultan;
  - los commits de resolución actualizan su estado.
- **Versión objetivo:** Corte de registro de deuda.
- **Fecha de resolución:** 2026-07-22.
- **Corte:** Atlas v4.1 Corte 3.
- **Commit de resolución:** `9397d9b`.
- **Evidencia:** `docs/TECHNICAL_DEBT.md` existe, contiene IDs y estados, fue consultado antes del corte y registra aquí las resoluciones con sus SHA reales.

---

## ATLAS-TD-020 — Documentos históricos no están claramente marcados

- **Estado:** `RESOLVED`
- **Severidad:** `LOW`
- **Origen:** Auditoría documental Atlas v4.1
- **Ejemplo conocido:** `docs/TECHNICAL_LOG_V3_8.md`
- **Descripción:** Documentos históricos pueden interpretarse como documentación vigente.
- **Corrección propuesta:** Añadir un banner de documento histórico o moverlos a una ubicación histórica sin romper enlaces.
- **Prueba de aceptación:** Los documentos anteriores indican claramente su versión y estado.
- **Versión objetivo sugerida:** Corte 3 o limpieza documental posterior.
- **Fecha de resolución:** 2026-07-22.
- **Corte:** Atlas v4.1 Corte 3.
- **Commit de resolución:** `215f7ba`.
- **Evidencia:** `docs/TECHNICAL_LOG_V3_8.md` incluye el banner histórico obligatorio y RFC-0011 diferencia su decisión histórica del estado vigente.

---

## ATLAS-TD-021 — Rutas personales en fallbacks de OCR y PDF

- **Estado:** `OPEN`
- **Severidad:** `LOW`
- **Origen:** Auditoría Atlas v4.1 Corte 3
- **Componentes:**
  - `core/pdf_reader.py`
  - `diagnostico_ocr.py`
- **Descripción:** Existen rutas de fallback con `C:\Users\delfa` para localizar herramientas externas como Poppler o Tesseract.
- **Impacto:** Reduce portabilidad y conserva una ruta personal en archivos rastreados. No bloquea la ejecución normal cuando las herramientas están disponibles en `PATH`.
- **Corrección propuesta:** Usar variables de entorno, configuración explícita o detección portable.
- **Prueba de aceptación:** `git grep -F "C:\Users\delfa" -- "*.py"` no devuelve rutas ejecutables.
- **Versión objetivo sugerida:** `v4.1.x`.
- **Commit de resolución:** pendiente.

---

## ATLAS-TD-022 — Fallos de archivos nuevos no persisten en el manifiesto

- **Estado:** `OPEN`
- **Severidad:** `MEDIUM`
- **Origen:** SDD-0 de indexación incremental, INV-7 y sección 14.4.
- **Componente:** `core/indexer.py`, `core/index_manifest.py`.
- **Descripción:** Si falla la primera indexación de un archivo, no existe una entrada
  previa donde conservar `last_error`; el archivo vuelve a descubrirse en cada sync,
  pero el fallo no queda persistido en el manifiesto.
- **Impacto:** El reintento funciona, aunque el estado pendiente no sobrevive como
  diagnóstico estructurado entre ejecuciones.
- **Corrección propuesta:** Diseñar en un corte futuro una representación compatible
  de fallos iniciales sin registrar una huella exitosa inexistente.
- **Prueba de aceptación:** Un fallo inicial sintético persiste como pendiente, se
  reintenta y converge sin confundirlo con un documento indexado.
- **Versión objetivo sugerida:** `v4.1.x`.
- **Commit de resolución:** pendiente.

---

## ATLAS-TD-023 — Reporte asimétrico si falla el manifiesto tras eliminar

- **Estado:** `OPEN`
- **Severidad:** `MEDIUM`
- **Origen:** SDD-0 de indexación incremental, INV-6 y sección 14.4.
- **Componente:** `core/indexer.py`, `core/index_manifest.py`.
- **Descripción:** Si Chroma elimina correctamente los chunks pero falla el guardado
  posterior del manifiesto, `eliminar_documento_indexado()` conserva actualmente
  `deleted`/`not_found` y registra el fallo solo en logs.
- **Impacto:** El resultado estructurado no representa la misma divergencia que queda
  observable entre Chroma y manifiesto.
- **Corrección propuesta:** Alinear el resultado público con la semántica de fallo
  parcial sin romper compatibilidad.
- **Prueba de aceptación:** Una falla sintética de `manifest.save` después del borrado
  produce un resultado no exitoso explícito y permite convergencia posterior.
- **Versión objetivo sugerida:** `v4.1.x`.
- **Commit de resolución:** pendiente.

---

## ATLAS-TD-024 — `.tmp` huérfanos del manifiesto sin limpieza

- **Estado:** `OPEN`
- **Severidad:** `LOW`
- **Origen:** SDD-0 de indexación incremental, sección 14.4.
- **Componente:** `core/index_manifest.py`.
- **Descripción:** La publicación atómica puede dejar un archivo `.tmp` si el proceso
  termina antes de `os.replace`; no existe una política explícita de limpieza.
- **Impacto:** Acumula artefactos de mantenimiento sin afectar el manifiesto válido.
- **Corrección propuesta:** Definir una limpieza segura que nunca sustituya ni borre
  el manifiesto publicado.
- **Prueba de aceptación:** Un `.tmp` sintético se gestiona sin modificar el JSON
  válido ni interpretar el temporal como estado vigente.
- **Versión objetivo sugerida:** `v4.1.x`.
- **Commit de resolución:** pendiente.

---

## ATLAS-TD-025 — Conteos de chunks sin verificación profunda

- **Estado:** `OPEN`
- **Severidad:** `MEDIUM`
- **Origen:** SDD-0 de indexación incremental, secciones 6 y 14.4.
- **Componente:** `core/index_consistency.py`, manifiesto y Chroma.
- **Descripción:** IDX-C1 comprueba presencia por identidad, pero no publica
  `mismatch_chunk_counts` porque aún no existe una semántica validada para duplicados
  legacy, estados intermedios o cambios de chunking.
- **Impacto:** Una identidad puede tener chunks presentes y aun así diferir del conteo
  registrado sin una categoría específica.
- **Corrección propuesta:** Definir primero la semántica y luego añadir diagnóstico y
  reparación en un corte separado.
- **Prueba de aceptación:** Fixtures para conteo vigente, faltante, duplicado legacy y
  cambio de chunking producen resultados no ambiguos.
- **Versión objetivo sugerida:** `v4.1.x`.
- **Commit de resolución:** pendiente.

---

## ATLAS-TD-026 — Purga controlada de huérfanos diferida

- **Estado:** `OPEN`
- **Severidad:** `INFORMATIONAL`
- **Origen:** SDD-0 de indexación incremental, secciones 9 y 14.4.
- **Componente:** operación futura del índice.
- **Descripción:** Atlas 4.1 detecta y reporta vectores sin fuente ni manifiesto, pero
  deliberadamente no los elimina y no expone una opción de purga.
- **Impacto:** No es un defecto del contrato actual; registra una capacidad destructiva
  posible que requiere diseño y consentimiento propios.
- **Corrección propuesta:** Solo mediante una especificación futura independiente con
  preview, identidad verificable, confirmación explícita y rollback.
- **Prueba de aceptación:** El corte futuro deberá demostrar que preview no escribe y
  que nada se elimina sin consentimiento inequívoco.
- **Versión objetivo sugerida:** posterior a `v4.1`.
- **Commit de resolución:** pendiente.

---

## ATLAS-TD-027 — Cambio de modelo no dispara reindexación

- **Estado:** `OPEN`
- **Severidad:** `INFORMATIONAL`
- **Origen:** SDD-0 de indexación incremental, sección 14.4.
- **Componente:** `core/index_manifest.py`, `core/indexer.py`.
- **Descripción:** El manifiesto registra `embedding_model` de forma informativa, pero
  sincronización y consistencia no lo usan como disparador de reindexación.
- **Impacto:** Un cambio explícito de modelo puede requerir reconstrucción manual para
  homogeneizar embeddings; no hay migración automática en v4.1.
- **Corrección propuesta:** Definir compatibilidad y política de reindexación en un
  corte futuro antes de automatizarla.
- **Prueba de aceptación:** Cambiar el modelo en fixtures produce el resultado
  contractual elegido sin mezclar embeddings silenciosamente.
- **Versión objetivo sugerida:** `v4.1.x` o posterior.
- **Commit de resolución:** pendiente.

---

# Historial de deudas resueltas

Atlas v4.1 Corte 3 y su follow-up resolvieron, con evidencia en sus entradas originales: ATLAS-TD-004, 005, 006, 007, 008, 009, 010, 011, 012, 013, 015, 016, 017, 019 y 020.

---

# Reglas de mantenimiento

1. No eliminar entradas resueltas.
2. No reutilizar IDs.
3. No registrar preferencias de estilo como deuda técnica.
4. Toda deuda debe tener evidencia concreta.
5. Todo seguimiento aceptado por una auditoría debe:
   - vincularse a una deuda existente; o
   - crear una deuda nueva.
6. Un builder no puede marcar una deuda como resuelta sin:
   - cambio implementado;
   - prueba de aceptación;
   - commit;
   - evidencia en el informe final.
7. Una deuda puede resolverse dentro de otro corte solo si:
   - está directamente relacionada;
   - no amplía materialmente el alcance;
   - tiene pruebas claras;
   - el planner lo declara explícitamente.
8. Las decisiones legales, de producto o de compatibilidad no se infieren automáticamente.
