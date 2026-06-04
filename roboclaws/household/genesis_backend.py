from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any

from roboclaws.household.camera_control import load_camera_control_request
from roboclaws.household.subprocess_backend import _parse_last_json_object

GENESIS_SUBPROCESS_BACKEND = "genesis_subprocess"
GENESIS_SCENE_CAMERA_VIEW_VARIANT = "genesis-prepared-usd-scene-camera"
DEFAULT_GENESIS_PYTHON = Path(__file__).resolve().parents[2] / ".venv-genesis" / "bin" / "python"
DEFAULT_GENESIS_WORKER_TIMEOUT_S = 120.0
GENESIS_WORKER_TIMEOUTS_S = {
    "init": 180.0,
    "camera_views": 240.0,
}
GENESIS_WORKER_SCRIPT = (
    Path(__file__).resolve().parents[2]
    / "scripts"
    / "genesis_cleanup"
    / "genesis_backend_worker.py"
)


class GenesisSubprocessBackend:
    """Subprocess boundary for the optional Genesis World runtime.

    The normal Roboclaws process must not import Genesis or Torch. The worker
    owns those heavy imports and can be pointed at a separate `.venv-genesis/`
    interpreter for local render evidence.
    """

    def __init__(
        self,
        *,
        run_dir: Path,
        scene_usd_path: Path,
        python_executable: Path | None = None,
        runtime_mode: str | None = None,
    ) -> None:
        self.run_dir = run_dir
        self.state_path = run_dir / "genesis_backend_state.json"
        self.scene_usd_path = scene_usd_path
        self.python_executable = python_executable or Path(
            os.environ.get("ROBOCLAWS_GENESIS_PYTHON", str(DEFAULT_GENESIS_PYTHON))
        )
        self.runtime_mode = runtime_mode or os.environ.get("ROBOCLAWS_GENESIS_RUNTIME_MODE", "real")
        result = self._run_worker(
            "init",
            "--run-dir",
            str(run_dir),
            "--scene-usd-path",
            str(scene_usd_path),
            "--runtime-mode",
            self.runtime_mode,
        )
        self.backend = GENESIS_SUBPROCESS_BACKEND
        self.runtime = result.get("runtime") if isinstance(result.get("runtime"), dict) else {}
        self.scene_usd = str(result.get("scene_usd") or scene_usd_path)
        self.scene_load = (
            result.get("scene_load") if isinstance(result.get("scene_load"), dict) else {}
        )

    def render_camera_control_request(
        self,
        output_dir: Path,
        *,
        request_path: Path,
    ) -> dict[str, Any]:
        """Render externally supplied Roboclaws camera-control views."""

        request = load_camera_control_request(request_path)
        resolution = request["render_resolution"]
        return self._run_worker(
            "camera_views",
            "--output-dir",
            str(output_dir),
            "--camera-request-path",
            str(request_path),
            "--render-width",
            str(resolution["width"]),
            "--render-height",
            str(resolution["height"]),
        )

    def _run_worker(self, command: str, *args: str) -> dict[str, Any]:
        if not self.python_executable.is_file():
            raise RuntimeError(
                "Genesis Python runtime is missing: "
                f"{self.python_executable}. Create .venv-genesis/ or set "
                "ROBOCLAWS_GENESIS_PYTHON. CI tests may set "
                "ROBOCLAWS_GENESIS_RUNTIME_MODE=fake explicitly."
            )
        worker_command = [
            str(self.python_executable),
            str(GENESIS_WORKER_SCRIPT),
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
                env=_genesis_worker_env(self.runtime_mode),
                timeout=_genesis_worker_timeout_s(command),
            )
        except subprocess.TimeoutExpired as exc:
            timeout_s = _genesis_worker_timeout_s(command)
            raise RuntimeError(
                f"Genesis subprocess worker timed out ({command}, {timeout_s:g}s)"
            ) from exc
        if completed.returncode != 0:
            raise RuntimeError(
                "Genesis subprocess worker failed "
                f"({command}, exit {completed.returncode}): {completed.stderr.strip()}"
            )
        return _parse_last_json_object(completed.stdout)


def _genesis_worker_env(runtime_mode: str) -> dict[str, str]:
    env = os.environ.copy()
    for key in (
        "PYTHONPATH",
        "AMENT_PREFIX_PATH",
        "COLCON_PREFIX_PATH",
        "ROS_DISTRO",
        "ROS_VERSION",
        "ROS_PYTHON_VERSION",
    ):
        env.pop(key, None)
    env.setdefault("PYTHONUNBUFFERED", "1")
    env.setdefault("ROBOCLAWS_GENESIS_RUNTIME_MODE", runtime_mode)
    return env


def _genesis_worker_timeout_s(command: str) -> float:
    override = os.environ.get("ROBOCLAWS_GENESIS_WORKER_TIMEOUT_S")
    if override:
        return float(override)
    return GENESIS_WORKER_TIMEOUTS_S.get(command, DEFAULT_GENESIS_WORKER_TIMEOUT_S)
