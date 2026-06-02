from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from roboclaws.household.agibot_sdk_runner import (
    AGIBOT_GDK_BACKEND_VARIANT,
    AGIBOT_GDK_NORMAL_NAVI_PROVENANCE,
    AGIBOT_SDK_RUNNER_BACKEND,
    BLOCKED_MANIPULATION_TOOLS,
    AgibotSDKRunnerAdapter,
)
from roboclaws.household.nav2_adapter import BLOCKED_CAPABILITY_PROVENANCE
from roboclaws.household.realworld_contract import (
    CAMERA_MODEL_POLICY_MODE,
    CLEANUP_WORKLIST_SCHEMA,
    REAL_ROBOT_MAP_BUNDLE_SCHEMA,
    REALWORLD_CONTRACT,
)
from roboclaws.household.scenario import build_cleanup_scenario
from roboclaws.household.types import CleanupScenario
from roboclaws.mcp.profiles import REAL_ROBOT_CLEANUP_PROFILE, contract_profile_metadata


class AgibotCleanupBackendSession:
    """CleanupBackendSession-shaped Agibot marker for shared MCP reports."""

    def __init__(self, scenario: CleanupScenario | None = None) -> None:
        self.scenario = scenario or build_cleanup_scenario(seed=7)
        self.backend = self

    def object_locations(self) -> dict[str, str]:
        return self.scenario.object_locations()


