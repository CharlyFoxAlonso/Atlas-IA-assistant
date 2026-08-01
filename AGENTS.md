# AGENTS.md

## Purpose

This file is the permanent repository-level instruction and routing entry point for Atlas.

Keep task prompts short. Do not repeat the policies and workflows referenced below unless a task introduces an explicit exception.

Before acting, inspect the current repository state and read the files relevant to the requested scope. Repository evidence takes priority over summaries, historical reports, agent output, and assumptions.

---

## 1. Required instruction routing

Apply the policy files relevant to every repository task:

- Git and working-tree safety:
  - `.agents/policies/git-safety.md`
- Testing, validation, and evidence:
  - `.agents/policies/testing.md`

Select exactly one primary playbook according to the requested mode:

- Investigation and planning without implementation:
  - `.agents/playbooks/plan.md`
- Code, test, configuration, or documentation changes:
  - `.agents/playbooks/implement.md`
- Read-only validation of an existing implementation:
  - `.agents/playbooks/verify.md`
- Independent evidence-based audit:
  - `.agents/playbooks/audit.md`

Optional integration:

- Repository navigation and structural impact analysis:
  - `.agents/integrations/codebase-memory-mcp.md`

Final response format:

- `.agents/templates/final-report.md`

More specific `AGENTS.md` files, when present in subdirectories, extend or override this file only within their directory scope.

---

## 2. Atlas product identity

Atlas is a personal, single-user, local-first and hybrid Python application.

Its current purpose is to:

- ingest user-selected documents and study material;
- maintain a local knowledge base and retrieval workflow;
- use local models through Ollama when available;
- support optional external model providers when explicitly selected;
- answer from stored user material;
- support study and examination workflows;
- preserve user data locally;
- remain portable and reproducible on Windows systems.

Atlas is not a multi-tenant SaaS, distributed platform, enterprise service mesh, or microservice product.

Do not introduce enterprise-scale architecture merely because it would be conventional in a larger product. Proposals must be proportionate to a personal, single-user application and supported by a demonstrated requirement.

Do not transform Atlas into another project.

---

## 3. Product and repository names

Keep these identities separate.

### Atlas

The application governed by this repository.

Current Atlas behavior is determined by its current source code, configuration, tests, and verified specifications.

### Atlas Auditor

An agent role and review workflow used to inspect Atlas independently.

Atlas Auditor is not a product subsystem and must not be treated as runtime application code.

Agent definitions, audit reports, plans, and implementation reports contain claims. They are not authoritative descriptions of runtime behavior unless confirmed against the current repository.

### Frontier

Frontier is a separate architectural or experimental body of work.

Do not import Frontier requirements, terminology, data models, contracts, or architectural decisions into Atlas unless the current task explicitly authorizes an integration and the repository contains corresponding current implementation evidence.

References to Frontier inside inherited documents do not make Frontier part of Atlas.

### Xilas

Xilas is a separate product.

Do not apply Xilas-specific requirements, specifications, architecture, terminology, persistence rules, or product goals to Atlas.

### Historical Atlas names and inherited documentation

Documents may refer to earlier Atlas stages, Atlas Auditor variants, Prometeo, Frontier, or other historical names.

Treat those references as historical context until their claims are verified against the current repository.

Do not rename current components or revive historical architecture solely to make old documentation consistent.

---

## 4. Sources of authority

Use this order when determining current behavior:

1. current source code and public runtime contracts;
2. current tests and executed validation;
3. current configuration and dependency declarations;
4. explicitly approved and still-applicable specifications or architectural decisions;
5. current user instructions for the task;
6. maintained product and architecture documentation;
7. implementation reports, audit reports, plans, and agent output;
8. historical or inherited documentation;
9. inference.

A higher-ranked source does not automatically prove correctness, but it takes precedence when two descriptions conflict.

Tests prove only the behavior exercised by their assertions.

Documentation does not override current behavior unless the task explicitly asks to implement or audit conformance to a governing specification.

When documentation and implementation disagree:

- report the discrepancy;
- determine whether the code or documentation is expected to change;
- do not silently reconcile them;
- do not describe planned behavior as implemented behavior.

---

## 5. Documentation classification

Before relying on a document, classify it.

### Governing

A document is governing only when the repository or current task explicitly identifies it as an active specification, contract, architectural decision, or policy.

Examples may include:

- this `AGENTS.md`;
- files under `.agents/`;
- active specifications;
- accepted architectural decision records;
- explicitly approved plans for the current cut.

### Descriptive

A document describes the system but must be checked against current implementation.

Examples may include:

- README files;
- architecture overviews;
- installation instructions;
- development guides;
- module documentation.

### Evidentiary

A document records work or observations from a particular revision.

Examples include:

- `docs/reviews/general/`;
- `docs/reviews/cuts/`;
- implementation reports;
- verification reports;
- audit reports.

Evidentiary documents are revision-bound. They do not automatically describe the current HEAD.

### Historical or inherited

A document is historical or inherited when it:

