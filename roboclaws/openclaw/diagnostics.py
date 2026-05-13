from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from roboclaws.core.turn_metrics import (
    encode_frame_to_b64_jpeg,
    get_provider_turn_metrics,
    round_seconds,
    serialize_prompt_state,
    summarize_payload_metrics,
)
from roboclaws.core.vlm import create_provider, provider_status_snapshot
from roboclaws.openclaw.bridge import OpenClawBridge


@dataclass
class ReplayTurn:
    """One replay turn rehydrated from replay.json + saved PNG frames."""

    replay_dir: Path
    step: int
    agent_id: int
    prompt_state: dict[str, Any]
    frame: np.ndarray
    overhead: np.ndarray
    chase: np.ndarray | None = None


def load_replay_turn(replay_dir: str | Path, *, step: int = 0) -> ReplayTurn:
    """Load a single turn from a replay directory written by ReplayRecorder."""
    replay_path = Path(replay_dir)
    manifest = json.loads((replay_path / "replay.json").read_text())
    matches = [rec for rec in manifest.get("steps", []) if int(rec.get("step", -1)) == step]
    if not matches:
        raise KeyError(f"step {step} not found in {replay_path / 'replay.json'}")

    record = matches[0]
    agent_id = int(record["agent_id"])
    tag = f"{step:04d}"
    frame_path = replay_path / "agent_frames" / f"{tag}_agent{agent_id}.png"
    overhead_path = replay_path / "overhead" / f"{tag}_overhead.png"
    if not frame_path.exists():
        raise FileNotFoundError(frame_path)
    if not overhead_path.exists():
        raise FileNotFoundError(overhead_path)

    frame = np.asarray(Image.open(frame_path).convert("RGB"), dtype=np.uint8)
    overhead = np.asarray(Image.open(overhead_path).convert("RGB"), dtype=np.uint8)
    chase = _load_extra_view(replay_path, record, "chase")
    return ReplayTurn(
        replay_dir=replay_path,
        step=step,
        agent_id=agent_id,
        prompt_state=dict(record.get("vlm_prompt_state", {})),
        frame=frame,
        overhead=overhead,
        chase=chase,
    )


def _load_extra_view(replay_path: Path, record: dict[str, Any], label: str) -> np.ndarray | None:
    for view in record.get("extra_views", []):
        if not isinstance(view, dict) or view.get("label") != label:
            continue
        rel_path = view.get("path")
        if not rel_path:
            continue
        path = replay_path / str(rel_path)
        if path.exists():
            return np.asarray(Image.open(path).convert("RGB"), dtype=np.uint8)
    return None


def probe_openclaw_ping(bridge: OpenClawBridge, *, agent_id: int) -> dict[str, Any]:
    """Measure a minimal Gateway ping against one named agent."""
    started = time.perf_counter()
    reply = bridge.ping(agent_id=agent_id)
    return {
        "probe": "openclaw_ping",
        "agent_id": agent_id,
        "duration_seconds": round_seconds(time.perf_counter() - started),
        "reply": reply[:200],
    }


def probe_openclaw_turn(bridge: OpenClawBridge, turn: ReplayTurn) -> dict[str, Any]:
    """Measure a full OpenClaw bridge turn using one saved replay step."""
    started = time.perf_counter()
    response = bridge.step(
        agent_id=turn.agent_id,
        frame=turn.frame,
        map_v2=turn.overhead,
        chase=turn.chase if turn.chase is not None else turn.overhead,
        state=turn.prompt_state,
        step_idx=turn.step,
    )
    return {
        "probe": "openclaw_turn",
        "step": turn.step,
        "agent_id": turn.agent_id,
        "duration_seconds": round_seconds(time.perf_counter() - started),
        "response": {
            "action": response.get("action"),
            "reasoning_preview": str(response.get("reasoning", ""))[:200],
        },
        "transport_metrics": bridge.get_last_step_metrics(),
    }


def probe_direct_provider(provider: Any, turn: ReplayTurn) -> dict[str, Any]:
    """Measure a direct provider turn using the same saved replay step."""
    prompt_state_text, prompt_state_metrics = serialize_prompt_state(turn.prompt_state)
    fpv_b64, fpv_metrics = encode_frame_to_b64_jpeg(turn.frame)
    overhead_b64, overhead_metrics = encode_frame_to_b64_jpeg(turn.overhead)
    chase_frame = turn.chase if turn.chase is not None else turn.overhead
    chase_b64, chase_metrics = encode_frame_to_b64_jpeg(chase_frame)
    started = time.perf_counter()
    response = provider.get_action(
        images=[fpv_b64, overhead_b64, chase_b64],
        state=turn.prompt_state,
    )
    duration_seconds = round_seconds(time.perf_counter() - started)
    return {
        "probe": "direct_provider_turn",
        "step": turn.step,
        "agent_id": turn.agent_id,
        "duration_seconds": duration_seconds,
        "response": {
            "action": response.get("action"),
            "reasoning_preview": str(response.get("reasoning", ""))[:200],
        },
        "payload": summarize_payload_metrics(
            transport="vlm_base64_jpeg",
            prompt_state_chars=prompt_state_metrics["chars"],
            image_metrics=[
                {"label": "fpv", **fpv_metrics},
                {"label": "map_v2", **overhead_metrics},
                {"label": "chase", **chase_metrics},
            ],
            extra={"prompt_state_preview": prompt_state_text[:120]},
        ),
        "provider_status": provider_status_snapshot(provider),
        "provider_metrics": get_provider_turn_metrics(provider),
    }


def run_latency_probe(
    replay_dir: str | Path,
    *,
    step: int = 0,
    model: str = "kimi-k2.6",
    gateway_url: str | None = None,
) -> dict[str, Any]:
    """Run Gateway and direct-provider latency probes against one saved turn."""
    turn = load_replay_turn(replay_dir, step=step)
    results: dict[str, Any] = {
        "replay_dir": str(Path(replay_dir)),
        "step": turn.step,
        "agent_id": turn.agent_id,
        "model": model,
        "probes": [],
    }

    with OpenClawBridge(gateway_url=gateway_url) as bridge:
        try:
            results["probes"].append(probe_openclaw_ping(bridge, agent_id=turn.agent_id))
        except Exception as exc:  # noqa: BLE001 - diagnostic output should be complete
            results["probes"].append(
                {
                    "probe": "openclaw_ping",
                    "error_kind": exc.__class__.__name__,
                    "error": str(exc),
                }
            )
        try:
            results["probes"].append(probe_openclaw_turn(bridge, turn))
        except Exception as exc:  # noqa: BLE001 - diagnostic output should be complete
            results["probes"].append(
                {
                    "probe": "openclaw_turn",
                    "error_kind": exc.__class__.__name__,
                    "error": str(exc),
                }
            )

    provider = create_provider(model)
    try:
        try:
            results["probes"].append(probe_direct_provider(provider, turn))
        except Exception as exc:  # noqa: BLE001 - diagnostic output should be complete
            results["probes"].append(
                {
                    "probe": "direct_provider_turn",
                    "error_kind": exc.__class__.__name__,
                    "error": str(exc),
                }
            )
    finally:
        close = getattr(provider, "close", None)
        if callable(close):
            close()
    return results
