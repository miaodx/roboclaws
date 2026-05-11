from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from analyze_view_experiment import analyze_results  # noqa: E402


def test_analyze_results_renders_tables_and_comparisons(tmp_path: Path) -> None:
    rows = [
        {
            "game": "territory",
            "variant": variant,
            "seed": seed,
            "scene": "FloorPlan201",
            "status": "ok",
            "cells_claimed_total": claimed,
            "usd": 0.1,
            "wallclock_seconds": 12.0,
            "blocking_events": 1,
            "total_steps": 20,
        }
        for variant, claimed in [("baseline", 10), ("map-v2", 12), ("map-v2+chase", 13)]
        for seed in [1, 2]
    ] + [
        {
            "game": "coverage",
            "variant": variant,
            "seed": seed,
            "scene": "FloorPlan201",
            "status": "ok",
            "coverage_fraction": coverage,
            "usd": 0.2,
            "wallclock_seconds": 9.0,
            "blocking_events": 0,
            "total_steps": 18,
        }
        for variant, coverage in [("baseline", 0.50), ("map-v2", 0.60), ("map-v2+chase", 0.65)]
        for seed in [1, 2]
    ]

    output_path = tmp_path / "summary.md"
    summary = analyze_results(rows, output_path=output_path, bootstrap_samples=100)

    assert "# View Experiment Summary" in summary
    assert "## Territory" in summary
    assert "## Coverage" in summary
    assert "| Comparison | Pairs | p-value | Effect Size |" in summary
    assert "B vs A" in summary
    assert "C vs A" in summary
    assert "C vs B" in summary
    assert output_path.read_text() == summary
