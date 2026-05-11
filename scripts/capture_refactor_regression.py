from __future__ import annotations

import argparse
import time
from pathlib import Path
from typing import Any

from roboclaws.regression import (
    CaptureRequest,
    append_jsonl,
    build_artifact_dir,
    build_run_id,
    get_suite,
    parse_csv,
    parse_int_csv,
    validate_capture_label,
)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture refactor-regression baselines or candidates.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--suite", required=True, help="Comma-separated suite names")
    parser.add_argument("--output-dir", default="output/refactor-regression", dest="output_dir")
    parser.add_argument("--label", required=True, help="Immutable capture-set label")
    parser.add_argument("--scenes", default="FloorPlan201")
    parser.add_argument("--seeds", default="1")
    parser.add_argument("--agents", type=int, default=None)
    parser.add_argument("--steps", type=int, default=20)
    parser.add_argument("--model", default="mock")
    parser.add_argument("--allow-local", action="store_true")
    return parser.parse_args(argv)


def run_capture(
    *,
    suites: list[str],
    output_dir: str,
    label: str,
    scenes: list[str],
    seeds: list[int],
    agents: int | None,
    steps: int,
    model: str,
    allow_local: bool = False,
) -> dict[str, Any]:
    capture_label = validate_capture_label(label)
    label_root = Path(output_dir) / capture_label
    label_root.mkdir(parents=True, exist_ok=True)
    results_path = label_root / "results.jsonl"

    attempted_runs = 0
    successful_runs = 0
    failed_runs = 0

    for suite_name in suites:
        suite = get_suite(suite_name)
        effective_agents = agents if agents is not None else suite.default_agents

        for scene in scenes:
            for seed in seeds:
                attempted_runs += 1
                request = CaptureRequest(
                    label=capture_label,
                    scene=scene,
                    seed=seed,
                    agents=effective_agents,
                    steps=steps,
                    model=model,
                    allow_local=allow_local,
                )
                run_id = build_run_id()
                artifact_dir = build_artifact_dir(
                    label_root,
                    suite_name=suite.name,
                    scene=scene,
                    seed=seed,
                    run_id=run_id,
                )
                artifact_dir.mkdir(parents=True, exist_ok=True)

                started = time.perf_counter()
                try:
                    row = suite.capture_ok_row(
                        request=request,
                        artifact_dir=artifact_dir,
                        run_id=run_id,
                        elapsed_seconds=time.perf_counter() - started,
                    )
                    successful_runs += 1
                except Exception as exc:  # noqa: BLE001 - keep append-only history on failures
                    row = suite.capture_error_row(
                        request=request,
                        artifact_dir=artifact_dir,
                        run_id=run_id,
                        exc=exc,
                        elapsed_seconds=time.perf_counter() - started,
                    )
                    failed_runs += 1

                append_jsonl(results_path, row)

    return {
        "results_path": str(results_path),
        "attempted_runs": attempted_runs,
        "successful_runs": successful_runs,
        "failed_runs": failed_runs,
        "had_errors": failed_runs > 0,
    }


def main() -> int:
    args = _parse_args()
    result = run_capture(
        suites=parse_csv(args.suite),
        output_dir=args.output_dir,
        label=args.label,
        scenes=parse_csv(args.scenes),
        seeds=parse_int_csv(args.seeds),
        agents=args.agents,
        steps=args.steps,
        model=args.model,
        allow_local=args.allow_local,
    )
    print(f"results.jsonl : {result['results_path']}")
    print(f"attempted     : {result['attempted_runs']}")
    print(f"successful    : {result['successful_runs']}")
    print(f"failed        : {result['failed_runs']}")
    return 1 if result["had_errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
