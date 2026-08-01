# Auditoría de corte — Incorporación de Workflow 2.0 (gobernanza y agentes)

Fecha: 2026-08-01
Tipo: Corte
Repositorio: Atlas
Rama: atlas-v4.1-incremental-indexing
Commit base: aba2d43d6a0a22bd3df9e2ad7fb10e3f895f80a7 (HEAD auditado; cambio 100 % en working tree)
Commit final: (sin commit — superficie sin rastrear)
Rango auditado: working tree vs HEAD aba2d43 (no existe rango de commits)
Archivo: AGENTS.md, .agents/**, .opencode/** (superficie de gobernanza y agentes)
Gate: ACCEPT WITH NON-BLOCKING FINDINGS

---

## 1. Resumen ejecutivo

Workflow 2.0 está incorporado como **contenido de working tree sin commit** sobre el
HEAD `aba2d43`, junto con una modificación de 18 líneas en `AGENTS.md` (bloque de
routing delimitado). No existe un plan ni un reporte de auditoría previo de la
migración en `docs/`.

La incorporación es **internamente coherente y ejecutable**: la secuencia
Planner → Plan Reviewer → aprobación → Builder → Auditor está completa; los gates y
handoffs están definidos; los cuatro roles están implementados como agentes de
OpenCode y de Claude; los cuatro comandos de OpenCode existen; la skill canónica se
descubre (verificada en esta misma sesión); `validate_workflow.py` pasa (exit 0) y
todos los hashes de `install-state.json` coinciden con los archivos reales.

Los hallazgos son no bloqueantes: ambigüedad de precedencia entre el sistema de
playbooks preexistente y los roles de Workflow 2.0 (dos fuentes por regla), cuatro
vocabularios de gates de auditoría conviviendo, estado sin commit de toda la
superficie, y una frontera de privacidad a nivel de permisos más débil en los
agentes workflow-* que en los agentes atlas-* preexistentes.

**Respuesta a la pregunta central:** sí, Workflow 2.0 está suficientemente
consolidado para gobernar los próximos cortes con prompts compactos, siempre que se
resuelvan los seguimientos F1 (precedencia), F2 (vocabulario de gates) y F3
(decisión de commit) antes de declarar la gobernanza cerrada.

---

## 2. Objetivo

Determinar si Workflow 2.0 está correctamente incorporado, es ejecutable por los
agentes y puede gobernar los próximos cortes sin duplicaciones, contradicciones ni
pérdida de reglas.

## 3. Alcance

- `AGENTS.md` (modificación en working tree)
- `.agents/**` (workflow-2/, skills/workflow-2/, playbooks, policies, templates, skills)
- `.opencode/**` (agents workflow-*, commands, project-identity, skills, templates)
- `CLAUDE.md` y `.claude/**` (superficie Claude Code de la misma incorporación)

## 4. Fuera de alcance

- Implementación de cortes IDX-C1..INT-C7 de la SDD (solo se verificó ausencia de contradicción)
- Contenido de `.opencode/skills/*` (skills de dominio preexistentes, salvo colisiones)
- Código de producción y tests de Atlas
- Cualquier escritura fuera del reporte

---

## 5. Estado Git (CONFIRMED)

| Ítem | Valor |
|---|---|
| Rama | `atlas-v4.1-incremental-indexing` |
| HEAD | `aba2d43d6a0a22bd3df9e2ad7fb10e3f895f80a7` |
| Origin | `2a4700d` (la rama va 2 commits adelante: `e3f428f`, `aba2d43`, ambos de la SDD; **no** son Workflow 2.0) |
| AGENTS.md | Modificado: solo bloque `<!-- workflow-2:begin/end -->` añadido (L560-576); `git diff --check` exit 0 |
| Untracked | `.agents/skills/workflow-2/`, `.agents/workflow-2/`, `.claude/`, `.opencode/agents/workflow-*.md` (×4), `.opencode/commands/`, `CLAUDE.md` |
| Untracked preexistente (trabajo de usuario, no parte de la incorporación) | `docs/reviews/cuts/2026-08-01-aba2d43-sdd0-incremental-indexing-contracts-review.md` |

Base determinada con Git: **HEAD `aba2d43` es la base correcta**; el diff de la
incorporación es íntegramente working tree vs HEAD. No hay rango de commits que
auditar.

## 6. Instrucciones aplicables

`AGENTS.md` (bloque workflow-2 incluido), `.agents/playbooks/audit.md`,
`.agents/policies/git-safety.md`, `.agents/policies/testing.md`,
`.agents/workflow-2/core.md`, `.agents/workflow-2/contracts/handoffs.md`,
`.agents/workflow-2/roles/auditor.md`, `.agents/skills/workflow-2/SKILL.md`.
---

## 7. Mapa de archivos y autoridad

| Archivo | Clasificación | Evidencia |
|---|---|---|
| `AGENTS.md` (working tree) | `AUTHORITATIVE` | Routing raíz; contiene el bloque gestionado de workflow-2 (L560-576) |
| `AGENTS.md` (HEAD) | — | No contiene el bloque; el bloque está sin commit (CONFIRMED por diff) |
| `.agents/workflow-2/core.md` | `AUTHORITATIVE` | Reglas permanentes, secuencia de roles, routing de políticas |
| `.agents/workflow-2/contracts/handoffs.md` | `AUTHORITATIVE` | Contratos entre roles y gates |
| `.agents/workflow-2/roles/{planner,plan-reviewer,builder,auditor}.md` | `AUTHORITATIVE` | Reglas por rol; vocabularios de gate propios |
| `.agents/workflow-2/policies/{engineering,security,debugging,prototypes,definition-of-done}.md` | `SUPPORTING` | Políticas de riesgo cargadas por core.md |
| `.agents/workflow-2/policies/git.md`, `policies/testing.md` | `REDUNDANT` | Copias condensadas de `.agents/policies/git-safety.md` y `testing.md` (mismo dominio, dos fuentes) |
| `.agents/workflow-2/templates/{microcut-plan,plan-review,build-report,audit-report}.md` | `TEMPLATE` | Referenciados genéricamente por SKILL.md y roles |
| `.agents/workflow-2/templates/bug-report.md` | `UNREFERENCED` | Ninguna instrucción lo referencia por nombre |
| `.agents/workflow-2/version.json`, `install-state.json` | `SUPPORTING` | Estado de instalación; hashes verificados coincidentes (CONFIRMED) |
| `.agents/skills/workflow-2/SKILL.md` | `AUTHORITATIVE` | Entrada canónica; descubierta por OpenCode en esta sesión (CONFIRMED) |
| `.agents/skills/workflow-2/references/migration-rules.md` | `SUPPORTING` | Referenciado por SKILL.md |
| `.agents/skills/workflow-2/references/role-selection.md` | `UNREFERENCED` | Ninguna instrucción lo referencia (grep CONFIRMED) |
| `.agents/skills/workflow-2/agents/openai.yaml` | `UNREFERENCED` | No referenciado por ninguna instrucción |
| `.agents/skills/workflow-2/scripts/*.py` | `SUPPORTING` | Tooling de migración; `validate_workflow.py` exit 0 |
| `.opencode/agents/workflow-*.md` (×4) | `SUPPORTING` | Superficie ejecutable; ruta válida (`.opencode/agents/`); delegan en la skill |
| `.opencode/commands/workflow-{plan,review-plan,build,audit}.md` | `SUPPORTING` | Triggers compactos; ruta `.opencode/commands/` válida |
| `.claude/agents/workflow-*.md` (×4) | `SUPPORTING` | Superficie Claude Code; skills: workflow-2-claude |
| `.claude/skills/workflow-2-claude/SKILL.md` | `SUPPORTING` | Adaptador sin duplicación (delega en la skill canónica) |
| `CLAUDE.md` | `SUPPORTING` | Importa `@AGENTS.md`; contiene 2 referencias rotas (R1, R2) |
| `.agents/playbooks/{plan,implement,verify,audit}.md` | `REDUNDANT` | Siguen ruteados por AGENTS.md §1 pero su dominio se superpone con los roles |
| `.agents/policies/git-safety.md`, `testing.md` | `AUTHORITATIVE` | Políticas de proyecto, más específicas de Atlas; siguen ruteadas por AGENTS.md |
| `.agents/templates/final-report.md` | `TEMPLATE` | Formato de respuesta raíz (AGENTS.md §1); convive con los templates de workflow-2 |
| `.agents/integrations/codebase-memory-mcp.md` | `SUPPORTING` | Integración opcional; sin conflicto |
| `.opencode/project-identity.md` | `SUPPORTING` | Identidad del proyecto; cargado por `opencode.json` |
| `.opencode/agents/atlas-auditor.md` | `REDUNDANT` | Auditor preexistente con vocabulario de gates propio (C2); permisos de privacidad más estrictos que workflow-auditor (F4) |
| `.opencode/agents/atlas-plan-to-{codex,kimik3}.md` | `SUPPORTING` | Planificadores preexistentes; sin conflicto directo |
| `.opencode/skills/auditoria/SKILL.md` | `SUPPORTING` | Skill de dominio preexistente |
| `.agents/skills/auditoria/SKILL.MD` | `REDUNDANT` | Duplicado preexistente de la skill auditoria (contenido distinto, 3.5 KB vs 5.3 KB); no descubierta en esta sesión |
| `.opencode/_index/SKILLS_INDEX.md`, `_templates/*`, `scripts/validate-skills.py` | `SUPPORTING` | Tooling de authoring; indexa solo `.opencode/skills` |
| `docs/reviews/cuts/*` | `HISTORICAL` (evidencial) | Reportes ligados a revisión; el más reciente usa el gate de atlas-auditor (evidencia de C2) |
| `docs/spec/atlas-v4.1-incremental-indexing-sdd.md` | `AUTHORITATIVE` (dominio) | Gobernante de contratos de indexación; sin contradicción con workflow-2 |
---

## 8. Diagrama textual del Workflow 2.0 real

```text
Prompt compacto del usuario
   │  (AGENTS.md §1 + bloque workflow-2 → elige UN rol; skill carga core.md + handoffs)
   ▼
┌─ Planner (solo lectura) ───────────────┐
│  investiga repo → contrato microcut    │
│  veredicto: VIABLE | VIABLE WITH       │
│  CONDITIONS | NOT VIABLE               │
└───────────────┬────────────────────────┘
                ▼
┌─ Plan Reviewer (solo lectura, independiente) ─┐
│  gate: APPROVED | APPROVED WITH CONDITIONS |  │
│  REJECTED                                     │
└───────────────┬────────────────────────────────┘
                ▼
        Aprobación (gate del reviewer;
        autorización explícita del usuario solo para
        commit/push/ops destructivas — core.md regla 11)
                ▼
┌─ Builder (único escritor) ─────────────┐
│  implementa solo el contrato aprobado  │
│  → tests → diff → Builder report       │
│  (no se auto-aprueba, no commitea)     │
└───────────────┬────────────────────────┘
                ▼
┌─ Auditor (solo lectura, independiente) ─────────┐
│  verifica contrato vs diff real vs evidencia    │
│  veredicto: PASS | PASS WITH OBSERVATIONS |     │
│  FAIL | INCONCLUSIVE                            │
└───────────────┬─────────────────────────────────┘
                ▼
   PASS / PASS WITH OBSERVATIONS → DoD cumplida (def. 12)
   FAIL / INCONCLUSIVE → remediación → Builder
   (mismo contrato o contrato nuevo — core.md L31-32)
                ▼
   Commit/push SOLO con autorización explícita del usuario
```

Puntos de detención definidos: plan no viable; plan rechazado; contradicción entre
evidencia y contrato; expansión de alcance; decisión durable de producto/arquitectura
faltante; riesgo de datos/seguridad no planificado; verificación obligatoria ausente
(handoffs.md «Renegotiation»; core.md regla 10).

Separación de responsabilidades: Planner, Plan Reviewer y Auditor son read-only;
Builder es el único escritor; el veredicto técnico final lo emite el Auditor
(core.md regla 12; handoffs.md). Verificado además a nivel de permisos: los agentes
OpenCode de los tres roles read-only declaran `edit: deny` y los agentes Claude
declaran `permissionMode: plan` con `disallowedTools` (validate_workflow.py lo
comprueba, exit 0).

Correcciones documentales vs reauditorías: el flujo define remediación → Builder
bajo el mismo contrato o uno nuevo (core.md L31-32), y AGENTS.md §12 fija la
inmutabilidad de reportes salvo corrección pedida. No existe una vía diferenciada
«corrección documental» dentro del workflow (se trataría como microcut de
documentación PRODUCTION); gap menor, no bloqueante.

---

## 9. Duplicaciones

| ID | Archivos | Regla afectada | Fuente que debería quedar autoritativa | Corrección mínima | Riesgo si no se corrige |
|---|---|---|---|---|---|
| D1 | `.agents/policies/git-safety.md` ↔ `.agents/workflow-2/policies/git.md` | Reglas Git (estado inicial, trabajo de usuario, ops prohibidas, diff final) | `.agents/policies/git-safety.md` (específica de Atlas; git.md es copia condensada) | Declarar en core.md que las políticas de proyecto prevalecen y tratar git.md como resumen | Divergencia futura entre las dos redacciones |
| D2 | `.agents/policies/testing.md` ↔ `.agents/workflow-2/policies/testing.md` | Clases de evidencia, orden de ejecución, no debilitar tests | `.agents/policies/testing.md` (más detallada) | Igual que D1 | Divergencia en criterios de evidencia según el agente que ejecute |
| D3 | `.agents/playbooks/*` ↔ `.agents/workflow-2/roles/*` | Proceso completo de plan/implementación/auditoría | La que AGENTS.md declare (hoy ninguna tiene precedencia) | Sentencia de precedencia en AGENTS.md (F1) | Dos procesos para el mismo tipo de tarea; gates y formatos distintos |
| D4 | `.agents/templates/final-report.md` ↔ `.agents/workflow-2/templates/*.md` | Formato de informe final | La que AGENTS.md declare por modo | Ídem F1/F2 | Reportes inconsistentes entre modos |
| D5 | `.opencode/agents/atlas-auditor.md` ↔ `.opencode/agents/workflow-auditor.md` ↔ `.agents/workflow-2/roles/auditor.md` | Veredicto de auditoría | workflow-auditor + roles/auditor.md para cortes workflow-2 | Normalizar vocabulario (F2) | Cuatro vocabularios de gates conviviendo (C2) |
| D6 | `.agents/skills/auditoria/SKILL.MD` ↔ `.opencode/skills/auditoria/SKILL.md` | Skill «auditoria» (preexistente, contenido distinto) | `.opencode/skills/auditoria/SKILL.md` (la descubierta por OpenCode) | Alinear/eliminar la copia en un corte separado | Colisión de nombre y ambigüedad (preexistente, no introducida por workflow-2) |
---

## 10. Contradicciones

| ID | Archivos | Regla afectada | Fuente autoritativa | Corrección mínima | Riesgo |
|---|---|---|---|---|---|
| C1 | AGENTS.md §1 (playbooks) ↔ AGENTS.md bloque workflow-2 (roles) | Qué proceso gobierna cada tarea; no hay precedencia declarada | AGENTS.md (debe declararlo explícitamente) | 1 frase de precedencia en el bloque workflow-2 (p. ej., «los roles gobiernan cortes y migraciones; los playbooks siguen para investigación y verificación read-only no cubierta por un rol») | Cada agente resuelve la ambigüedad distinto; cortes con procesos mezclados |
| C2 | Vocabularios de gates: atlas-auditor (`ACCEPT`/`ACCEPT WITH FOLLOW-UP`/`REQUEST CHANGES`/`REJECT`) vs `.agents/playbooks/audit.md` (`HEALTHY`…`CRITICAL`) vs `.agents/playbooks/verify.md` (`APPROVED`/`APPROVED WITH NOTES`) vs workflow-2 (`PASS`/`PASS WITH OBSERVATIONS`/`FAIL`/`INCONCLUSIVE`) | Veredicto técnico de auditoría/verificación | workflow-2 (roles/auditor.md + handoffs.md) para cortes gobernados por workflow-2 | Adoptar PASS/PASS WITH OBSERVATIONS/FAIL/INCONCLUSIVE para cortes; marcar los demás como legacy en su documento | Gates incomparables entre reportes; evidencia: el reporte SDD de 2026-08-01 usa «ACCEPT WITH NON-BLOCKING FINDINGS», variante de atlas-auditor |
| C3 | `implement.md` («APPROVED WITH NOTES») vs `plan-reviewer.md` («APPROVED WITH CONDITIONS») | Mismo slot semántico (aprobación con condiciones) con nombres distintos | workflow-2 (plan-reviewer.md) | Unificar nombre | Confusión menor al comparar gates |

No se detectó contradicción con la SDD activa de Atlas 4.1 (gobierna contratos de
indexación; workflow-2 gobierna proceso) ni con el flujo de cortes IDX-C1..INT-C7
(ambos asumen cortes pequeños y evidencia). No hay mezcla de reglas genéricas con
decisiones específicas de Atlas: la SDD y `docs/architecture/*` siguen siendo el
hogar de las decisiones de producto.

---

## 11. Referencias rotas o contenido obsoleto

| ID | Severidad | Hallazgo | Evidencia |
|---|---|---|---|
| R1 | LOW | `CLAUDE.md` L7: «Use `/workflow-2` …» — no existe skill ni comando con ese nombre para Claude; la skill se llama `workflow-2-claude` (frontmatter y carpeta) | Lectura de `.claude/skills/workflow-2-claude/SKILL.md` L2 |
| R2 | LOW | `CLAUDE.md` L8: «Keep Claude-specific path rules under `.claude/rules/`» — el directorio `.claude/rules/` no existe | `Test-Path .claude\rules` = False |
| R3 | LOW | `references/role-selection.md` huérfano: ninguna instrucción lo referencia | grep repo: solo aparece en `install-state.json` |
| R4 | LOW | `agents/openai.yaml` huérfano: no referenciado por ninguna instrucción | grep repo: 0 referencias |
| R5 | LOW | `templates/bug-report.md` huérfano: `policies/debugging.md` no lo referencia por nombre | grep en `.agents/workflow-2/**`: solo en install-state.json |
| R6 | INFORMATIONAL | `SKILLS_INDEX.md` no incluye la skill workflow-2 | El indexador escanea solo `.opencode/skills`; la skill vive en `.agents/skills` (comportamiento esperado) |

Rutas verificadas como existentes: todos los paths referenciados por AGENTS.md
(core.md, handoffs.md, roles/*), por SKILL.md (`../../workflow-2/*`,
`references/migration-rules.md`, `scripts/*`), por la skill claude
(`.agents/skills/workflow-2/SKILL.md`) y por `opencode.json`
(`.opencode/project-identity.md`). `validate_workflow.py` (exit 0) confirma la
existencia de los archivos requeridos; verifiqué además manualmente los hashes de
archivo completo de `AGENTS.md` y `CLAUDE.md` contra `routing_blocks` de
`install-state.json`: coinciden. El bloque de routing de `AGENTS.md` no introduce
dependencias circulares: skill → core → políticas → roles es acíclico; `CLAUDE.md`
importa `AGENTS.md` (referencia, no ciclo).
---

## 12. Hallazgos

Formato: ID / Severidad / Archivo / Problema / Evidencia / Impacto / Corrección mínima / Estado.

### F1 — MEDIUM — AGENTS.md (bloque workflow-2) y AGENTS.md §1 — Precedencia no declarada entre playbooks y roles
- Problema: dos sistemas de proceso (playbooks por modo; roles por tarea) conviven sin que ninguno declare precedencia; el mapeo es parcial (plan-reviewer y verify no tienen contraparte; los gates difieren).
- Evidencia: AGENTS.md §1 «Select exactly one primary playbook»; bloque workflow-2 «Select exactly one role file»; ningún archivo declara cuál prevalece.
- Impacto: agentes distintos pueden gobernar el mismo tipo de tarea con procesos, gates y formatos distintos; divergencia futura.
- Corrección mínima: agregar una frase de precedencia en el bloque workflow-2 (ver C1) y reflejarla en core.md.
- Estado: CONFIRMED.

### F2 — MEDIUM — Superficie de auditoría — Cuatro vocabularios de gates para el mismo concepto
- Problema: el veredicto técnico final tiene 4 vocabularios incompatibles según el documento que el agente cargue.
- Evidencia: `.opencode/agents/atlas-auditor.md` §16 (ACCEPT/ACCEPT WITH FOLLOW-UP/REQUEST CHANGES/REJECT); `.agents/playbooks/audit.md` §15 (HEALTHY/…/CRITICAL); `.agents/playbooks/verify.md` §13 (APPROVED/APPROVED WITH NOTES/REJECTED/INCONCLUSIVE); `.agents/workflow-2/roles/auditor.md` (PASS/PASS WITH OBSERVATIONS/FAIL/INCONCLUSIVE). El reporte `docs/reviews/cuts/2026-08-01-aba2d43-sdd0-incremental-indexing-contracts-review.md` usa «ACCEPT WITH NON-BLOCKING FINDINGS», variante de atlas-auditor.
- Impacto: gates incomparables entre reportes; el usuario debe traducir vocabularios.
- Corrección mínima: adoptar el vocabulario de workflow-2 para cortes; marcar los demás como legacy.
- Estado: CONFIRMED.

### F3 — MEDIUM — Working tree — Superficie íntegra sin commit y sin registro de migración
- Problema: toda la incorporación (AGENTS.md, CLAUDE.md, `.agents/workflow-2/**`, `.agents/skills/workflow-2/**`, `.opencode/agents/workflow-*`, `.opencode/commands/`, `.claude/**`) está sin rastrear; no existe plan ni auditoría de la migración en `docs/`.
- Evidencia: `git status --porcelain=v1` (6 entradas untracked + AGENTS.md modificado); `audit_repo.py` decide `DEFER` cuando la superficie de agentes tiene cambios sin commit; grep: sin documentos de plan/revisión en `docs/`.
- Impacto: `git clean -fdx` o un checkout destructivo eliminaría la incorporación completa; sin historia revisión-por-revisión; la regla «audit the migration» de migration-rules.md no tiene artefacto.
- Corrección mínima: decisión del usuario de commitear la superficie como corte de migración de políticas propio (separado de cortes de producto), seguido de una auditoría del diff commiteado.
- Estado: CONFIRMED.

### F4 — MEDIUM — `.opencode/agents/workflow-*.md` — Frontera de privacidad a nivel de permisos más débil que los agentes atlas-*
- Problema: los agentes workflow-* declaran `read: allow` sin denies para `.env`, `memory/**` y `vector_db/**`; los agentes atlas-* preexistentes los niegan explícitamente. La protección queda solo a nivel de texto (AGENTS.md §6, security.md).
- Evidencia: frontmatter de `workflow-planner.md` (read allow plano) vs `atlas-auditor.md` (`*.env: deny`, `memory/**: deny`, `vector_db/**: deny`).
- Impacto: un agente con instrucciones incompletas podría leer datos privados del usuario; viola el principio de mínimo privilegio declarado en security.md.
- Corrección mínima: replicar los denies de lectura de atlas-auditor en los 4 agentes workflow-* de OpenCode.
- Estado: CONFIRMED.

### F5 — LOW — CLAUDE.md — Referencia rota a `/workflow-2`
- Problema: no existe skill ni comando con ese nombre para Claude; la skill es `workflow-2-claude`.
- Evidencia: frontmatter `.claude/skills/workflow-2-claude/SKILL.md` L2 (`name: workflow-2-claude`); sin archivo `.claude/commands/workflow-2*`.
- Impacto: un usuario de Claude Code que invoque `/workflow-2` no obtendrá el workflow.
- Corrección mínima: cambiar a `/workflow-2-claude` (o renombrar la skill).
- Estado: CONFIRMED.

### F6 — LOW — CLAUDE.md — Referencia a `.claude/rules/` inexistente
- Problema: la instrucción remite reglas de Claude a un directorio que no existe.
- Evidencia: `Test-Path .claude\rules` = False.
- Impacto: directiva colgante; el primer archivo de reglas de Claude no tendría hogar consistente.
- Corrección mínima: crear el directorio cuando existan reglas, o eliminar la frase.
- Estado: CONFIRMED.

### F7 — LOW — `.agents/workflow-2/policies/git.md` y `testing.md` — Duplicación con políticas de proyecto
- Problema: copias condensadas de `git-safety.md` y `testing.md` (D1, D2) sin declaración de jerarquía.
- Impacto: divergencia futura entre redacciones; dos fuentes para la misma regla.
- Corrección mínima: declarar en core.md que las políticas de proyecto prevalecen; tratar las de workflow-2 como resumen gestionado.
- Estado: CONFIRMED.

### F8 — LOW — `.agents/skills/workflow-2/references/role-selection.md`, `agents/openai.yaml`, `templates/bug-report.md` — Huérfanos
- Problema: no referenciados por ninguna instrucción (R3, R4, R5).
- Impacto: contenido muerto que puede divergir o confundir.
- Corrección mínima: referenciarlos desde SKILL.md/core.md o retirarlos del paquete gestionado.
- Estado: CONFIRMED.

### F9 — LOW — `.agents/skills/auditoria/SKILL.MD` — Duplicado preexistente de la skill auditoria
- Problema: segunda copia de la skill «auditoria» con contenido distinto (3.5 KB vs 5.3 KB); solo la de `.opencode/skills` se descubre en esta sesión.
- Impacto: colisión de nombre y ambigüedad; preexistente a Workflow 2.0.
- Corrección mínima: corte separado para alinear/eliminar la copia de `.agents/skills`.
- Estado: CONFIRMED (no introducido por la incorporación).

### F10 — INFORMATIONAL — Workflow 2.0 — Sin vía diferenciada para correcciones documentales y sin ejemplo de prompt compacto
- Problema: las correcciones de documentación se tratan como microcut PRODUCTION; AGENTS.md §14 muestra el ejemplo compacto con terminología de playbooks, no de workflow-2.
- Impacto: fricción menor; los comandos `/workflow-*` cubren el hueco.
- Corrección mínima: opcional; añadir un ejemplo compacto workflow-2 en AGENTS.md.
- Estado: INFERRED (impacto) / CONFIRMED (hechos).

---

## 13. Claims verificados

| Claim | Resultado |
|---|---|
| Los archivos gestionados coinciden con `install-state.json` | CONFIRMED (`validate_workflow.py` exit 0 + verificación manual de hashes de AGENTS.md/CLAUDE.md) |
| La secuencia Plan → Review → Build → Audit está completa y con gates | CONFIRMED (core.md L24-32, handoffs.md, roles/*) |
| Los roles read-only niegan edición a nivel de permisos | CONFIRMED (frontmatter OpenCode `edit: deny`; Claude `permissionMode: plan`; validate exit 0) |
| Las rutas referenciadas existen | CONFIRMED (todas las referencias de AGENTS.md, SKILL.md, CLAUDE.md y opencode.json resueltas) |
| Descubrimiento por OpenCode | CONFIRMED (la skill workflow-2 se cargó en esta misma sesión desde `.agents/skills/workflow-2/`; `.opencode/agents/` y `.opencode/commands/` son rutas válidas según la skill customize-opencode) |
| Workflow 2.0 contradice la SDD 4.1 o mezcla decisiones de producto | FALSO (no detectada contradicción; la SDD gobierna contratos de indexación) |
| No hay pérdida de reglas de Git/testing/seguridad respecto a las políticas de Atlas | CONFIRMED con matiz: las versiones workflow-2 son condensadas pero compatibles (D1/D2) |

## 14. Falsos positivos descartados

- Hash de `routing_blocks` de `install-state.json` presuntamente desincronizado: descartado. El hash registrado es del **archivo completo** (según `migrate_repo.py` L101-105), y coincide con el estado real (CONFIRMED).
- `SKILLS_INDEX.md` sin la skill workflow-2: descartado como defecto; el indexador solo cubre `.opencode/skills` (R6).
---

## 15. Evidencia reproducida

| Comando | Resultado | Exit |
|---|---|---|
| `git rev-parse --abbrev-ref HEAD` / `git rev-parse HEAD` | `atlas-v4.1-incremental-indexing` / `aba2d43d6a0a22bd3df9e2ad7fb10e3f895f80a7` | 0 |
| `git status --porcelain=v1 -b` | 1 modified (AGENTS.md) + 6 untracked (superficie workflow-2) + 1 untracked preexistente (reporte SDD) | 0 |
| `git diff HEAD -- AGENTS.md` | Solo añade el bloque workflow-2 (L560-576) | 0 |
| `git diff --check` | Sin errores de whitespace | 0 |
| `python .agents\skills\workflow-2\scripts\validate_workflow.py .` | `Workflow 2.0 validation passed` | 0 |
| Verificación manual de hashes (AGENTS.md, CLAUDE.md) vs `install-state.json` | Coinciden (incluidos `routing_blocks`) | — |
| grep de referencias (`role-selection`, `openai.yaml`, `bug-report`, `/workflow-2`, `.claude/rules`) | R3/R4/R5/R1/R2 confirmados | — |

## 16. Cambios obligatorios (no bloqueantes para la ejecución del workflow; bloqueantes para declarar la gobernanza cerrada)

1. **F1/C1** — Declarar precedencia en AGENTS.md entre playbooks y roles (1 frase en el bloque workflow-2).
2. **F2/C2** — Normalizar el vocabulario de gates para cortes (adoptar PASS/PASS WITH OBSERVATIONS/FAIL/INCONCLUSIVE).
3. **F3** — Decidir y ejecutar el commit de la superficie (corte de migración de políticas, autorizado por el usuario), seguido de auditoría del diff commiteado.
4. **F4** — Replicar los denies de lectura de `.env`/`memory/`/`vector_db/` en los 4 agentes workflow-* de OpenCode.
5. **F5/R1** — Corregir la referencia `/workflow-2` en CLAUDE.md.

## 17. Seguimientos no bloqueantes

- F6/R2 — Crear `.claude/rules/` o quitar la frase de CLAUDE.md.
- F7/D1/D2 — Declarar prevalencia de las políticas de proyecto sobre las copias workflow-2.
- F8/R3/R4/R5 — Referenciar o retirar `role-selection.md`, `openai.yaml`, `bug-report.md`.
- F9/D6 — Corte separado para la duplicación preexistente de la skill auditoria.
- F10 — Ejemplo de prompt compacto workflow-2 en AGENTS.md §14 (opcional).
- C3 — Unificar «APPROVED WITH NOTES» / «APPROVED WITH CONDITIONS».
- Registrar la auditoría de la migración (migration-rules.md «After applying») cuando se commitee la superficie.

## 18. Orden recomendado de corrección

1. Commit de la superficie (F3) — desbloquea el tooling y da historia.
2. Precedencia en AGENTS.md (F1/C1) + re-validar (`validate_workflow.py`).
3. Normalización de gates (F2/C2, C3).
4. Denies de lectura en agentes workflow-* (F4).
5. Referencias de CLAUDE.md (F5/F6).
6. Prevalencia de políticas y huérfanos (F7/F8).
7. Duplicación de skill auditoria (F9) y ejemplos compactos (F10) en cortes separados.

## 19. Limitaciones

- No se ejecutó `.opencode/scripts/validate-skills.py` porque reescribe `SKILLS_INDEX.md` (efecto de escritura; la auditoría es read-only).
- No se pudo verificar la invocación real de los agentes/commands de Claude Code (sin sesión de Claude Code disponible); la verificación es estructural (rutas y convenciones estándar).
- El descubrimiento de la skill workflow-2 por OpenCode está confirmado por la sesión actual; el descubrimiento de los agentes workflow-* se verificó por convención de rutas válidas (`.opencode/agents/`, `.opencode/commands/`), no por invocación.
- El estado sin commit impide auditar un diff formal entre revisiones.

## 20. Estado final del working tree

Sin cambios por esta auditoría. Único archivo nuevo: este reporte
(`docs/reviews/cuts/2026-08-01-aba2d43-cut-workflow-2-governance-review.md`), sin
rastrear, sin stage, sin commit, sin push. No se modificó AGENTS.md, `.agents/**`,
`.opencode/**`, código, tests ni documentación existente.

---

## 21. Conclusión y gate

**Gate: ACCEPT WITH NON-BLOCKING FINDINGS**

**¿Workflow 2.0 está suficientemente consolidado como para gobernar los siguientes
cortes de Atlas sin repetir instrucciones extensas en cada prompt?**

**Sí, con condiciones no bloqueantes.** El workflow es ejecutable hoy: la skill se
descubre, el routing de AGENTS.md apunta a archivos existentes, los cuatro roles y
sus gates están definidos, los comandos `/workflow-*` cubren el ciclo completo,
`validate_workflow.py` pasa y no hay contradicciones internas ni pérdida de reglas
respecto de las políticas de Atlas. Para que la gobernanza quede cerrada sin
ambigüedad, antes de los próximos cortes conviene resolver F1 (precedencia), F2
(vocabulario de gates) y F3 (commit de la superficie); ninguno impide ejecutar un
corte workflow-2 en el estado actual.

---

## 22. Pregunta de cierre (convención Atlas Auditor)

¿Querés que el reporte documental quede como está (sin rastrear) o preferís revisar
alguna sección antes de considerarlo definitivo?