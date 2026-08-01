---
name: workflow-2
description: Plan, review, implement, audit, debug, or migrate small software changes through evidence-based contracts. Use for microcuts, bug fixes, refactors, plan reviews, independent code audits, repository workflow setup, or migrations involving AGENTS.md, .agents, .opencode, CLAUDE.md, or .claude. Do not use to bypass approval, broaden scope, or perform mass repository rewrites.
---

# Workflow 2.0

Turn a request into one small contractual change with a separate plan gate,
single writer and independent audit.

## Select the mode

- Investigation or design: Planner.
- Review of a proposed plan: Plan Reviewer.
- Approved code or configuration change: Builder.
- Review of an existing diff: Auditor.
- Unexplained failure: use the debugging policy before Builder.
- Repository setup or upgrade: use the migration scripts and rules.

If the role is not obvious, read `references/role-selection.md` first.

Do not combine roles in one pass. Planner, reviewer and Auditor remain
read-only. Builder is the only writer.

## Load the canonical rules

From this skill directory, read:

- `../../workflow-2/core.md`;
- `../../workflow-2/contracts/handoffs.md`;
- exactly one file under `../../workflow-2/roles/`;
- only the risk policies selected by `core.md`.

Read project-specific `AGENTS.md` files and applicable domain skills before
deciding scope. Project rules may strengthen this workflow.

## Execute the contract

1. Record repository state and pre-existing user work.
2. Inspect current source, callers, tests, configuration and active specs.
3. Separate facts, inferences, assumptions and decisions.
4. Produce or verify a microcut contract.
5. Obtain the required approval before Builder.
6. Implement only the approved surface.
7. Execute relevant checks and review the complete diff.
8. Hand off to an independent Auditor.
9. Return remediation to Builder when the verdict is `FAIL`.

Stop and renegotiate when evidence contradicts the contract, scope must expand,
user work cannot be preserved, or a product/architecture/security decision is
missing.

## Migrate repositories

Read `references/migration-rules.md`, then run:

```powershell
python scripts/audit_repo.py C:\path\repo --markdown
python scripts/migrate_repo.py C:\path\repo
python scripts/migrate_repo.py C:\path\repo --apply
python scripts/validate_workflow.py C:\path\repo
```

Always dry-run first. Migrate one repository, inspect and audit its diff, then
continue to the next. Do not apply to a dirty or temporary worktree by default.

## Output

Use the matching template under `../../workflow-2/templates/`. Report only
executed evidence and the real final Git state. Never let Builder issue the
final technical verdict.
