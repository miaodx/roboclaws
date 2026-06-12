# Archived ADR-Shaped Execution Records

This archive contains ADR-shaped files that were created during earlier
long-running proof, retry, and implementation loops. They are preserved for
traceability, but they are not part of the default architecture decision
surface.

Use these files only when reconstructing historical proof-loop context. Do not
copy their pattern for new work.

Current rule:

- durable architecture or public-contract decision -> `docs/adr/`
- execution plan or refactor scope -> `docs/plans/YYYY-MM-DD-short-topic.md`
- active standalone status -> `docs/status/active/`
- shipped evidence and phase history -> `docs/retrospectives/`

Do not move these files back into `docs/adr/` unless one is rewritten or
superseded as a concise durable decision with clear alternatives and
consequences.
