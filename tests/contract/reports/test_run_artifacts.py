from __future__ import annotations

import math

from roboclaws.core.run_artifacts import (
    FRAME_CAPTURE_EVENT,
    build_autonomous_summary,
    build_frame_capture_payload,
    build_replay_manifest,
    build_replay_report_context,
    build_replay_step,
    build_run_result,
    build_snapshot_archive_paths,
    build_snapshot_metrics,
    build_trace_event,
)


def test_run_artifact_contract_links_replay_trace_snapshots_and_summary() -> None:
    state = {
        "agent_id": 0,
        "position": {"x": 1.0, "y": 0.0, "z": 2.0},
        "rotation": {"y": 90.0},
        "camera_horizon": 30.0,
        "last_action_success": True,
        "last_action_error": "",
    }
    replay_step = build_replay_step(
        step=1,
        agent_id=0,
        game_state={"score": 7},
        vlm_prompt_state={"my_agent_id": 0},
        vlm_response={"reasoning": "advance", "action": "MoveAhead"},
        provider_status={"provider_name": "mock"},
        turn_metrics={"payload": {"image_count": 3}},
        overhead_label="map_v2",
        extra_views=[{"label": "chase", "path": "scene_views/0001_view0_chase.png"}],
    )
    manifest = build_replay_manifest(
        game="territory",
        agent_count=1,
        duration_seconds=12.345,
        vlm_cost_usd=0.0012349,
        final_scores={0: 7},
        termination_reason="done",
        provider_status={"provider_name": "mock"},
        steps=[replay_step],
    )
    report_context = build_replay_report_context(manifest)

    snapshot_paths = build_snapshot_archive_paths(
        container_dir="/home/node/.openclaw/workspaces/agent-0/snapshots",
        archive_stem="goal-001",
    )
    frame_payload = build_frame_capture_payload(
        seen_by_agent=False,
        fpv="fpv-b64",
        overhead="map-b64",
        agent_state=state,
        view_variant="map-v2+chase",
        image_labels=["fpv", "map_v2", "chase"],
        baseline_overhead="raw-map-b64",
        chase="chase-b64",
    )
    trace_events = [
        build_trace_event(
            tool="observe_archived",
            event="request",
            ts=1000.0,
            wallclock_elapsed=0.0,
            request={"label": "goal"},
        ),
        build_trace_event(
            tool="observe_archived",
            event=FRAME_CAPTURE_EVENT,
            ts=1000.1,
            wallclock_elapsed=0.1,
            **frame_payload,
        ),
        build_trace_event(
            tool="move",
            event="request",
            ts=1000.2,
            wallclock_elapsed=0.2,
            request={"direction": "MoveAhead"},
        ),
        build_trace_event(
            tool="done",
            event="request",
            ts=1000.3,
            wallclock_elapsed=0.3,
            request={"reason": "goal"},
        ),
    ]
    run_result = build_run_result(
        terminated_by="done",
        wallclock_s=5.5,
        final_message="goal reached",
        view_variant="map-v2+chase",
        model="mock",
        bridge_metrics={"prompt_chars": 10},
        sim_server_metrics=build_snapshot_metrics(
            runtime_s=5.5,
            last_trace_age_s=0.0,
            queued_human_messages=0,
            observed_once=True,
            moves_since_observe=0,
            done_event_set=True,
            done_reason="goal",
            tool_event_counts={"observe_archived:request": 1},
        ),
        transcript_source="none",
        transcript_messages=[],
        diagnostics_files={},
    )
    summary = build_autonomous_summary(
        events=trace_events,
        frames=[trace_events[1]],
        run_result=run_result,
    )

    assert manifest["metadata"]["total_steps"] == 1
    assert report_context.provider_status == {"provider_name": "mock"}
    assert report_context.steps[0]["overhead_label"] == "map_v2"
    assert snapshot_paths == {
        "fpv": "/home/node/.openclaw/workspaces/agent-0/snapshots/goal-001.fpv.png",
        "map": "/home/node/.openclaw/workspaces/agent-0/snapshots/goal-001.map.png",
        "chase": "/home/node/.openclaw/workspaces/agent-0/snapshots/goal-001.chase.png",
    }
    assert trace_events[1]["event"] == FRAME_CAPTURE_EVENT
    assert trace_events[1]["image_labels"] == ["fpv", "map_v2", "chase"]
    assert run_result["sim_server_metrics"]["observed_once"] is True
    assert summary["tool_calls_by_type"] == {"observe": 0, "move": 1, "done": 1}
    assert summary["frames_unseen_by_agent"] == 1
    assert summary["wallclock_seconds"] == 5.5
    assert summary["view_variant"] == "map-v2+chase"
    assert not math.isinf(summary["observe_to_move_ratio"])
