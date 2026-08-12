<!-- workflow-2:managed version=2.1.0 -->
# Definition of Done

A microcut is complete only when:

1. The approved objective and every acceptance criterion have evidence.
2. Semantic invariants, public contracts and user data are preserved or their
   authorized change is documented and tested.
3. Relevant baseline, focused and regression checks pass.
4. Required lint, type, build, security, integration, smoke or device checks
   pass, or the verdict is explicitly limited.
5. A corrected defect has a regression test when technically possible.
6. The test can detect the defect for critical behavior.
7. The diff is small, in scope, understandable and free of secrets, temporary
   artifacts, dead code and accidental formatting.
8. Dependencies, resources, errors and external boundaries are explicit.
9. Difficult-to-reverse decisions include migration and rollback.
10. Documentation describes implemented behavior only.
11. Builder explains the change, evidence, deviations and residual risks.
12. Auditor independently returns `PASS` or `PASS WITH OBSERVATIONS`.
13. Final Git state and any pre-existing changes are reported honestly.

Near-complete is not complete. Missing mandatory evidence yields `INCONCLUSIVE`
or `FAIL`, not an optimistic pass.
