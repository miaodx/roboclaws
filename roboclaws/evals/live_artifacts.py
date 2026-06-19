"""Artifact source helpers for live eval product runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

LIVE_SURFACE_DISCOVERY_MTIME_TOLERANCE_S = 1.0


def discover_live_surface_run_dir(
    kwargs: dict[str, Any],
    *,
    output_dir: Path,
    fallback_run_dir: Path,
    stdout: str = "",
    started_wall_time_s: float | None = None,
) -> Path:
    """Return the actual artifact directory created by the public live route."""

    seed_leaf = f"seed-{int(kwargs['seed'])}"
    priority_candidates = _unique_live_surface_candidates(
        [fallback_run_dir, _live_surface_run_dir_from_stdout(stdout)]
    )
    for candidate in priority_candidates:
        if _live_surface_run_dir_has_stale_evidence(
            candidate,
            started_wall_time_s=started_wall_time_s,
        ):
            _raise_stale_live_surface_run_dir(candidate, started_wall_time_s=started_wall_time_s)
        if _live_surface_run_dir_has_current_evidence(
            candidate,
            started_wall_time_s=started_wall_time_s,
        ):
            return candidate
    discovered = _discovered_live_surface_run_dirs(
        output_dir,
        seed_leaf=seed_leaf,
        exclude=priority_candidates,
    )
    current_discovered = [
        candidate
        for candidate in discovered
        if _live_surface_run_dir_has_current_evidence(
            candidate,
            started_wall_time_s=started_wall_time_s,
        )
    ]
    if len(current_discovered) == 1:
        return current_discovered[0]
    if len(current_discovered) > 1:
        _raise_ambiguous_live_surface_run_dirs(
            current_discovered,
            output_dir=output_dir,
            seed_leaf=seed_leaf,
        )
    stale_discovered = [
        candidate
        for candidate in discovered
        if _live_surface_run_dir_has_stale_evidence(
            candidate,
            started_wall_time_s=started_wall_time_s,
        )
    ]
    if stale_discovered:
        _raise_stale_live_surface_run_dirs(stale_discovered, started_wall_time_s)
    for candidate in priority_candidates:
        if candidate.exists():
            return candidate
    current_existing = [
        candidate
        for candidate in discovered
        if candidate.exists()
        and _live_surface_run_dir_is_current(
            candidate,
            started_wall_time_s=started_wall_time_s,
        )
    ]
    if len(current_existing) == 1:
        return current_existing[0]
    if len(current_existing) > 1:
        _raise_ambiguous_live_surface_run_dirs(
            current_existing,
            output_dir=output_dir,
            seed_leaf=seed_leaf,
        )
    return fallback_run_dir


def load_live_eval_json(path: Path) -> dict[str, Any]:
    """Load an optional live eval JSON sidecar, failing aloud when present but corrupt."""

    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid live eval JSON artifact {path}: {exc.msg}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"live eval JSON artifact {path} must contain an object")
    return payload


def _unique_live_surface_candidates(candidates: list[Path | None]) -> list[Path]:
    result: list[Path] = []
    seen: set[Path] = set()
    for candidate in candidates:
        if candidate is None:
            continue
        key = candidate.resolve()
        if key in seen:
            continue
        seen.add(key)
        result.append(candidate)
    return result


def _discovered_live_surface_run_dirs(
    output_dir: Path,
    *,
    seed_leaf: str,
    exclude: list[Path],
) -> list[Path]:
    excluded = {path.resolve() for path in exclude}
    candidates = [
        candidate
        for pattern in (f"*/{seed_leaf}", seed_leaf)
        for candidate in output_dir.glob(pattern)
        if candidate.is_dir() and candidate.resolve() not in excluded
    ]
    return sorted(candidates, key=lambda item: item.stat().st_mtime, reverse=True)


def _raise_ambiguous_live_surface_run_dirs(
    candidates: list[Path],
    *,
    output_dir: Path,
    seed_leaf: str,
) -> None:
    paths = ", ".join(str(path) for path in candidates)
    raise RuntimeError(
        f"ambiguous live surface run artifacts for {seed_leaf} under {output_dir}: {paths}"
    )


def _raise_stale_live_surface_run_dir(path: Path, *, started_wall_time_s: float) -> None:
    _raise_stale_live_surface_run_dirs([path], started_wall_time_s)


def _raise_stale_live_surface_run_dirs(
    paths: list[Path],
    started_wall_time_s: float | None,
) -> None:
    joined = ", ".join(str(path) for path in paths)
    start = "unknown" if started_wall_time_s is None else f"{started_wall_time_s:.3f}"
    raise RuntimeError(
        f"stale live surface run artifacts at {joined}: evidence predates live run start {start}"
    )


def _live_surface_run_dir_has_evidence(path: Path) -> bool:
    return (
        (path / "run_result.json").is_file()
        or (path / "live_status.json").is_file()
        or (path / "trace.jsonl").is_file()
    )


def _live_surface_run_dir_has_current_evidence(
    path: Path,
    *,
    started_wall_time_s: float | None,
) -> bool:
    return any(
        evidence.is_file()
        and _live_surface_run_dir_is_current(evidence, started_wall_time_s=started_wall_time_s)
        for evidence in _live_surface_evidence_paths(path)
    ) and not _live_surface_run_dir_has_stale_evidence(
        path,
        started_wall_time_s=started_wall_time_s,
    )


def _live_surface_run_dir_has_stale_evidence(
    path: Path,
    *,
    started_wall_time_s: float | None,
) -> bool:
    if started_wall_time_s is None:
        return False
    return any(
        evidence.is_file()
        and not _live_surface_run_dir_is_current(
            evidence,
            started_wall_time_s=started_wall_time_s,
        )
        for evidence in _live_surface_evidence_paths(path)
    )


def _live_surface_evidence_paths(path: Path) -> tuple[Path, ...]:
    return (
        path / "run_result.json",
        path / "live_status.json",
        path / "trace.jsonl",
    )


def _live_surface_run_dir_is_current(
    path: Path,
    *,
    started_wall_time_s: float | None,
) -> bool:
    if started_wall_time_s is None:
        return True
    try:
        return (
            path.stat().st_mtime >= started_wall_time_s - LIVE_SURFACE_DISCOVERY_MTIME_TOLERANCE_S
        )
    except FileNotFoundError:
        return False


def _live_surface_run_dir_from_stdout(stdout: str) -> Path | None:
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line.startswith("Artifacts"):
            continue
        _, _, value = line.partition(":")
        path = value.strip()
        if path:
            return Path(path)
    return None
