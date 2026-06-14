"""CLI facade for repo-native eval suite tools."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from roboclaws.evals.regression import promote_regression_from_cli_overrides
from roboclaws.evals.runner import DEFAULT_OUTPUT_ROOT, run_eval_suite


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run a Roboclaws eval suite.")
    parser.add_argument("overrides", nargs="*", help="key=value overrides.")
    args = parser.parse_args(argv)
    if args.overrides and args.overrides[0] in {"promote-regression", "promote_regression"}:
        try:
            promotion = promote_regression_from_cli_overrides(
                _parse_key_value_args(args.overrides[1:])
            )
        except ValueError as exc:
            parser.exit(2, f"error: {exc}\n")
        print(json.dumps(promotion, sort_keys=True))
        return 0
    try:
        run = _run_eval_from_overrides(_parse_key_value_args(args.overrides))
    except ValueError as exc:
        parser.exit(2, f"error: {exc}\n")
    print(json.dumps({"results": str(run.results_path), "report": str(run.report_path)}))
    return 0


def _run_eval_from_overrides(overrides: dict[str, str]):
    values = dict(overrides)
    suite_ref = values.pop("suite", "smoke_regression")
    budget = values.pop("budget", "smoke")
    output_root = Path(values.pop("output_dir", str(DEFAULT_OUTPUT_ROOT)))
    stamp = values.pop("stamp", None)
    agent_engine = values.pop("agent_engine", "direct-runner")
    provider_profile = values.pop("provider_profile", None)
    model = values.pop("model", None)
    live_execution = values.pop("live_execution", "blocked")
    live_timeout_s = _optional_float(values.pop("live_timeout_s", None))
    if values:
        keys = ", ".join(sorted(values))
        raise ValueError(f"unsupported eval override(s): {keys}")
    return run_eval_suite(
        suite_ref,
        output_root=output_root,
        budget=budget,
        stamp=stamp,
        agent_engine=agent_engine,
        provider_profile=provider_profile,
        model=model,
        live_execution=live_execution,
        live_timeout_s=live_timeout_s,
    )


def _parse_key_value_args(argv: list[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    index = 0
    while index < len(argv):
        item = argv[index]
        if item.startswith("--"):
            key = item.removeprefix("--").replace("-", "_")
            if "=" in key:
                key, value = key.split("=", 1)
            else:
                index += 1
                if index >= len(argv):
                    raise ValueError(f"missing value for {item}")
                value = argv[index]
            parsed[key] = value
        elif "=" in item:
            key, value = item.split("=", 1)
            parsed[key.replace("-", "_")] = value
        else:
            raise ValueError(f"unsupported eval argument {item!r}; expected key=value")
        index += 1
    return parsed


def _optional_float(value: str | None) -> float | None:
    if value in {None, ""}:
        return None
    return float(value)
