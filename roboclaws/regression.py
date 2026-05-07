from __future__ import annotations

import datetime as dt
import importlib
import json
import random
import re
import subprocess
import sys
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLES_DIR = REPO_ROOT / "examples"
TEST_FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"
SCHEMA_VERSION = 1
STABLE_PAIRING_KEYS: tuple[str, ...] = (
    "suite",
    "backend",
    "scene",
    "seed",
    "game",
    "model",
    "agents",
    "variant",
)
COMMON_ROW_KEYS: tuple[str, ...] = (
    *STABLE_PAIRING_KEYS,
    "label",
    "status",
    "artifact_dir",
    "run_id",
    "captured_at",
    "commit_sha",
    "schema_version",
)
CAPTURE_LABEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
FAILED_TERMINATIONS = {"provider_error", "provider_unstable"}

if str(EXAMPLES_DIR) not in sys.path:
    sys.path.insert(0, str(EXAMPLES_DIR))


class RegressionError(RuntimeError):
    """Base exception for refactor-regression capture and analysis helpers."""


class UnknownRegressionSuiteError(RegressionError):
    """Raised when a suite name is not present in the registry."""


class LocalOnlySuiteError(RegressionError):
    """Raised when a local-only suite is invoked without an explicit override."""


@dataclass(frozen=True)
class CaptureRequest:
    """Normalized capture inputs for one suite/scene/seed coordinate."""

    label: str
    scene: str
    seed: int
    agents: int
    steps: int
    model: str
    allow_local: bool = False


CaptureFn = Callable[[CaptureRequest, Path], dict[str, Any]]


@dataclass(frozen=True)
class RegressionSuite:
    """One registered regression suite backed by a shipped runner."""

    name: str
    backend: str
    game: str
    capture: CaptureFn
    default_agents: int = 1
    default_variant: str | None = None
    local_dev_only: bool = False

    def capture_ok_row(
        self,
        *,
        request: CaptureRequest,
        artifact_dir: Path,
        run_id: str,
        elapsed_seconds: float,
    ) -> dict[str, Any]:
        """Run this suite coordinate and return its normalized success row."""
        if self.local_dev_only and not request.allow_local:
            raise LocalOnlySuiteError(
                f"Suite {self.name!r} is local-dev only. Re-run with --allow-local "
                "from a workstation session that satisfies AGENTS.md §1 and §7."
            )
        artifact_dir.mkdir(parents=True, exist_ok=True)
        seed_rng(request.seed)
        metrics = dict(self.capture(request, artifact_dir))
        variant = metrics.pop("variant", self.default_variant)
        row_model = metrics.pop("model", request.model)
        metrics.setdefault("wallclock_seconds", round(elapsed_seconds, 3))
        return normalize_capture_row(
            suite=self,
            request=request,
            artifact_dir=artifact_dir,
            run_id=run_id,
            status="ok",
            variant=variant,
            model=str(row_model) if row_model is not None else request.model,
            extra=metrics,
        )

    def capture_error_row(
        self,
        *,
        request: CaptureRequest,
        artifact_dir: Path,
        run_id: str,
        exc: Exception,
        elapsed_seconds: float,
    ) -> dict[str, Any]:
        """Return the normalized error row for a failed suite coordinate."""
        return normalize_capture_row(
            suite=self,
            request=request,
            artifact_dir=artifact_dir,
            run_id=run_id,
            status="error",
            variant=self.default_variant,
            extra={
                "error_kind": exc.__class__.__name__,
                "error": str(exc),
                "wallclock_seconds": round(elapsed_seconds, 3),
            },
        )


SUITE_REGISTRY: dict[str, RegressionSuite] = {}
_COMMIT_SHA_CACHE: str | None = None


def register_suite(suite: RegressionSuite) -> RegressionSuite:
    """Register *suite* by name."""
    SUITE_REGISTRY[suite.name] = suite
    return suite


def get_suite(name: str) -> RegressionSuite:
    """Return a registered suite or raise a helpful error."""
    try:
        return SUITE_REGISTRY[name]
    except KeyError as exc:
        available = ", ".join(sorted(SUITE_REGISTRY))
        raise UnknownRegressionSuiteError(
            f"Unknown regression suite {name!r}. Choose from: {available}"
        ) from exc


