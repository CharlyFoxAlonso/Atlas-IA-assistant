# AGENTS.md — Atlas Repository Governance

**Proyecto:** Atlas — Asistente AI híbrido (local/nube) con RAG semántico, búsqueda web, voz, visión y memoria persistente.

**Propósito:** Este archivo define la gobernanza del repositorio, políticas de seguridad, playbooks operativos e integraciones disponibles para agentes que operan en este repositorio.

---

## 1. Jerarquía de Instrucciones

Cuando operes en este repositorio, aplicá las instrucciones en este orden:

1. **Políticas transversales** (`.agents/policies/*.md`)
2. **Playbook correspondiente a tu rol** (`.agents/playbooks/*.md`)
3. **Integraciones opcionales** (`.agents/integrations/*.md`)
4. **Instrucciones específicas del task** (proporcionadas en la conversación)

Las políticas y playbooks son de cumplimiento obligatorio. Las integraciones son opcionales y se aplican cuando agregan valor al task.

---

## 2. Políticas Transversales

| Archivo | Descripción |
|---|---|
| `.agents/policies/git-safety.md` | Reglas de seguridad Git: inspección previa, operaciones prohibidas, control de alcance, commits, reporte final. |
| `.agents/policies/testing.md` | Política de evidencia: categorías de evidencia, baseline, orden de tests, coverage, fallos, reporte final. |

**Obligatorio:** Antes de cualquier task que inspeccione o modifique el repositorio, leé y aplicá `git-safety.md`. Antes de cualquier task que cambie o verifique comportamiento, leé y aplicá `testing.md`.

---

## 3. Playbooks por Rol

| Playbook | Uso |
|---|---|
| `.agents/playbooks/implement.md` | Tasks que modifican código, crean archivos, corrigen defectos, refactorizan o implementan un plan aprobado. |
| `.agents/playbooks/verify.md` | Tasks que revisan, testean o validan una implementación existente sin modificarla. |
| `.agents/playbooks/audit.md` | Tasks de auditoría evidence-based de código, arquitectura, documentación, seguridad o calidad. |
| `.agents/playbooks/plan.md` | Tasks de investigación, análisis, diseño o planificación sin modificar código productivo. |

**Regla:** Usá exactamente el playbook que corresponde al task solicitado. No combinés playbooks ni cambies de rol durante un task sin autorización explícita.

---

## 4. Integraciones Opcionales

| Integración | Descripción | Cuándo usar |
|---|---|---|
| `.agents/integrations/codebase-memory-mcp.md` | Uso de Codebase Memory MCP para localizar símbolos, dependencias, tests, relaciones arquitectónicas e impacto de cambios. | Cuando agrega valor: localizar símbolos, explorar arquitectura, estimar impacto, encontrar tests relacionados. No usar ceremonialmente para cambios triviales. |

**Regla:** La integración es opcional. Su salida no reemplaza lectura de código fuente, búsqueda directa, revisión de diff o ejecución de tests. Si no está disponible, continuá con herramientas normales del repositorio.

---

## 5. Templates

| Template | Uso |
|---|---|
| `.agents/templates/final-report.md` | Estructura obligatoria para reportes finales de tasks de implementación, verificación, auditoría o planificación. |

---

## 6. Identidad y Alcance del Proyecto

**Atlas** es un asistente personal de IA local-first e híbrido construido en Python.

**Objetivos:**
- Utilizar modelos locales mediante Ollama
- Reducir dependencia de suscripciones de IA
- Ingerir documentos y material académico
- Construir RAG local con ChromaDB
- Responder desde material almacenado por el usuario
- Generar y corregir exámenes
- Utilizar proveedores externos opcionales (NVIDIA, Groq) cuando el usuario lo decide
- Ser portable e instalable en otras computadoras Windows

**No es:**
- Un SaaS multi-tenant
- Una arquitectura de microservicios
- Un sistema empresarial distribuido
- Un producto diferente (no Xilas, no Frontier)

**Stack tecnológico:** Python 3.11–3.13 · Ollama / NVIDIA NIM / Groq · Streamlit · FastAPI · ChromaDB + sentence-transformers · pypdf / docx / pptx / Tesseract / Pillow · Groq Whisper / Vosk / Edge TTS / pyttsx3 · DuckDuckGo / Tavily / SearXNG

---

## 6.1 Distinción de Identidades Documentadas

Este repositorio contiene referencias a varios "personajes" o identidades en su documentación histórica. Distinguí claramente:

| Identidad | Contexto | Tratamiento actual |
|---|---|---|
| **Atlas** | Producto actual | Referencia principal del producto |
| **Atlas Auditor** | Agente de auditoría (`.opencode/agents/atlas-auditor.md`) | Rol específico de auditoría |
| **Frontier** | Proyecto anterior/histórico | Referencia histórica, no producto actual |
| **Xilas** | Proyecto anterior/histórico | Referencia histórica, no producto actual |
| **Charly / Usuario** | Usuario humano original | Datos personales — **no incluir en docs públicas, ni logs, ni commits** |

