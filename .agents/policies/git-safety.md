# Git Safety Policy

Apply this policy to every task that may inspect or modify repository files.

## 1. Inspect the initial state

Before editing, run:

```powershell
git status --short
git branch --show-current
git rev-parse --short HEAD
```

Treat all existing modifications and untracked files as user-owned work.

Never delete, overwrite, restore, or discard them.

## 2. Prohibited operations

Unless the user explicitly authorizes them for the current task, do not run:

```text
git commit
git push
git pull
git merge
git rebase
git reset
git restore
git checkout
git switch
git clean
git stash
git cherry-pick
git revert
```

Do not create, delete, rename, or move branches or tags.

Read-only Git commands are allowed, including:

```text
git status
git diff
git log
git show
git branch --show-current
git rev-parse
git ls-files
```

## 3. Scope control

Modify only files explicitly allowed by the task.

Before finishing, run:

```powershell
git status --short
git diff --stat
git diff --check
```

Review the diff for every file changed by the task.

When an out-of-scope change appears:

1. do not remove or hide it;
2. determine whether it existed before the task;
3. preserve it;
4. report it clearly;
5. do not expand the task to fix it.

## 4. Shared modified files

When an allowed file already contains user changes:

- inspect its existing diff before editing;
- preserve those changes;
- make the smallest necessary edit;
- avoid replacing the whole file when a local edit is sufficient;
- review the final diff carefully.

When ownership is uncertain, preserve the change.

## 5. No automatic cleanup

Do not:

- delete untracked files;
- restore modified files;
- reformat the entire repository;
- reorder imports globally;
- normalize line endings globally;
- regenerate unrelated files;
- perform cleanup outside the requested scope.

A refactor does not authorize general cleanup.

## 6. Formatting and line endings

Avoid unrelated changes caused by:

- CRLF/LF conversion;
- encoding changes;
- trailing whitespace;
- formatters;
- import sorting.

When a whole file changes unexpectedly, investigate before continuing.

Do not describe the diff as clean when relevant formatting or line-ending warnings remain.

## 7. Commits

Do not create commits by default.

A commit is allowed only when explicitly requested and after:

- reviewing the complete diff;
- running the required tests;
- confirming that all changes are in scope;
- excluding unrelated files;
- reporting the real results.

## 8. Final report

Report briefly:

- initial branch and commit;
- initial modified or untracked files;
- previous user changes preserved;
- files changed by the task;
- out-of-scope changes detected;
- Git validation commands executed;
- whether any write operation such as commit or push was performed.

Never claim the working tree was clean when it was not.

## Final rule

Preserving user work has priority over cleaning the repository.

Never use destructive Git operations, never silently alter unrelated work, and never claim a clean result without inspecting the actual repository state.