class AgibotCleanupMCPContract:
    """Agibot adapter-backed implementation of the shared cleanup MCP contract."""

    def __init__(
        self,
        *,
        run_dir: Path,
        context_json: Path,
        runner_script: Path | None = None,
        runner_python: str | Path | None = None,
        real_movement_enabled: bool = False,
        agibot_map_artifact_dir: Path | None = None,
        scenario: CleanupScenario | None = None,
        task_prompt: str = "Build a semantic map from Agibot G2 public evidence.",
    ) -> None:
        self.scenario = scenario or build_cleanup_scenario(seed=7)
        self.contract = AgibotCleanupBackendSession(self.scenario)
        self.task_prompt = task_prompt
        self.perception_mode = CAMERA_MODEL_POLICY_MODE
        self.map_mode = "agibot_minimal_map_context"
        self.visual_grounding_pipeline_id = "agibot_g2_head_color"
        self.adapter = AgibotSDKRunnerAdapter(
            context_json=context_json,
            run_dir=run_dir,
            runner_script=runner_script,
            runner_python=runner_python,
            real_movement_enabled=real_movement_enabled,
            agibot_map_artifact_dir=agibot_map_artifact_dir,
        )
        self.real_movement_enabled = bool(real_movement_enabled)
        self._current_waypoint_id = ""
        self._visited_waypoint_ids: set[str] = set()
        self._observed_waypoint_ids: set[str] = set()
        self._raw_fpv_observations: list[dict[str, Any]] = []
        self._tool_event_counts: dict[str, int] = {}

    def public_tool_names(self) -> list[str]:
        return [
            "metric_map",
            "fixture_hints",
            "navigate_to_room",
            "navigate_to_waypoint",
            "observe",
            "adjust_camera",
            "declare_visual_candidates",
            "navigate_to_visual_candidate",
            "inspect_visible_object",
            "navigate_to_object",
            "pick",
            "navigate_to_receptacle",
            "open_receptacle",
            "place",
            "place_inside",
            "close_receptacle",
            "done",
        ]

    def public_receptacles_by_id(self) -> dict[str, dict[str, Any]]:
        fixtures = {}
        for room in self.fixture_hints().get("rooms") or []:
            for fixture in room.get("fixtures") or []:
                fixture_id = str(fixture.get("fixture_id") or "")
                if fixture_id:
                    fixtures[fixture_id] = dict(fixture)
        return fixtures

    def internal_fixture_id_for_public_reference(self, fixture_id: str | None) -> str | None:
        return fixture_id

    def metric_map(self) -> dict[str, Any]:
        metric_map = dict(self.adapter.metric_map())
        metric_map.setdefault("schema", REAL_ROBOT_MAP_BUNDLE_SCHEMA)
        metric_map.setdefault("contract", REALWORLD_CONTRACT)
        metric_map.setdefault("tool", "metric_map")
        metric_map.setdefault("status", "ok")
        metric_map.setdefault("ok", True)
        metric_map["inspection_waypoints"] = [
            {
                **dict(item),
                "visited": str(item.get("waypoint_id") or "") in self._visited_waypoint_ids,
            }
            for item in metric_map.get("inspection_waypoints") or []
        ]
        metric_map["runtime_metric_map"] = self.runtime_metric_map_payload(
            metric_map=metric_map,
            fixture_hints=self.fixture_hints(),
        )
        return metric_map

    def fixture_hints(self) -> dict[str, Any]:
        payload = dict(self.adapter.fixture_hints())
        payload.setdefault("contract", REALWORLD_CONTRACT)
        payload.setdefault("tool", "fixture_hints")
        payload.setdefault("status", "ok")
        payload.setdefault("ok", True)
        payload.setdefault("schema", "static_fixture_semantic_map_v1")
        return payload

    def navigate_to_room(self, room_id: str) -> dict[str, Any]:
        return self._remember_navigation(self.adapter.navigate_to_room(room_id=room_id))

    def navigate_to_waypoint(self, waypoint_id: str) -> dict[str, Any]:
        return self._remember_navigation(self.adapter.navigate_to_waypoint(waypoint_id=waypoint_id))

    def navigate_to_receptacle(self, fixture_id: str) -> dict[str, Any]:
        return self._remember_navigation(
            self.adapter.navigate_to_fixture_preferred_waypoint(fixture_id=fixture_id)
        )

    def navigate_to_object(self, object_id: str) -> dict[str, Any]:
        return self.adapter.navigate_to_object(object_id=object_id)

    def navigate_to_visual_candidate(
        self,
        source_observation_id: str | None = None,
        category: str = "",
        target_fixture_id: str = "",
        evidence_note: str = "",
        image_region: dict[str, Any] | str | None = None,
        *,
        source_fixture_id: str = "",
        confidence: float | None = None,
        producer_type: str = "",
        producer_id: str = "",
    ) -> dict[str, Any]:
        del category, evidence_note, image_region, source_fixture_id, confidence, producer_type
        del producer_id
        return self._remember_navigation(
            self.adapter.navigate_to_visual_candidate(
                source_observation_id=str(source_observation_id or ""),
                target_fixture_id=target_fixture_id,
            )
        )

    def observe(self) -> dict[str, Any]:
        response = dict(self.adapter.observe(label="shared_cleanup_mcp_observe"))
        waypoint_id = self._current_waypoint_id
        if waypoint_id:
            self._observed_waypoint_ids.add(waypoint_id)
        response.setdefault("current_room_id", "")
        response.setdefault("waypoint_id", waypoint_id)
        response.setdefault("perception_mode", self.perception_mode)
        response.setdefault("structured_detections_available", False)
        response.setdefault("visible_object_detections", [])
        response.setdefault("private_target_truth_included", False)
        raw = self._raw_observation_from_response(response, waypoint_id=waypoint_id)
        response["raw_fpv_observation"] = raw
        self._raw_fpv_observations.append(raw)
        return response

    def adjust_camera(self, yaw_delta_deg: float = 0.0, pitch_delta_deg: float = 0.0) -> dict:
        del yaw_delta_deg, pitch_delta_deg
        return self._blocked(
            "adjust_camera",
            "agibot_camera_motion_unproven",
            "Agibot G2 camera adjustment is blocked until bounded control is proven.",
        )

    def declare_visual_candidates(
        self,
        observation_id: str | None = None,
        *,
        candidates: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None = None,
        producer_type: str = "",
        producer_id: str = "",
    ) -> dict[str, Any]:
        del candidates, producer_type, producer_id
        return self._blocked(
            "declare_visual_candidates",
            "agibot_cleanup_mcp_camera_labels_blocked",
            (
                "Use semantic-map-build camera-labels for Agibot G2 visual grounding; "
                "the shared cleanup MCP path keeps manipulation and cleanup labels blocked."
            ),
            extra={"observation_id": observation_id or ""},
        )

    def inspect_visible_object(self, object_id: str) -> dict[str, Any]:
        return self._blocked(
            "inspect_visible_object",
            "agibot_cleanup_object_observation_unavailable",
            "No cleanup object handles are exposed by the Agibot shared MCP pilot.",
            extra={"object_id": object_id},
        )

    def pick(self, object_id: str) -> dict[str, Any]:
        return self._blocked_manipulation("pick", object_id=object_id)

    def open_receptacle(self, fixture_id: str) -> dict[str, Any]:
        return self._blocked_manipulation("open_receptacle", fixture_id=fixture_id)

    def place(self, fixture_id: str) -> dict[str, Any]:
        return self._blocked_manipulation("place", fixture_id=fixture_id)

    def place_inside(self, fixture_id: str) -> dict[str, Any]:
        return self._blocked_manipulation("place_inside", fixture_id=fixture_id)

    def close_receptacle(self, fixture_id: str) -> dict[str, Any]:
        return self._blocked_manipulation("close_receptacle", fixture_id=fixture_id)

    def done(self, reason: str = "") -> dict[str, Any]:
        self._count("done")
        total_waypoints = len(self.metric_map().get("inspection_waypoints") or [])
        coverage = len(self._observed_waypoint_ids) / total_waypoints if total_waypoints else 1.0
        completion = (
            "physical_agibot_cleanup_pilot_rehearsal"
            if not self.real_movement_enabled
            else "physical_agibot_cleanup_pilot_complete"
        )
        score = {
            "completion_status": completion,
            "cleanup_status": completion,
            "restored_count": 0,
            "total_targets": 0,
            "object_results": [],
            "mess_restoration_rate": 0.0,
            "sweep_coverage_rate": round(coverage, 6),
            "disturbance_count": 0,
            "semantic_acceptability": {
                "accepted_count": 0,
                "total_targets": 0,
                "acceptance_rate": 0.0,
            },
        }
        return {
            "ok": True,
            "tool": "done",
            "status": "ok",
            "reason": reason,
            "cleanup_status": completion,
            "score": score,
            "final_locations": self.scenario.object_locations(),
            "final_containment": {},
            "tool_event_counts": dict(self._tool_event_counts),
            "contract": REALWORLD_CONTRACT,
            "policy_uses_private_truth": False,
        }

    def agent_view_payload(self) -> dict[str, Any]:
        metric_map = self.metric_map()
        fixture_hints = self.fixture_hints()
        runtime_metric_map = self.runtime_metric_map_payload(
            metric_map=metric_map,
            fixture_hints=fixture_hints,
        )
        return {
            "contract": REALWORLD_CONTRACT,
            "perception_mode": self.perception_mode,
            "structured_detections_available": False,
            "metric_map": metric_map,
            "runtime_metric_map": runtime_metric_map,
            "fixture_hints": fixture_hints,
            "observed_objects": [],
            "raw_fpv_observations": [dict(item) for item in self._raw_fpv_observations],
            "camera_model_policy_evidence": self.camera_model_policy_payload(),
            "model_declared_observations": [],
            "model_declared_observation_evidence": {
                "schema": "model_declared_observations_v1",
                "perception_mode": self.perception_mode,
                "observation_count": 0,
                "resolved_count": 0,
                "acted_count": 0,
                "observations": [],
                "private_truth_included": False,
            },
            "policy_view": self.policy_view_payload(),
            "cleanup_worklist": self.cleanup_worklist_payload(),
            "observed_waypoint_ids": sorted(self._observed_waypoint_ids),
            "public_tool_names": self.public_tool_names(),
            "forbidden_private_fields_absent": True,
        }

    def runtime_metric_map_payload(
        self,
        *,
        metric_map: dict[str, Any] | None = None,
        fixture_hints: dict[str, Any] | None = None,
        cleanup_worklist: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        del cleanup_worklist
        public_metric_map = metric_map if metric_map is not None else self.metric_map()
        public_fixture_hints = fixture_hints if fixture_hints is not None else self.fixture_hints()
        return {
            "schema": "runtime_metric_map_v1",
            "contract": REALWORLD_CONTRACT,
            "freshness": "current_run",
            "map_mode": "agibot_minimal_map_context",
            "minimal_map_mode": True,
            "source_map_mutated": False,
            "private_truth_included": False,
            "static_map": {
                "rooms": [dict(item) for item in public_metric_map.get("rooms") or []],
                "fixtures": [
                    dict(fixture)
                    for room in public_fixture_hints.get("rooms") or []
                    for fixture in room.get("fixtures") or []
                ],
                "inspection_waypoints": [
                    dict(item) for item in public_metric_map.get("inspection_waypoints") or []
                ],
                "driveable_ways": [
                    dict(item) for item in public_metric_map.get("driveable_ways") or []
                ],
                "contains_runtime_observations": False,
                "map_mode": "agibot_minimal_map_context",
                "minimal_map_mode": True,
            },
            "public_semantic_anchors": [],
            "observed_objects": [],
            "map_update_candidates": [],
            "visited_waypoint_ids": sorted(self._visited_waypoint_ids),
            "observed_waypoint_ids": sorted(self._observed_waypoint_ids),
            "cleanup_worklist_summary": {
                "schema": CLEANUP_WORKLIST_SCHEMA,
                "object_count": 0,
                "pending_count": 0,
                "held_object_id": None,
                "prior_count": 0,
            },
            "producer_summary": {
                "observed_object_count": 0,
                "public_semantic_anchor_count": 0,
                "map_update_candidate_count": 0,
            },
        }

    def cleanup_worklist_payload(self, *, fixture_hints: dict[str, Any] | None = None) -> dict:
        del fixture_hints
        return {
            "schema": CLEANUP_WORKLIST_SCHEMA,
            "waypoint_source": "agibot_sdk_agent_view_export",
            "held_object_id": None,
            "objects": [],
            "waypoints": [
                {
                    "waypoint_id": str(item.get("waypoint_id") or ""),
                    "room_id": str(item.get("room_id") or ""),
                    "state": "visited"
                    if str(item.get("waypoint_id") or "") in self._observed_waypoint_ids
                    else "unvisited",
                    "purpose": str(item.get("purpose") or "inspect_fixture"),
                    "waypoint_source": str(item.get("waypoint_source") or ""),
                }
                for item in self.metric_map().get("inspection_waypoints") or []
            ],
            "rooms": [],
            "public_policy_note": (
                "Agibot shared cleanup MCP path exposes navigation and perception only; "
                "physical manipulation remains blocked."
            ),
        }

    def camera_model_policy_payload(self) -> dict[str, Any]:
        return {
            "schema": "camera_model_policy_v1",
            "perception_mode": self.perception_mode,
            "enabled": True,
            "model_provenance": "agibot_g2_policy_camera",
            "visual_grounding_pipeline_id": self.visual_grounding_pipeline_id,
            "visual_grounding_pipeline_ids": [self.visual_grounding_pipeline_id],
            "visual_grounding_failure_count": 0,
            "event_count": len(self._raw_fpv_observations),
            "candidate_count": 0,
            "unresolved_count": 0,
            "duplicate_rate": 0.0,
            "events": [],
            "private_truth_included": False,
            "policy_note": "Agibot G2 head_color evidence is robot-local public perception.",
        }

    def policy_view_payload(self) -> dict[str, Any]:
        return {
            "schema": "realworld_cleanup_policy_view_v1",
            "policy_observation_camera": "head_color",
            "allowed_inputs": [
                "metric_map",
                "runtime_metric_map",
                "fixture_hints",
                "raw_fpv_observations",
                "navigation_status",
            ],
            "excluded_report_only_views": ["private_operator_evidence", "private_evaluation"],
            "public_contract_note": (
                "Agibot G2 policy input uses head_color and public map context."
            ),
        }

    def private_evaluation_payload(self, score: dict[str, Any]) -> dict[str, Any]:
        return {
            "generated_mess_count": 0,
            "generated_mess_set": [],
            "acceptable_destination_sets": {},
            "mess_restoration_rate": score.get("mess_restoration_rate", 0.0),
            "sweep_coverage_rate": score.get("sweep_coverage_rate", 0.0),
            "disturbance_count": score.get("disturbance_count", 0),
            "completion_status": score.get("completion_status", ""),
            "object_results": [],
            "public_contract_note": "Agibot shared MCP pilot does not run private cleanup scoring.",
        }

    def attach_raw_fpv_observation_artifact(
        self,
        observation_id: str,
        *,
        views: dict[str, Any],
        robot_view_label: str | None = None,
        camera_control_contract: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        del views, robot_view_label, camera_control_contract
        for item in self._raw_fpv_observations:
            if item.get("observation_id") == observation_id:
                return dict(item)
        return None

    def backend_name(self) -> str:
        return AGIBOT_SDK_RUNNER_BACKEND

    def run_result_overrides(self) -> dict[str, Any]:
        return {
            "cleanup_profile": REAL_ROBOT_CLEANUP_PROFILE,
            "cleanup_profile_metadata": contract_profile_metadata(REAL_ROBOT_CLEANUP_PROFILE),
            "backend": AGIBOT_SDK_RUNNER_BACKEND,
            "backend_variant": AGIBOT_GDK_BACKEND_VARIANT,
            "primitive_provenance": AGIBOT_GDK_NORMAL_NAVI_PROVENANCE
            if self._has_successful_gdk_navigation()
            else BLOCKED_CAPABILITY_PROVENANCE,
            "generated_mess_count": 0,
            "requested_generated_mess_count": 0,
            "manipulation_evidence": {
                "schema": "physical_manipulation_block_v1",
                "status": BLOCKED_CAPABILITY_PROVENANCE,
                "primitive_provenance": BLOCKED_CAPABILITY_PROVENANCE,
                "planner_backed": False,
                "strict_proof_eligible": False,
                "api_semantic_state_edits": False,
                "physical_robot": True,
                "backend": AGIBOT_GDK_BACKEND_VARIANT,
                "evidence_note": "Agibot shared cleanup MCP intentionally blocks manipulation.",
                "blockers": list(BLOCKED_MANIPULATION_TOOLS),
            },
            "agibot_sdk_runner": {
                "schema": "agibot_sdk_runner_boundary_v1",
                "backend_variant": AGIBOT_GDK_BACKEND_VARIANT,
                "runner_script": str(self.adapter.runner_script),
                "real_movement_enabled": self.real_movement_enabled,
                "gdk_imported_by_roboclaws": False,
                "public_tool_boundary": self.public_tool_names(),
            },
        }

    def real_robot_readiness_payload(self, trace_events: list[dict[str, Any]]) -> dict[str, Any]:
        del trace_events
        total_waypoints = len(self.metric_map().get("inspection_waypoints") or [])
        observed_rate = (
            len(self._observed_waypoint_ids) / total_waypoints if total_waypoints else 1.0
        )
        movement_complete = self.real_movement_enabled and self._has_successful_gdk_navigation()
        return {
            "schema": "real_robot_readiness_v1",
            "status": "physical_agibot_cleanup_pilot_complete"
            if movement_complete
            else "physical_agibot_cleanup_pilot_rehearsal",
            "backend_variant": AGIBOT_GDK_BACKEND_VARIANT,
            "movement_enabled": self.real_movement_enabled,
            "physical_navigation_pilot": True,
            "physical_cleanup_ready": False,
            "manipulation_ready": False,
            "visited_waypoint_ids": sorted(self._visited_waypoint_ids),
            "observed_waypoint_ids": sorted(self._observed_waypoint_ids),
            "observed_waypoint_rate": round(observed_rate, 6),
            "human_takeover_stop": False,
        }

    def _remember_navigation(self, response: dict[str, Any]) -> dict[str, Any]:
        response = dict(response)
        waypoint_id = str(response.get("waypoint_id") or "")
        if waypoint_id:
            self._current_waypoint_id = waypoint_id
            self._visited_waypoint_ids.add(waypoint_id)
        return response

    def _raw_observation_from_response(
        self,
        response: dict[str, Any],
        *,
        waypoint_id: str,
    ) -> dict[str, Any]:
        artifact = response.get("camera_artifact") or response.get("fpv_image") or ""
        provenance = str(response.get("primitive_provenance") or "")
        return {
            "schema": "raw_fpv_observation_v1",
            "observation_id": str(
                response.get("observation_id") or f"agibot_observe_{time.time_ns()}"
            ),
            "source": "agibot_g2_policy_camera",
            "camera": str(
                response.get("policy_observation_camera")
                or response.get("would_capture_camera")
                or "head_color"
            ),
            "waypoint_id": waypoint_id,
            "perception_mode": self.perception_mode,
            "status": "ok" if response.get("ok") else "blocked_capability",
            "ok": bool(response.get("ok")),
            "primitive_provenance": provenance or BLOCKED_CAPABILITY_PROVENANCE,
            "image_artifacts": {"fpv": artifact} if artifact else {},
            "private_target_truth_included": False,
        }

    def _blocked_manipulation(
        self,
        tool: str,
        *,
        object_id: str = "",
        fixture_id: str = "",
    ) -> dict[str, Any]:
        extra = {}
        if object_id:
            extra["object_id"] = object_id
        if fixture_id:
            extra["fixture_id"] = fixture_id
            extra["receptacle_id"] = fixture_id
        return self._blocked(
            tool,
            "physical_manipulation_unproven",
            "Agibot physical manipulation remains blocked in the cleanup pilot.",
            extra=extra,
        )

    def _blocked(
        self,
        tool: str,
        failure_type: str,
        message: str,
        *,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = {
            "ok": False,
            "tool": tool,
            "status": "blocked_capability",
            "contract": REALWORLD_CONTRACT,
            "primitive_provenance": BLOCKED_CAPABILITY_PROVENANCE,
            "error_reason": "blocked_capability",
            "failure_type": failure_type,
            "backend_error_summary": message,
            "physical_navigation_pilot": True,
            "physical_cleanup_ready": False,
            "manipulation_ready": False,
        }
        if extra:
            payload.update(extra)
        return payload

    def _has_successful_gdk_navigation(self) -> bool:
        return any(
            item.get("primitive_provenance") == AGIBOT_GDK_NORMAL_NAVI_PROVENANCE and item.get("ok")
            for item in self.adapter.subphase_results
        )

    def _count(self, tool: str) -> None:
        self._tool_event_counts[f"{tool}:request"] = (
            self._tool_event_counts.get(f"{tool}:request", 0) + 1
        )