def parse_csv(value: str) -> list[str]:
    """Split a comma-separated CLI value into non-empty trimmed strings."""
    return [part.strip() for part in value.split(",") if part.strip()]


def parse_int_csv(value: str) -> list[int]:
    """Split a comma-separated CLI value into integers."""
    return [int(part.strip()) for part in value.split(",") if part.strip()]


def validate_capture_label(label: str) -> str:
    """Reject empty or obviously mutable capture labels."""
    cleaned = label.strip()
    if not cleaned:
        raise ValueError("capture-set label must not be empty")
    if cleaned in {"baseline", "candidate"}:
        raise ValueError(
            "capture-set label must be an immutable snapshot name such as "
            "'baseline-2026-04-23' or 'candidate-dongxu-dev-0423'"
        )
    if not CAPTURE_LABEL_RE.match(cleaned):
        raise ValueError(
            "capture-set label must match [A-Za-z0-9][A-Za-z0-9._-]* (example: baseline-2026-04-23)"
        )
    return cleaned


def build_run_id() -> str:
    """Return a unique capture id suitable for artifact paths."""
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%f")
    return f"{stamp}-{uuid.uuid4().hex[:8]}"


def build_artifact_dir(
    output_root: Path,
    *,
    suite_name: str,
    scene: str,
    seed: int,
    run_id: str,
) -> Path:
    """Return the per-run artifact directory for one stable coordinate tuple."""
    return output_root / suite_name / f"{scene}-seed{seed}" / run_id


def append_jsonl(path: Path, row: dict[str, Any]) -> None:
    """Append one JSON row to *path*."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(_jsonable(row), sort_keys=True) + "\n")


def seed_rng(seed: int) -> None:
    """Seed the repo's common RNGs the same way the view experiment does."""
    random.seed(seed)
    np.random.seed(seed)


def current_commit_sha() -> str:
    """Return the current HEAD SHA, cached for the current process."""
    global _COMMIT_SHA_CACHE
    if _COMMIT_SHA_CACHE is not None:
        return _COMMIT_SHA_CACHE
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception:  # noqa: BLE001 - capture rows should still be writable off-git
        _COMMIT_SHA_CACHE = "unknown"
    else:
        _COMMIT_SHA_CACHE = result.stdout.strip() or "unknown"
    return _COMMIT_SHA_CACHE


def stable_pairing_coordinates(
    *,
    suite: RegressionSuite,
    request: CaptureRequest,
    variant: str | None,
    model: str | None = None,
) -> dict[str, Any]:
    """Return the phase-04 stable pairing tuple for one capture row."""
    return {
        "suite": suite.name,
        "backend": suite.backend,
        "scene": request.scene,
        "seed": int(request.seed),
        "game": suite.game,
        "model": model if model is not None else request.model,
        "agents": int(request.agents),
        "variant": variant,
    }


