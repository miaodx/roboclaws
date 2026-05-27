from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from roboclaws.molmo_cleanup.subprocess_backend import (
    _parse_last_json_object,
    _scenario_from_worker_payload,
)

ISAACLAB_SUBPROCESS_BACKEND = "isaaclab_subprocess"
ISAAC_SEMANTIC_POSE_PROVENANCE = "isaac_semantic_pose"
ISAAC_SEMANTIC_POSE_STATE_SCHEMA = "isaac_semantic_pose_state_v1"
ISAAC_SEMANTIC_POSE_EVENT_SCHEMA = "isaac_semantic_pose_event_v1"
ISAAC_SEMANTIC_POSE_STATE_SOURCE = "backend_json_state"
ISAAC_SCENE_INDEX_ARTIFACT_SCHEMA = "isaac_scene_index_artifact_v1"
ISAACLAB_ROBOT_VIEW_VARIANT = "isaaclab-fpv-map-chase-verify"
DEFAULT_ISAACLAB_PYTHON = Path(__file__).resolve().parents[2] / ".venv-isaaclab" / "bin" / "python"
DEFAULT_ISAAC_WORKER_TIMEOUT_S = 120.0
ISAAC_WORKER_TIMEOUTS_S = {
    "init": 300.0,
    "snapshot": 120.0,
    "robot_views": 120.0,
}
ISAAC_WORKER_SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "isaac_lab_cleanup"
    / "isaac_lab_backend_worker.py"
)


