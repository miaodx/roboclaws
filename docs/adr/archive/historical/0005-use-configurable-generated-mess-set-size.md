# Use Configurable Generated Mess Set Size

Roboclaws MolmoSpaces cleanup harnesses will use an explicit configurable
Generated Mess Set size instead of the historical fixed five-object selector.
ADR-0003 keeps the Generated Mess Set private; this ADR makes the hidden set
large enough to match the real-world cleanup contract from `CONTEXT.md`.

The canonical ADR-0003 real-world harness target for v1 is the lower bound of
that contract: 10 generated objects by default, with CLI and backend parameters
allowing larger runs up to the available scene inventory. The scorer evaluates
the whole generated set, derives its success threshold from the requested set
size, and reports the requested and actual generated counts in private
evaluation artifacts. The deterministic sweep baseline may still use public
category heuristics, but it must not receive the Generated Mess Set, hidden
target count, acceptable destinations, or private target receptacles.

The legacy five-object synthetic cleanup fixture remains available for fast
contract tests and compatibility with current-contract bridge artifacts. It is a
test fixture, not the default evidence shape for ADR-0003 v1 real-world cleanup.
