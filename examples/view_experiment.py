"""Experiment harness for Phase 2.4 view-variant sweeps."""

from __future__ import annotations

import argparse
import itertools
import json
import random
import sys
import time
from pathlib import Path
from typing import Any, Callable

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

from coverage_game import run_coverage_game
from territory_game import run_territory_game

GAME_CHOICES = ("territory", "coverage")
GAME_RUNNERS: dict[str, Callable[..., dict[str, Any]]] = {
    "territory": run_territory_game,
    "coverage": run_coverage_game,
}


def _parse_csv(value: str) -> list[str]:
    return [part.strip() for part in value.split(",") if part.strip()]


def _parse_int_csv(value: str) -> list[int]:
    return [int(part.strip()) for part in value.split(",") if part.strip()]


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sweep view variants across scenes, seeds, and games.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--variants", default="baseline,map-v2,map-v2+chase")
    parser.add_argument("--seeds", default="1,2,3,4,5")
    parser.add_argument("--scenes", default="FloorPlan201,FloorPlan205,FloorPlan210")
    parser.add_argument("--games", default="territory,coverage")
    parser.add_argument("--model", default="kimi-coding")
    parser.add_argument("--agents", type=int, default=3)
    parser.add_argument("--steps", type=int, default=200)
    parser.add_argument("--output-dir", default="output/view-experiment", dest="output_dir")
    parser.add_argument(
        "--max-usd",
        type=float,
        default=None,
        help="Cumulative wallet cap across the full sweep.",
    )
    return parser.parse_args(argv)


def _append_jsonl(path: Path, row: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, sort_keys=True) + "\n")


def _load_replay_summary(run_dir: Path) -> dict[str, Any]:
    replay_path = run_dir / "replay.json"
    if not replay_path.exists():
        return {}
    replay = json.loads(replay_path.read_text())
    return replay.get("summary", {})


def _territory_metrics(result: dict[str, Any]) -> dict[str, Any]:
    cells_claimed = {int(agent_id): count for agent_id, count in result["cells_claimed"].items()}
    return {
        "cells_claimed_total": int(sum(cells_claimed.values())),
        "blocking_events": int(result.get("blocking_events", 0)),
        "primary_metric": int(sum(cells_claimed.values())),
    }


def _coverage_metrics(result: dict[str, Any]) -> dict[str, Any]:
    coverage_pct = float(result.get("coverage_pct", 0.0))
    return {
        "cells_covered": int(result.get("cells_covered", 0)),
        "coverage_fraction": coverage_pct / 100.0,
        "work_balance": float(result.get("work_balance", 0.0)),
        "primary_metric": coverage_pct / 100.0,
    }


def run_view_experiment(
    *,
    variants: list[str],
    seeds: list[int],
    scenes: list[str],
    games: list[str],
    model: str,
    agents: int,
    steps: int,
    output_dir: str,
    max_usd: float | None = None,
) -> dict[str, Any]:
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    results_path = root / "results.jsonl"
    spent_usd = 0.0
    total_runs = len(variants) * len(seeds) * len(scenes) * len(games)
    completed_runs = 0
    aborted_for_budget = False

    for run_index, (variant, seed, scene, game) in enumerate(
        itertools.product(variants, seeds, scenes, games),
        start=1,
    ):
        if game not in GAME_RUNNERS:
            raise ValueError(f"Unknown game: {game!r}. Choose from {GAME_CHOICES}.")
        if max_usd is not None and spent_usd >= max_usd:
            remaining = total_runs - completed_runs
            print(f"Wallet gate hit at ${spent_usd:.6f}; stopping with {remaining} runs remaining.")
            aborted_for_budget = True
            break

        random.seed(seed)
        np.random.seed(seed)
        run_dir = root / variant / game / f"{scene}-seed{seed}"
        run_dir.parent.mkdir(parents=True, exist_ok=True)
        runner = GAME_RUNNERS[game]
        started = time.perf_counter()
        row: dict[str, Any] = {
            "variant": variant,
            "seed": seed,
            "scene": scene,
            "game": game,
            "model": model,
            "agents": agents,
            "status": "error",
            "run_index": run_index,
            "output_dir": str(run_dir),
        }

        try:
            result = runner(
                scene=scene,
                agent_count=agents,
                steps=steps,
                model=model,
                output_dir=str(run_dir),
                views=variant,
            )
            summary = _load_replay_summary(run_dir)
            row.update(
                {
                    "status": "ok",
                    "termination_reason": result.get("termination_reason"),
                    "usd": float(result.get("vlm_cost_usd", 0.0)),
                    "wallclock_seconds": round(time.perf_counter() - started, 3),
                    "total_steps": int(
                        result.get("total_steps")
                        or summary.get("total_steps")
                        or summary.get("step_count")
                        or 0
                    ),
                    "provider_status": result.get("provider_status", {}),
                }
            )
            if game == "territory":
                row.update(_territory_metrics(result))
            else:
                row.update(_coverage_metrics(result))
        except Exception as exc:  # noqa: BLE001 - continue the sweep after per-run failures
            row.update(
                {
                    "status": "error",
                    "error_kind": exc.__class__.__name__,
                    "error": str(exc),
                    "usd": 0.0,
                    "wallclock_seconds": round(time.perf_counter() - started, 3),
                }
            )

        spent_usd += float(row.get("usd", 0.0))
        row["cumulative_usd"] = round(spent_usd, 6)
        _append_jsonl(results_path, row)
        completed_runs += 1

    return {
        "results_path": str(results_path),
        "completed_runs": completed_runs,
        "spent_usd": round(spent_usd, 6),
        "aborted_for_budget": aborted_for_budget,
    }


def main() -> None:
    args = _parse_args()
    result = run_view_experiment(
        variants=_parse_csv(args.variants),
        seeds=_parse_int_csv(args.seeds),
        scenes=_parse_csv(args.scenes),
        games=_parse_csv(args.games),
        model=args.model,
        agents=args.agents,
        steps=args.steps,
        output_dir=args.output_dir,
        max_usd=args.max_usd,
    )
    print(f"results.jsonl : {result['results_path']}")
    print(f"runs complete : {result['completed_runs']}")
    print(f"spent usd     : ${result['spent_usd']:.6f}")
    print(f"budget stop   : {result['aborted_for_budget']}")


if __name__ == "__main__":
    main()
