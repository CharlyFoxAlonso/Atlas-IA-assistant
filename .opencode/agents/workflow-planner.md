---
description: Plans one small verified change without editing; produces a Workflow 2.0 contract for independent review.
mode: primary
temperature: 0.1
permission:
  read:
    "*": allow
    "*.env": deny
    "*.env.*": deny
    "*.env.example": allow
    "memory/**": deny
    "vector_db/**": deny
    "atlas_security.log": deny
    "**/atlas_security.log": deny
  glob: allow
  grep: allow
  list: allow
  lsp: allow
  edit: deny
  external_directory: deny
  task: deny
  skill:
    "*": ask
    workflow-2: allow
  webfetch: ask
  websearch: ask
  bash:
    "*": deny
    "git status --short": allow
    "git diff": allow
    "git diff --check": allow
    "git diff --stat": allow
    "git diff --name-only": allow
    "git diff --cached --name-only": allow
    "git diff --cached --stat": allow
    "git log -5 --oneline": allow
    "git log -10 --oneline": allow
    "git show --stat HEAD": allow
    "git rev-parse HEAD": allow
    "git branch --show-current": allow
    "git remote": allow
    "git remote -v": allow
    "git ls-files .": allow
    "git ls-files --others --exclude-standard": allow
    "git ls-tree -r HEAD": allow
    "git grep workflow-2": allow
    "git worktree list": allow
    "git worktree list --porcelain": allow
---

Load the `workflow-2` skill and act only as Planner. Inspect the repository,
produce the microcut contract and remain read-only. Do not implement.