def normalize_capture_row(
    *,
    suite: RegressionSuite,
    request: CaptureRequest,
    artifact_dir: Path,
    run_id: str,
    status: str,
    variant: str | None,
    model: str | None = None,
    captured_at: str | None = None,
    commit_sha: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a JSON-serializable capture row with the required common fields."""
    row = stable_pairing_coordinates(
        suite=suite,
        request=request,
        variant=variant,
        model=model,
    )
    row.update(
        {
            "label": request.label,
            "status": status,
            "artifact_dir": str(artifact_dir),
            "run_id": run_id,
            "captured_at": captured_at
            or dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
            "commit_sha": commit_sha or current_commit_sha(),
            "schema_version": SCHEMA_VERSION,
        }
    )
    if extra:
        row.update(_jsonable(extra))
    row.setdefault("variant", None)
    return row


def load_replay_summary(run_dir: Path) -> dict[str, Any]:
    """Return the replay summary dict or an empty dict."""
    replay = load_json(run_dir / "replay.json")
    summary = replay.get("summary", {})
    return summary if isinstance(summary, dict) else {}


def load_replay_steps(run_dir: Path) -> list[dict[str, Any]]:
    """Return the replay step list or an empty list."""
    replay = load_json(run_dir / "replay.json")
    steps = replay.get("steps", [])
    return steps if isinstance(steps, list) else []


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON object from *path* when present, else return {}."""
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def load_replay_summary_reference() -> dict[str, Any]:
    """Load the replay-summary contract fixture."""
    return load_json(TEST_FIXTURES_DIR / "replay_summary_reference.json")


def load_row_reference() -> dict[str, Any]:
    """Load the common row contract fixture."""
    return load_json(TEST_FIXTURES_DIR / "refactor_regression_row_reference.json")


def load_trace_schema_reference() -> dict[str, Any]:
    """Load the additive-vs-exact OpenClaw trace contract fixture."""
    return load_json(TEST_FIXTURES_DIR / "trace_schema_reference.json")


def latest_step_game_state(run_dir: Path) -> dict[str, Any]:
    """Return the final replay step's game_state dict when present."""
    steps = load_replay_steps(run_dir)
    if not steps:
        return {}
    game_state = steps[-1].get("game_state", {})
    return game_state if isinstance(game_state, dict) else {}


def _jsonable(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.ndarray):
        return value.tolist()
    return value


def _metric_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _metric_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _ensure_non_provider_failure(result: dict[str, Any]) -> None:
    termination_reason = str(result.get("termination_reason", "unknown"))
    if termination_reason in FAILED_TERMINATIONS:
        raise RegressionError(f"runner terminated with {termination_reason}")


def _load_example_attr(module_name: str, attr_name: str) -> Any:
    module = importlib.import_module(module_name)
    return getattr(module, attr_name)


def _run_exploration(**kwargs: Any) -> dict[str, Any]:
    return _load_example_attr("single_agent_explore", "run_exploration")(**kwargs)


def _run_territory_game(**kwargs: Any) -> dict[str, Any]:
    return _load_example_attr("territory_game", "run_territory_game")(**kwargs)


def _run_coverage_game(**kwargs: Any) -> dict[str, Any]:
    return _load_example_attr("coverage_game", "run_coverage_game")(**kwargs)


def _run_openclaw_demo(**kwargs: Any) -> dict[str, Any]:
    return _load_example_attr("openclaw_demo", "run_openclaw_demo")(**kwargs)


def _run_autonomous_navigation(**kwargs: Any) -> dict[str, Any]:
    return _load_example_attr("openclaw_nav_autonomous", "run_autonomous_navigation")(**kwargs)


def _capture_explore_vlm(request: CaptureRequest, artifact_dir: Path) -> dict[str, Any]:
    result = _run_exploration(
        scene=request.scene,
        steps=request.steps,
        model=request.model,
        output_dir=str(artifact_dir),
        provider_seed=request.seed,
    )
    _ensure_non_provider_failure(result)
    summary = load_replay_summary(artifact_dir)
    return {
        "cells_visited": _metric_int(result.get("cells_visited")),
        "termination_reason": str(result.get("termination_reason", "unknown")),
        "usd": _metric_float(result.get("vlm_cost_usd", summary.get("vlm_cost_usd"))),
        "provider_status": result.get("provider_status", {}),
        "total_steps": _metric_int(result.get("total_steps", summary.get("total_steps"))),
        "wallclock_seconds": _metric_float(summary.get("game_duration_seconds")),
    }


def _capture_territory_vlm(request: CaptureRequest, artifact_dir: Path) -> dict[str, Any]:
    result = _run_territory_game(
        scene=request.scene,
        agent_count=request.agents,
        steps=request.steps,
        model=request.model,
        output_dir=str(artifact_dir),
        backend="vlm",
        provider_seed=request.seed,
    )
    _ensure_non_provider_failure(result)
    summary = load_replay_summary(artifact_dir)
    claimed = result.get("cells_claimed", {})
    if isinstance(claimed, dict):
        cells_claimed_total = sum(_metric_int(value) for value in claimed.values())
    else:
        cells_claimed_total = 0
    return {
        "cells_claimed_total": cells_claimed_total,
        "blocking_events": _metric_int(result.get("blocking_events")),
        "termination_reason": str(result.get("termination_reason", "unknown")),
        "usd": _metric_float(result.get("vlm_cost_usd", summary.get("vlm_cost_usd"))),
        "provider_status": result.get("provider_status", {}),
        "total_steps": _metric_int(result.get("total_steps", summary.get("total_steps"))),
        "wallclock_seconds": _metric_float(summary.get("game_duration_seconds")),
        "variant": "map-v2+chase",
    }


def _capture_coverage_vlm(request: CaptureRequest, artifact_dir: Path) -> dict[str, Any]:
    result = _run_coverage_game(
        scene=request.scene,
        agent_count=request.agents,
        steps=request.steps,
        model=request.model,
        output_dir=str(artifact_dir),
        backend="vlm",
        provider_seed=request.seed,
    )
    _ensure_non_provider_failure(result)
    summary = load_replay_summary(artifact_dir)
    return {
        "coverage_fraction": _metric_float(result.get("coverage_pct")) / 100.0,
        "cells_covered": _metric_int(result.get("cells_covered")),
        "work_balance": _metric_float(result.get("work_balance")),
        "termination_reason": str(result.get("termination_reason", "unknown")),
        "usd": _metric_float(result.get("vlm_cost_usd", summary.get("vlm_cost_usd"))),
        "provider_status": result.get("provider_status", {}),
        "total_steps": _metric_int(result.get("total_steps", summary.get("total_steps"))),
        "wallclock_seconds": _metric_float(summary.get("game_duration_seconds")),
        "variant": "map-v2+chase",
    }


def _capture_openclaw_demo(request: CaptureRequest, artifact_dir: Path) -> dict[str, Any]:
    result = _run_openclaw_demo(
        scene=request.scene,
        agent_count=request.agents,
        steps=request.steps,
        output_dir=str(artifact_dir),
    )
    _ensure_non_provider_failure(result)
    summary = load_replay_summary(artifact_dir)
    final_state = latest_step_game_state(artifact_dir)
    provider_status = result.get("provider_status", {})
    model_name = None
    if isinstance(provider_status, dict):
        raw_model = provider_status.get("model")
        model_name = str(raw_model) if raw_model else None
    return {
        "visited_cells": _metric_int(final_state.get("visited_cells")),
        "steps_executed": _metric_int(result.get("steps_executed")),
        "termination_reason": str(result.get("termination_reason", "unknown")),
        "usd": _metric_float(summary.get("vlm_cost_usd")),
        "provider_status": provider_status,
        "total_steps": _metric_int(summary.get("total_steps", result.get("steps_executed"))),
        "wallclock_seconds": _metric_float(summary.get("game_duration_seconds")),
        "variant": "map-v2+chase",
        "model": model_name,
    }


def _capture_territory_openclaw(request: CaptureRequest, artifact_dir: Path) -> dict[str, Any]:
    result = _run_territory_game(
        scene=request.scene,
        agent_count=request.agents,
        steps=request.steps,
        model=request.model,
        output_dir=str(artifact_dir),
        backend="openclaw",
    )
    _ensure_non_provider_failure(result)
    summary = load_replay_summary(artifact_dir)
    claimed = result.get("cells_claimed", {})
    if isinstance(claimed, dict):
        cells_claimed_total = sum(_metric_int(value) for value in claimed.values())
    else:
        cells_claimed_total = 0
    return {
        "cells_claimed_total": cells_claimed_total,
        "blocking_events": _metric_int(result.get("blocking_events")),
        "termination_reason": str(result.get("termination_reason", "unknown")),
        "usd": _metric_float(summary.get("vlm_cost_usd")),
        "provider_status": result.get("provider_status", {}),
        "total_steps": _metric_int(result.get("total_steps", summary.get("total_steps"))),
        "wallclock_seconds": _metric_float(summary.get("game_duration_seconds")),
        "variant": "map-v2+chase",
    }


def _capture_coverage_openclaw(request: CaptureRequest, artifact_dir: Path) -> dict[str, Any]:
    result = _run_coverage_game(
        scene=request.scene,
        agent_count=request.agents,
        steps=request.steps,
        model=request.model,
        output_dir=str(artifact_dir),
        backend="openclaw",
    )
    _ensure_non_provider_failure(result)
    summary = load_replay_summary(artifact_dir)
    return {
        "coverage_fraction": _metric_float(result.get("coverage_pct")) / 100.0,
        "cells_covered": _metric_int(result.get("cells_covered")),
        "work_balance": _metric_float(result.get("work_balance")),
        "termination_reason": str(result.get("termination_reason", "unknown")),
        "usd": _metric_float(summary.get("vlm_cost_usd")),
        "provider_status": result.get("provider_status", {}),
        "total_steps": _metric_int(result.get("total_steps", summary.get("total_steps"))),
        "wallclock_seconds": _metric_float(summary.get("game_duration_seconds")),
        "variant": "map-v2+chase",
    }


def _autonomous_wall_budget(steps: int) -> float:
    return max(300.0, float(steps) * 6.0)


def _capture_openclaw_autonomous(request: CaptureRequest, artifact_dir: Path) -> dict[str, Any]:
    _run_autonomous_navigation(
        scene=request.scene,
        max_moves=request.steps,
        wall_budget=_autonomous_wall_budget(request.steps),
        output_dir=artifact_dir,
        skip_bootstrap=False,
    )
    run_result = load_json(artifact_dir / "run_result.json")
    summary = load_json(artifact_dir / "summary.json")
    terminated_by = str(run_result.get("terminated_by", "unknown"))
    tool_calls = summary.get("tool_calls_by_type", {})
    observe_calls = _metric_int(tool_calls.get("observe")) if isinstance(tool_calls, dict) else 0
    if terminated_by == "error":
        final_message = str(run_result.get("final_message", "unknown error"))
        raise RegressionError(f"autonomous run terminated_by=error: {final_message}")
    if observe_calls == 0:
        raise RegressionError("autonomous run produced zero observe calls")
    view_variant = str(summary.get("view_variant", run_result.get("view_variant", "baseline")))
    return {
        "terminated_by": terminated_by,
        "transcript_source": str(
            summary.get("transcript_source", run_result.get("transcript_source", "none"))
        ),
        "tool_calls_by_type": tool_calls if isinstance(tool_calls, dict) else {},
        "frames_unseen_by_agent": _metric_int(summary.get("frames_unseen_by_agent")),
        "decision_modes": summary.get("decision_modes", {}),
        "wallclock_seconds": _metric_float(
            summary.get("wallclock_seconds", run_result.get("wallclock_s"))
        ),
        "view_variant": view_variant,
        "variant": view_variant,
        "model": str(run_result.get("model") or request.model),
    }


def _register_builtin_suites() -> None:
    if SUITE_REGISTRY:
        return
    register_suite(
        RegressionSuite(
            name="explore-vlm",
            backend="vlm",
            game="explore",
            capture=_capture_explore_vlm,
            default_agents=1,
        )
    )
    register_suite(
        RegressionSuite(
            name="territory-vlm",
            backend="vlm",
            game="territory",
            capture=_capture_territory_vlm,
            default_agents=2,
            default_variant="map-v2+chase",
        )
    )
    register_suite(
        RegressionSuite(
            name="coverage-vlm",
            backend="vlm",
            game="coverage",
            capture=_capture_coverage_vlm,
            default_agents=2,
            default_variant="map-v2+chase",
        )
    )
    register_suite(
        RegressionSuite(
            name="openclaw-demo",
            backend="openclaw",
            game="navigation",
            capture=_capture_openclaw_demo,
            default_agents=2,
            default_variant="map-v2+chase",
            local_dev_only=True,
        )
    )
    register_suite(
        RegressionSuite(
            name="territory-openclaw",
            backend="openclaw",
            game="territory",
            capture=_capture_territory_openclaw,
            default_agents=2,
            default_variant="map-v2+chase",
            local_dev_only=True,
        )
    )
    register_suite(
        RegressionSuite(
            name="coverage-openclaw",
            backend="openclaw",
            game="coverage",
            capture=_capture_coverage_openclaw,
            default_agents=2,
            default_variant="map-v2+chase",
            local_dev_only=True,
        )
    )
    register_suite(
        RegressionSuite(
            name="openclaw-autonomous",
            backend="openclaw",
            game="autonomous-navigation",
            capture=_capture_openclaw_autonomous,
            default_agents=1,
            default_variant="map-v2+chase",
            local_dev_only=True,
        )
    )


_register_builtin_suites()
