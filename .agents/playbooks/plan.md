# Planning Playbook

Use this playbook when the task is to investigate, analyze, design, or produce an implementation plan without modifying production code.

Before starting, read and apply:

- `.agents/policies/git-safety.md`

When `codebase-memory-mcp` is available and useful, also apply:

- `.agents/integrations/codebase-memory-mcp.md`

## 1. Planning is read-only

Do not modify source code, tests, configuration, dependencies, or documentation unless the task explicitly requests a planning document.

Do not implement partial fixes while investigating.

Do not create commits or perform destructive Git operations.

## 2. Understand the request

Identify:

- the objective;
- expected behavior;
- constraints;
- allowed scope;
- forbidden scope;
- acceptance criteria;
- referenced specifications or decisions.

Resolve questions through repository inspection whenever possible.

Do not invent requirements that are not supported by the task or project documentation.

## 3. Inspect the repository

Before proposing changes:

- inspect the repository state;
- read referenced plans and specifications;
- locate relevant entry points;
- inspect current implementations;
- inspect callers, imports, tests, and contracts;
- identify existing project patterns.

Do not plan from filenames, summaries, or assumptions alone.

## 4. Use Codebase Memory optionally

When useful, apply:

- `.agents/integrations/codebase-memory-mcp.md`

Use it to locate symbols, dependencies, tests, and architectural relationships.

Verify important findings against the current source code.

If unavailable, continue with direct repository inspection.

## 5. Separate facts from assumptions

Clearly distinguish:

### Confirmed facts

Verified directly in current source code, tests, configuration, or authoritative project documentation.

### Inferences

Reasonable conclusions derived from confirmed evidence.

### Open questions

Information that could not be confirmed and may affect implementation.

Do not present inferred or indexed relationships as confirmed facts.

## 6. Analyze contracts and impact

Identify relevant:

- public interfaces;
- signatures;
- return values;
- exceptions;
- visible messages;
- side effects;
- persistence formats;
- callers;
- dependencies;
- tests;
- compatibility constraints.

Estimate which files must change and which files should remain untouched.

Do not claim that impact analysis is complete without inspecting actual references.

## 7. Prefer the smallest viable design

The plan should propose the smallest complete change that satisfies the objective.

Prefer:

- existing patterns;
- localized changes;
- preserved contracts;
- clear boundaries;
- direct tests;
- reversible steps.

Avoid speculative abstractions, unrelated cleanup, or broad redesign.

## 8. Define exact scope

List:

- files expected to change;
- files that may change only if necessary;
- files explicitly excluded;
- dependencies or configuration that must remain unchanged.

Explain why each expected file is involved.

Do not include files merely because they are nearby.

## 9. Define implementation steps

Provide ordered, executable steps.

Each step should state:

- what changes;
- where it changes;
- why it is required;
- which contract must be preserved;
- how it will be verified.

Avoid vague instructions such as:

- improve the architecture;
- update the logic;
- handle edge cases;
- add tests as needed.

## 10. Define validation

Specify:

- focused tests;
- full-suite command;
- syntax, build, or type checks;
- smoke tests;
- manual verification when necessary;
- expected observable results.

Use commands already supported by the repository whenever possible.

Do not claim validation has passed during planning unless it was actually executed.

## 11. Identify risks

Document only meaningful risks, such as:

- hidden callers;
- shared mutable state;
- persistence compatibility;
- UI coupling;
- import cycles;
- platform differences;
- concurrency;
- incomplete test coverage;
- stale indexed data.

For each risk, include a concrete mitigation or verification step.

## 12. Avoid duplication

Reference existing policies, specifications, and project documentation instead of copying them into the plan.

The plan should contain only task-specific information.

Do not repeat general Git, testing, or reporting rules already defined elsewhere.

## 13. Plan output

The final plan should include:

1. objective;
2. current-state findings;
3. proposed approach;
4. files in scope;
5. files excluded;
6. ordered implementation steps;
7. validation commands;
8. risks and mitigations;
9. unresolved questions;
10. viability verdict.

Use one verdict:

### VIABLE

The task can be implemented with the available evidence and defined scope.

### VIABLE WITH CONDITIONS

The task is implementable, but specific conditions or unresolved details must be addressed during implementation.

### NOT VIABLE

The task cannot be implemented safely with the current information, scope, or repository state.

## Final rule

Investigate before designing.

Produce a specific, minimal, evidence-based plan without implementing it.