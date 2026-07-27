# Audit Playbook

Use this playbook to perform an evidence-based audit of code, architecture, documentation, security boundaries, or implementation quality.

Before starting, read and apply:

- `.agents/policies/git-safety.md`
- `.agents/policies/testing.md`

When `codebase-memory-mcp` is available and useful, also apply:

- `.agents/integrations/codebase-memory-mcp.md`

## 1. Audit is read-only

Do not modify source code, tests, configuration, dependencies, or documentation unless the task explicitly requests remediation.

Do not silently fix findings.

Separate:

- investigation;
- findings;
- recommendations;
- implementation.

## 2. Define the audit target

Identify:

- the component or scope being audited;
- the stated objective;
- relevant specifications;
- architectural decisions;
- expected contracts;
- acceptance or quality criteria;
- explicitly excluded areas.

Do not expand the audit beyond the requested scope without clearly labeling the additional observation.

## 3. Inspect the real repository

Audit the current repository state, not summaries alone.

Inspect:

- relevant source files;
- entry points;
- callers and dependencies;
- tests;
- configuration;
- persistence formats;
- error handling;
- documentation;
- changed and untracked files when relevant.

Treat reports and plans as claims that must be compared with actual implementation.

## 4. Use Codebase Memory optionally

When useful, apply:

- `.agents/integrations/codebase-memory-mcp.md`

Use it to:

- map modules and symbols;
- locate callers and dependencies;
- inspect architectural relationships;
- find related tests;
- identify potential impact areas.

Verify important findings against current source code.

If unavailable, continue with direct repository inspection.

## 5. Evidence levels

Classify evidence as:

### CONFIRMED

Directly supported by current source code, configuration, documentation, diff, or executed validation.

### INFERRED

A reasonable conclusion supported by confirmed evidence but not directly demonstrated.

### UNVERIFIED

A plausible concern or claim that could not be confirmed with available evidence.

Do not present inferred or unverified information as fact.

## 6. Audit dimensions

Evaluate only dimensions relevant to the task.

Possible dimensions include:

- correctness;
- scope compliance;
- contract preservation;
- architecture;
- dependency direction;
- coupling and cohesion;
- error handling;
- persistence compatibility;
- security boundaries;
- test quality;
- observability;
- maintainability;
- documentation accuracy;
- operational risk;
- platform compatibility.

Do not force every audit to cover every category.

## 7. Architecture review

When architecture is in scope, inspect:

- module responsibilities;
- dependency direction;
- layer boundaries;
- UI/domain/infrastructure separation;
- circular dependencies;
- duplicated responsibilities;
- hidden global state;
- public interfaces;
- unnecessary abstractions;
- boundaries that exist only in documentation.

Prefer concrete examples over broad architectural opinions.

Do not recommend redesign merely because another pattern is possible.

## 8. Correctness review

Inspect:

- expected behavior;
- edge cases;
- error paths;
- state transitions;
- input validation;
- output consistency;
- side effects;
- compatibility with existing callers.

Use executed tests when available.

Static inspection alone must not be reported as proof of runtime correctness.

## 9. Test review

Apply `.agents/policies/testing.md` when validation is required.

Evaluate whether tests:

- cover changed behavior;
- exercise public contracts;
- include relevant failures and edge cases;
- contain meaningful assertions;
- avoid excessive implementation coupling;
- preserve regression coverage.

Do not require unrelated test expansion.

## 10. Security review

When security is in scope, inspect relevant:

- trust boundaries;
- input validation;
- path handling;
- command execution;
- authentication and authorization;
- secret handling;
- dependency exposure;
- data leakage;
- unsafe defaults;
- destructive operations.

Do not claim a security guarantee from limited inspection.

Clearly state untested attack surfaces and environmental assumptions.

## 11. Documentation review

Compare documentation with current implementation.

Identify:

- outdated claims;
- undocumented public behavior;
- planned features described as implemented;
- renamed or missing components;
- incorrect commands;
- broken architectural descriptions;
- inconsistent terminology.

The source code is authoritative for current behavior unless the task explicitly audits conformance to a governing specification.

## 12. Findings

Every finding must include:

- title;
- severity;
- affected component;
- evidence;
- impact;
- recommendation;
- confidence level when not fully confirmed.

Use these severities:

### CRITICAL

Immediate risk of severe data loss, security compromise, or unusable core behavior.

### HIGH

Major defect, broken contract, serious architectural risk, or likely regression.

### MEDIUM

Meaningful issue with limited impact or manageable risk.

### LOW

Minor defect, maintainability issue, or limited inconsistency.

### INFORMATIONAL

Relevant observation without a required corrective action.

Do not inflate severity.

## 13. Recommendations

Recommendations must be:

- tied to a finding;
- proportionate to its impact;
- compatible with the current architecture;
- scoped clearly;
- ordered by priority.

Prefer the smallest corrective action that resolves the demonstrated problem.

Separate required remediation from optional improvement.

## 14. Avoid speculative redesign

Do not recommend:

- new frameworks;
- plugin systems;
- service decomposition;
- dependency injection;
- large rewrites;
- abstraction layers;
- dependency changes;

unless they directly address a confirmed problem and smaller changes are insufficient.

## 15. Final report

Keep the report concise and evidence-based.

Include:

1. audit target;
2. scope and exclusions;
3. evidence reviewed;
4. validation executed;
5. confirmed strengths;
6. findings ordered by severity;
7. unverified risks;
8. prioritized recommendations;
9. limitations;
10. audit verdict.

Use one verdict:

### HEALTHY

No material issue was found within the audited scope.

### HEALTHY WITH IMPROVEMENTS

No blocking issue exists, but meaningful improvements are recommended.

### NEEDS REMEDIATION

One or more confirmed issues require correction before the audited component should be considered reliable.

### CRITICAL

Severe confirmed risk requires immediate attention.

### INCONCLUSIVE

Available evidence was insufficient to support a reliable verdict.

## Final rule

Audit the real system, not its intended design.

Distinguish evidence from inference, avoid speculative redesign, and never hide uncertainty.