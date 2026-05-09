from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

from roboclaws.molmo_cleanup.types import (
    CleanupObject,
    CleanupReceptacle,
    CleanupScenario,
    PrivateScoringManifest,
    TargetRule,
)

MOLMOSPACES_SUBPROCESS_BACKEND = "molmospaces_subprocess"
DEFAULT_MOLMOSPACES_PYTHON = Path("/tmp/roboclaws-molmospaces-spike/.venv/bin/python")
WORKER_SCRIPT = Path(__file__).resolve().parents[2] / "scripts" / "molmospaces_subprocess_worker.py"


class MolmoSpacesSubprocessBackend:
    """Backend wrapper for the isolated Python 3.11 MolmoSpaces runtime."""

    def __init__(
        self,
        *,
        run_dir: Path,
        seed: int = 7,
        python_executable: Path | None = None,
        scene_source: str = "procthor-10k-val",
        scene_index: int = 0,
        include_robot: bool = False,
        robot_name: str = "rby1m",
    ) -> None:
        self.run_dir = run_dir
        self.state_path = run_dir / "molmospaces_backend_state.json"
        self.python_executable = python_executable or Path(
            os.environ.get("ROBOCLAWS_MOLMOSPACES_PYTHON", str(DEFAULT_MOLMOSPACES_PYTHON))
        )
        init_args = [
            "--seed",
            str(seed),
            "--scene-source",
            scene_source,
            "--scene-index",
            str(scene_index),
        ]
        if include_robot:
            init_args.extend(["--include-robot", "--robot-name", robot_name])
        result = self._run_worker("init", *init_args)
        self.backend = MOLMOSPACES_SUBPROCESS_BACKEND
        self.scenario = _scenario_from_worker_payload(
            result["scenario"],
            result["private_manifest"],
        )
        self.runtime = result["runtime"]
        self.model_stats = result["model_stats"]
        self.scene_xml = result["scene_xml"]
        self.metadata_object_count = result["metadata_object_count"]
        self.robot = result.get("robot")

    @property
    def held_object_id(self) -> str | None:
        state = self._read_state()
        value = state.get("held_object_id")
        return str(value) if value is not None else None

    def object_locations(self) -> dict[str, str]:
        result = self._run_worker("locations")
        return {str(key): str(value) for key, value in result["final_locations"].items()}

    def write_snapshot(self, output_path: Path, *, title: str) -> Path:
        self._run_worker("snapshot", "--output-path", str(output_path), "--title", title)
        return output_path

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

    def observe(self) -> dict[str, Any]:
        return self._run_worker("observe")

    def scene_objects(self, category: str | None = None) -> dict[str, Any]:
        result = self._run_worker("scene_objects")
        if category is not None:
            result["objects"] = [
                item for item in result["objects"] if item.get("category") == category
            ]
        return result

    def goto(self, receptacle_id: str) -> dict[str, Any]:
        return self._run_worker("goto", "--receptacle-id", receptacle_id)

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

    def object_done(self, object_id: str, receptacle_id: str) -> dict[str, Any]:
        return self._run_worker(
            "object_done",
            "--object-id",
            object_id,
            "--receptacle-id",
            receptacle_id,
        )

    def done(self, reason: str = "") -> dict[str, Any]:
        return self._run_worker("done", "--reason", reason)

    def _read_state(self) -> dict[str, Any]:
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _run_worker(self, command: str, *args: str) -> dict[str, Any]:
        if not self.python_executable.is_file():
            raise RuntimeError(
                "MolmoSpaces Python 3.11 runtime is missing: "
                f"{self.python_executable}. Set ROBOCLAWS_MOLMOSPACES_PYTHON."
            )
        completed = subprocess.run(
            [
                str(self.python_executable),
                str(WORKER_SCRIPT),
                "--state-path",
                str(self.state_path),
                command,
                *args,
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            raise RuntimeError(
                "MolmoSpaces subprocess worker failed "
                f"({command}, exit {completed.returncode}): {completed.stderr.strip()}"
            )
        return _parse_last_json_object(completed.stdout)


def _parse_last_json_object(stdout: str) -> dict[str, Any]:
    for line in reversed(stdout.splitlines()):
        line = line.strip()
        if not line.startswith("{"):
            continue
        payload = json.loads(line)
        if isinstance(payload, dict):
            return payload
    raise RuntimeError(f"MolmoSpaces worker returned no JSON object: {stdout!r}")


def _scenario_from_worker_payload(
    public: dict[str, Any],
    private: dict[str, Any],
) -> CleanupScenario:
    manifest = PrivateScoringManifest(
        scenario_id=str(private["scenario_id"]),
        success_threshold=int(private["success_threshold"]),
        targets=tuple(
            TargetRule(
                object_id=str(target["object_id"]),
                valid_receptacle_ids=tuple(str(value) for value in target["valid_receptacle_ids"]),
            )
            for target in private["targets"]
        ),
    )
    return CleanupScenario(
        scenario_id=str(public["scenario_id"]),
        task=str(public["task"]),
        seed=int(public["seed"]),
        objects=tuple(
            CleanupObject(
                object_id=str(item["object_id"]),
                name=str(item["name"]),
                category=str(item["category"]),
                location_id=str(item.get("location_id", "")),
                pickupable=bool(item.get("pickupable", True)),
            )
            for item in public["objects"]
        ),
        receptacles=tuple(
            CleanupReceptacle(
                receptacle_id=str(item["receptacle_id"]),
                name=str(item["name"]),
                room_area=str(item.get("room_area", "unknown")),
                kind=str(item.get("kind", "receptacle")),
                category=str(item["category"]) if item.get("category") is not None else None,
            )
            for item in public["receptacles"]
        ),
        private_manifest=manifest,
    )
