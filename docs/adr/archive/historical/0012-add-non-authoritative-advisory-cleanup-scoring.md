# Add Non-Authoritative Advisory Cleanup Scoring

Roboclaws will add an advisory cleanup scoring artifact for ADR-0003
MolmoSpaces cleanup runs, but deterministic scoring remains the only
authoritative pass/fail signal.

The real-world-style harness already separates Agent View from Private
Evaluation and annotates deterministic score rows with semantic acceptability.
The broader cleanup plan still calls for an Advisory LLM Scorer or model-check
layer that can explain ambiguous placements and disagreements without changing
whether a run passes. Adding that layer directly to the authoritative Scorer
would blur the public/private boundary and make tests dependent on model
availability.

The advisory scorer will therefore be a post-run review adapter:

- it consumes final score rows and scenario metadata after the run ends;
- it writes `advisory_evaluation.json` and `run_result["advisory_evaluation"]`;
- the shared Cleanup Artifact Report renders an "Advisory Review" section when
  the artifact is present;
- advisory verdicts, disagreements, and notes never change
  `cleanup_status`, `completion_status`, `mess_restoration_rate`,
  `sweep_coverage_rate`, or `disturbance_count`;
- the default adapter is deterministic and CI-safe, using the same public
  semantic rubric shape that a future live model scorer must satisfy;
- future paid or remote model adapters may be added only behind explicit flags
  and must use the same output schema.

This preserves ADR-0003 public/private separation: the Cleanup Agent never sees
advisory scoring during the run, and the report shows advisory review only as
post-run evidence next to Private Evaluation.
