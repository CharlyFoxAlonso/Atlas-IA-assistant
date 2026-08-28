# Audit report — Remediación de gobernanza Workflow 2.0

Fecha: 2026-08-01
Tipo: Corte
Repositorio: C:\Users\delfa\Documents\Atlas
Rama: atlas-v4.1-incremental-indexing
Commit base: aba2d43d6a0a22bd3df9e2ad7fb10e3f895f80a7 (HEAD)
Archivo: docs/reviews/cuts/2026-08-01-aba2d43-cut-workflow-2-remediation-review.md
Gate: FAIL

## 1. Resumen ejecutivo

La remediación cerró correctamente los hallazgos de jerarquía de autoridad,
vocabularios de gates, duplicación normativa Git/testing, permisos de los
agentes OpenCode, referencias Claude y consumidores de archivos huérfanos
(role-selection.md y bug-report.md). El estado de instalación
(install-state.json, versionado, hashes) es consistente y verificado
manualmente; migrate_repo.py no modificó archivos fuera del alcance.

Existe UN hallazgo BLOQUEANTE: la eliminación de
`.agents/skills/workflow-2/agents/openai.yaml` no puede demostrarse como
prescindible. El archivo es metadata esperada por la convención oficial de
skills de OpenAI/Codex, por la convención personal del usuario y por el
tooling Codex activo en la máquina. La única base de la decisión fue un grep
interno sin referencias, exactamente el razonamiento que el pedido de auditoría
excluyó como suficiente. La eliminación se clasifica UNVERIFIED y debe
restaurarse antes del commit.

La superficie NO puede versionarse como un único corte de migración en su
estado actual. Tras restaurar openai.yaml (y re-registrar el estado oficial),
la superficie es versionable como un único corte.

## 2. Objetivo

Determinar si la remediación cerró correctamente los hallazgos de jerarquía,
gates, duplicación normativa, permisos, referencias rotas y archivos huérfanos,
y si la superficie puede versionarse como un único corte de migración.

## 3. Alcance