class IsaacLabSubprocessBackend:
    """Subprocess boundary for the heavy Isaac Sim / Isaac Lab runtime.

    The wrapper deliberately mirrors ``MolmoSpacesSubprocessBackend`` without
    importing Isaac packages in the normal Roboclaws process. CI tests may opt
    into the worker's explicit fake protocol mode; real local runs should use a
    `.venv-isaaclab/` Python with Isaac installed.
    """

    def __init__(
        self,
        *,
        run_dir: Path,
        seed: int = 7,
        python_executable: Path | None = None,
        scene_source: str = "procthor-10k-val",
        scene_index: int = 0,
        include_robot: bool = False,
        robot_name: str = "simple_camera_rig",
        generated_mess_count: int = 1,
        map_bundle_dir: Path | None = None,
        scene_usd_path: Path | None = None,
        runtime_mode: str | None = None,
    ) -> None:
        self.run_dir = run_dir
        self.state_path = run_dir / "isaac_lab_backend_state.json"
        self.python_executable = python_executable or Path(
            os.environ.get("ROBOCLAWS_ISAACLAB_PYTHON", str(DEFAULT_ISAACLAB_PYTHON))
        )
        self.runtime_mode = runtime_mode or os.environ.get(
            "ROBOCLAWS_ISAACLAB_RUNTIME_MODE", "real"
        )
        self.snapshot_artifacts: list[dict[str, Any]] = []
        init_args = [
            "--run-dir",
            str(run_dir),
            "--seed",
            str(seed),
            "--scene-source",
            scene_source,
            "--scene-index",
            str(scene_index),
            "--generated-mess-count",
            str(generated_mess_count),
            "--runtime-mode",
            self.runtime_mode,
        ]
        if include_robot:
            init_args.extend(["--include-robot", "--robot-name", robot_name])
        if map_bundle_dir is not None:
            init_args.extend(["--map-bundle-dir", str(map_bundle_dir)])
        if scene_usd_path is not None:
            init_args.extend(["--scene-usd-path", str(scene_usd_path)])
        result = self._run_worker("init", *init_args)
        self.backend = ISAACLAB_SUBPROCESS_BACKEND
        self.scenario = _scenario_from_worker_payload(
            result["scenario"],
            result["private_manifest"],
        )
        self.runtime = result["runtime"]
        self.scene_usd = result.get("scene_usd", "")
        self.scene_index = int(result.get("scene_index", scene_index))
        self.object_index = result.get("object_index", {})
        self.receptacle_index = result.get("receptacle_index", {})
        self.segmentation = result.get("segmentation", {})
        self.scene_load = result.get("scene_load", {})
        self.scene_index_diagnostics = result.get("scene_index_diagnostics", {})
        self.scene_binding_diagnostics = result.get("scene_binding_diagnostics", {})
        self.mapping_gaps = result.get("mapping_gaps", [])
        self.requested_generated_mess_count = int(
            result.get("requested_generated_mess_count", generated_mess_count)
        )
        self.generated_mess_count = int(result.get("generated_mess_count", 0))
        self.robot = result.get("robot")

    @property
    def held_object_id(self) -> str | None:
        state = self._read_state()
        value = state.get("held_object_id")
        return str(value) if value is not None else None

    def object_locations(self) -> dict[str, str]:
        result = self._run_worker("locations")
        return {str(key): str(value) for key, value in result["final_locations"].items()}

    @property
    def mess_placement_diagnostics(self) -> list[dict[str, Any]]:
        return []

    @property
    def placement_diagnostics(self) -> list[dict[str, Any]]:
        raw = self._read_state().get("placement_diagnostics") or []
        return [dict(item) for item in raw if isinstance(item, dict)]

    @property
    def semantic_pose_state(self) -> dict[str, Any]:
        raw = self._read_state().get("semantic_pose_state") or {}
        return dict(raw) if isinstance(raw, dict) else {}

    def scene_index_artifact_payload(self) -> dict[str, Any]:
        """Return report-only USD scene index evidence without private scoring truth."""

        return {
            "schema": ISAAC_SCENE_INDEX_ARTIFACT_SCHEMA,
            "backend": ISAACLAB_SUBPROCESS_BACKEND,
            "runtime_mode": str(self.runtime.get("runtime_mode") or self.runtime_mode),
            "scene_index": self.scene_index,
            "scene_usd": self.scene_usd,
            "object_index_count": len(self.object_index),
            "receptacle_index_count": len(self.receptacle_index),
            "object_index": self.object_index,
            "receptacle_index": self.receptacle_index,
            "scene_load": self.scene_load,
            "scene_index_diagnostics": self.scene_index_diagnostics,
            "scene_binding_diagnostics": self.scene_binding_diagnostics,
            "segmentation": self.segmentation,
            "mapping_gaps": self.mapping_gaps,
            "requested_generated_mess_count": self.requested_generated_mess_count,
            "generated_mess_count": self.generated_mess_count,
            "agent_facing": False,
            "private_manifest_exposed_to_agent": False,
        }

    def write_snapshot(self, output_path: Path, *, title: str) -> Path:
        result = self._run_worker("snapshot", "--output-path", str(output_path), "--title", title)
        self._record_snapshot_artifact(result, title=title)
        return output_path

    def write_snapshot_with_resolution(
        self,
        output_path: Path,
        *,
        title: str,
        width: int,
        height: int,
    ) -> Path:
        result = self._run_worker(
            "snapshot",
            "--output-path",
            str(output_path),
            "--title",
            title,
            "--render-width",
            str(width),
            "--render-height",
            str(height),
        )
        self._record_snapshot_artifact(result, title=title)
        return output_path

    def _record_snapshot_artifact(self, result: dict[str, Any], *, title: str) -> None:
        if result.get("ok") is not True:
            raise RuntimeError(f"Isaac Lab snapshot failed: {result}")
        provenance = result.get("snapshot_provenance")
        if not isinstance(provenance, dict):
            provenance = {}
        self.snapshot_artifacts.append(
            {
                "title": title,
                "output_path": str(result.get("output_path") or ""),
                "visual_artifact_provenance": result.get("visual_artifact_provenance"),
                "placeholder_visuals": result.get("placeholder_visuals"),
                "snapshot_provenance": provenance,
            }
        )

    def write_robot_views(
        self,
        output_dir: Path,
        *,
        label: str,
        focus_object_id: str | None = None,
        focus_receptacle_id: str | None = None,
    ) -> dict[str, Any]:
        args = ["--output-dir", str(output_dir), "--label", label]
        if focus_object_id is not None:
            args.extend(["--focus-object-id", focus_object_id])
        if focus_receptacle_id is not None:
            args.extend(["--focus-receptacle-id", focus_receptacle_id])
        return self._run_worker("robot_views", *args)

    def write_robot_views_with_resolution(
        self,
        output_dir: Path,
        *,
        label: str,
        width: int,
        height: int,
        focus_object_id: str | None = None,
        focus_receptacle_id: str | None = None,
    ) -> dict[str, Any]:
        args = [
            "--output-dir",
            str(output_dir),
            "--label",
            label,
            "--render-width",
            str(width),
            "--render-height",
            str(height),
        ]
        if focus_object_id is not None:
            args.extend(["--focus-object-id", focus_object_id])
        if focus_receptacle_id is not None:
            args.extend(["--focus-receptacle-id", focus_receptacle_id])
        return self._run_worker("robot_views", *args)

    def observe(self) -> dict[str, Any]:
        return self._run_worker("observe")

    def navigate_to_object(self, object_id: str) -> dict[str, Any]:
        return self._run_worker("navigate_to_object", "--object-id", object_id)

    def navigate_to_receptacle(self, receptacle_id: str) -> dict[str, Any]:
        return self._run_worker("navigate_to_receptacle", "--receptacle-id", receptacle_id)

    def pick(self, object_id: str) -> dict[str, Any]:
        return self._run_worker("pick", "--object-id", object_id)

    def open_receptacle(self, receptacle_id: str) -> dict[str, Any]:
        return self._run_worker("open_receptacle", "--receptacle-id", receptacle_id)

    def place(self, receptacle_id: str) -> dict[str, Any]:
        return self._run_worker("place", "--receptacle-id", receptacle_id)

    def place_inside(self, receptacle_id: str) -> dict[str, Any]:
        return self._run_worker("place_inside", "--receptacle-id", receptacle_id)

    def close_receptacle(self, receptacle_id: str) -> dict[str, Any]:
        return self._run_worker("close_receptacle", "--receptacle-id", receptacle_id)

    def done(self, reason: str = "") -> dict[str, Any]:
        return self._run_worker("done", "--reason", reason)

    def _read_state(self) -> dict[str, Any]:
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _run_worker(self, command: str, *args: str) -> dict[str, Any]:
        if not self.python_executable.is_file():
            raise RuntimeError(
                "Isaac Lab Python runtime is missing: "
                f"{self.python_executable}. Create .venv-isaaclab/ or set "
                "ROBOCLAWS_ISAACLAB_PYTHON. CI tests may set "
                "ROBOCLAWS_ISAACLAB_RUNTIME_MODE=fake explicitly."
            )
        worker_command = [
            str(self.python_executable),
            str(ISAAC_WORKER_SCRIPT),
            "--state-path",
            str(self.state_path),
            command,
            *args,
        ]
        try:
            completed = subprocess.run(
                worker_command,
                check=False,
                capture_output=True,
                text=True,
                env=_isaac_worker_env(self.runtime_mode),
                timeout=_isaac_worker_timeout_s(command),
            )
        except subprocess.TimeoutExpired as exc:
            timeout_s = _isaac_worker_timeout_s(command)
            raise RuntimeError(
                f"Isaac Lab subprocess worker timed out ({command}, {timeout_s:g}s)"
            ) from exc
        if completed.returncode != 0:
            raise RuntimeError(
                "Isaac Lab subprocess worker failed "
                f"({command}, exit {completed.returncode}): {completed.stderr.strip()}"
            )
        return _parse_last_json_object(completed.stdout)


def _isaac_worker_env(runtime_mode: str) -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("PYTHONUNBUFFERED", "1")
    env.setdefault("ROBOCLAWS_ISAACLAB_RUNTIME_MODE", runtime_mode)
    return env


def _isaac_worker_timeout_s(command: str) -> float:
    override = os.environ.get("ROBOCLAWS_ISAACLAB_WORKER_TIMEOUT_S")
    if override:
        return float(override)
    return ISAAC_WORKER_TIMEOUTS_S.get(command, DEFAULT_ISAAC_WORKER_TIMEOUT_S)
