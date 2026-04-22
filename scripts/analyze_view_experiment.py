from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

PRIMARY_METRICS: dict[str, tuple[str, str]] = {
    "territory": ("cells_claimed_total", "Cells claimed"),
    "coverage": ("coverage_fraction", "Coverage fraction"),
    "openclaw-demo": ("visited_cells", "Visited cells"),
}
COMPARISONS: tuple[tuple[str, str, str], ...] = (
    ("B vs A", "map-v2", "baseline"),
    ("C vs A", "map-v2+chase", "baseline"),
    ("C vs B", "map-v2+chase", "map-v2"),
)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Analyze a Phase 2.4 view-experiment results.jsonl file.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--input", required=True, dest="input_path")
    parser.add_argument("--output", default=None, dest="output_path")
    parser.add_argument("--bootstrap-samples", type=int, default=1000, dest="bootstrap_samples")
    return parser.parse_args(argv)


def _load_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text().splitlines():
        stripped = line.strip()
        if stripped:
            rows.append(json.loads(stripped))
    return rows


def _bootstrap_ci(values: list[float], samples: int = 1000) -> tuple[float, float]:
    if not values:
        return (0.0, 0.0)
    if len(values) == 1:
        return (values[0], values[0])
    rng = np.random.default_rng(0)
    arr = np.asarray(values, dtype=float)
    means = []
    for _ in range(samples):
        sample = rng.choice(arr, size=len(arr), replace=True)
        means.append(float(sample.mean()))
    return (
        float(np.quantile(means, 0.025)),
        float(np.quantile(means, 0.975)),
    )


def _rank_abs(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=lambda idx: values[idx])
    ranks = [0.0] * len(values)
    rank = 1
    i = 0
    while i < len(order):
        j = i
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        average_rank = (rank + (rank + (j - i) - 1)) / 2.0
        for pos in range(i, j):
            ranks[order[pos]] = average_rank
        rank += j - i
        i = j
    return ranks


def _paired_wilcoxon(differences: list[float]) -> tuple[float, float, int]:
    non_zero = [diff for diff in differences if diff != 0]
    if not non_zero:
        return (1.0, 0.0, 0)
    ranks = _rank_abs([abs(diff) for diff in non_zero])
    ranks2 = [int(round(rank * 2)) for rank in ranks]
    observed_positive = sum(rank for rank, diff in zip(ranks2, non_zero) if diff > 0)
    total_rank = sum(ranks2)
    observed_min = min(observed_positive, total_rank - observed_positive)

    extreme = 0
    combinations = 1 << len(ranks2)
    for bits in range(combinations):
        positive = 0
        for idx, rank in enumerate(ranks2):
            if bits & (1 << idx):
                positive += rank
        if min(positive, total_rank - positive) <= observed_min:
            extreme += 1

    p_value = extreme / combinations
    effect = 0.0 if total_rank == 0 else (2.0 * observed_positive - total_rank) / total_rank
    return (p_value, effect, len(non_zero))


