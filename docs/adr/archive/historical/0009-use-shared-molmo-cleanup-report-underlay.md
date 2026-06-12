# Use Shared Molmo Cleanup Report Underlay

Roboclaws MolmoSpaces cleanup demos will render review artifacts through the
shared `roboclaws/molmo_cleanup/report.py` report underlay and shared semantic
labels from `roboclaws/molmo_cleanup/semantic_timeline.py`.

Current-contract bridge runs, ADR-0003 real-world-style runs, direct-agent
dogfood, and OpenClaw dogfood may expose different contract sections, but they
must reuse the same report module for summary metrics, before/after snapshots,
semantic cleanup subphases, score tables, and the Robot View Timeline when
robot views are recorded. The report-facing semantic loop is normalized to
`nav -> pick -> nav -> open? -> place`; raw traces and `run_result.json` keep
the full tool names for verification.

Contract-specific sections remain conditional. Current-contract artifacts may
lack Agent View and Private Evaluation because they do not satisfy ADR-0003.
Synthetic artifacts may lack Robot View Timeline because no RBY1M views were
recorded. Those are evidence differences, not permission to clone a separate
HTML implementation. New MolmoSpaces cleanup demos should add adapters to the
shared report underlay instead of creating another report renderer.
