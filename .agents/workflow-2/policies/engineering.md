<!-- workflow-2:managed version=2.1.0 -->
# Engineering policy

## Easy to read and change

- Use domain names that reveal intent, units and side effects.
- Keep a function at one conceptual level and one clear responsibility.
- Prefer few arguments; replace traveling groups and positional booleans with a
  named concept when that reduces ambiguity.
- Separate decisions from effects and business rules from infrastructure.
- Make dependencies explicit; avoid mutable global state and temporal coupling.
- Encapsulate external SDKs and formats behind application-owned boundaries.
- Handle errors explicitly and fail early at trust boundaries.
- Give every acquired resource an owner and guaranteed release path.

## DRY and cohesion

Maintain one identifiable source of truth for each unit of knowledge, including
configuration, schemas, validation, messages and documentation. Generate
derived representations when that is simpler than synchronized manual copies.

Do not abstract coincidental similarity. A small temporary duplication is
safer than the wrong shared abstraction.

## Change discipline

- Apply the Boy Scout rule only within the authorized surface.
- Keep local refactors behavior-preserving and covered by relevant tests.
- Do not introduce speculative factories, registries, frameworks, event buses,
  services, plugin systems or configuration options.
- Prefer text, open formats and versionable artifacts when practical.
- Measure before optimizing and compare before/after evidence.
- Comments explain non-obvious intent, constraints and tradeoffs; they do not
  narrate unclear code.

Metrics are investigation signals, not automatic verdicts. Optimize cognitive
load and domain clarity, not line counts.
