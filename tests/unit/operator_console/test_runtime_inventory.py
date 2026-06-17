from __future__ import annotations

import json
import os
from pathlib import Path

from roboclaws.operator_console.launcher import route_readiness
from roboclaws.operator_console.paths import console_output_root
from roboclaws.operator_console.routes import get_selection
from roboclaws.operator_console.runtime_inventory import runtime_inventory_payload

CODEX_ENV = {
    "CODEX_BASE_URL": "https://codex.example.test/v1",
    "CODEX_API_KEY": "key",
}
MUJOCO_CODEX_CLEANUP = "molmospaces/val_0::mujoco::cleanup::codex-cli::world-oracle-labels"


def test_runtime_inventory_lists_eval_harness_detached_live_row(tmp_path: Path) -> None:
    row_dir = (
        tmp_path
        / "output"
        / "eval-harness"
        / "focused"
        / "rows"
        / "codex-cleanup-camera-raw-fpv-live-product"
    )
    run_dir = row_dir / "run" / "0615_1225" / "seed-7"
    run_dir.mkdir(parents=True)
    (run_dir / "live_status.json").write_text(
        json.dumps({"phase": "running-codex", "started_at_epoch": 1.0}),
        encoding="utf-8",
    )
    (run_dir / "tmux_session.txt").write_text(
        "roboclaws-molmo-codex-0615_1225-run-p18788-seed-7\n",
        encoding="utf-8",
    )
    (run_dir / "visual_backend_slot.json").write_text(
        json.dumps(
            {
                "slot_id": 1,
                "path": str(tmp_path / "output" / "molmo" / "visual-backend-slots" / "slot-1.json"),
                "port": 18788,
            }
        ),
        encoding="utf-8",
    )
    (run_dir / "driver.log").write_text(
        "Authorization: Bearer SECRET_TOKEN_VALUE\nCODEX_API_KEY=secret-key-value\n",
        encoding="utf-8",
    )
    manifest = {
        "rows": [
            {
                "row_id": "codex-cleanup-camera-raw-fpv-live-product",
                "row_kind": "live_agent_eval",
                "row_dir": str(row_dir),
                "status": "ran",
                "outcome": "passed",
                "axes": {
                    "world": "molmospaces/val_0",
                    "backend": "mujoco",
                    "intent": "cleanup",
                    "preset": "cleanup",
                    "agent_engine": "codex-cli",
                    "evidence_lane": "camera-raw-fpv",
                },
            }
        ]
    }
    (tmp_path / "output" / "eval-harness" / "focused" / "eval_harness.json").write_text(
        json.dumps(manifest),
        encoding="utf-8",
    )

    payload = runtime_inventory_payload(tmp_path, ports=[18788])

    task = next(
        item
        for item in payload["tasks"]
        if item["id"] == "eval-row:codex-cleanup-camera-raw-fpv-live-product"
    )
    assert task["owner"] == "eval-harness"
    assert task["status"] == "running"
    assert task["row_id"] == "codex-cleanup-camera-raw-fpv-live-product"
    assert task["route_id"] == "molmospaces/val_0::mujoco::cleanup::codex-cli::camera-raw-fpv"
    assert any(resource["kind"] == "tmux_session" for resource in task["resources"])
    assert any(resource["kind"] == "visual_slot" for resource in task["resources"])
    assert any(action["label"] == "Attach" for action in task["actions"])
    assert not any(action["type"] == "api_post" for action in task["actions"])
    assert "SECRET_TOKEN_VALUE" not in json.dumps(task)
    assert "secret-key-value" not in json.dumps(task)


def test_runtime_inventory_exposes_direct_stop_only_for_operator_runs(tmp_path: Path) -> None:
    route = get_selection(MUJOCO_CODEX_CLEANUP)
    run_id = "operator-run"
    run_dir = console_output_root(tmp_path) / "runs" / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "operator_state.json").write_text(
        json.dumps(
            {
                "run_id": run_id,
                "route": route.to_payload(),
                "phase": "running",
                "pid": os.getpid(),
                "backend_lock": route.lock_name,
                "run_dir": str(run_dir),
            }
        ),
        encoding="utf-8",
    )

    payload = runtime_inventory_payload(tmp_path)

    task = next(item for item in payload["tasks"] if item["id"] == f"operator-run:{run_id}")
    assert task["owner"] == "operator-console"
    assert any(
        action["type"] == "api_post" and action["label"] == "Stop"
        for action in task["actions"]
    )


def test_readiness_names_background_eval_owner_before_start(tmp_path: Path) -> None:
    route = get_selection(MUJOCO_CODEX_CLEANUP)
    row_dir = tmp_path / "output" / "eval-harness" / "focused" / "rows" / "codex-cleanup-live"
    run_dir = row_dir / "run" / "0615_1225" / "seed-7"
    run_dir.mkdir(parents=True)
    (run_dir / "live_status.json").write_text(
        json.dumps({"phase": "running-codex"}),
        encoding="utf-8",
    )
    (run_dir / "visual_backend_slot.json").write_text(
        json.dumps({"slot_id": 1, "port": 18788}),
        encoding="utf-8",
    )
    (tmp_path / "output" / "eval-harness" / "focused" / "eval_harness.json").write_text(
        json.dumps(
            {
                "rows": [
                    {
                        "row_id": "codex-cleanup-live",
                        "row_kind": "live_agent_eval",
                        "row_dir": str(row_dir),
                        "status": "ran",
                        "axes": {
                            "world": "molmospaces/val_0",
                            "backend": "mujoco",
                            "intent": "cleanup",
                            "preset": "cleanup",
                            "agent_engine": "codex-cli",
                            "evidence_lane": "world-oracle-labels",
                        },
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    readiness = route_readiness(
        tmp_path,
        route,
        overrides={"port": "18788"},
        env=CODEX_ENV,
    )

    assert readiness["can_start"] is False
    assert readiness["blocker_kind"] == "background_task"
    assert "Background task eval-row:codex-cleanup-live" in readiness["blocker"]
    assert readiness["background_blockers"][0]["owner"] == "eval-harness"
