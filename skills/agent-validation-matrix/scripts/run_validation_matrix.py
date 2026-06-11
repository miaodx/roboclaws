#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import importlib.util
import json
import os
import shutil
import socket
import subprocess
import urllib.parse
from pathlib import Path
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = Path(__file__).resolve().parents[3]
SELECTOR_PATH = SCRIPT_DIR / "select_validation_matrix.py"
DEFAULT_VISUAL_GROUNDING_BASE_URL = "http://127.0.0.1:18880"

spec = importlib.util.spec_from_file_location("agent_validation_selector", SELECTOR_PATH)
if spec is None or spec.loader is None:
    raise RuntimeError(f"could not load selector at {SELECTOR_PATH}")
selector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(selector)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Recommend or execute an adaptive Roboclaws agent-validation matrix.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("mode", choices=("recommend", "execute"))
    parser.add_argument("--budget", choices=("smoke", "focused", "full"), default="focused")
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--since")
    parser.add_argument("--changed-file", action="append", default=[])
    parser.add_argument("--agent-engine", default="")
    parser.add_argument("--provider-profile", default="")
    parser.add_argument("--evidence-lane", default="")
    parser.add_argument("--camera-labeler", default="")
    parser.add_argument("--output-dir", type=Path)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    matrix = selector.build_validation_matrix(
        mode=args.mode,
        budget=args.budget,
        plan=args.plan,
        since=args.since,
        changed_files=selector._split_csv_values(args.changed_file),
        agent_engine=selector._split_csv(args.agent_engine),
        provider_profile=selector._split_csv(args.provider_profile),
        evidence_lane=selector._split_csv(args.evidence_lane),
        camera_labeler=selector._split_csv(args.camera_labeler),
        output_dir=args.output_dir,
    )
    output_dir = Path(matrix["output_dir"])
    output_dir.mkdir(parents=True, exist_ok=True)
    if args.mode == "execute":
        _execute_matrix(matrix)
    _write_outputs(matrix, output_dir)
    print(f"agent validation matrix: {output_dir / 'validation_matrix.json'}")
    print(f"agent validation report: {output_dir / 'validation_matrix.html'}")
    return _exit_status(matrix)


def _execute_matrix(matrix: dict[str, Any]) -> None:
    for gate in matrix["gates"]:
        if not gate.get("selected"):
            continue
        if gate.get("status") == "required_skipped_by_user_budget":
            continue
        blockers = _gate_blockers(gate, matrix)
        if blockers:
            gate["status"] = "required_blocked"
            gate["blocker_category"] = blockers[0]["category"]
            gate["blockers"] = blockers
            continue
        _run_gate(gate)


def _gate_blockers(gate: dict[str, Any], matrix: dict[str, Any]) -> list[dict[str, str]]:
    blockers: list[dict[str, str]] = []
    requirements = gate.get("requires") or []
    axes = gate.get("axes") or {}
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
            blockers.append({"category": "missing_command", "detail": "just is not on PATH"})
        elif requirement == "python_env" and not (REPO_ROOT / ".venv" / "bin" / "python").exists():
            blockers.append(
                {"category": "missing_python_env", "detail": ".venv/bin/python is missing"}
            )
        elif requirement == "docker" and shutil.which("docker") is None:
            blockers.append({"category": "missing_docker", "detail": "docker is not on PATH"})
        elif requirement == "codex_provider" and not _has_codex_provider(axes):
            blockers.append(
                {
                    "category": "missing_provider_key",
                    "detail": (
                        "codex-env requires CODEX_BASE_URL and CODEX_API_KEY; "
                        "mify requires XM_LLM_API_KEY"
                    ),
                }
            )
        elif requirement == "openai_agents_package" and not _has_module("agents"):
            blockers.append(
                {
                    "category": "missing_optional_dependency",
                    "detail": "openai-agents package is not installed",
                }
            )
        elif requirement == "dino_sidecar" and not _dino_sidecar_available():
            blockers.append(
                {
                    "category": "dino_sidecar_unavailable",
                    "detail": "Grounding DINO visual-grounding sidecar is not reachable",
                }
            )
        elif requirement == "runtime_map_prior" and not _runtime_prior_available(matrix):
            blockers.append(
                {
                    "category": "missing_runtime_map_prior",
                    "detail": "map-build prior artifact is required before cleanup consumer gate",
                }
            )
    return blockers


