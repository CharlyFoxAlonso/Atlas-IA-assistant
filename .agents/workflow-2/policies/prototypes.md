<!-- workflow-2:managed version=2.0.0 -->
# Prototypes and experiments policy

Classify experimental work before implementation:

- `PRODUCTION`: intended product code with full quality gates.
- `TRACER`: minimal real end-to-end path intended to survive and be hardened.
- `PROTOTYPE`: disposable code used only to learn.
- `LEARNING TEST`: executable record of a dependency's real behavior.
- `BENCHMARK`: controlled measurement with a defined scenario and threshold.

A prototype must be visibly marked, isolated from production modules and real
credentials, excluded from release, and removed or archived when the question
is answered. Do not evolve a prototype incrementally into production without a
new plan and implementation audit.

A tracer follows production boundaries and receives tests appropriate to the
path it claims to implement. A benchmark records environment, data, before and
after results, and complexity tradeoffs.
