<!-- workflow-2:managed version=2.1.0 -->
# Security policy

- Treat prompts, model output, files, paths, URLs, commands and external data as
  untrusted input.
- Validate at trust boundaries; reject invalid state early and visibly.
- Apply least privilege to agents, tools, filesystem access and credentials.
- Never print, copy, commit or place secrets, tokens, credentials, private keys
  or personal data in reports.
- Do not inspect real private data when synthetic fixtures can verify behavior.
- Confine file operations to the authorized workspace and account for traversal,
  absolute paths, symlinks and accidental overwrite.
- Do not execute generated commands without parsing, validation and the required
  user approval.
- Do not add network access, telemetry, remote processing, permissions or
  production dependencies without explicit authorization.
- Pin and audit dependencies according to project policy; do not update them as
  incidental cleanup.
- Preserve safe failure behavior. Never convert a security failure into silent
  success or empty output.

Security review is bounded to the inspected surface. Never claim total security
from a limited audit.
