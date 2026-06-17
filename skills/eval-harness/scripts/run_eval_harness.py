#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import importlib.util
import json
import os
import re
import shutil
import socket
import subprocess
import urllib.parse
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[3]
SELECTOR_PATH = SCRIPT_DIR / "select_eval_harness.py"
DEFAULT_VISUAL_GROUNDING_BASE_URL = "http://127.0.0.1:18880"
PROVIDER_TIMING_PROXY_ENV = "ROBOCLAWS_PROVIDER_TIMING_PROXY"

spec = importlib.util.spec_from_file_location("eval_harness_selector", SELECTOR_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"could not load selector at {SELECTOR_PATH}")
selector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(selector)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Recommend or execute adaptive Roboclaws eval-harness rows.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("mode", choices=("recommend", "execute"))
    parser.add_argument("--budget", choices=("smoke", "focused", "full"), default="focused")
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--since")
    parser.add_argument("--changed-file", action="append", default=[])
    parser.add_argument("--agent-engine", default="")
    parser.add_argument("--provider-profile", default="")
    parser.add_argument("--intent", default="")
    parser.add_argument("--preset", default="")
    parser.add_argument("--evidence-lane", default="")
    parser.add_argument("--camera-labeler", default="")
    parser.add_argument("--output-dir", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    manifest = selector.build_eval_harness(
        mode=args.mode,
        budget=args.budget,
        plan=args.plan,
        since=args.since,
        changed_files=selector._split_csv_values(args.changed_file),
        agent_engine=selector._split_csv(args.agent_engine),
        provider_profile=selector._split_csv(args.provider_profile),
        intent=selector._split_csv(args.intent),
        preset=selector._split_csv(args.preset),
        evidence_lane=selector._split_csv(args.evidence_lane),
        camera_labeler=selector._split_csv(args.camera_labeler),
        output_dir=args.output_dir,
    )
    output_dir = Path(manifest["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.mode == "execute":
        _execute_harness(manifest)
    _write_outputs(manifest, output_dir)
    print(f"eval harness manifest: {output_dir / 'eval_harness.json'}")
    print(f"eval harness report: {output_dir / 'eval_harness.html'}")
    return _exit_status(manifest)


def _execute_harness(manifest: dict[str, Any]) -> None:
    for row in manifest["rows"]:
        if not row.get("selected"):
            continue
        if row.get("status") == "skipped_by_budget":
            continue
        blockers = _row_blockers(row, manifest)
        if blockers:
            row["status"] = "blocked"
            row["blocker_category"] = blockers[0]["category"]
            row["blockers"] = blockers
            continue
        _run_row(row, manifest)


def _row_blockers(row: dict[str, Any], manifest: dict[str, Any]) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []
    requirements = row.get("requires") or []
    axes = row.get("axes") or {}
    priority = {
        "codex_provider": 0,
        "openai_agents_package": 1,
        "dino_sidecar": 2,
        "runtime_map_prior": 3,
        "just": 4,
        "python_env": 5,
        "docker": 6,
    }
    for requirement in sorted(requirements, key=lambda item: priority.get(str(item), 100)):
        if requirement == "just" and shutil.which("just") is None:
            blockers.append(_environment_blocker("just is not on PATH"))
        elif requirement == "python_env" and not (REPO_ROOT / ".venv" / "bin" / "python").exists():
            blockers.append(_environment_blocker(".venv/bin/python is missing"))
        elif requirement == "docker" and shutil.which("docker") is None:
            blockers.append(_environment_blocker("docker is not on PATH"))
        elif requirement == "codex_provider" and not _has_codex_provider(axes):
            blockers.append(
                {
                    "category": "model_or_provider_unavailable",
                    "detail": (
                        "codex-env requires CODEX_BASE_URL and CODEX_API_KEY; "
                        "mify requires XM_LLM_API_KEY"
                    ),
                }
            )
        elif requirement == "openai_agents_package" and not _has_module("agents"):
            blockers.append(_environment_blocker("openai-agents package is not installed"))
        elif requirement == "dino_sidecar" and not _dino_sidecar_available():
            blockers.append(
                _environment_blocker("Grounding DINO visual-grounding sidecar is not reachable")
            )
        elif requirement == "runtime_map_prior" and not _runtime_prior_available(manifest):
            blockers.append(
                _environment_blocker(
                    "map-build prior artifact is required before cleanup consumer row"
                )
            )
    return blockers


def _environment_blocker(detail: str) -> dict[str, str]:
    return {"category": "environment_blocked", "detail": detail}


def _run_row(row: dict[str, Any], manifest: dict[str, Any]) -> None:
    row_dir = Path(row["row_dir"])
    row_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = row_dir / "stdout.log"
    stderr_path = row_dir / "stderr.log"
    command = _resolve_row_command(row, manifest)
    env = _row_environment(row)
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    stdout_path.write_text(result.stdout, encoding="utf-8")
    stderr_path.write_text(result.stderr, encoding="utf-8")
    row["status"] = "ran"
    row["exit_code"] = result.returncode
    row["outcome"] = "passed" if result.returncode == 0 else "failed"
    row["output_artifacts"] = [
        _display_path(stdout_path),
        _display_path(stderr_path),
    ]
    _attach_eval_outputs(row)
    _classify_eval_result_row(row)
    _classify_failed_row(row, stderr=result.stderr, stdout=result.stdout)


def _row_environment(row: dict[str, Any]) -> dict[str, str]:
    env = os.environ.copy()
    if _should_default_provider_timing_proxy(row) and PROVIDER_TIMING_PROXY_ENV not in env:
        env[PROVIDER_TIMING_PROXY_ENV] = "1"
        row["defaulted_provider_timing_proxy"] = True
    return env


def _should_default_provider_timing_proxy(row: dict[str, Any]) -> bool:
    axes = row.get("axes") or {}
    return row.get("expense") == "live-agent" and axes.get("agent_engine") in {
        "codex-cli",
        "claude-code",
    }


def _resolve_row_command(row: dict[str, Any], manifest: dict[str, Any]) -> list[str]:
    command = [_resolve_row_argument(str(item), manifest) for item in row["command"]]
    row["resolved_command"] = command
    row["resolved_command_display"] = " ".join(command)
    return command


def _resolve_row_argument(argument: str, manifest: dict[str, Any]) -> str:
    return re.sub(
        r"\$\{([^}:]+):([^}]+)\}",
        lambda match: str(_row_artifact_path(manifest, match.group(1), match.group(2))),
        argument,
    )


def _row_artifact_path(manifest: dict[str, Any], row_id: str, artifact_name: str) -> Path:
    run_dir = _row_run_dir(manifest, row_id)
    matches = sorted(run_dir.glob(f"**/{artifact_name}"))
    if not matches:
        raise FileNotFoundError(f"{row_id} did not produce {artifact_name} under {run_dir}")
    return matches[-1]


def _row_run_dir(manifest: dict[str, Any], row_id: str) -> Path:
    for row in manifest.get("rows") or []:
        if row.get("row_id") == row_id:
            return Path(row["row_dir"]) / "run"
    raise KeyError(f"unknown eval-harness row id: {row_id}")


def _classify_failed_row(row: dict[str, Any], *, stderr: str, stdout: str) -> None:
    if row.get("exit_code") == 0:
        return
    combined = f"{stderr}\n{stdout}".lower()
    if (
        "another interactive codex molmo cleanup session appears to be active" in combined
        or ("requested mcp port" in combined and "is already accepting connections" in combined)
        or "no molmospaces visual backend slot is available" in combined
    ):
        row["status"] = "blocked"
        row["outcome"] = "blocked"
        row["blocker_category"] = "environment_blocked"
        row["blockers"] = [
            _environment_blocker(
                "another live Molmo cleanup MCP session, port owner, or visual slot is active"
            )
        ]
    elif any(
        marker in combined
        for marker in (
            "model_or_provider_unavailable",
            "provider 502",
            "provider 429",
            "bad gateway",
            "rate limit",
            "model service",
            "missing provider env",
            "missing_provider_key",
        )
    ):
        row["status"] = "blocked"
        row["outcome"] = "blocked"
        row["blocker_category"] = "model_or_provider_unavailable"
        row["blockers"] = [
            {
                "category": "model_or_provider_unavailable",
                "detail": "provider, key, rate-limit, or model service failure",
            }
        ]


def _attach_eval_outputs(row: dict[str, Any]) -> None:
    if row.get("row_kind") not in {"eval_suite", "live_agent_eval"}:
        return
    for item in row.get("command") or []:
        if not str(item).startswith("output_dir="):
            continue
        output_root = Path(str(item).split("=", 1)[1])
        stamp = _command_value(row, "stamp")
        if stamp:
            matches = sorted(output_root.glob(f"*/{stamp}"))
            if matches:
                artifacts = list(row.get("output_artifacts") or [])
                for path in (matches[-1] / "eval_results.json", matches[-1] / "eval_report.html"):
                    if path.exists():
                        artifacts.append(_display_path(path))
                row["output_artifacts"] = artifacts


def _classify_eval_result_row(row: dict[str, Any]) -> None:
    if row.get("row_kind") not in {"eval_suite", "live_agent_eval"}:
        return
    result_paths = [
        REPO_ROOT / str(path)
        for path in row.get("output_artifacts") or []
        if str(path).endswith("eval_results.json")
    ]
    if not result_paths:
        return
    payload = _load_json(result_paths[-1])
    aggregate = payload.get("aggregate") if isinstance(payload.get("aggregate"), dict) else {}
    failed = int(aggregate.get("failed") or 0)
    blocked = int(aggregate.get("blocked") or 0)
    total = int(aggregate.get("total") or 0)
    row["eval_aggregate"] = {
        "total": total,
        "passed": int(aggregate.get("passed") or 0),
        "failed": failed,
        "blocked": blocked,
        "failure_classes": aggregate.get("failure_classes") or {},
    }
    if failed:
        row["outcome"] = "failed"
        row["failure_class"] = _first_failure_class(aggregate)
    elif blocked:
        row["status"] = "blocked"
        row["outcome"] = "blocked"
        row["blocker_category"] = _first_failure_class(aggregate) or "environment_blocked"


def _load_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _first_failure_class(aggregate: dict[str, Any]) -> str:
    failure_classes = aggregate.get("failure_classes")
    if isinstance(failure_classes, dict) and failure_classes:
        return str(next(iter(failure_classes)))
    return ""


def _command_value(row: dict[str, Any], key: str) -> str:
    prefix = f"{key}="
    for item in row.get("command") or []:
        text = str(item)
        if text.startswith(prefix):
            return text.split("=", 1)[1]
    return ""


def _has_codex_provider(axes: dict[str, Any]) -> bool:
    profile = str(axes.get("provider_profile") or "codex-env")
    if profile == "mify":
        return bool(os.environ.get("XM_LLM_API_KEY"))
    return bool(os.environ.get("CODEX_BASE_URL") and os.environ.get("CODEX_API_KEY"))


def _has_module(module_name: str) -> bool:
    return importlib.util.find_spec(module_name) is not None


def _dino_sidecar_available() -> bool:
    base_url = os.environ.get("VISUAL_GROUNDING_BASE_URL", DEFAULT_VISUAL_GROUNDING_BASE_URL)
    parsed = urllib.parse.urlparse(base_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        with socket.create_connection((host, port), timeout=0.35):
            return True
    except OSError:
        return False


def _runtime_prior_available(manifest: dict[str, Any]) -> bool:
    for row in manifest.get("rows") or []:
        if row.get("row_id") != "direct-map-build-world-oracle":
            continue
        if row.get("status") != "ran" or row.get("outcome") != "passed":
            return False
        run_dir = Path(row["row_dir"]) / "run"
        return any(run_dir.glob("**/runtime_metric_map.json"))
    return False


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _write_outputs(manifest: dict[str, Any], output_dir: Path) -> None:
    json_path = output_dir / "eval_harness.json"
    md_path = output_dir / "eval_harness.md"
    html_path = output_dir / "eval_harness.html"
    json_path.write_text(
        json.dumps(_redacted_manifest(manifest), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    md_path.write_text(_render_markdown(manifest), encoding="utf-8")
    html_path.write_text(_render_html(manifest), encoding="utf-8")


def _redacted_manifest(value: Any) -> Any:
    private_keys = {
        "private_goal_reference",
        "private_evaluation",
        "private_manifest",
        "generated_mess_set",
        "acceptable_destinations",
        "hidden_targets",
        "raw_provider_logs",
    }
    if isinstance(value, dict):
        return {
            key: _redacted_manifest(child)
            for key, child in value.items()
            if str(key) not in private_keys
        }
    if isinstance(value, list):
        return [_redacted_manifest(item) for item in value]
    return value


def _render_markdown(manifest: dict[str, Any]) -> str:
    lines = [
        "# Eval Harness",
        "",
        f"- Mode: `{manifest['mode']}`",
        f"- Budget: `{manifest['budget']}`",
        f"- Selected rows: `{manifest['summary']['selected_row_count']}`",
        "",
        "## Signals",
        "",
    ]
    if manifest.get("signals"):
        for signal in manifest["signals"]:
            files = ", ".join(signal.get("matched_files") or [])
            patterns = ", ".join(signal.get("matched_patterns") or [])
            detail = files or patterns or signal.get("source", "")
            lines.append(f"- `{signal['id']}`: {detail}")
    else:
        lines.append("- none")
    lines.extend(["", "## Rows", ""])
    for row in manifest["rows"]:
        selected = "selected" if row.get("selected") else "skipped"
        lines.append(f"### {row['row_id']}")
        lines.append("")
        lines.append(f"- Kind: `{row['row_kind']}`")
        lines.append(f"- Status: `{row['status']}`")
        if row.get("outcome"):
            lines.append(f"- Outcome: `{row['outcome']}`")
        if row.get("failure_class"):
            lines.append(f"- Failure class: `{row['failure_class']}`")
        lines.append(f"- Selection: `{selected}`")
        if row.get("blocker_category"):
            lines.append(f"- Blocker: `{row['blocker_category']}`")
        if row.get("reason_selected"):
            lines.append(f"- Rationale: {row['reason_selected']}")
        if row.get("skip_reason"):
            lines.append(f"- Skip reason: {row['skip_reason']}")
        if row.get("output_artifacts"):
            artifacts = ", ".join(str(item) for item in row["output_artifacts"])
            lines.append(f"- Artifacts: {artifacts}")
        lines.append(f"- Command: `{row['command_display']}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_html(manifest: dict[str, Any]) -> str:
    rows = []
    for row in manifest["rows"]:
        rows.append(
            "<tr>"
            f"<td>{html.escape(row['row_id'])}</td>"
            f"<td>{html.escape(row['row_kind'])}</td>"
            f"<td>{html.escape(str(row['status']))}</td>"
            f"<td>{html.escape(str(row.get('outcome') or ''))}</td>"
            f"<td>{html.escape(str(row.get('failure_class') or ''))}</td>"
            f"<td>{html.escape(str(row.get('blocker_category') or ''))}</td>"
            f"<td><code>{html.escape(row['command_display'])}</code></td>"
            "</tr>"
        )
    return (
        '<!doctype html><html><head><meta charset="utf-8">'
        "<title>Eval Harness</title>"
        "<style>body{font-family:sans-serif;margin:24px;}"
        "table{border-collapse:collapse;width:100%;}"
        "td,th{border:1px solid #ccc;padding:6px;vertical-align:top;}"
        "code{white-space:pre-wrap;}</style></head><body>"
        "<h1>Eval Harness</h1>"
        f"<p>Mode: <code>{html.escape(manifest['mode'])}</code> "
        f"Budget: <code>{html.escape(manifest['budget'])}</code></p>"
        "<table><thead><tr><th>Row</th><th>Kind</th><th>Status</th>"
        "<th>Outcome</th><th>Failure class</th><th>Blocker</th>"
        "<th>Command</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></body></html>\n"
    )


def _exit_status(manifest: dict[str, Any]) -> int:
    blocked = [
        row
        for row in manifest["rows"]
        if row.get("selected") and row.get("status") == "blocked"
    ]
    failed = [
        row
        for row in manifest["rows"]
        if row.get("selected")
        and row.get("status") == "ran"
        and (row.get("exit_code") or row.get("outcome") == "failed")
    ]
    if failed:
        return 1
    if blocked:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