- describes an older Atlas architecture;
- refers primarily to Frontier, Xilas, Prometeo, or another project;
- references removed or renamed modules;
- describes planned work as though it were current;
- has not been reconciled with current source and tests.

Historical material may explain intent but must not govern implementation without verification.

---

## 6. Architectural boundaries

Preserve the existing dependency direction unless an approved task explicitly changes it.

### Entry points and UI

Top-level UI or application entry points may coordinate workflows.

They should not become the source of truth for:

- domain rules;
- path policy;
- persistence formats;
- indexing behavior;
- security validation;
- provider-independent logic.

Do not move reusable core behavior into UI modules.

### `core/`

`core/` contains the application’s reusable behavior and integration logic.

Preserve established public symbols and callers unless a contract change is explicitly required.

Do not add a new abstraction layer merely to relocate a small amount of code.

### `core/system/`

`core/system/` contains low-level system policy and infrastructure foundations.

Higher-level modules may depend on these foundations. System modules must not depend on UI entry points or higher-level application workflows.

Path policy belongs in the centralized path system. Do not introduce new independent path literals when an existing centralized path contract applies.

### Configuration

`core.config` exposes application configuration and compatibility constants used by current callers.

Do not create competing sources of truth for values already centralized there or in `core.system`.

When preserving a historical public symbol, prefer an explicit compatibility alias over an independent duplicate definition.

Be aware that module imports may have observable effects. Inspect import-time behavior before introducing a new dependency.

### Security

Security validation must remain centralized and reusable.

Do not weaken:

- path containment checks;
- input validation;
- command restrictions;
- URL and network boundaries;
- secret handling;
- private-data exclusions;
- failure behavior;

solely to make a test or workflow pass.

Security claims require evidence bounded to the inspected surface. Do not claim that Atlas is completely secure.

### Ingestion and indexing

Document ingestion, URL ingestion, crawling, indexing, synchronization, and full reconstruction are distinct operations.

Preserve their current public contracts and operation order.

Do not replace incremental behavior with a full rebuild, or a full rebuild with incremental behavior, unless the task explicitly requires it and affected callers are verified.

Source artifacts must not be silently deleted because indexing failed unless an active specification explicitly requires deletion.

### Persistence and user data

Treat user data as private and irreplaceable.

Do not inspect, modify, index, summarize, delete, or expose real content from:

- `.env`;
- `memory/`;
- `vector_db/`;
- personal documents;
- personal chats;
- profiles;
- credentials;
- tokens;
- logs that may contain private data;

unless the user explicitly authorizes the exact operation and it is required for the task.

Prefer temporary directories, synthetic fixtures, fake providers, and isolated stores in tests.

Never run tests against the user’s real knowledge base.

### Local and external models

Local model support and optional cloud providers must remain separable.

Do not make external network access, paid APIs, credentials, or Ollama availability mandatory for workflows that currently degrade or operate without them.

Tests must not invoke real paid providers, real Ollama models, or uncontrolled network access unless explicitly authorized.

---

## 7. Permanent contracts

Unless a task explicitly changes them, preserve:

- Windows compatibility;
- single-user operation;
- local-first data ownership;
- optional cloud-provider use;
- public import paths used by existing callers;
- public return types and observable messages;
- persistence and index compatibility;
- safe failure behavior;
- user-owned source artifacts;
- explicit separation between saved, indexed, skipped, failed, and pending states;
- compatibility aliases that current callers still import.

Do not infer that an internal refactor authorizes a public contract change.

When a contract must change:

- identify all verified callers;
- update only authorized callers;
- add focused regression tests;
- document the migration or incompatibility when externally observable.

---

## 8. Change design rules

Prefer the smallest complete and reversible cut.

A normal Atlas change should:

- address one demonstrated objective;
- modify the minimum necessary production surface;
- preserve unrelated behavior;
- reuse existing patterns;
- include focused tests for changed observable behavior;
- avoid dependency changes unless explicitly authorized;
- avoid broad formatting or cleanup;
- leave unrelated findings for separate cuts.

Do not introduce speculative:

- microservices;
- plugin frameworks;
- dependency containers;
- generic registries;
- event infrastructure;
- abstract hierarchies;
- distributed storage;
- multi-user authentication;
- large rewrites.

A larger design is acceptable only when a confirmed requirement cannot be met safely through a smaller change.

---

## 9. Testing and validation

Apply `.agents/policies/testing.md`.

Atlas currently uses Python `unittest` for its repository test modules.

Use the project virtual environment when available:

```powershell
.venv\Scripts\python.exe
```

Confirmed validation forms include:

```powershell
.venv\Scripts\python.exe -m unittest <test modules> -v
```

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

```powershell
.venv\Scripts\python.exe -m compileall core tests
```

Select focused test modules from the actual affected code and tests. Do not copy an old test list into a new task without checking that those modules still exist and remain relevant.

Before executing tests:

- inspect their fixtures and side effects;
- confirm that they use synthetic or temporary data;
- isolate environment variables, current working directory, module cache, filesystem paths, network, and providers when relevant;
- verify that imports do not write into real user locations.