- HEAD base: aba2d43.
- AGENTS.md (modificado).
- .agents/workflow-2/** (core, contracts, policies, roles, templates, version,
  install-state).
- .agents/skills/workflow-2/** (SKILL.md, references, scripts).
- .opencode/agents/workflow-*.md y .opencode/commands/**.
- CLAUDE.md y .claude/** (agents, skills).
- Verificación del retiro de .agents/skills/workflow-2/agents/openai.yaml.

## 4. Fuera de alcance

- Código de producción, tests de Atlas, SDD, .env, memory/, vector_db/.
- .opencode/agents/atlas-* (preexistentes, no modificados).
- Reportes previos en docs/reviews/cuts/ (trabajo de usuario preexistente).

## 5. Estado Git (observado y reproducido)

- Rama: atlas-v4.1-incremental-indexing; HEAD: aba2d43d6a0a22bd3df9e2ad7fb10e3f895f80a7.
- Modificados: 1 (AGENTS.md).
- Sin rastrear: 43 (41 de la superficie de migración + 2 reportes preexistentes:
  governance-review y sdd0-incremental-indexing-contracts-review).
- git diff --check: exit 0 (sin errores de whitespace).
- Sin stage, sin commits, sin push (verificado).

## 6. Instrucciones aplicables

- AGENTS.md (global; bloque de routing Workflow 2.0 con jerarquía de autoridad).
- .agents/workflow-2/core.md, contracts/handoffs.md, roles/auditor.md.
- .agents/policies/git-safety.md y .agents/policies/testing.md (fuentes
  normativas únicas).
- Pedido de auditoría del usuario (2026-08-01), incluido el punto crítico sobre
  openai.yaml.

## 7. Entorno

- OS: Windows (PowerShell 5.1).
- Python: intérprete global `python` (validación ejecutada; bytecode generado
  cpython-314).
- Git: repositorio local en C:\Users\delfa\Documents\Atlas.

## 8. Diff inspeccionado

- AGENTS.md: único archivo rastreado modificado. El diff agrega el bloque
  gestionado `<!-- workflow-2:begin -->...<!-- workflow-2:end -->` con routing
  de roles y la jerarquía de autoridad (AGENTS.md global; Workflow 2.0 gobierna
  microcortes; git-safety.md y testing.md fuentes únicas; playbooks
  legacy/supporting). Coherente con core.md.
- Los 41 archivos de superficie restantes están sin rastrear (incorporación
  nueva, no commiteada). Todos inspeccionados por lectura directa (listado
  completo en el inventario, sección 18).

## 9. Criterios de aceptación (evaluación)

| Criterio | Resultado | Evidencia |
|---|---|---|
| Jerarquía de autoridad inequívoca | PASS | AGENTS.md (bloque routing, líneas 558-582) y core.md seccion Authority hierarchy (lineas 34-44): 4 niveles sin ambiguedad; playbooks declarados legacy/supporting en ambos |
| Workflow 2.0 como proceso gobernante de microcortes | PASS | AGENTS.md (roles por modo), core.md Role sequence (lineas 26-32), SKILL.md (Execute the contract) |
| git-safety.md y testing.md fuentes normativas unicas | PASS | core.md linea 39-42; policies/git.md y testing.md (5 lineas, solo referencia); grep de duplicacion en 7 policies: 0 reglas duplicadas |
| Vocabularios unicos Reviewer y Auditor | PASS | core.md Verdict vocabulary (46-54); handoffs.md (23, 42); roles/plan-reviewer.md (19-23) y auditor.md (21-25); templates plan-review.md y audit-report.md; grep legacy en toda la superficie: solo clausulas normativas "must not be used" |
| Ausencia de reglas Git/testing duplicadas | PASS | policies/git.md y testing.md son rutas de referencia; ninguna otra policy repite reglas de git-safety.md/testing.md (grep confirmado) |
| Denies efectivos en los 4 agentes OpenCode | PASS | Los 4 frontmatters (lineas 6-14) con read map: *.env deny, *.env.* deny, *.env.example allow, memory/** deny, vector_db/** deny, atlas_security.log deny, **/atlas_security.log deny. Patron consistente con .opencode/agents/atlas-auditor.md preexistente (mismo esquema, sin atlas_security.log) |
| Builder como unico rol con edicion permitida | PASS | planner/plan-reviewer/auditor: edit deny; builder: edit allow (OpenCode); Claude: disallowedTools Write/Edit/NotebookEdit en 3 roles, builder incluye Edit; validado tambien por validate_workflow.py (exit 0) |
| Referencias Claude validas | PASS | CLAUDE.md: @AGENTS.md, .claude/agents/ (4 archivos existen), skill workflow-2-claude (existe); sin /workflow-2, sin .claude/rules (Test-Path .claude\rules = False); frontmatter de los 4 agentes y de la skill validos |
| role-selection.md y bug-report.md con consumidores reales | PASS | SKILL.md linea 20 referencia references/role-selection.md; policies/debugging.md linea 24 referencia ../templates/bug-report.md |
| Consistencia de install-state.json, versionado y hashes | PASS | version.json 2.0.0 = install-state version; hashes de files validados por validate_workflow.py (exit 0); routing_blocks verificados manualmente: SHA256(AGENTS.md)=772456b5... y SHA256(CLAUDE.md)=af26c877... coinciden con install-state |
| migrate_repo.py sin modificaciones fuera de alcance | PASS | Codigo: apply() escribe solo managed_source_files (.agents/workflow-2, .agents/skills/workflow-2, .claude/skills/workflow-2-claude, globs workflow-*.md en .opencode/agents, .opencode/commands, .claude/agents) + bloques AGENTS.md/CLAUDE.md + install-state.json; 2 ejecuciones KEEP-only; git status: ningun archivo rastreado fuera de AGENTS.md modificado; sin .workflow-2.tmp residuales |
| Inventario exacto de modificados y sin rastrear | PASS | 1 M + 43 ??; detalle completo en seccion 18 |
| Retiro de openai.yaml justificado | FAIL | No puede demostrarse prescindible; hallazgo B1 (seccion 11) |

## 10. Evidencia reproducida

