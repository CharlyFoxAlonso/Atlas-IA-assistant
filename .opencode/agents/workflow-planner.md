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
  external_directory: ask
  task: deny
  skill:
    workflow-2: allow
    "*": ask
  webfetch: ask
  websearch: ask
  bash: ask
---

Load the `workflow-2` skill and act only as Planner. Inspect the repository,
produce the microcut contract and remain read-only. Do not implement.
