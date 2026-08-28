# Verification Playbook

Use this playbook to review, test, or validate an existing implementation without modifying it.

Before starting, read and apply:

- `.agents/policies/git-safety.md`
- `.agents/policies/testing.md`

When `codebase-memory-mcp` is available and useful, also apply:

- `.agents/integrations/codebase-memory-mcp.md`

## 1. Verification is read-only

Do not modify source code, tests, configuration, dependencies, or documentation unless the task explicitly requests fixes.

Do not convert verification into implementation.

When a defect is found:

- record it;
- provide supporting evidence;
- explain its impact;
- do not fix it silently.

## 2. Identify the contract

Before validating, read:

- the current request;
- the approved plan or specification;
- acceptance criteria;
- referenced architectural decisions;
- relevant project policies.

Extract the exact behavior and scope that must be verified.

Do not introduce additional requirements during review.

## 3. Inspect repository state

Before running checks:

- inspect the current branch and commit;
- record modified and untracked files;
- identify pre-existing user changes;
- determine which files belong to the implementation under review.

Do not assume every current diff was produced by the reviewed task.

## 4. Inspect the implementation

Review:

- every in-scope changed file;
- relevant source context;
- callers and dependencies;
- tests added or changed;
- visible messages and errors;
- public contracts;
- persistence or compatibility effects;
- unexpected out-of-scope changes.

Compare the actual implementation with the requested behavior, not only with the implementation report.

## 5. Use Codebase Memory optionally

When useful, apply:

- `.agents/integrations/codebase-memory-mcp.md`

Use it to locate:

- affected symbols;
- callers and references;
- related tests;
- structural dependencies;
- potentially missed impact areas.

Verify important findings against current source code.

If unavailable, continue with direct repository inspection.

## 6. Validate scope

Confirm that:

- required files were changed;
- excluded files were not intentionally modified;
- unrelated cleanup was not introduced;
- dependencies were not changed without authorization;
- contracts outside the task remain preserved.

Distinguish task changes from pre-existing user changes.

A scope violation is a verification failure even when tests pass.

## 7. Validate behavior

Apply `.agents/policies/testing.md`.

When applicable, run:

1. syntax, compilation, or build checks;
2. focused tests;
3. the complete test suite;
4. smoke tests;
5. requested manual verification.

Record the exact command, result, and exit code.

Do not treat static inspection as runtime proof.

## 8. Verify acceptance criteria

Evaluate every acceptance criterion separately.

Classify each one as:

### PASS

Supported by direct inspection or executed evidence.

### FAIL

Contradicted by the implementation or validation results.

### NOT VERIFIED

Insufficient evidence or an unavailable required check.

Do not mark a criterion as passed because another related criterion passed.

## 9. Check regressions

Inspect whether the change may have affected:

- existing callers;
- imports;
- error behavior;
- UI behavior;
- persisted data;
- platform compatibility;
- initialization order;
- shared state;
- previous tests.

Use the full suite and source inspection together.

Passing focused tests alone does not prove absence of regressions.

## 10. Review test quality

Confirm that tests:

- exercise observable behavior;
- cover the changed contract;
- include relevant success and failure cases;
- contain meaningful assertions;
- are not disabled or weakened;
- do not merely reproduce the implementation.

Do not require unnecessary tests outside the requested scope.

## 11. Classify findings

Use these severities:

### BLOCKING

The implementation cannot be accepted because of:

- incorrect behavior;
- failed required tests;
- scope violation;
- data-loss risk;
- broken contract;
- security issue;
- missing required functionality;
- insufficient mandatory evidence.

### NON-BLOCKING

The implementation is acceptable, but a limited issue or improvement should be recorded.

### INFORMATIONAL

A relevant observation that does not affect acceptance.

Every finding must include:

- affected file or component;
- evidence;
- impact;
- violated requirement, when applicable.

Avoid speculative findings without supporting evidence.

## 12. Do not overstate results

Do not claim:

- full correctness from passing tests alone;
- absence of callers from one search result;
- no regressions without relevant validation;
- successful manual verification when none occurred;
- updated MCP index unless refresh succeeded;
- a clean working tree when changes exist.

State verification limits explicitly.

## 13. Final report

Keep the report concise and evidence-based.

Include:

1. verification target;
2. repository state;
3. files reviewed;
4. acceptance-criteria results;
5. validation commands and exit codes;
6. blocking findings;
7. non-blocking findings;
8. unverified areas;
9. final verdict.

Use one verdict:

### APPROVED

All required acceptance criteria pass, required checks succeed, and no blocking finding exists.

### APPROVED WITH NOTES

All required behavior passes, with only non-blocking findings or clearly limited observations.

### REJECTED

At least one required criterion fails, a required check fails, scope was violated, or a blocking finding exists.

### INCONCLUSIVE

Required evidence could not be obtained, so approval or rejection cannot be justified.

## Final rule

Verify the implementation against the real request and real repository state.

Do not fix silently, do not invent evidence, and do not approve work that was not adequately demonstrated.