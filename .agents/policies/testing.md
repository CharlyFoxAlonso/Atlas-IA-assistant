# Testing and Evidence Policy

Apply this policy to every task that changes or verifies behavior.

## 1. Evidence first

Never claim a change works only because:

- the code looks correct;
- it compiles;
- the implementation appears reasonable;
- tests are expected to pass.

Claims must be supported by executed checks.

## 2. Evidence categories

Keep these categories separate.

### Static inspection

Examples:

- reading source code;
- reviewing imports;
- searching references;
- inspecting the diff.

Static inspection does not prove runtime behavior.

### Compilation or syntax checks

Examples:

```powershell
python -m compileall .
```

This proves only that the checked code is syntactically valid and can be processed by that command.

It does not prove correct behavior.

### Automated tests

Use the framework already configured by the repository.

Examples:

```powershell
python -m unittest discover -v
pytest -v
```

Tests must be executed, not inferred.

Report:

- command;
- passed;
- failed;
- errors;
- skipped;
- exit code.

Do not invent unavailable metrics.

### Smoke tests

A smoke test verifies a minimal execution path, such as:

- importing the application;
- starting the program;
- running one basic workflow.

A smoke test does not replace focused tests or the full suite.

### Manual verification

Report manual verification only when it was actually performed.

State exactly:

- what action was performed;
- what result was observed;
- what was not checked.

## 3. Baseline

When practical, run the relevant tests before modifying code.

Record existing failures so they can be distinguished from regressions introduced by the task.

Do not attribute a pre-existing failure to the new change without evidence.

## 4. Test order

When applicable, use this order:

1. syntax or compilation check;
2. focused tests;
3. full test suite;
4. smoke test;
5. requested manual verification.

Skip irrelevant stages, but report what was skipped when it matters.

## 5. New behavior

When a task adds or changes observable behavior:

- add or update focused tests when allowed;
- test outputs, errors, state changes, and public contracts;
- avoid tests that only reproduce implementation details.

Do not weaken existing assertions merely to make tests pass.

## 6. Failures

Do not hide failures by:

- disabling tests;
- deleting tests;
- broad exception handling;
- changing expected results without justification;
- reporting only successful commands;
- rerunning until one result succeeds without explaining previous failures.

When a required check fails, report it clearly.

## 7. Exit codes

Record the exit code for important validation commands, especially:

- compilation;
- focused tests;
- full test suites;
- linters;
- type checkers;
- build commands.

An exit code of `0` means the command completed successfully, not that every possible behavior was verified.

## 8. Coverage

Coverage is supplementary evidence.

It does not replace:

- meaningful assertions;
- focused behavior tests;
- regression testing.

Report coverage only when it was actually measured.

## 9. Unavailable checks

When a check cannot be executed:

- explain why;
- report the evidence that is available;
- state the remaining limitation;
- do not present the task as fully verified.

Examples include missing dependencies, unavailable services, unsupported environments, or required credentials.

## 10. Final report

Report validation briefly under separate headings:

- static inspection;
- syntax or compilation;
- focused tests;
- full suite;
- smoke test;
- manual verification;
- limitations.

For every executed command, include its real result and exit code.

Never describe a check as passed when it was not executed.

## Final rule

Executed evidence has priority over confidence.

When verification is incomplete, state the limitation instead of claiming success.