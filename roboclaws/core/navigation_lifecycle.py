from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class NavigationRunLifecycle:
    """Shared filesystem and result lifecycle for navigation runs."""

    scene: str
    output_dir: Path
    host: str
    port: int
    agent_id: int = 0
    started: float = field(default_factory=time.monotonic)

    @property
    def snapshots_dir(self) -> Path:
        return self.output_dir / "snapshots" / f"agent-{self.agent_id}"

    @property
    def mcp_url(self) -> str:
        return f"http://{self.host}:{self.port}/mcp"

    def prepare_output_dir(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def elapsed_seconds(self) -> float:
        return round(time.monotonic() - self.started, 3)

    def write_json(self, filename: str, payload: dict[str, Any]) -> dict[str, Any]:
        path = self.output_dir / filename
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload

    def write_direct_run_result(
        self,
        *,
        terminated_by: str,
        snapshot_metrics: dict[str, Any],
        error: str | None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "terminated_by": terminated_by,
            "scene": self.scene,
            "mcp_url": self.mcp_url,
            "output_dir": str(self.output_dir),
            "snapshots_dir": str(self.snapshots_dir),
            "wallclock_s": self.elapsed_seconds(),
            "sim_server_metrics": snapshot_metrics,
        }
        if error is not None:
            payload["error"] = error
        return self.write_json("run_result.json", payload)
