# Final Report Template

Use this template for the final response after planning, implementation, verification, or audit tasks.

Keep the report concise, factual, and based on inspected or executed evidence.

Omit sections that do not apply.

## Result

**Mode:** planning | implementation | verification | audit  
**Verdict:** `<verdict defined by the active playbook>`

One brief sentence describing the outcome.

## Scope

**Requested objective:**  
`<objective>`

**Files reviewed:**  
- `<file>`

**Files changed:**  
- `<file>`

**Files intentionally excluded:**  
- `<file or area>`

Do not list files that were not inspected or changed.

## Work completed

- `<specific action completed>`
- `<specific action completed>`

Describe only work that was actually performed.

Do not describe planned or proposed work as completed.

## Key decisions

- `<decision and brief reason>`

Include only decisions that materially affected the result.

## Contracts preserved or changed

**Preserved:**

- `<signature, message, behavior, format, or compatibility contract>`

**Changed:**

- `<explicitly authorized contract change>`

Write `None` when no relevant contract changed.

## Validation

For each executed command:

```text
<command>
Result: <passed, failed, or partial>
Exit code: <code>
Evidence: <brief factual result>
```

Separate when applicable:

- static inspection;
- syntax or compilation;
- focused tests;
- full suite;
- smoke test;
- manual verification.

Never report an unexecuted check as passed.

## Acceptance criteria

Use this section only when explicit criteria exist.

| Criterion | Result | Evidence |
|---|---|---|
| `<criterion>` | PASS / FAIL / NOT VERIFIED | `<evidence>` |

Evaluate each criterion independently.

## Findings

### Blocking

- `<finding and evidence>`

Write `None` when no blocking finding exists.

### Non-blocking

- `<finding and evidence>`

Write `None` when no non-blocking finding exists.

### Out of scope

- `<relevant issue discovered but not modified>`

Do not silently fix unrelated findings.

## Repository state

**Initial branch:** `<branch>`  
**Initial commit:** `<commit>`  
**Pre-existing changes:** `<summary or none>`  
**Final modified files:** `<summary>`  
**Commit created:** yes / no  
**Push performed:** yes / no

Do not claim the working tree was clean unless verified.

## Tooling

Include only materially used integrations.

**Codebase Memory MCP:** used / not used / unavailable  
**Index refreshed:** yes / no / not required / failed

Briefly state what the integration helped locate when it was used.

## Limitations

- `<missing evidence, unavailable environment, unexecuted check, or unresolved question>`

Write `None` only when all required evidence was obtained.

## Next action

Include only when a concrete next step remains.

`<single recommended next action>`