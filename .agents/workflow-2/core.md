<!-- workflow-2:managed version=2.1.0 -->
# Workflow 2.1 core

## Permanent rules

1. Inspect the real repository and Git state before making claims or edits.
2. Treat every existing change as user-owned work.
3. Work on one explicit, observable objective at a time.
4. Separate facts, inferences, assumptions and unresolved questions.
5. Preserve public contracts, data and error behavior unless the approved cut
   explicitly changes them.
6. Prefer the smallest complete and reversible change.
7. Keep decisions close to their domain and external providers behind narrow
   boundaries.
8. Do not accept generated code that cannot be explained from the diff,
   contracts and tests.
9. Execute relevant verification; never report an unexecuted check as passed.
10. Stop and renegotiate when repository evidence contradicts the plan, a new
    product or architecture decision appears, or safe scope must expand.
11. Do not commit, push, publish, deploy or perform destructive Git operations
    unless the user explicitly authorizes that exact action.
12. An independent Auditor, not Builder, issues the technical verdict.

## Role sequence

```text
Planner → Plan Reviewer → approval → Builder → Auditor
```

Planner, Plan Reviewer and Auditor are read-only. Builder is the single writer.
When Auditor rejects a cut, remediation returns to Builder under the same or a
newly approved contract.

## Authority hierarchy

1. `AGENTS.md` is the global authority for every task.
2. Workflow 2.1 roles govern all microcuts: Planner → Plan Reviewer → approval
   → Builder → Auditor.
3. Project policies are the single normative sources for their domains:
   `.agents/policies/git-safety.md` (Git) and `.agents/policies/testing.md`
   (testing and evidence). The local `policies/git.md` and
   `policies/testing.md` are routing references to those sources.
4. The playbooks under `.agents/playbooks/` are legacy/supporting: they apply
   only to tasks not governed by Workflow 2.1.

## Verdict vocabulary

Workflow 2.1 cuts use exactly these verdicts:

- Plan Reviewer: `APPROVED | APPROVED WITH CONDITIONS | REJECTED`
- Auditor: `PASS | PASS WITH OBSERVATIONS | FAIL | INCONCLUSIVE`

Legacy vocabularies (for example `HEALTHY`, `ACCEPT`, `APPROVED WITH NOTES`,
`REQUEST CHANGES`) must not be used in new Workflow 2.1 cuts.

## Policy routing

Always load:

- `policies/git.md` (routing reference to the project Git policy)
- `contracts/handoffs.md`

Load `policies/testing.md` (routing reference to the project testing policy)
for implementation, verification and audit. Load the remaining policies only
when the task touches their risk:

- `engineering.md`: code or design changes;
- `security.md`: untrusted input, paths, commands, secrets, network, data;
- `debugging.md`: defects or unexplained failures;
- `prototypes.md`: experiments, spikes, tracers or learning tests;
- `definition-of-done.md`: Builder handoff and final audit.

Project-specific instructions may strengthen these rules. A material conflict
must be reported, not silently resolved.
