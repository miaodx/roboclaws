from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from roboclaws.regression import STABLE_PAIRING_KEYS

PROVIDER_FAILURE_TERMINATIONS = {"provider_error", "provider_unstable"}
PolicyCheck = Callable[[str, dict[str, Any], dict[str, Any]], list[dict[str, Any]]]


@dataclass(frozen=True)
class ThresholdPolicy:
    """Suite-specific regression thresholds."""

    name: str
    compare_rows: PolicyCheck
    exact_suites: tuple[str, ...] = ()
    suite_prefixes: tuple[str, ...] = ()

    def matches(self, suite: str) -> bool:
        return suite in self.exact_suites or any(
            suite.startswith(prefix) for prefix in self.suite_prefixes
        )

    def compare(
        self,
        suite: str,
        baseline: dict[str, Any],
        candidate: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return self.compare_rows(suite, baseline, candidate)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare baseline and candidate refactor-regression captures.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--output-dir", default=None, dest="output_dir")
    return parser.parse_args(argv)


def load_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped:
            rows.append(json.loads(stripped))
    return rows


def _pairing_key(row: dict[str, Any]) -> tuple[Any, ...]:
    return tuple(row.get(key) for key in STABLE_PAIRING_KEYS)


def _index_rows(rows: list[dict[str, Any]]) -> dict[tuple[Any, ...], dict[str, Any]]:
    indexed: dict[tuple[Any, ...], dict[str, Any]] = {}
    for row in rows:
        indexed[_pairing_key(row)] = row
    return indexed


def _coordinate_dict(row: dict[str, Any]) -> dict[str, Any]:
    return {key: row.get(key) for key in STABLE_PAIRING_KEYS}


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _check_min_delta(
    *,
    metric: str,
    baseline: float,
    candidate: float,
    max_drop: float,
) -> dict[str, Any]:
    threshold = baseline - max_drop
    passed = candidate >= threshold
    return {
        "metric": metric,
        "passed": passed,
        "baseline": baseline,
        "candidate": candidate,
        "detail": f"candidate >= {threshold:.3f}",
    }


def _check_max_delta(
    *,
    metric: str,
    baseline: float,
    candidate: float,
    max_increase: float,
) -> dict[str, Any]:
    threshold = baseline + max_increase
    passed = candidate <= threshold
    return {
        "metric": metric,
        "passed": passed,
        "baseline": baseline,
        "candidate": candidate,
        "detail": f"candidate <= {threshold:.3f}",
    }


def _check_max_pct(
    *,
    metric: str,
    baseline: float,
    candidate: float,
    max_increase_ratio: float,
) -> dict[str, Any]:
    if baseline <= 0:
        passed = candidate <= baseline
        detail = "baseline <= 0; candidate must not increase above baseline"
    else:
        threshold = baseline * (1.0 + max_increase_ratio)
        passed = candidate <= threshold
        detail = f"candidate <= {threshold:.3f}"
    return {
        "metric": metric,
        "passed": passed,
        "baseline": baseline,
        "candidate": candidate,
        "detail": detail,
    }


def _check_max_pct_or_absolute(
    *,
    metric: str,
    baseline: float,
    candidate: float,
    max_increase_ratio: float,
    absolute_slack: float,
) -> dict[str, Any]:
    if baseline <= 0:
        threshold = absolute_slack
    else:
        threshold = max(baseline * (1.0 + max_increase_ratio), baseline + absolute_slack)
    passed = candidate <= threshold
    return {
        "metric": metric,
        "passed": passed,
        "baseline": baseline,
        "candidate": candidate,
        "detail": f"candidate <= {threshold:.3f} (ratio or absolute slack)",
    }


def _check_exact(metric: str, baseline: Any, candidate: Any) -> dict[str, Any]:
    return {
        "metric": metric,
        "passed": baseline == candidate,
        "baseline": baseline,
        "candidate": candidate,
        "detail": "exact match required",
    }


def _check_tool_call_tolerance(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    *,
    tolerance: int,
) -> dict[str, Any]:
    baseline_counts = {str(key): _as_int(value) for key, value in baseline.items()}
    candidate_counts = {str(key): _as_int(value) for key, value in candidate.items()}
    keys = sorted(set(baseline_counts) | set(candidate_counts))
    deltas = {key: candidate_counts.get(key, 0) - baseline_counts.get(key, 0) for key in keys}
    passed = all(abs(delta) <= tolerance for delta in deltas.values())
    return {
        "metric": "tool_calls_by_type",
        "passed": passed,
        "baseline": baseline_counts,
        "candidate": candidate_counts,
        "detail": f"per-key delta within +/-{tolerance}: {deltas}",
    }


def _check_no_new_provider_failure(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
) -> dict[str, Any]:
    baseline_reason = str(baseline.get("termination_reason", "unknown"))
    candidate_reason = str(candidate.get("termination_reason", "unknown"))
    baseline_failed = baseline_reason in PROVIDER_FAILURE_TERMINATIONS
    candidate_failed = candidate_reason in PROVIDER_FAILURE_TERMINATIONS
    return {
        "metric": "provider_failure_termination",
        "passed": not (candidate_failed and not baseline_failed),
        "baseline": baseline_reason,
        "candidate": candidate_reason,
        "detail": "candidate must not introduce a new provider failure termination",
    }


def _status_check(baseline: dict[str, Any], candidate: dict[str, Any]) -> list[dict[str, Any]]:
    if baseline.get("status") == "ok" and candidate.get("status") == "ok":
        return []
    return [
        {
            "metric": "capture_status",
            "passed": False,
            "baseline": baseline.get("status"),
            "candidate": candidate.get("status"),
            "detail": "both rows must be status=ok before metric checks can pass",
        }
    ]


def _explore_vlm_checks(
    suite: str,
    baseline: dict[str, Any],
    candidate: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        _check_min_delta(
            metric="cells_visited",
            baseline=_as_float(baseline.get("cells_visited")),
            candidate=_as_float(candidate.get("cells_visited")),
            max_drop=1.0,
        ),
        _check_max_pct_or_absolute(
            metric="usd",
            baseline=_as_float(baseline.get("usd")),
            candidate=_as_float(candidate.get("usd")),
            max_increase_ratio=0.25,
            absolute_slack=0.01,
        ),
        _check_max_pct_or_absolute(
            metric="wallclock_seconds",
            baseline=_as_float(baseline.get("wallclock_seconds")),
            candidate=_as_float(candidate.get("wallclock_seconds")),
            max_increase_ratio=0.50,
            absolute_slack=120.0,
        ),
    ]


def _openclaw_demo_checks(
    suite: str,
    baseline: dict[str, Any],
    candidate: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        _check_min_delta(
            metric="visited_cells",
            baseline=_as_float(baseline.get("visited_cells")),
            candidate=_as_float(candidate.get("visited_cells")),
            max_drop=1.0,
        ),
        _check_max_pct(
            metric="usd",
            baseline=_as_float(baseline.get("usd")),
            candidate=_as_float(candidate.get("usd")),
            max_increase_ratio=0.25,
        ),
        _check_max_pct(
            metric="wallclock_seconds",
            baseline=_as_float(baseline.get("wallclock_seconds")),
            candidate=_as_float(candidate.get("wallclock_seconds")),
            max_increase_ratio=0.50,
        ),
    ]


def _territory_checks(
    suite: str,
    baseline: dict[str, Any],
    candidate: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        _check_min_delta(
            metric="cells_claimed_total",
            baseline=_as_float(baseline.get("cells_claimed_total")),
            candidate=_as_float(candidate.get("cells_claimed_total")),
            max_drop=2.0,
        ),
        _check_max_delta(
            metric="blocking_events",
            baseline=_as_float(baseline.get("blocking_events")),
            candidate=_as_float(candidate.get("blocking_events")),
            max_increase=2.0,
        ),
        _check_no_new_provider_failure(baseline, candidate),
    ]


def _coverage_checks(
    suite: str,
    baseline: dict[str, Any],
    candidate: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        _check_min_delta(
            metric="coverage_fraction",
            baseline=_as_float(baseline.get("coverage_fraction")),
            candidate=_as_float(candidate.get("coverage_fraction")),
            max_drop=0.05,
        ),
        _check_min_delta(
            metric="work_balance",
            baseline=_as_float(baseline.get("work_balance")),
            candidate=_as_float(candidate.get("work_balance")),
            max_drop=0.10,
        ),
        _check_max_pct(
            metric="total_steps",
            baseline=_as_float(baseline.get("total_steps")),
            candidate=_as_float(candidate.get("total_steps")),
            max_increase_ratio=0.20,
        ),
    ]


def _openclaw_autonomous_checks(
    suite: str,
    baseline: dict[str, Any],
    candidate: dict[str, Any],
) -> list[dict[str, Any]]:
    return [
        _check_exact(
            "transcript_source",
            baseline.get("transcript_source"),
            candidate.get("transcript_source"),
        ),
        _check_tool_call_tolerance(
            baseline.get("tool_calls_by_type", {}),
            candidate.get("tool_calls_by_type", {}),
            tolerance=2,
        ),
        _check_max_delta(
            metric="frames_unseen_by_agent",
            baseline=_as_float(baseline.get("frames_unseen_by_agent")),
            candidate=_as_float(candidate.get("frames_unseen_by_agent")),
            max_increase=2.0,
        ),
    ]


THRESHOLD_POLICIES: tuple[ThresholdPolicy, ...] = (
    ThresholdPolicy(
        name="explore-vlm",
        compare_rows=_explore_vlm_checks,
        exact_suites=("explore-vlm",),
    ),
    ThresholdPolicy(
        name="openclaw-demo",
        compare_rows=_openclaw_demo_checks,
        exact_suites=("openclaw-demo",),
    ),
    ThresholdPolicy(
        name="territory",
        compare_rows=_territory_checks,
        suite_prefixes=("territory-",),
    ),
    ThresholdPolicy(
        name="coverage",
        compare_rows=_coverage_checks,
        suite_prefixes=("coverage-",),
    ),
    ThresholdPolicy(
        name="openclaw-autonomous",
        compare_rows=_openclaw_autonomous_checks,
        exact_suites=("openclaw-autonomous",),
    ),
)


def threshold_policy_for_suite(suite: str) -> ThresholdPolicy | None:
    for policy in THRESHOLD_POLICIES:
        if policy.matches(suite):
            return policy
    return None


def _suite_checks(
    suite: str,
    baseline: dict[str, Any],
    candidate: dict[str, Any],
) -> list[dict[str, Any]]:
    status_checks = _status_check(baseline, candidate)
    if status_checks:
        return status_checks

    policy = threshold_policy_for_suite(suite)
    if policy is not None:
        return policy.compare(suite, baseline, candidate)

    return [
        {
            "metric": "suite_policy",
            "passed": False,
            "baseline": suite,
            "candidate": suite,
            "detail": f"no threshold policy registered for suite {suite!r}",
        }
    ]


def analyze_capture_sets(
    *,
    baseline_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    baseline_index = _index_rows(baseline_rows)
    candidate_index = _index_rows(candidate_rows)

    comparisons: list[dict[str, Any]] = []
    missing_pairs: list[dict[str, Any]] = []

    all_keys = sorted(
        set(baseline_index) | set(candidate_index),
        key=lambda key: tuple("" if value is None else str(value) for value in key),
    )

    overall_passed = True

    for key in all_keys:
        baseline = baseline_index.get(key)
        candidate = candidate_index.get(key)

        if baseline is None or candidate is None:
            row = baseline or candidate
            assert row is not None
            missing_pairs.append(
                {
                    "coordinates": _coordinate_dict(row),
                    "missing": "baseline" if baseline is None else "candidate",
                }
            )
            overall_passed = False
            continue

        suite = str(baseline.get("suite", candidate.get("suite", "")))
        checks = _suite_checks(suite, baseline, candidate)
        pair_passed = all(check["passed"] for check in checks)
        overall_passed = overall_passed and pair_passed
        comparisons.append(
            {
                "coordinates": _coordinate_dict(baseline),
                "baseline_artifact_dir": baseline.get("artifact_dir"),
                "candidate_artifact_dir": candidate.get("artifact_dir"),
                "status": "pass" if pair_passed else "fail",
                "checks": checks,
            }
        )

    return {
        "pairing_keys": list(STABLE_PAIRING_KEYS),
        "baseline_rows": len(baseline_rows),
        "candidate_rows": len(candidate_rows),
        "passed": overall_passed and not missing_pairs,
        "missing_pairs": missing_pairs,
        "comparisons": comparisons,
    }


def _summary_markdown(summary: dict[str, Any]) -> str:
    lines: list[str] = [
        "# Refactor Regression Summary",
        "",
        f"Outcome: **{'PASS' if summary['passed'] else 'FAIL'}**",
        "",
        f"Baseline rows: {summary['baseline_rows']}",
        f"Candidate rows: {summary['candidate_rows']}",
        "",
    ]

    lines.extend(["## Missing Pairs", ""])
    if summary["missing_pairs"]:
        lines.extend(
            [
                "| Suite | Backend | Scene | Seed | Game | Model | Agents | Variant | Missing |",
                "|-------|---------|-------|------|------|-------|--------|---------|---------|",
            ]
        )
        for item in summary["missing_pairs"]:
            coords = item["coordinates"]
            row_text = (
                "| {suite} | {backend} | {scene} | {seed} | {game} | {model} | "
                "{agents} | {variant} | {missing} |"
            )
            lines.append(
                row_text.format(
                    suite=coords.get("suite"),
                    backend=coords.get("backend"),
                    scene=coords.get("scene"),
                    seed=coords.get("seed"),
                    game=coords.get("game"),
                    model=coords.get("model"),
                    agents=coords.get("agents"),
                    variant=coords.get("variant"),
                    missing=item["missing"],
                )
            )
    else:
        lines.append("None.")
    lines.append("")

    lines.extend(["## Pair Results", ""])
    if not summary["comparisons"]:
        lines.append("No overlapping coordinate pairs.")
        lines.append("")
        return "\n".join(lines).rstrip() + "\n"

    for comparison in summary["comparisons"]:
        coords = comparison["coordinates"]
        lines.extend(
            [
                "### {suite} — {scene} seed {seed}".format(
                    suite=coords.get("suite"),
                    scene=coords.get("scene"),
                    seed=coords.get("seed"),
                ),
                "",
                f"Status: **{comparison['status'].upper()}**",
                "",
                f"Baseline artifact: `{comparison['baseline_artifact_dir']}`",
                f"Candidate artifact: `{comparison['candidate_artifact_dir']}`",
                "",
                "| Check | Result | Baseline | Candidate | Detail |",
                "|-------|--------|----------|-----------|--------|",
            ]
        )
        for check in comparison["checks"]:
            lines.append(
                "| {metric} | {result} | {baseline} | {candidate} | {detail} |".format(
                    metric=check["metric"],
                    result="PASS" if check["passed"] else "FAIL",
                    baseline=json.dumps(check["baseline"], sort_keys=True),
                    candidate=json.dumps(check["candidate"], sort_keys=True),
                    detail=str(check["detail"]).replace("|", "\\|"),
                )
            )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def write_summary(
    *,
    summary: dict[str, Any],
    output_dir: Path,
) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_json_path = output_dir / "summary.json"
    summary_md_path = output_dir / "summary.md"
    summary_json_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    summary_md_path.write_text(_summary_markdown(summary), encoding="utf-8")
    return {
        "summary_json": str(summary_json_path),
        "summary_md": str(summary_md_path),
    }


def main() -> int:
    args = _parse_args()
    baseline_path = Path(args.baseline)
    candidate_path = Path(args.candidate)
    output_dir = (
        Path(args.output_dir) if args.output_dir is not None else candidate_path.parent / "analysis"
    )

    summary = analyze_capture_sets(
        baseline_rows=load_rows(baseline_path),
        candidate_rows=load_rows(candidate_path),
    )
    outputs = write_summary(summary=summary, output_dir=output_dir)

    print(f"summary.md   : {outputs['summary_md']}")
    print(f"summary.json : {outputs['summary_json']}")
    print(f"passed       : {summary['passed']}")
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
