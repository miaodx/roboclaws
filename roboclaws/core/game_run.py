from __future__ import annotations

import time
from typing import Any

import numpy as np

from roboclaws.core.replay import ReplayRecorder
from roboclaws.core.turn_metrics import (
    encode_frame_to_b64_jpeg,
    round_seconds,
    summarize_payload_metrics,
)
from roboclaws.core.views import encode_prompt_images, image_labels_for_variant
from roboclaws.core.vlm import create_provider


def create_game_provider(
    *,
    backend: str,
    gateway_url: str | None,
    agent_count: int,
    model: str,
    agent_soul_content: dict[int, str],
    provider_seed: int | None = None,
):
    """Return the provider Adapter for a direct VLM or OpenClaw game run."""
    from roboclaws.openclaw.bridge import build_openclaw_provider_or_die

    if backend == "openclaw":
        return build_openclaw_provider_or_die(gateway_url=gateway_url, agent_count=agent_count)

    kwargs: dict[str, Any] = {"agent_souls": agent_soul_content} if agent_soul_content else {}
    if model == "mock" and provider_seed is not None:
        kwargs["seed"] = provider_seed
    try:
        return create_provider(model, **kwargs)
    except TypeError:
        return create_provider(model)


def prepare_prompt_payload(
    *,
    backend: str,
    prompt_image_frames: list[np.ndarray],
    prompt_state_text: str,
    prompt_state_metrics: dict[str, Any],
    view_variant: str = "map-v2+chase",
) -> tuple[list[Any], dict[str, Any], float]:
    """Return provider images, payload metrics, and encoding time for a game turn."""
    if backend == "openclaw":
        return (
            list(prompt_image_frames),
            summarize_payload_metrics(
                transport="openclaw_ndarray",
                prompt_state_chars=prompt_state_metrics["chars"],
                image_metrics=[
                    {"label": label} for label in image_labels_for_variant(view_variant)
                ],
            ),
            0.0,
        )

    prompt_images, image_metrics, encode_seconds = encode_prompt_images(
        image_frames=prompt_image_frames,
        encoder=encode_frame_to_b64_jpeg,
    )
    return (
        prompt_images,
        summarize_payload_metrics(
            transport="vlm_base64_jpeg",
            prompt_state_chars=prompt_state_metrics["chars"],
            image_metrics=image_metrics,
            extra={"prompt_state_preview": prompt_state_text[:120]},
        ),
        round_seconds(encode_seconds),
    )


def record_game_turn(
    *,
    recorder: ReplayRecorder,
    step: int,
    agent_id: int,
    agent_frames: list[np.ndarray],
    overhead_frame: np.ndarray,
    game_state: dict[str, Any],
    prompt_state: dict[str, Any],
    response: dict[str, Any],
    provider_status: dict[str, Any],
    turn_metrics: dict[str, Any],
    step_started: float,
) -> None:
    """Record one game turn and persist post-recording timing metrics."""
    record_started = time.perf_counter()
    recorder.record_step(
        step=step,
        agent_id=agent_id,
        agent_frames=agent_frames,
        overhead_frame=overhead_frame,
        game_state=game_state,
        vlm_prompt_state=prompt_state,
        vlm_response=response,
        provider_status=provider_status,
        turn_metrics=turn_metrics,
    )
    turn_metrics["timings"]["record_step_seconds"] = round_seconds(
        time.perf_counter() - record_started
    )
    turn_metrics["timings"]["step_loop_seconds"] = round_seconds(time.perf_counter() - step_started)
    recorder._steps[-1].turn_metrics = dict(turn_metrics)