| Comando / inspeccion | Resultado |
|---|---|
| python .agents\skills\workflow-2\scripts\validate_workflow.py . | exit 0: "Workflow 2.0 validation passed" |
| git diff --check | exit 0 |
| git status --short --untracked-files=all | 1 M + 43 ?? (capturado completo) |
| git diff -- AGENTS.md | bloque de routing + jerarquia agregados |
| git rev-parse HEAD / branch --show-current | aba2d43d6a0a22bd3df9e2ad7fb10e3f895f80a7 / atlas-v4.1-incremental-indexing |
| SHA256 manual AGENTS.md y CLAUDE.md vs routing_blocks | Coinciden exactamente |
| Lectura directa de 41 archivos de superficie | Todos inspeccionados (ver seccion 8) |
| Grep vocabulario legacy (HEALTHY, ACCEPT, REQUEST CHANGES, APPROVED WITH NOTES, NOT APPROVED) en .agents/workflow-2, .agents/skills/workflow-2, .claude, .opencode/agents/workflow-* | Solo clausulas normativas "must not be used" (core.md 53-54; auditor.md 24-25) |
| Grep openai.yaml / default_prompt / display_name / short_description en el repo | Solo menciones en el reporte de gobernanza previo (ningun consumidor interno) |
| Inspeccion de C:\Users\delfa\.codex (skills, plugins, .system) | Cientos de skills con agents/openai.yaml (convencion oficial OpenAI en uso) |
| Inspeccion de C:\Users\delfa\.agents\skills | grill-with-docs contiene agents/openai.yaml (convencion personal del usuario) |
| git ls-files .opencode/agents | atlas-auditor.md, atlas-plan-to-codex.md, atlas-plan-to-kimik3.md (uso activo de Codex con Atlas) |
| Web: developers.openai.com/codex/skills y github.com/openai/skills | agents/openai.yaml = metadata oficial recomendada (UI, invocacion, dependencias); skill-creator lo genera; campos interface.display_name/short_description/default_prompt identicos a los registrados del archivo eliminado |
| Test-Path .claude\rules | False (sin directorio; ninguna referencia en CLAUDE.md) |
| git check-ignore __pycache__ | .gitignore:21 cubre el .pyc generado (no entrara al commit) |
| Busqueda de .workflow-2.tmp | Ninguno |

## 11. Hallazgos BLOQUEANTES

### B1 — Retiro de agents/openai.yaml clasificado UNVERIFIED (debe restaurarse)

- ID: B1
- Severidad: BLOCKING
- Archivo: .agents/skills/workflow-2/agents/openai.yaml (eliminado)
- Problema: la remediacion retiro el archivo y, para que la validacion pasara,
  el Builder tambien elimino su entrada de la lista REQUIRED de
  validate_workflow.py. La decision se baso solo en ausencia de referencias
  internas (grep). Ese razonamiento es insuficiente: el archivo es metadata
  esperada por convencion externa, tooling y distribucion de skills.
- Evidencia:
  1. Convencion oficial OpenAI/Codex: developers.openai.com/codex/skills
     documenta agents/openai.yaml para metadata de UI, politica de invocacion
     y dependencias; el repositorio openai/skills lo declara "recommended"
     (seccion agents/) y el skill-creator lo genera con exactamente los campos
     del archivo eliminado (interface: display_name, short_description,
     default_prompt).
  2. Convencion personal del usuario: C:\Users\delfa\.agents\skills\
     grill-with-docs\agents\openai.yaml existe; el paquete workflow-2 vive en
     .agents/skills/workflow-2/, la misma familia de ruta.
  3. Tooling activo: C:\Users\delfa\.codex\ contiene cientos de skills con
     agents/openai.yaml (plugins oficiales y curated, .system/skill-creator,
     .tmp/plugins/.agents/skills/plugin-creator).
  4. El repositorio rastrea .opencode/agents/atlas-plan-to-codex.md: el usuario
     usa Codex con Atlas; la skill workflow-2 es candidata a consumo Codex
     (donde el openai.yaml define metadata de UI y politica de invocacion).
  5. validate_workflow.py fue modificado por el propio Builder para dejar de
     exigir el archivo: su exit 0 no constituye evidencia independiente de
     prescindibilidad.
  6. El contenido original no es recuperable de Git (nunca fue commiteado).
- Impacto: perdida de la metadata de distribucion OpenAI/Codex de la skill;
  el paquete deja de cumplir la convencion de distribucion externa de skills
  utilizada por el usuario; una instalacion futura en Codex (CLI o ChatGPT
  desktop) pierde display_name, short_description y default_prompt, y la skill
  podria invocarse implicitamente sin control de politica.
- Criterio violado: "No aceptes su eliminacion solo porque grep no encuentre
  referencias internas" (pedido de auditoria); contrato de remediacion
  C6 ("referenciar si son necesarios o retirar del paquete" exige demostrar
  que no son necesarios).
- Correccion minima:
  1. Regenerar .agents/skills/workflow-2/agents/openai.yaml con metadata
     valida de interfaz para la skill workflow-2 (display_name,
     short_description de 25-64 caracteres, default_prompt que mencione la
     skill), siguiendo references/openai_yaml.md de openai/skills o el
     generador oficial generate_openai_yaml.py.
  2. Restaurar la entrada .agents/skills/workflow-2/agents/openai.yaml en la
     lista REQUIRED de validate_workflow.py (para que el archivo vuelva a estar
     protegido por la validacion).
  3. Re-ejecutar el mecanismo oficial: python .agents\skills\workflow-2\scripts\
     migrate_repo.py C:\Users\delfa\Documents\Atlas --apply --allow-dirty
     (KEEP/CREATE del archivo; re-registro del hash en install-state.json).
  4. Re-ejecutar validate_workflow.py y git diff --check.
