# Implementation Playbook

Use this playbook for tasks that modify code, create files, fix defects, refactor behavior, or implement an approved plan.

Before starting, read and apply:

- `.agents/policies/git-safety.md`
- `.agents/policies/testing.md`

When `codebase-memory-mcp` is available and useful, also apply:

- `.agents/integrations/codebase-memory-mcp.md`

## 1. Understand the task

Before editing:

1. read the current instruction;
2. read every referenced plan or specification;
3. inspect the affected source files;
4. inspect relevant callers, imports, tests, and contracts;
5. identify the explicitly allowed scope.

Do not implement from summaries, symbol names, or assumptions alone.

## 2. Establish the baseline

Before modifying code:

- inspect the repository state;
- preserve existing user changes;
- run relevant baseline tests when practical;
- record existing failures;
- identify files that must not change.

A pre-existing failure must not be reported as a new regression without evidence.

## 3. Control scope

Modify only:

- explicitly authorized files;
- files strictly required to complete the task;
- directly related tests;
- requested documentation.

Do not use the task to:

- clean nearby code;
- redesign unrelated modules;
- rename unrelated symbols;
- change dependencies;
- reformat the repository;
- fix unrelated defects.

Report out-of-scope findings instead of silently fixing them.

## 4. Make the smallest correct change

Prefer:

- localized edits;
- existing project patterns;
- preserved public behavior;
- clear dependency direction;
- reversible changes;
- direct tests.

A minimal change must still be complete, correct, and testable.

Do not add abstractions unless the approved task requires them.

## 5. Preserve contracts

Before changing a public or shared component, identify:

- signature;
- return type;
- exceptions;
- visible messages;
- side effects;
- operation order;
- callers;
- stored formats;
- compatibility requirements.

Do not change a contract unless explicitly required.

When a contract must change, update all authorized callers and tests consistently.

## 6. Separate logic from effects

When supported by the existing architecture:

- keep pure logic separate from UI;
- keep decisions separate from execution;
- keep domain logic separate from disk and network access;
- prevent internal modules from depending on higher-level layers.

Do not create new architectural layers without a demonstrated need.

## 7. Avoid speculative architecture

Do not introduce unrequested:

- factories;
- registries;
- plugin systems;
- abstract hierarchies;
- generic interfaces;
- event systems;
- dependency containers;
- configuration frameworks.

Use them only when explicitly required or necessary to preserve an existing boundary.

## 8. Implement incrementally

Recommended sequence:

1. implement the isolated change;
2. add or update focused tests;
3. integrate it with existing code;
4. run focused validation;
5. run the full suite;
6. review the final diff;
7. report the result.

Recheck scope after every significant step.

## 9. Handle errors honestly

Do not hide defects through:

- broad exception handling;
- silent fallback values;
- empty returns;
- disabled validation;
- weakened assertions;
- removed tests.

Preserve current error behavior unless the task explicitly changes it.

Test new error behavior when observable.

## 10. Dependencies

Do not add, remove, or update dependencies without explicit authorization.

Before proposing a new dependency, verify that:

- the standard library is insufficient;
- the repository has no existing solution;
- the dependency solves a real requirement;
- its maintenance cost is justified.

## 11. Use Codebase Memory optionally

When `codebase-memory-mcp` is available and its use adds value, follow:

- `.agents/integrations/codebase-memory-mcp.md`

Typical useful cases include:

- locating symbols and references;
- inspecting callers and dependencies;
- exploring unfamiliar architecture;
- estimating change impact;
- locating related tests.

Do not use it ceremonially for trivial, fully localized changes.

Its output does not replace:

- reading current source code;
- searching the repository directly;
- reviewing the diff;
- running tests.

If unavailable, continue with normal repository tools unless the task explicitly requires it.

## 12. Validate the implementation

Apply `.agents/policies/testing.md`.

As applicable:

- run syntax or compilation checks;
- run focused tests;
- run the complete suite;
- perform relevant smoke tests;
- perform requested manual verification.

Report only checks that were actually executed.

Never claim that unexecuted tests pass.

## 13. Review the diff

Before finishing, inspect:

- every changed file;
- new files;
- out-of-scope changes;
- unused imports;
- dead code;
- changed messages;
- changed contracts;
- unexpected formatting;
- line-ending changes;
- conflict markers;
- temporary data;
- secrets or credentials.

Run the final Git checks required by `git-safety.md`.

If the diff is substantially larger than expected, investigate before reporting completion.

## 14. Documentation

Update documentation only when:

- explicitly requested;
- public behavior changed;
- a meaningful architectural boundary was introduced;
- project rules require it.

Document only implemented and verified behavior.

Do not describe planned work as completed.

## 15. Final report

Keep the report concise and evidence-based.

Include:

1. objective completed;
2. files changed;
3. important implementation decisions;
4. preserved behavior or contracts;
5. validation commands and real results;
6. limitations or failed checks;
7. out-of-scope findings;
8. final repository state;
9. verdict.

Use one verdict:

### APPROVED

The implementation satisfies the requested scope and all required checks pass.

### APPROVED WITH NOTES

The implementation satisfies the scope, with clearly documented non-blocking limitations.

### REJECTED

The implementation has a regression, scope violation, failed required check, or insufficient evidence.

## Final rule

Implement only what was requested.

Preserve user work, avoid speculative redesign, verify with real evidence, and report limitations honestly.