def _group_success_rows(rows: list[dict[str, Any]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("status") != "ok":
            continue
        grouped[(str(row["game"]), str(row["variant"]))].append(row)
    return grouped


def _primary_metric(row: dict[str, Any]) -> tuple[str, float]:
    game = str(row["game"])
    metric_key, metric_label = PRIMARY_METRICS.get(game, ("primary_metric", "Primary metric"))
    value = float(row.get(metric_key, row.get("primary_metric", 0.0)))
    return (metric_label, value)


def _paired_rows(
    grouped: dict[tuple[str, str], list[dict[str, Any]]],
    game: str,
    left: str,
    right: str,
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    left_rows = {(row["seed"], row["scene"]): row for row in grouped.get((game, left), [])}
    right_rows = {(row["seed"], row["scene"]): row for row in grouped.get((game, right), [])}
    keys = sorted(set(left_rows) & set(right_rows))
    return [(left_rows[key], right_rows[key]) for key in keys]


def _determine_best_variant(
    summaries: dict[str, dict[str, Any]],
    comparisons: list[dict[str, Any]],
) -> str | None:
    if not summaries:
        return None
    best_variant = max(summaries.items(), key=lambda item: item[1]["primary_mean"])[0]
    rivals = [summary for variant, summary in summaries.items() if variant != best_variant]
    if not rivals:
        return best_variant
    second_best = max(rivals, key=lambda item: item["primary_mean"])["variant"]
    for comparison in comparisons:
        variants = {comparison["left"], comparison["right"]}
        if variants == {best_variant, second_best} and comparison["p_value"] < 0.05:
            return best_variant
    return None


def analyze_results(
    rows: list[dict[str, Any]],
    *,
    output_path: Path | None = None,
    bootstrap_samples: int = 1000,
) -> str:
    grouped = _group_success_rows(rows)
    all_games = sorted({str(row["game"]) for row in rows})
    lines: list[str] = ["# View Experiment Summary", ""]

    for game in all_games:
        game_rows = [row for row in rows if str(row["game"]) == game]
        success_group = {
            variant: grouped[(game, variant)]
            for (_game, variant), variant_rows in grouped.items()
            if _game == game
            for _ in [variant_rows]
        }
        if not game_rows:
            continue

        metric_label = PRIMARY_METRICS.get(game, ("primary_metric", "Primary metric"))[1]
        variant_summaries: dict[str, dict[str, Any]] = {}
        for variant, variant_rows in sorted(success_group.items()):
            primary_values = [_primary_metric(row)[1] for row in variant_rows]
            usd_values = [float(row.get("usd", 0.0)) for row in variant_rows]
            steps_values = [float(row.get("total_steps", 0.0)) for row in variant_rows]
            wallclock_values = [float(row.get("wallclock_seconds", 0.0)) for row in variant_rows]
            blocking_values = [float(row.get("blocking_events", 0.0)) for row in variant_rows]
            ci_low, ci_high = _bootstrap_ci(primary_values, samples=bootstrap_samples)
            variant_summaries[variant] = {
                "variant": variant,
                "primary_mean": float(np.mean(primary_values)) if primary_values else 0.0,
                "ci_low": ci_low,
                "ci_high": ci_high,
                "usd_mean": float(np.mean(usd_values)) if usd_values else 0.0,
                "steps_mean": float(np.mean(steps_values)) if steps_values else 0.0,
                "wallclock_mean": float(np.mean(wallclock_values)) if wallclock_values else 0.0,
                "blocking_mean": float(np.mean(blocking_values)) if blocking_values else 0.0,
                "ok_runs": len(variant_rows),
                "total_runs": sum(1 for row in game_rows if row.get("variant") == variant),
            }

        comparisons: list[dict[str, Any]] = []
        for label, left, right in COMPARISONS:
            pairs = _paired_rows(grouped, game, left, right)
            differences = [
                _primary_metric(left_row)[1] - _primary_metric(right_row)[1]
                for left_row, right_row in pairs
            ]
            p_value, effect, pair_count = _paired_wilcoxon(differences)
            comparisons.append(
                {
                    "label": label,
                    "left": left,
                    "right": right,
                    "pairs": pair_count,
                    "p_value": p_value,
                    "effect": effect,
                }
            )

        best_variant = _determine_best_variant(variant_summaries, comparisons)
        lines.extend(
            [
                f"## {game.title()}",
                "",
                f"Primary metric: {metric_label}",
                "",
                (
                    "| Variant | Mean | 95% CI | Mean USD | Mean Wallclock | "
                    "Mean Blocking | Mean Steps | OK/Total |"
                ),
                "|---------|------|--------|----------|----------------|---------------|------------|----------|",
            ]
        )
        for variant, summary in sorted(variant_summaries.items()):
            label = f"**{variant}**" if variant == best_variant else variant
            lines.append(
                (
                    "| {variant} | {mean:.3f} | [{low:.3f}, {high:.3f}] | "
                    "{usd:.3f} | {wallclock:.3f} | {blocking:.3f} | "
                    "{steps:.2f} | {ok}/{total} |"
                ).format(
                    variant=label,
                    mean=summary["primary_mean"],
                    low=summary["ci_low"],
                    high=summary["ci_high"],
                    usd=summary["usd_mean"],
                    wallclock=summary["wallclock_mean"],
                    blocking=summary["blocking_mean"],
                    steps=summary["steps_mean"],
                    ok=summary["ok_runs"],
                    total=summary["total_runs"],
                )
            )

        lines.extend(
            [
                "",
                "| Comparison | Pairs | p-value | Effect Size |",
                "|------------|-------|---------|-------------|",
            ]
        )
        for comparison in comparisons:
            lines.append(
                "| {label} | {pairs} | {p_value:.4f} | {effect:.3f} |".format(**comparison)
            )
        lines.append("")

    summary_text = "\n".join(lines).rstrip() + "\n"
    if output_path is not None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(summary_text)
    return summary_text


def main() -> None:
    args = _parse_args()
    input_path = Path(args.input_path)
    output_path = Path(args.output_path) if args.output_path else input_path.parent / "summary.md"
    rows = _load_rows(input_path)
    summary = analyze_results(
        rows,
        output_path=output_path,
        bootstrap_samples=args.bootstrap_samples,
    )
    print(summary, end="")


if __name__ == "__main__":
    main()
