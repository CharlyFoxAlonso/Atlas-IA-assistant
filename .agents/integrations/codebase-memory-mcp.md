# Codebase Memory MCP Integration

Use `codebase-memory-mcp` as an optional repository navigation and impact-analysis tool.

Its absence or failure must not block work that can be completed through direct source inspection and standard repository tools.

## 1. Purpose

Use it when helpful to:

- locate files and symbols;
- find definitions and references;
- inspect callers, callees, imports, and dependencies;
- explore unfamiliar architecture;
- identify related tests;
- estimate change impact;
- maintain repository index freshness.

It assists investigation. It is not authoritative evidence.

## 2. When to use it

Consider using it for:

- planning;
- implementation;
- refactoring;
- debugging;
- architectural analysis;
- impact assessment;
- verification of structural changes.

Skip it when the task is trivial, fully localized, and already understood.

Avoid unnecessary queries that do not affect the task.

## 3. Recommended workflow

When useful:

1. query the index for relevant files and symbols;
2. inspect reported relationships;
3. open and read the current source code;
4. verify callers, imports, tests, and contracts directly;
5. implement the change;
6. review the diff;
7. run required validation;
8. refresh the index when structural relationships changed.

Never modify behavior from MCP summaries alone.

## 4. Source code has priority

Verify important MCP findings against the current repository.

Confirm:

- the symbol still exists;
- its signature is current;
- references are still valid;
- no relevant callers were omitted;
- indexed files match the working tree;
- tests reflect the real contract.

When the index conflicts with the current source, trust the current source.

## 5. Impact analysis limits

Use impact analysis to discover areas that may require inspection.

Do not use it alone to claim:

- all dependencies were found;
- the change is safe;
- no regressions exist;
- all callers are covered;
- behavior is verified.

Those claims require source inspection, diff review, and executed tests.

## 6. Planning use

During planning, use it to:

- map relevant modules;
- locate existing implementations;
- identify shared contracts;
- find likely affected files;
- reduce unnecessary repository scanning.

Plans must distinguish:

- facts confirmed in source code;
- relationships suggested by the index;
- unresolved assumptions.

Do not present inferred graph relationships as confirmed facts.

## 7. Implementation use

Before editing, use it when helpful to:

- locate the target symbol;
- find callers and dependencies;
- identify related tests;
- understand the surrounding boundary.

After editing, use it when helpful to:

- inspect newly affected references;
- verify structural relationships;
- refresh the repository index.

It never replaces testing or diff inspection.

## 8. Index refresh

Refresh the index when changes affect:

- symbols;
- modules;
- imports;
- dependencies;
- entry points;
- architectural boundaries;
- file structure.

A refresh is usually unnecessary for changes limited to:

- comments;
- documentation;
- formatting;
- text without structural impact;
- files ignored by the integration.

If refresh fails, report the limitation.

Never claim the index was updated unless the operation succeeded.

## 9. Unavailability or failure

When the integration is unavailable:

- continue with direct file inspection;
- use repository search;
- inspect imports and references;
- use language-specific tools;
- run tests normally.

Do not reject a task only because the MCP is unavailable.

Block only when the current instruction explicitly requires an operation that cannot be completed without it.

## 10. Avoid overuse

Do not:

- query the MCP for every file by default;
- replace source reading with summaries;
- trust indexed relationships blindly;
- treat graph output as runtime evidence;
- stop a simple task because the integration failed;
- add unnecessary MCP ceremony to localized changes.

Use it only when it reduces uncertainty or navigation cost.

## 11. Reporting

When materially used, report briefly:

- what it helped locate;
- which findings were verified against source code;
- whether the index was refreshed;
- any stale, missing, or inconsistent data found.

Do not list every query.

## Final rule

Use `codebase-memory-mcp` when available and valuable.

Current source code, the actual diff, and executed tests always take priority over indexed data.