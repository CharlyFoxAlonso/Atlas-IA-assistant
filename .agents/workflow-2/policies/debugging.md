<!-- workflow-2:managed version=2.1.0 -->
# Debugging policy

Before correcting a defect:

1. Reproduce the observed symptom.
2. Reduce it to the smallest reasonable input and environment.
3. Prefer a single documented reproduction command.
4. Record expected and observed results.
5. Distinguish root cause from downstream symptoms.
6. Form hypotheses that can be falsified.
7. Change one relevant variable at a time.
8. Confirm the cause with evidence, not correlation.
9. Add a regression test that fails under the defect.
10. Check whether the same root condition exists in related paths.

Do not blame the compiler, operating system, dependency or environment before
investigation. Do not catch broad exceptions, return empty values or add retries
that conceal the cause.

If reproduction is impossible, report the evidence gathered, missing condition
and risk. Do not present a speculative patch as a confirmed fix.

Record the investigation in `../templates/bug-report.md`.