Report the exact command, exit code, pass count, failures, errors, skipped tests, and `_FailedTest` results when available.

Compilation is not proof of behavior.

A focused suite is not proof of repository-wide correctness.

Never weaken assertions, delete tests, or hide failures to obtain a green result.

---

## 10. Git and scope

Apply `.agents/policies/git-safety.md`.

All existing modified and untracked files are user-owned work.

Do not delete, restore, overwrite, stage, commit, or include them unless the current task explicitly authorizes them.

Do not create commits or push by default.

A request to implement code is not automatically authorization to commit or push.

Keep production changes, tests, agent definitions, and evidentiary reports separated when separate commits improve traceability.

Never describe the working tree as clean without verifying it.

---

## 11. Codebase Memory MCP

`codebase-memory-mcp` is optional.

When available and useful, apply:

- `.agents/integrations/codebase-memory-mcp.md`

Use it to reduce navigation cost and identify candidate relationships, callers, imports, and tests.

Do not use it ceremonially for trivial localized changes.

Its output is not authoritative evidence.

Confirm material graph findings against:

- current source code;
- repository search;
- imports and callers;
- the actual diff;
- executed tests.

If it is unavailable, times out, is stale, or is not exposed in the current environment:

- record the limitation accurately;
- continue through direct repository inspection;
- do not invent a technical cause;
- do not block a task that can be completed without it.

Do not claim that the graph or index was refreshed unless the refresh actually succeeded.

---

## 12. Agent and report files

Files under `.opencode/`, `.agents/`, and `docs/reviews/` govern or record development workflows; they are not runtime product modules.

Changes to agent behavior must be reviewed as agent-policy changes, not mixed silently into product cuts.

Audit and review reports must:

- identify the audited revision;
- distinguish reproduced evidence from claims;
- remain immutable unless an explicit correction is requested;
- remain outside product commits unless documentation versioning is explicitly authorized.

An accepted historical report does not automatically approve later commits.

---

## 13. Task-mode defaults

### Planning

Read:

- `.agents/playbooks/plan.md`

Planning is read-only unless a planning document is explicitly requested.

Inspect the real repository before proposing files, architecture, tests, or commands.

### Implementation

Read:

- `.agents/playbooks/implement.md`

Implement only the approved scope.

Preserve contracts and user work. Validate with executed evidence.

### Verification

Read:

- `.agents/playbooks/verify.md`

Verification is read-only unless fixes are explicitly requested.

Judge the implementation against the actual request and acceptance criteria, not against its implementation report alone.

### Audit

Read:

- `.agents/playbooks/audit.md`

Audit independently.

Treat plans, reports, documentation, and implementer claims as evidence to verify, not as facts to inherit.

Do not silently remediate findings.

---

## 14. Prompt economy

Future task prompts should normally contain only:

- mode or selected playbook;
- objective;
- task-specific scope;
- task-specific exclusions;
- referenced active specification or plan;
- acceptance criteria;
- explicitly authorized Git actions.

Do not repeat generic Git, testing, MCP, evidence, reporting, or scope-control rules already routed by this file.

Example:

```text
Mode: implementation
Objective: <task-specific objective>
In scope: <files or subsystem>
Out of scope: <explicit exclusions>
Specification: <path, when applicable>
Acceptance criteria: <task-specific criteria>
Git authorization: no commit and no push
```

The agent must expand this compact request by reading `AGENTS.md` and the routed files, not by asking the user to paste permanent policies again.

---

## 15. Final rule

Inspect the current Atlas repository before acting.

Keep Atlas separate from Atlas Auditor, Frontier, Xilas, and historical documentation.

Preserve user data, current contracts, working-tree changes, and local-first behavior.

Prefer small verified cuts over speculative redesign.

Current source, the actual diff, and executed tests take priority over indexed data, reports, summaries, and confidence.

<!-- workflow-2:begin -->
## Workflow 2.0 routing

For every repository task, read `.agents/workflow-2/core.md` and
`.agents/workflow-2/contracts/handoffs.md`.

Select exactly one role file:

- planning: `.agents/workflow-2/roles/planner.md`
- plan review: `.agents/workflow-2/roles/plan-reviewer.md`
- implementation: `.agents/workflow-2/roles/builder.md`
- independent audit: `.agents/workflow-2/roles/auditor.md`

Load only the risk policies required by the task. Project-specific rules in
this file and more specific nested instruction files remain authoritative for
their scope. Do not broaden scope or overwrite existing user work.

Authority hierarchy:
- `AGENTS.md` remains the global authority for every task.
- Workflow 2.0 roles govern all microcuts: Plan → Plan Review → Build → Audit.
- Git rules: `.agents/policies/git-safety.md` is the single normative source.
- Testing rules: `.agents/policies/testing.md` is the single normative source.
- The playbooks under `.agents/playbooks/` are legacy/supporting: they apply
  only to tasks not governed by Workflow 2.0, and their verdict vocabularies
  must not be used in Workflow 2.0 cuts.
<!-- workflow-2:end -->