def _run_gate(gate: dict[str, Any]) -> None:
    gate_dir = Path(gate["gate_dir"])
    gate_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = gate_dir / "stdout.log"
    stderr_path = gate_dir / "stderr.log"
    result = subprocess.run(
        [str(item) for item in gate["command"]],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    stdout_path.write_text(result.stdout, encoding="utf-8")
    stderr_path.write_text(result.stderr, encoding="utf-8")
    gate["status"] = "required_ran"
    gate["exit_code"] = result.returncode
    gate["outcome"] = "passed" if result.returncode == 0 else "failed"
    gate["output_artifacts"] = [
        _display_path(stdout_path),
        _display_path(stderr_path),
    ]
    _classify_failed_gate(gate, stderr=result.stderr, stdout=result.stdout)


def _classify_failed_gate(gate: dict[str, Any], *, stderr: str, stdout: str) -> None:
    if gate.get("exit_code") == 0:
        return
    combined = f"{stderr}\n{stdout}".lower()
    if "another interactive codex molmo cleanup session appears to be active" in combined:
        gate["status"] = "required_blocked"
        gate["outcome"] = "blocked"
        gate["blocker_category"] = "live_session_active"
        gate["blockers"] = [
            {
                "category": "live_session_active",
                "detail": "another interactive Codex Molmo cleanup session is active",
            }
        ]


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


def _runtime_prior_available(matrix: dict[str, Any]) -> bool:
    for gate in matrix.get("gates") or []:
        if gate.get("gate_id") != "direct-map-build-world-oracle":
            continue
        if gate.get("status") != "required_ran" or gate.get("outcome") != "passed":
            return False
        run_dir = Path(gate["gate_dir"]) / "run"
        return any(run_dir.glob("**/runtime_metric_map.json"))
    return False


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT))
    except ValueError:
        return str(path)


def _write_outputs(matrix: dict[str, Any], output_dir: Path) -> None:
    json_path = output_dir / "validation_matrix.json"
    md_path = output_dir / "validation_matrix.md"
    html_path = output_dir / "validation_matrix.html"
    json_path.write_text(json.dumps(matrix, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(_render_markdown(matrix), encoding="utf-8")
    html_path.write_text(_render_html(matrix), encoding="utf-8")


def _render_markdown(matrix: dict[str, Any]) -> str:
    lines = [
        "# Agent Validation Matrix",
        "",
        f"- Mode: `{matrix['mode']}`",
        f"- Budget: `{matrix['budget']}`",
        f"- Selected gates: `{matrix['summary']['selected_gate_count']}`",
        "",
        "## Signals",
        "",
    ]
    if matrix.get("signals"):
        for signal in matrix["signals"]:
            files = ", ".join(signal.get("matched_files") or [])
            patterns = ", ".join(signal.get("matched_patterns") or [])
            detail = files or patterns or signal.get("source", "")
            lines.append(f"- `{signal['id']}`: {detail}")
    else:
        lines.append("- none")
    lines.extend(["", "## Gates", ""])
    for gate in matrix["gates"]:
        selected = "selected" if gate.get("selected") else "skipped"
        lines.append(f"### {gate['gate_id']}")
        lines.append("")
        lines.append(f"- Status: `{gate['status']}`")
        lines.append(f"- Selection: `{selected}`")
        if gate.get("blocker_category"):
            lines.append(f"- Blocker: `{gate['blocker_category']}`")
        if gate.get("reason_selected"):
            lines.append(f"- Rationale: {gate['reason_selected']}")
        lines.append(f"- Command: `{gate['command_display']}`")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _render_html(matrix: dict[str, Any]) -> str:
    rows = []
    for gate in matrix["gates"]:
        rows.append(
            "<tr>"
            f"<td>{html.escape(gate['gate_id'])}</td>"
            f"<td>{html.escape(str(gate['status']))}</td>"
            f"<td>{html.escape(str(gate.get('blocker_category') or ''))}</td>"
            f"<td><code>{html.escape(gate['command_display'])}</code></td>"
            "</tr>"
        )
    return (
        '<!doctype html><html><head><meta charset="utf-8">'
        "<title>Agent Validation Matrix</title>"
        "<style>body{font-family:sans-serif;margin:24px;}"
        "table{border-collapse:collapse;width:100%;}"
        "td,th{border:1px solid #ccc;padding:6px;vertical-align:top;}"
        "code{white-space:pre-wrap;}</style></head><body>"
        "<h1>Agent Validation Matrix</h1>"
        f"<p>Mode: <code>{html.escape(matrix['mode'])}</code> "
        f"Budget: <code>{html.escape(matrix['budget'])}</code></p>"
        "<table><thead><tr><th>Gate</th><th>Status</th><th>Blocker</th>"
        "<th>Command</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></body></html>\n"
    )


def _exit_status(matrix: dict[str, Any]) -> int:
    blocked = [
        gate
        for gate in matrix["gates"]
        if gate.get("selected") and gate.get("status") == "required_blocked"
    ]
    failed = [
        gate
        for gate in matrix["gates"]
        if gate.get("selected") and gate.get("status") == "required_ran" and gate.get("exit_code")
    ]
    if failed:
        return 1
    if blocked:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
