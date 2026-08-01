<!-- workflow-2:managed version=2.0.0 -->
# Contracts and handoffs

## Planner → Plan Reviewer

Required output:

- observable objective and user need;
- confirmed current-state evidence;
- requirements, assumptions and open questions;
- semantic invariants, variable policies and technical constraints;
- exact in-scope and out-of-scope areas;
- affected contracts, dependencies and external boundaries;
- implementation classification: production, tracer, prototype or learning test;
- test strategy, rollback and acceptance criteria;
- risks and stop conditions.

Planner does not edit and does not prescribe private implementation details
that can safely remain local and reversible.

## Plan Reviewer → Builder

The reviewer returns `APPROVED`, `APPROVED WITH CONDITIONS` or `REJECTED`.
Builder may start only with a viable, approved contract. Conditions must be
objective and resolved before or during the named implementation step.

## Builder authority

Builder may inspect, add focused tests, edit authorized files and perform local
refactoring required for a clean implementation. Builder may not redefine the
requirement, widen scope, alter durable architecture, weaken controls, commit,
push or approve its own work.

Builder output must include the actual diff scope, commands and results,
deviations, unresolved risks and a handoff to Auditor.

## Builder → Auditor

Auditor receives the approved contract, repository base, actual diff, Builder
report and reproducible commands. Auditor verifies rather than trusts.

Auditor returns `PASS`, `PASS WITH OBSERVATIONS`, `FAIL` or `INCONCLUSIVE` and
does not edit. Every blocking finding must identify evidence, impact, violated
criterion and the smallest sufficient remediation.

## Renegotiation

Stop when:

- evidence contradicts an approved assumption;
- a required file or dependency is outside scope;
- a data, security or compatibility risk was not planned;
- existing user changes cannot be preserved;
- verification cannot demonstrate a required criterion;
- continuing requires a product or architecture choice.

Report: observation, evidence, impact, options, recommendation and the smallest
decision needed. Do not continue by inventing authority.