- Prueba de aceptacion: validate_workflow.py exit 0 con la entrada REQUIRED
  restaurada; install-state.json registra el hash de agents/openai.yaml;
  git status muestra el archivo presente en la superficie.
- Estado: CONFIRMED (eliminacion ejecutada) / prescindibilidad NO VERIFIED.

## 12. Hallazgos NO BLOQUEANTES

### N1 — validate_workflow.py no valida routing_blocks

- ID: N1 — Severidad: LOW (INFORMACIONAL)
- Archivo: .agents/skills/workflow-2/scripts/validate_workflow.py (lineas
  84-98)
- Problema: la validacion compara hashes de la clave "files" pero ignora la
  clave "routing_blocks" (AGENTS.md y CLAUDE.md) registrada en install-state.
- Evidencia: lectura del script; los routing_blocks fueron verificados
  manualmente en esta auditoria (coinciden).
- Impacto: nulo en el estado actual; una divergencia futura de AGENTS.md o
  CLAUDE.md fuera del bloque gestionado no seria detectada por el validador.
- Correccion minima: ampliar validate() para comparar routing_blocks contra
  SHA256 de AGENTS.md y CLAUDE.md.
- Estado: CONFIRMED (limitacion del tooling).

### N2 — Artefacto __pycache__ generado por la ejecucion de scripts

- ID: N2 — Severidad: LOW (INFORMACIONAL)
- Archivo: .agents/skills/workflow-2/scripts/__pycache__/workflow_lib.cpython-314.pyc
- Problema: ejecutar los scripts oficiales genero bytecode en la superficie.
- Evidencia: git check-ignore -v: .gitignore:21 (__pycache__/) lo ignora.
- Impacto: no entrara al commit; sin accion requerida.
- Estado: CONFIRMED (cubierto por .gitignore).

### N3 — Reportes preexistentes fuera de la superficie de migracion

- ID: N3 — Severidad: LOW (INFORMACIONAL)
- Archivo: docs/reviews/cuts/2026-08-01-aba2d43-cut-workflow-2-governance-review.md
  y 2026-08-01-aba2d43-sdd0-incremental-indexing-contracts-review.md
- Problema: ambos estan sin rastrear y NO pertenecen a la superficie de
  migracion Workflow 2.0.
- Evidencia: git status --short; inventario de la superficie.
- Impacto: el futuro commit del corte de migracion debe excluirlos (o el
  usuario debe decidir versionarlos por separado).
- Estado: CONFIRMED.

## 13. Claims confirmados

- Jerarquia de autoridad inequivoca: CONFIRMED (AGENTS.md + core.md, lectura
  directa).
- Workflow 2.0 gobernante de microcortes: CONFIRMED.
- Fuentes normativas unicas Git/testing: CONFIRMED (core.md + archivos de
  referencia + grep sin duplicaciones).
- Vocabularios unicos de gates: CONFIRMED (grep de vocabulario legacy solo en
  clausulas normativas).
- Denies de privacidad en los 4 agentes OpenCode: CONFIRMED (lectura de los 4
  frontmatters).
- Builder unico con edicion: CONFIRMED (OpenCode y Claude).
- Referencias Claude validas: CONFIRMED (CLAUDE.md, 4 agentes, skill
  workflow-2-claude; sin referencias rotas).
- role-selection.md y bug-report.md con consumidores: CONFIRMED (SKILL.md L20,
  debugging.md L24).
- install-state/version/hashes consistentes: CONFIRMED (validador + verificacion
  manual de routing_blocks).
- migrate_repo.py sin escrituras fuera de alcance: CONFIRMED (codigo + git
  status + 2 ejecuciones KEEP-only).
- Inventario exacto: CONFIRMED (git status capturado).

## 14. Claims parciales

- Ninguno.

## 15. Claims no verificados

- Prescindibilidad de agents/openai.yaml: NOT VERIFIED (por el contrario, la
  evidencia de convencion y tooling indica que es esperado; hallazgo B1).

## 16. Falsos positivos descartados

- "referencia rota a .claude/rules en workflow_lib.py": descartado; es
  inventario opcional de superficie (surface_inventory, lineas 165-176), no una
  instruccion; el directorio no existe y el rglob nunca itera.