**Regla:** En documentación pública, reportes, commits y comunicación externa, usá solo "Atlas" como nombre del producto. No expongas datos personales, rutas privadas ni referencias al usuario original.

---

## 7. Entrypoints del Proyecto

| Comando | Descripción |
|---|---|
| `python run.py` | CLI interactivo |
| `streamlit run atlas_ui.py` | UI web |
| `uvicorn main_api:app --reload` | API REST |
| `python -m core.system` | CLI técnico (doctor/heal/launch) |

---

## 8. Directorios Clave

| Directorio | Contenido |
|---|---|
| `core/` | Cerebro, router, modelos, config, RAG, memoria, seguridad, multimodal |
| `core/system/` | Doctor, healer, launcher, paths, logs, command runner |
| `agents/` | Stats researcher, export study |
| `tests/` | Tests unitarios (unittest) |
| `scripts/` | Backup, restore, distribución |
| `docs/` | Arquitectura, RFCs, guías de instalación |
| `memory/` | Datos de usuario, perfiles, diario (gitignored) |
| `vector_db/` | ChromaDB persistente (gitignored) |
| `.opencode/` | Configuración de opencode (agents, commands, skills, project-identity) |
| `.agents/` | Gobernanza del repositorio (políticas, playbooks, integraciones, templates) |

---

## 9. Convenciones

- **Type hints:** obligatorios en `core/system/`, recomendados en el resto
- **Docstrings:** estilo Google
- **Idioma:** Español en UI/mensajes · Inglés en APIs internas (mantener mezcla existente)
- **Dry-run por defecto:** healer y launcher requieren `--apply` para modificar el sistema
- **Commits:** mensaje conciso que coincida con estilo del repo; no commitear sin autorización explícita

---

## 10. Principios de Diseño

- Local-first
- Privacy-first
- Arquitectura modular
- Provider-agnostic
- Streaming by default
- Explícito sobre implícito
- Fail safely

---

## 11. Invariantas Arquitectónicas

1. **Interfaces contienen orquestación, no lógica de dominio central.** UI, CLI y API delegan a `core/` para pensar, buscar, clasificar y operar vectores.
2. **Acceso a proveedores LLM NO está totalmente centralizado.** `brain.py`, `digestion_worker.py` y `exam_mode.py` implementan sus propios streams o llamadas directas a Ollama, NVIDIA y Groq junto al gateway en `core/models.py`. Esto es deuda técnica conocida (ATLAS-TD-001).
3. **Reparaciones del sistema default a dry-run.** Healer y launcher requieren `--apply` explícito.
4. **Datos personales y vector DB permanecen locales.** `memory/` y `vector_db/` son gitignored sin mecanismo de sync.

---

## 12. Variables de Entorno (`.env`)

| Variable | Descripción |
|---|---|
| `NVIDIA_API_KEY` | Clave API de NVIDIA |
| `GROQ_API_KEY` | Clave API de Groq |
| `TAVILY_API_KEY` | Clave API de Tavily |
| `MODELO_LOCAL` | Default: `qwen3:8b` |
| `MOTOR_POR_DEFECTO` | `atlas` / `prometeo` / `groq` |
| `URL_OLLAMA` | Default: `http://127.0.0.1:11434` |
| `SEARXNG_URL` | URL de instancia SearXNG |
| `ATLAS_DATA_DIR` | Override de directorio de datos |
| `ATLAS_MEMORY_DIR` | Override de directorio de memoria |

**Regla:** Nunca commitees `.env`, variantes privadas, claves, tokens ni secretos.

---

## 13. Rutas y Commits

- Los archivos de governance (`.agents/`, `AGENTS.md`) se versionan normalmente
- Los reportes de auditoría en `docs/reviews/` se versionan
- `memory/` y `vector_db/` son gitignored
- No se commitean secretos, rutas absolutas de máquina local ni datos personales

---

## 14. Referencias Rápidas

| Documento | Ubicación |
|---|---|
| Project Identity | `.opencode/project-identity.md` |
| Auditor Agent | `.opencode/agents/atlas-auditor.md` |
| Git Safety Policy | `.agents/policies/git-safety.md` |
| Testing Policy | `.agents/policies/testing.md` |
| Implement Playbook | `.agents/playbooks/implement.md` |
| Verify Playbook | `.agents/playbooks/verify.md` |
| Audit Playbook | `.agents/playbooks/audit.md` |
| Plan Playbook | `.agents/playbooks/plan.md` |
| Codebase Memory MCP | `.agents/integrations/codebase-memory-mcp.md` |
| Final Report Template | `.agents/templates/final-report.md` |

---

## 15. Regla Final

**Preservá el trabajo del usuario, evitá rediseños especulativos, verificá con evidencia real, y reportá limitaciones honestamente.**

El código fuente es la fuente de verdad autoritativa para el comportamiento actual. La documentación puede estar desactualizada; el código nunca miente sobre lo que hace actualmente.