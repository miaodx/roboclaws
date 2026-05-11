from __future__ import annotations

import json
from pathlib import Path

from roboclaws.molmo_cleanup.artifact_report import (
    load_cleanup_scenario_artifact,
    rerender_cleanup_report_from_run_result,
)
from roboclaws.molmo_cleanup.report_visual_core import assert_cleanup_report_visual_core
from roboclaws.molmo_cleanup.scenario import build_cleanup_scenario, write_scenario_bundle
from roboclaws.molmo_cleanup.scoring import score_cleanup
from roboclaws.molmo_cleanup.semantic_acceptability import (
    annotate_score_with_semantic_acceptability,
)
from roboclaws.molmo_cleanup.semantic_timeline import semantic_substeps


def test_load_cleanup_scenario_artifact_uses_adjacent_private_manifest(tmp_path: Path) -> None:
    scenario = build_cleanup_scenario(seed=7)
    paths = write_scenario_bundle(tmp_path, scenario)

    loaded = load_cleanup_scenario_artifact(paths["scenario"])

    assert loaded.scenario_id == scenario.scenario_id
    assert loaded.private_manifest.success_threshold == scenario.private_manifest.success_threshold
    assert [target.object_id for target in loaded.private_manifest.targets] == [
        target.object_id for target in scenario.private_manifest.targets
    ]


def test_rerender_cleanup_report_from_run_result_uses_shared_visual_core(
    tmp_path: Path,
) -> None:
    scenario = build_cleanup_scenario(seed=7)
    write_scenario_bundle(tmp_path, scenario)
    receptacle_by_id = {item.receptacle_id: item.to_public_dict() for item in scenario.receptacles}
    target = scenario.private_manifest.targets[0]
    obj = next(item for item in scenario.objects if item.object_id == target.object_id)
    target_receptacle_id = target.valid_receptacle_ids[0]
    trace_events = _semantic_trace(
        object_id=obj.object_id,
        source_receptacle_id=obj.location_id,
        target_receptacle_id=target_receptacle_id,
    )
    trace_path = tmp_path / "trace.jsonl"
    trace_path.write_text(
        "\n".join(json.dumps(event, sort_keys=True) for event in trace_events) + "\n",
        encoding="utf-8",
    )
    before = tmp_path / "before.png"
    after = tmp_path / "after.png"
    before.write_bytes(b"before")
    after.write_bytes(b"after")
    final_locations = scenario.object_locations()
    final_locations[obj.object_id] = target_receptacle_id
    score = annotate_score_with_semantic_acceptability(
        score_cleanup(final_locations, scenario.private_manifest).to_dict(),
        scenario,
    )
    run_result = {
        "backend": "test",
        "cleanup_status": "success",
        "contract": "current_contract",
        "current_contract_shortcuts": ["global_scene_objects"],
        "agent_driven": True,
        "mcp_server": "molmo_cleanup",
        "policy": "codex_agent",
        "primitive_provenance": "api_semantic",
        "scenario_id": scenario.scenario_id,
        "semantic_substeps": semantic_substeps(trace_events, receptacle_by_id),
        "score": score,
        "robot_view_steps": [
            {
                "action": f"navigate_to_object {obj.object_id}",
                "semantic_phase": "navigate_to_object",
                "robot_pose": {},
                "views": {"fpv": "robot_views/nav.fpv.png"},
                "focus": {},
            },
            {
                "action": f"place {obj.object_id}",
                "semantic_phase": "place",
                "robot_pose": {},
                "views": {"fpv": "robot_views/place.fpv.png"},
                "focus": {},
            },
        ],
        "artifacts": {
            "scenario": "stale-output/demo/scenario.json",
            "trace": "stale-output/demo/trace.jsonl",
            "before_snapshot": "stale-output/demo/before.png",
            "after_snapshot": "stale-output/demo/after.png",
            "report": str(tmp_path / "report.html"),
        },
    }
    run_result_path = tmp_path / "run_result.json"
    run_result_path.write_text(json.dumps(run_result, indent=2, sort_keys=True), encoding="utf-8")
    (tmp_path / "report.html").write_text("<h2>Semantic Substeps</h2>raw</table>", encoding="utf-8")

    report_path = rerender_cleanup_report_from_run_result(run_result_path)

    report_text = report_path.read_text(encoding="utf-8")
    assert report_path == tmp_path / "report.html"
    assert_cleanup_report_visual_core(
        report_text,
        require_semantic_subphases=True,
        require_robot_timeline=True,
    )
    assert "<span>nav</span><small>object</small>" in report_text
    assert "<span>pick</span><small>object</small>" in report_text
    assert "navigate_to_object -&gt; pick" not in report_text


def _semantic_trace(
    *,
    object_id: str,
    source_receptacle_id: str,
    target_receptacle_id: str,
) -> list[dict[str, object]]:
    responses = [
        {
            "tool": "navigate_to_object",
            "ok": True,
            "object_id": object_id,
            "location_id": source_receptacle_id,
            "source_receptacle_id": source_receptacle_id,
            "primitive_provenance": "api_semantic",
        },
        {
            "tool": "pick",
            "ok": True,
            "object_id": object_id,
            "location_id": "held_by_agent",
            "source_receptacle_id": source_receptacle_id,
            "primitive_provenance": "api_semantic",
        },
        {
            "tool": "navigate_to_receptacle",
            "ok": True,
            "object_id": object_id,
            "receptacle_id": target_receptacle_id,
            "primitive_provenance": "api_semantic",
        },
        {
            "tool": "place",
            "ok": True,
            "object_id": object_id,
            "receptacle_id": target_receptacle_id,
            "location_id": target_receptacle_id,
            "location_relation": "on",
            "primitive_provenance": "api_semantic",
        },
    ]
    events: list[dict[str, object]] = []
    for response in responses:
        events.append({"event": "response", "tool": response["tool"], "response": response})
    return events
