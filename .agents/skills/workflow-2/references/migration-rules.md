# Migration rules

## Before applying

- Confirm the path is the intended primary repository, not a disposable
  worktree, clone, backup or generated workspace.
- Record branch, commit, status and existing agent surfaces.
- Dry-run `migrate_repo.py` and inspect every planned action.
- Defer broad dirty working trees and conflicts in agent configuration.

## Preservation contract

The migrator may add its managed namespace and delimited routing blocks. It
must not delete, rename or replace project rules, domain skills, specialized
agents, commands or product code.

Files with local differences from their recorded installed hash are conflicts.
Resolve them manually; do not force an overwrite.

## After applying

- Run `validate_workflow.py`.
- Review status, diff check, stat and full diff.
- Confirm project-specific rules remain present.
- Test instruction discovery in the tools actually used by the repository.
- Audit the migration and stop before the next repository if the verdict is not
  `PASS` or `PASS WITH OBSERVATIONS`.
