from __future__ import annotations

import datetime as dt
import html
import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

MANIFEST_SCHEMA = "molmo_live_ci_report_manifest_v1"
STATUS_SCHEMA = "molmo_live_ci_entry_status_v1"


@dataclass(frozen=True)
class MolmoLiveModelEntry:
    name: str
    label: str
    provider_profile: str
    model: str
    secret_env: str


MODEL_ENTRIES: tuple[MolmoLiveModelEntry, ...] = (
    MolmoLiveModelEntry(
        name="kimi-k2.6",
        label="Kimi K2.6",
        provider_profile="kimi-anthropic",
        model="kimi-k2.6",
        secret_env="KIMI_API_KEY",
    ),
    MolmoLiveModelEntry(
        name="mimo-v2.5-pro",
        label="MiMo v2.5 Pro",
        provider_profile="mimo-anthropic",
        model="mimo-v2.5-pro",
        secret_env="MIMO_TP_KEY",
    ),
    MolmoLiveModelEntry(
        name="mimo-v2-omni",
        label="MiMo v2 Omni",
        provider_profile="mimo-anthropic",
        model="mimo-v2-omni",
        secret_env="MIMO_TP_KEY",
    ),
)


def entry_names() -> list[str]:
    return [entry.name for entry in MODEL_ENTRIES]


def entry_by_name(name: str) -> MolmoLiveModelEntry:
    for entry in MODEL_ENTRIES:
        if entry.name == name:
            return entry
    expected = ", ".join(entry_names())
    raise KeyError(f"unknown Molmo live model entry {name!r}; expected one of: {expected}")


def utc_timestamp() -> str:
    return dt.datetime.now(dt.UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def base_status(
    entry: MolmoLiveModelEntry,
    *,
    seed: int,
    generated_mess_count: int,
    profile: str,
    task: str,
) -> dict[str, Any]:
    return {
        "schema": STATUS_SCHEMA,
        "entry": entry.name,
        "label": entry.label,
        "provider_profile": entry.provider_profile,
        "model": entry.model,
        "secret_env": entry.secret_env,
        "driver": "claude",
        "profile": profile,
        "seed": seed,
        "generated_mess_count": generated_mess_count,
        "task": task,
        "created_at": utc_timestamp(),
        "status": "pending",
        "reason": "",
        "report_path": "",
        "run_dir": "",
        "diagnostic_path": "",
        "diagnostic_dir": "",
    }


def write_status(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def read_status(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != STATUS_SCHEMA:
        raise ValueError(f"{path} is not a {STATUS_SCHEMA} document")
    return payload


def status_path_for_entry(root: Path, entry_name: str) -> Path:
    return root / entry_name / "status.json"


def latest_seed_run_dir(entry_output_dir: Path, *, seed: int) -> Path | None:
    candidates = sorted(
        path
        for path in entry_output_dir.glob(f"*/seed-{seed}")
        if (path / "run_result.json").is_file()
    )
    return candidates[-1] if candidates else None


def latest_seed_artifact_dir(entry_output_dir: Path, *, seed: int) -> Path | None:
    candidates = sorted(path for path in entry_output_dir.glob(f"*/seed-{seed}") if path.is_dir())
    return candidates[-1] if candidates else None


def publish_seed_run(
    *,
    source_seed_dir: Path,
    publish_root: Path,
    entry_name: str,
    seed: int,
) -> Path:
    destination = publish_root / entry_name / f"seed-{seed}"
    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_seed_dir, destination)
    return destination


def publish_diagnostic_seed_run(
    *,
    source_seed_dir: Path,
    publish_root: Path,
    entry_name: str,
    seed: int,
) -> Path:
    destination = publish_root / entry_name / "diagnostics" / f"seed-{seed}"
    if destination.exists():
        shutil.rmtree(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source_seed_dir, destination)
    _write_diagnostic_index(destination)
    return destination


def report_path_for_entry(entry_name: str, *, seed: int) -> str:
    return f"{entry_name}/seed-{seed}/report.html"


def diagnostic_path_for_entry(entry_name: str, *, seed: int) -> str:
    return f"{entry_name}/diagnostics/seed-{seed}/diagnostics.html"


def _write_diagnostic_index(seed_dir: Path) -> Path:
    common_files = (
        "live_status.json",
        "claude-command.txt",
        "claude-events.jsonl",
        "claude.stderr.log",
        "checker.log",
        "server.pid",
        "trace.jsonl",
        "run_result.json",
        "report.html",
        "agent_view.json",
        "private_evaluation.json",
        "advisory_evaluation.json",
        "planner_proof_requests.json",
    )
    links = []
    for relative in common_files:
        path = seed_dir / relative
        if not path.is_file():
            continue
        size = path.stat().st_size
        links.append(
            "<li>"
            f'<a href="{html.escape(relative, quote=True)}">{html.escape(relative)}</a>'
            f" <span>{size} bytes</span>"
            "</li>"
        )
    if not links:
        links.append("<li>No common diagnostic files were found in this partial run.</li>")
    body = "\n".join(links)
    path = seed_dir / "diagnostics.html"
    path.write_text(
        "\n".join(
            [
                "<!doctype html>",
                '<meta charset="utf-8">',
                "<title>Molmo Live Cleanup Diagnostics</title>",
                "<h1>Molmo Live Cleanup Diagnostics</h1>",
                "<p>This directory is a partial seed run captured after a live CI failure.</p>",
                f"<ul>{body}</ul>",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def collect_entry_statuses(root: Path) -> list[dict[str, Any]]:
    statuses: list[dict[str, Any]] = []
    for entry in MODEL_ENTRIES:
        path = status_path_for_entry(root, entry.name)
        if path.is_file():
            statuses.append(read_status(path))
    return statuses


def write_manifest(root: Path, statuses: list[dict[str, Any]] | None = None) -> Path:
    if statuses is None:
        statuses = collect_entry_statuses(root)
    payload = {
        "schema": MANIFEST_SCHEMA,
        "generated_at": utc_timestamp(),
        "entries": statuses,
        "known_entries": [asdict(entry) for entry in MODEL_ENTRIES],
    }
    path = root / "live-report-manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path
