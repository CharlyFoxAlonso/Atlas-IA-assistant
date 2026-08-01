# Role selection

| User intent | Role | Writes allowed |
|---|---|---|
| understand, diagnose, design, estimate | Planner | no |
| challenge or approve a plan | Plan Reviewer | no |
| implement an approved cut | Builder | approved scope only |
| review a diff or completed change | Auditor | no |

Diagnosis identifies the cause; it does not imply authorization to fix it.
Review identifies findings; it does not imply authorization to remediate them.

When one request explicitly includes planning and implementation, still create
the plan contract and review gate before editing. Stop for user approval only
when a missing choice materially changes product, architecture, data or risk.
