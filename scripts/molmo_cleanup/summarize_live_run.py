#!/usr/bin/env python3
"""Summarize a detached Molmo cleanup live-agent run."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

DEFAULT_SEARCH_ROOT = Path("output/molmo/codex-report")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Probe a detached Molmo cleanup live-agent run.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "path",
        nargs="?",
        default="",
        help="run directory, run root, or run_result.json. Defaults to latest Codex report run.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    run_dir = _resolve_run_dir(Path(args.path) if args.path else None)
    if run_dir is None:
        print(f"error: no run found under {DEFAULT_SEARCH_ROOT}", file=sys.stderr)
        return 1
    if not run_dir.exists():
        print(f"error: run path does not exist: {run_dir}", file=sys.stderr)
        return 1

    summary = _summarize(run_dir)
    _print_summary(summary)
    return 0


def _resolve_run_dir(path: Path | None) -> Path | None:
    if path is None:
        candidates = sorted(
            (candidate for candidate in DEFAULT_SEARCH_ROOT.glob("*/seed-*") if candidate.is_dir()),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        return candidates[0] if candidates else None

    path = path.expanduser()
    if path.is_file() and path.name == "run_result.json":
        return path.parent
    if (path / "run_result.json").is_file() or (path / "trace.jsonl").exists():
        return path

    seed_dirs = sorted(
        (candidate for candidate in path.glob("seed-*") if candidate.is_dir()),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    if seed_dirs:
        return seed_dirs[0]
    return path


def _summarize(run_dir: Path) -> dict[str, Any]:
    session = _read_text(run_dir / "tmux_session.txt").strip()
    trace_events = _read_jsonl(run_dir / "trace.jsonl")
    runner_status = _read_json(run_dir / "live_status.json")
    run_result = _read_json(run_dir / "run_result.json")

    return {
        "run_dir": str(run_dir),
        "session": session,
        "tmux_state": _tmux_state(session),
        "runner": _runner_summary(runner_status),
        "artifacts": _artifact_summary(run_dir),
        "trace": _trace_summary(trace_events),
        "result": _result_summary(run_result, run_dir),
        "last_codex_message": _tail_text(run_dir / "codex-last-message.md", max_chars=800),
        "driver_tail": _tail_text(run_dir / "driver.log", max_chars=1200),
    }


def _runner_summary(status: dict[str, Any]) -> dict[str, Any]:
    started = _float_or_none(status.get("started_at_epoch"))
    finished = _float_or_none(status.get("finished_at_epoch"))
    now = time.time()
    elapsed = None
    if started is not None:
        elapsed = round((finished or now) - started, 1)
    return {
        "phase": str(status.get("phase") or "unknown"),
        "exit_status": status.get("exit_status"),
        "started_at": _format_epoch(started),
        "finished_at": _format_epoch(finished),
        "elapsed_s": elapsed,
    }


def _artifact_summary(run_dir: Path) -> dict[str, str]:
    names = (
        "run_live_codex.sh",
        "driver.log",
        "codex-events.jsonl",
        "codex-last-message.md",
        "codex.stderr.log",
        "trace.jsonl",
        "run_result.json",
        "report.html",
    )
    return {name: _artifact_state(run_dir / name) for name in names}


def _trace_summary(events: list[dict[str, Any]]) -> dict[str, Any]:
    responses = [event for event in events if event.get("event") == "response"]
    requests = [event for event in events if event.get("event") == "request"]
    tool_counts: dict[str, int] = {}
    for event in responses:
        tool = str(event.get("tool") or "")
        if tool and not tool.startswith("<"):
            tool_counts[tool] = tool_counts.get(tool, 0) + 1

    last = events[-1] if events else {}
    last_response = responses[-1] if responses else {}
    return {
        "events": len(events),
        "requests": len(requests),
        "responses": len(responses),
        "last_event": _tool_event_label(last),
        "last_response": _tool_event_label(last_response),
        "progress": {
            "observes": tool_counts.get("observe", 0),
            "navigate_to_object": tool_counts.get("navigate_to_object", 0),
            "picks": tool_counts.get("pick", 0),
            "navigate_to_receptacle": tool_counts.get("navigate_to_receptacle", 0),
            "opens": tool_counts.get("open_receptacle", 0),
            "places": tool_counts.get("place", 0),
            "place_inside": tool_counts.get("place_inside", 0),
            "closes": tool_counts.get("close_receptacle", 0),
            "done": tool_counts.get("done", 0),
        },
    }


def _result_summary(run_result: dict[str, Any], run_dir: Path) -> dict[str, Any]:
    if not run_result:
        return {"state": "pending"}
    score = run_result.get("score") if isinstance(run_result.get("score"), dict) else {}
    artifacts = run_result.get("artifacts") if isinstance(run_result.get("artifacts"), dict) else {}
    report = artifacts.get("report") or run_dir / "report.html"
    return {
        "state": "present",
        "cleanup_status": run_result.get("cleanup_status"),
        "completion_status": run_result.get("completion_status"),
        "restored": _score_fraction(score, "restored_count", "total_targets"),
        "sweep": run_result.get("sweep_coverage_rate"),
        "primitive_provenance": run_result.get("primitive_provenance"),
        "policy": run_result.get("policy"),
        "report": str(report),
    }


def _print_summary(summary: dict[str, Any]) -> None:
    print("Molmo cleanup live run")
    print(f"run_dir: {summary['run_dir']}")
    session = summary["session"] or "(none)"
    print(f"tmux: {session} [{summary['tmux_state']}]")

    runner = summary["runner"]
    elapsed = runner["elapsed_s"]
    elapsed_text = _format_duration(elapsed) if elapsed is not None else "unknown"
    print(
        "runner: "
        f"{runner['phase']} exit={runner['exit_status']} "
        f"elapsed={elapsed_text} started={runner['started_at']}"
    )
    if runner["finished_at"] != "unknown":
        print(f"finished: {runner['finished_at']}")

    trace = summary["trace"]
    print(
        "trace: "
        f"{trace['events']} events, {trace['requests']} requests, "
        f"{trace['responses']} responses"
    )
    print(f"last: {trace['last_event']}")
    print(f"last response: {trace['last_response']}")
    progress = trace["progress"]
    print(
        "progress: "
        f"observe={progress['observes']} nav_obj={progress['navigate_to_object']} "
        f"pick={progress['picks']} nav_rec={progress['navigate_to_receptacle']} "
        f"open={progress['opens']} place={progress['places']} "
        f"inside={progress['place_inside']} close={progress['closes']} done={progress['done']}"
    )

    result = summary["result"]
    if result["state"] == "present":
        print(
            "result: "
            f"{result['cleanup_status']} completion={result['completion_status']} "
            f"restored={result['restored']} sweep={result['sweep']} "
            f"policy={result['policy']}"
        )
        print(f"report: {result['report']}")
    else:
        print("result: pending")

    print("artifacts:")
    for name, state in summary["artifacts"].items():
        print(f"  {name}: {state}")

    if summary["last_codex_message"]:
        print("codex last message:")
        print(_indent(summary["last_codex_message"]))
    elif summary["driver_tail"]:
        print("driver log tail:")
        print(_indent(summary["driver_tail"]))


def _tmux_state(session: str) -> str:
    if not session:
        return "unknown"
    if shutil.which("tmux") is None:
        return "tmux-not-found"
    result = subprocess.run(
        ["tmux", "has-session", "-t", session],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return "running" if result.returncode == 0 else "stopped"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    events: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            events.append(item)
    return events


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _tail_text(path: Path, *, max_chars: int) -> str:
    text = _read_text(path)
    if len(text) <= max_chars:
        return text.strip()
    return text[-max_chars:].strip()


def _artifact_state(path: Path) -> str:
    if not path.exists():
        return "missing"
    if path.is_dir():
        return "dir"
    return f"{path.stat().st_size} bytes"


def _tool_event_label(event: dict[str, Any]) -> str:
    if not event:
        return "none"
    tool = event.get("tool", "?")
    kind = event.get("event", "?")
    elapsed = event.get("wallclock_elapsed")
    suffix = ""
    if isinstance(elapsed, int | float):
        suffix = f" at +{_format_duration(float(elapsed))}"
    return f"{tool}:{kind}{suffix}"


def _score_fraction(score: dict[str, Any], numerator: str, denominator: str) -> str:
    top = score.get(numerator)
    bottom = score.get(denominator)
    if top is None or bottom is None:
        return "unknown"
    return f"{top}/{bottom}"


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_epoch(value: float | None) -> str:
    if value is None:
        return "unknown"
    stamp = dt.datetime.fromtimestamp(value).astimezone()
    return stamp.strftime("%Y-%m-%d %H:%M:%S %Z")


def _format_duration(value: float | None) -> str:
    if value is None:
        return "unknown"
    if value < 60:
        return f"{value:.1f}s"
    minutes, seconds = divmod(int(value), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours}h{minutes:02d}m{seconds:02d}s"
    return f"{minutes}m{seconds:02d}s"


def _indent(text: str) -> str:
    return "\n".join(f"  {line}" for line in text.splitlines())


if __name__ == "__main__":
    raise SystemExit(main())