- "CLAUDE.md referencia rota": descartado; el contenido actual usa la skill
  real workflow-2-claude y los subagentes existentes.

## 17. Cambios obligatorios

- B1: restaurar .agents/skills/workflow-2/agents/openai.yaml (regenerado segun
  convencion oficial), restaurar su entrada REQUIRED en validate_workflow.py,
  re-registrar estado con migrate_repo.py --apply --allow-dirty y re-validar.
  Sin esta correccion, la superficie NO debe versionarse.

## 18. Inventario exacto del working tree

Modificado (1):
- AGENTS.md (bloque de routing Workflow 2.0 + jerarquia de autoridad).

Sin rastrear — superficie de migracion (41):
- .agents/skills/workflow-2/SKILL.md
- .agents/skills/workflow-2/references/migration-rules.md
- .agents/skills/workflow-2/references/role-selection.md
- .agents/skills/workflow-2/scripts/audit_repo.py
- .agents/skills/workflow-2/scripts/migrate_repo.py
- .agents/skills/workflow-2/scripts/validate_workflow.py
- .agents/skills/workflow-2/scripts/workflow_lib.py
- .agents/workflow-2/contracts/handoffs.md
- .agents/workflow-2/core.md
- .agents/workflow-2/install-state.json
- .agents/workflow-2/policies/debugging.md
- .agents/workflow-2/policies/definition-of-done.md
- .agents/workflow-2/policies/engineering.md
- .agents/workflow-2/policies/git.md
- .agents/workflow-2/policies/prototypes.md
- .agents/workflow-2/policies/security.md
- .agents/workflow-2/policies/testing.md
- .agents/workflow-2/roles/auditor.md
- .agents/workflow-2/roles/builder.md
- .agents/workflow-2/roles/plan-reviewer.md
- .agents/workflow-2/roles/planner.md
- .agents/workflow-2/templates/audit-report.md
- .agents/workflow-2/templates/bug-report.md
- .agents/workflow-2/templates/build-report.md
- .agents/workflow-2/templates/microcut-plan.md
- .agents/workflow-2/templates/plan-review.md
- .agents/workflow-2/version.json
- .claude/agents/workflow-auditor.md
- .claude/agents/workflow-builder.md
- .claude/agents/workflow-plan-reviewer.md
- .claude/agents/workflow-planner.md
- .claude/skills/workflow-2-claude/SKILL.md
- .opencode/agents/workflow-auditor.md
- .opencode/agents/workflow-builder.md
- .opencode/agents/workflow-plan-reviewer.md
- .opencode/agents/workflow-planner.md
- .opencode/commands/workflow-audit.md
- .opencode/commands/workflow-build.md
- .opencode/commands/workflow-plan.md
- .opencode/commands/workflow-review-plan.md
- CLAUDE.md

Sin rastrear — trabajo de usuario preexistente, fuera de la superficie (2):
- docs/reviews/cuts/2026-08-01-aba2d43-cut-workflow-2-governance-review.md
- docs/reviews/cuts/2026-08-01-aba2d43-sdd0-incremental-indexing-contracts-review.md

Nota: .agents/skills/workflow-2/agents/openai.yaml NO esta presente (eliminado;
hallazgo B1). .agents/skills/workflow-2/scripts/__pycache__/ existe pero esta
cubierto por .gitignore:21.

## 19. Limitaciones

- El contenido original de agents/openai.yaml no es recuperable (nunca fue
  commiteado); la restauracion requiere regeneracion segun la convencion
  oficial.
- No se ejecuto validacion de descubrimiento en Codex (no autorizado); la
  expectativa de consumo se basa en convencion oficial, instalacion local de
  Codex y uso historico de Codex en el repositorio.
- La verificacion de hashes "files" de install-state se delego en
  validate_workflow.py (exit 0); los routing_blocks se verificaron manualmente.

## 20. Estado final del working tree

Identico al estado inicial de la auditoria: 1 modificado (AGENTS.md) + 43 sin
rastrear. Esta auditoria no modifico ningun archivo; su unico archivo nuevo es
este reporte. Sin stage, sin commit, sin push.

## 21. Gate

FAIL

Motivo: hallazgo B1 BLOQUEANTE. La eliminacion de agents/openai.yaml es
UNVERIFIED como prescindible y debe revertirse (regenerar el archivo, restaurar
su entrada REQUIRED en el validador, re-registrar estado con el mecanismo
oficial y re-validar) antes de versionar la superficie como un unico corte de
migracion. Todo lo demas de la remediacion esta correctamente cerrado y
verificado.