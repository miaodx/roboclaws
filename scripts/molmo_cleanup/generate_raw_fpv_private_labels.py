#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    REPO_ROOT = Path(__file__).resolve().parents[2]
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))
else:
    REPO_ROOT = Path(__file__).resolve().parents[2]

from roboclaws.core.json_sources import read_json_object, read_jsonl_objects  # noqa: E402
from roboclaws.household.subprocess_backend import MolmoSpacesSubprocessBackend  # noqa: E402

MANIFEST_SCHEMA = "raw_fpv_private_label_manifest_v1"
REPORT_SCHEMA = "raw_fpv_private_label_generation_report_v1"
DEFAULT_RUN_DIR = Path("output/household/household-cleanup/codex-camera-raw/0606_1537/seed-7")
DEFAULT_OUTPUT_ROOT = Path("output/molmo/raw-fpv-private-labels")
LABEL_SCOPE_GENERATED_TARGETS = "generated-targets"
LABEL_SCOPE_CLEANUP_VISIBLE_MOVABLE = "cleanup-visible-movable"

SCREEN_GRID_REGIONS = (
    "upper_left",
    "upper_center",
    "upper_right",
    "middle_left",
    "center",
    "middle_right",
    "lower_left",
    "lower_center",
    "lower_right",
)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    report = generate_private_labels(args)
    print(json.dumps(_console_summary(report), indent=2, sort_keys=True))
    return 0 if report.get("status") in {"success", "partial"} else 2


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a scorer-only private RAW-FPV label manifest for fixed saved "
            "cleanup frames. Labels are derived by replaying saved robot poses and "
            "scorer-private generated-mess objects with MuJoCo segmentation."
        ),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--run-dir", type=Path, default=DEFAULT_RUN_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--max-observations", type=_non_negative_int_arg, default=0)
    parser.add_argument("--min-object-pixels", type=_positive_int_arg, default=12)
    parser.add_argument("--render-width", type=_positive_int_arg, default=540)
    parser.add_argument("--render-height", type=_positive_int_arg, default=360)
    parser.add_argument(
        "--label-scope",
        choices=(LABEL_SCOPE_GENERATED_TARGETS, LABEL_SCOPE_CLEANUP_VISIBLE_MOVABLE),
        default=LABEL_SCOPE_GENERATED_TARGETS,
        help=(
            "generated-targets preserves the live hidden-target recovery scorer. "
            "cleanup-visible-movable labels all cleanup-family movable objects for "
            "visible_movable_label_quality."
        ),
    )
    parser.add_argument(
        "--replay-mode",
        choices=("full_trace", "pre_cleanup_sweep"),
        default="full_trace",
        help=(
            "full_trace applies scorer-private equivalents of successful pick/place chains "
            "before labeling later observations; pre_cleanup_sweep stops before the first "
            "cleanup mutation."
        ),
    )
    parser.add_argument(
        "--keep-replay-artifacts",
        action="store_true",
        help="Keep private replay robot-view images under the output directory for debugging.",
    )
    return parser.parse_args(argv)


def generate_private_labels(args: argparse.Namespace) -> dict[str, Any]:
    source_run_dir = args.run_dir.expanduser()
    source_state_path = source_run_dir / "molmospaces_backend_state.json"
    trace_path = source_run_dir / "trace.jsonl"
    if not source_state_path.is_file():
        raise FileNotFoundError(source_state_path)
    if not trace_path.is_file():
        raise FileNotFoundError(trace_path)

    output_run_dir = _output_run_dir(args.output_dir, args.run_id)
    output_run_dir.mkdir(parents=True, exist_ok=True)

    source_state = _load_json(source_state_path)
    trace_rows = _iter_trace_rows(trace_path)
    observations = observations_from_trace(trace_rows, replay_mode=args.replay_mode)
    if args.max_observations and args.max_observations > 0:
        observations = observations[: int(args.max_observations)]
    generated_manifest = generated_mess_manifest_from_state(source_state)
    manifest_path = output_run_dir / "generated_mess_manifest.private.json"
    manifest_path.write_text(
        json.dumps(generated_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    replay_root: Path
    temporary_replay_root: tempfile.TemporaryDirectory[str] | None = None
    if args.keep_replay_artifacts:
        replay_root = output_run_dir / "private_replay"
        replay_root.mkdir(exist_ok=True)
    else:
        temporary_replay_root = tempfile.TemporaryDirectory(
            prefix="roboclaws_raw_fpv_private_labels_"
        )
        replay_root = Path(temporary_replay_root.name)

    labels: list[dict[str, Any]] = []
    frame_summaries: list[dict[str, Any]] = []
    try:
        backend = MolmoSpacesSubprocessBackend(
            run_dir=replay_root / "backend",
            seed=int(source_state.get("seed") or 7),
            python_executable=Path(str(source_state.get("python_executable") or sys.executable)),
            scene_source=str(source_state.get("scene_source") or "procthor-10k-val"),
            scene_index=int(source_state.get("scene_index") or 0),
            include_robot=True,
            robot_name=str(source_state.get("robot_name") or "rby1m"),
            generated_mess_count=len(generated_manifest["targets"]),
            generated_mess_manifest_path=manifest_path,
        )
        if args.replay_mode == "full_trace":
            labels, frame_summaries = _label_full_trace(
                backend,
                trace_rows=trace_rows,
                source_run_dir=source_run_dir,
                source_state=source_state,
                max_observations=int(args.max_observations or 0),
                output_dir=replay_root / "robot_views",
                min_object_pixels=int(args.min_object_pixels),
                render_width=int(args.render_width),
                render_height=int(args.render_height),
                label_scope=str(args.label_scope),
            )
        else:
            for observation in observations:
                frame_labels, frame_summary = _label_observation(
                    backend,
                    source_run_dir=source_run_dir,
                    source_state=source_state,
                    observation=observation,
                    output_dir=replay_root / "robot_views",
                    min_object_pixels=int(args.min_object_pixels),
                    render_width=int(args.render_width),
                    render_height=int(args.render_height),
                    label_scope=str(args.label_scope),
                )
                labels.extend(frame_labels)
                frame_summaries.append(frame_summary)
    finally:
        if temporary_replay_root is not None:
            temporary_replay_root.cleanup()
        elif not args.keep_replay_artifacts:
            shutil.rmtree(replay_root, ignore_errors=True)

    manifest = {
        "schema": MANIFEST_SCHEMA,
        "generated_at": _utc_timestamp(),
        "provenance": {
            "label_source": "private_molmospaces_replay_fpv_segmentation",
            "source_run_dir": str(source_run_dir),
            "source_trace": str(trace_path),
            "source_backend_state": str(source_state_path),
            "replay_mode": args.replay_mode,
            "label_scope": args.label_scope,
            "first_sweep_only": args.replay_mode == "pre_cleanup_sweep",
            "scorer_only": True,
            "private_truth_included_in_prompt_inputs": False,
        },
        "source_run": {
            "run_id": _run_id_for_path(source_run_dir),
            "seed": source_state.get("seed"),
            "scene_source": source_state.get("scene_source"),
            "scene_index": source_state.get("scene_index"),
            "generated_mess_count": len(generated_manifest["targets"]),
            "selected_object_count": len(source_state.get("selected_object_ids") or []),
        },
        "labels": labels,
    }
    manifest_output_path = output_run_dir / "raw_fpv_private_label_manifest.json"
    manifest_output_path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    labeled_frame_count = len({str(item.get("frame_id") or "") for item in labels})
    unique_object_count = len({str(item.get("object_id") or "") for item in labels})
    status = (
        "success"
        if labels
        and (
            str(args.label_scope) == LABEL_SCOPE_CLEANUP_VISIBLE_MOVABLE
            or unique_object_count >= len(generated_manifest["targets"])
        )
        else "partial"
    )
    report = {
        "schema": REPORT_SCHEMA,
        "status": status,
        "generated_at": _utc_timestamp(),
        "output_dir": str(output_run_dir),
        "source_run_dir": str(source_run_dir),
        "replay_mode": args.replay_mode,
        "label_scope": args.label_scope,
        "observation_count": len(observations),
        "first_sweep_observation_count": len(
            observations_from_trace(trace_rows, replay_mode="pre_cleanup_sweep")
        ),
        "label_count": len(labels),
        "labeled_frame_count": labeled_frame_count,
        "unique_labeled_object_count": unique_object_count,
        "selected_object_count": len(generated_manifest["targets"]),
        "min_object_pixels": int(args.min_object_pixels),
        "artifacts": {
            "manifest": str(manifest_output_path),
            "generated_mess_manifest": str(manifest_path),
            "private_replay": str(replay_root) if args.keep_replay_artifacts else "",
        },
        "frames": frame_summaries,
    }
    (output_run_dir / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return report


def first_sweep_observations_from_trace(trace_path: Path) -> list[dict[str, Any]]:
    return observations_from_trace(_iter_trace_rows(trace_path), replay_mode="pre_cleanup_sweep")


def observations_from_trace(
    trace_rows: list[dict[str, Any]],
    *,
    replay_mode: str,
) -> list[dict[str, Any]]:
    observations: list[dict[str, Any]] = []
    stop_tools = {"pick", "place", "place_inside", "open_receptacle", "close_receptacle"}
    for row in trace_rows:
        if row.get("event") == "request" and str(row.get("tool") or "") in stop_tools:
            if replay_mode == "pre_cleanup_sweep":
                break
        if row.get("event") != "response" or row.get("tool") != "observe":
            continue
        response = row.get("response") if isinstance(row.get("response"), dict) else {}
        raw = _raw_fpv_observation_from_response(response)
        if not raw or not raw.get("observation_id"):
            continue
        observations.append(_observation_from_raw(raw))
    return observations


def placement_bindings_from_trace(trace_rows: list[dict[str, Any]]) -> dict[str, dict[str, str]]:
    bindings = {}
    for row in trace_rows:
        if row.get("event") != "response" or row.get("tool") not in {"place", "place_inside"}:
            continue
        response = row.get("response") if isinstance(row.get("response"), dict) else {}
        if not response.get("ok"):
            continue
        public_object_id = str(response.get("object_id") or "")
        diagnostic = response.get("placement_diagnostic")
        if not public_object_id or not isinstance(diagnostic, dict):
            continue
        private_object_id = str(diagnostic.get("object_id") or "")
        receptacle_id = str(diagnostic.get("receptacle_id") or "")
        relation = str(diagnostic.get("relation") or "")
        if private_object_id and receptacle_id:
            bindings[public_object_id] = {
                "private_object_id": private_object_id,
                "receptacle_id": receptacle_id,
                "relation": relation if relation in {"on", "inside"} else "on",
                "place_tool": str(row.get("tool") or "place"),
            }
    return bindings


def generated_mess_manifest_from_state(state: dict[str, Any]) -> dict[str, Any]:
    manifest_targets: list[dict[str, Any]] = []
    by_object = {
        str(item.get("object_id") or ""): item
        for item in state.get("mess_placement_diagnostics") or []
        if isinstance(item, dict)
    }
    private_targets = (state.get("private_manifest") or {}).get("targets") or []
    for index, raw_target in enumerate(private_targets):
        if not isinstance(raw_target, dict):
            continue
        object_id = str(raw_target.get("object_id") or "")
        if not object_id:
            continue
        placement = by_object.get(object_id) or {}
        target_receptacle_ids = [
            str(item)
            for item in (
                raw_target.get("valid_receptacle_ids") or [raw_target.get("target_receptacle_id")]
            )
            if str(item)
        ]
        start_receptacle_id = str(placement.get("receptacle_id") or "")
        relation = str(placement.get("relation") or "on")
        if relation not in {"on", "inside"}:
            relation = "on"
        category = str(
            placement.get("object_category")
            or ((state.get("objects") or {}).get(object_id) or {}).get("category")
            or ""
        )
        manifest_targets.append(
            {
                "object_id": object_id,
                "category": category,
                "target_receptacle_id": target_receptacle_ids[0] if target_receptacle_ids else "",
                "valid_receptacle_ids": target_receptacle_ids,
                "start_receptacle_id": start_receptacle_id,
                "relation": relation,
                "placement_index": index,
            }
        )
    return {
        "schema": "roboclaws_generated_mess_manifest_v1",
        "provenance": "reconstructed_from_private_saved_backend_state",
        "scene": {
            "scene_source": state.get("scene_source"),
            "scene_index": state.get("scene_index"),
            "scene_metadata_source": "saved_molmospaces_backend_state",
        },
        "selection": {
            "selector": "saved_private_manifest.targets",
            "seed": state.get("seed"),
            "requested_generated_mess_count": len(manifest_targets),
        },
        "requested_generated_mess_count": len(manifest_targets),
        "generated_mess_count": len(manifest_targets),
        "success_threshold": int(
            (state.get("private_manifest") or {}).get("success_threshold") or 0
        ),
        "targets": manifest_targets,
    }


def _label_observation(
    backend: MolmoSpacesSubprocessBackend,
    *,
    source_run_dir: Path,
    source_state: dict[str, Any],
    observation: dict[str, Any],
    output_dir: Path,
    min_object_pixels: int,
    render_width: int,
    render_height: int,
    label_scope: str = LABEL_SCOPE_GENERATED_TARGETS,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    state = backend._read_state()  # noqa: SLF001 - private scorer replay utility.
    state["robot_pose"] = dict(observation.get("robot_pose") or {})
    _apply_robot_pose_to_qpos(state)
    backend.state_path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")

    frame_id = f"{_run_id_for_path(source_run_dir)}/{observation['observation_id']}"
    labels = []
    frame_summary = {
        "frame_id": frame_id,
        "source_observation_id": observation["observation_id"],
        "waypoint_id": observation.get("waypoint_id") or "",
        "image_artifact": observation.get("image_artifact") or "",
        "labels": [],
    }
    for object_id in label_object_ids_for_scope(source_state, label_scope=label_scope):
        result = backend.write_robot_views_with_resolution(
            output_dir,
            label=f"{observation['observation_id']}_{_safe_filename(str(object_id))}",
            width=render_width,
            height=render_height,
            focus_object_id=str(object_id),
        )
        focus = result.get("focus") or {}
        visibility = focus.get("fpv_visibility") or {}
        box = _object_box_from_visibility(visibility)
        pixels = int((box or {}).get("pixels") or 0)
        if box is None or pixels < min_object_pixels:
            continue
        bbox = normalize_box_xywh(box["bbox"], width=render_width, height=render_height)
        label = {
            "frame_id": frame_id,
            "source_observation_id": observation["observation_id"],
            "object_id": str(object_id),
            "category": str(focus.get("object_category") or ""),
            "bbox": bbox,
            "coarse_regions": coarse_regions_from_bbox(bbox),
            "surface_hint": surface_hint_from_focus(focus),
            "label_source": "private_molmospaces_replay_fpv_segmentation",
            "private": True,
            "hidden_target": label_scope == LABEL_SCOPE_GENERATED_TARGETS,
            "pixel_bbox": list(box["bbox"]),
            "object_pixels": pixels,
        }
        labels.append(label)
        frame_summary["labels"].append(
            {
                "object_id": str(object_id),
                "category": label["category"],
                "bbox": bbox,
                "coarse_regions": label["coarse_regions"],
                "object_pixels": pixels,
            }
        )
    return labels, frame_summary


def _label_full_trace(
    backend: MolmoSpacesSubprocessBackend,
    *,
    trace_rows: list[dict[str, Any]],
    source_run_dir: Path,
    source_state: dict[str, Any],
    max_observations: int,
    output_dir: Path,
    min_object_pixels: int,
    render_width: int,
    render_height: int,
    label_scope: str = LABEL_SCOPE_GENERATED_TARGETS,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    labels: list[dict[str, Any]] = []
    frame_summaries: list[dict[str, Any]] = []
    bindings = placement_bindings_from_trace(trace_rows)
    held_public_object_id = ""
    observed_count = 0
    for row in trace_rows:
        if str(row.get("event") or "") != "response":
            continue
        response = row.get("response") if isinstance(row.get("response"), dict) else {}
        tool = str(row.get("tool") or "")
        if tool == "observe":
            frame_labels, frame_summary, observed_count = _label_observe_response(
                backend,
                response=response,
                observed_count=observed_count,
                source_run_dir=source_run_dir,
                source_state=source_state,
                max_observations=max_observations,
                output_dir=output_dir,
                min_object_pixels=min_object_pixels,
                render_width=render_width,
                render_height=render_height,
                label_scope=label_scope,
            )
            if not frame_summary:
                continue
            labels.extend(frame_labels)
            frame_summaries.append(frame_summary)
            continue
        held_public_object_id = _replay_trace_action_response(
            backend,
            tool=tool,
            response=response,
            bindings=bindings,
            held_public_object_id=held_public_object_id,
        )
    return labels, frame_summaries


def _label_observe_response(
    backend: MolmoSpacesSubprocessBackend,
    *,
    response: dict[str, Any],
    observed_count: int,
    source_run_dir: Path,
    source_state: dict[str, Any],
    max_observations: int,
    output_dir: Path,
    min_object_pixels: int,
    render_width: int,
    render_height: int,
    label_scope: str,
) -> tuple[list[dict[str, Any]], dict[str, Any], int]:
    raw = _raw_fpv_observation_from_response(response)
    if not raw or not raw.get("observation_id"):
        return [], {}, observed_count
    observed_count += 1
    if max_observations and observed_count > max_observations:
        return [], {}, observed_count
    frame_labels, frame_summary = _label_observation(
        backend,
        source_run_dir=source_run_dir,
        source_state=source_state,
        observation=_observation_from_raw(raw),
        output_dir=output_dir,
        min_object_pixels=min_object_pixels,
        render_width=render_width,
        render_height=render_height,
        label_scope=label_scope,
    )
    return frame_labels, frame_summary, observed_count


def _replay_trace_action_response(
    backend: MolmoSpacesSubprocessBackend,
    *,
    tool: str,
    response: dict[str, Any],
    bindings: dict[str, dict[str, str]],
    held_public_object_id: str,
) -> str:
    if not response.get("ok"):
        return held_public_object_id
    if tool == "pick":
        return _replay_pick_response(backend, response=response, bindings=bindings)
    if tool == "navigate_to_receptacle" and held_public_object_id:
        binding = bindings.get(held_public_object_id)
        if binding:
            backend.navigate_to_receptacle(binding["receptacle_id"])
    elif tool in {"place", "place_inside"}:
        public_object_id = str(response.get("object_id") or held_public_object_id)
        if _replay_place_response(backend, public_object_id=public_object_id, bindings=bindings):
            return ""
    return held_public_object_id


def _replay_pick_response(
    backend: MolmoSpacesSubprocessBackend,
    *,
    response: dict[str, Any],
    bindings: dict[str, dict[str, str]],
) -> str:
    public_object_id = str(response.get("object_id") or "")
    binding = bindings.get(public_object_id)
    if not binding:
        return ""
    private_object_id = binding["private_object_id"]
    backend.navigate_to_object(private_object_id)
    backend.pick(private_object_id)
    return public_object_id


def _replay_place_response(
    backend: MolmoSpacesSubprocessBackend,
    *,
    public_object_id: str,
    bindings: dict[str, dict[str, str]],
) -> bool:
    binding = bindings.get(public_object_id)
    if not binding:
        return False
    if binding["place_tool"] == "place_inside":
        backend.place_inside(binding["receptacle_id"])
    else:
        backend.place(binding["receptacle_id"])
    return True


def _observation_from_raw(raw: dict[str, Any]) -> dict[str, Any]:
    robot_pose = (
        ((raw.get("camera_control_contract") or {}).get("robot_pose") or {})
        if isinstance(raw.get("camera_control_contract"), dict)
        else {}
    )
    return {
        "observation_id": str(raw.get("observation_id") or ""),
        "waypoint_id": str(raw.get("waypoint_id") or ""),
        "room_id": str(raw.get("room_id") or "generated_area"),
        "image_artifact": str((raw.get("image_artifacts") or {}).get("fpv") or ""),
        "robot_view_label": str(raw.get("robot_view_label") or ""),
        "robot_pose": dict(robot_pose) if isinstance(robot_pose, dict) else {},
    }


def normalize_box_xywh(
    xyxy: list[int] | tuple[int, int, int, int],
    *,
    width: int,
    height: int,
) -> list[float]:
    left, top, right, bottom = [float(value) for value in xyxy]
    box_width = max(0.0, right - left + 1.0)
    box_height = max(0.0, bottom - top + 1.0)
    return [
        round(max(0.0, min(1.0, left / float(width))), 6),
        round(max(0.0, min(1.0, top / float(height))), 6),
        round(max(0.0, min(1.0, box_width / float(width))), 6),
        round(max(0.0, min(1.0, box_height / float(height))), 6),
    ]


def coarse_regions_from_bbox(bbox: list[float]) -> list[str]:
    x, y, width, height = bbox
    center_x = max(0.0, min(0.999, x + width / 2.0))
    center_y = max(0.0, min(0.999, y + height / 2.0))
    col = 0 if center_x < 1 / 3 else 1 if center_x < 2 / 3 else 2
    row = 0 if center_y < 1 / 3 else 1 if center_y < 2 / 3 else 2
    return [SCREEN_GRID_REGIONS[row * 3 + col]]


def surface_hint_from_focus(focus: dict[str, Any]) -> str:
    text = (
        f"{focus.get('object_location_relation', '')} "
        f"{focus.get('receptacle_category', '')} "
        f"{focus.get('receptacle_label', '')}"
    ).lower()
    if "floor" in text:
        return "floor"
    if "table" in text or "counter" in text or "desk" in text or "stand" in text:
        return "table" if "table" in text or "desk" in text or "stand" in text else "counter"
    if "shelf" in text:
        return "shelf"
    if "bed" in text:
        return "bed"
    if "sofa" in text:
        return "sofa"
    return "unknown"


def label_object_ids_for_scope(state: dict[str, Any], *, label_scope: str) -> list[str]:
    if label_scope == LABEL_SCOPE_GENERATED_TARGETS:
        return [str(object_id) for object_id in state.get("selected_object_ids") or []]
    objects = state.get("objects") if isinstance(state.get("objects"), dict) else {}
    return [
        str(object_id)
        for object_id, item in sorted(objects.items())
        if isinstance(item, dict) and _category_family(item.get("category"))
    ]


def _category_family(value: Any) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "", str(value or "").lower())
    if not normalized:
        return ""
    fixture_terms = {
        "armchair",
        "bed",
        "bookcase",
        "bookshelf",
        "cabinet",
        "counter",
        "desk",
        "dresser",
        "floor",
        "fridge",
        "refrigerator",
        "shelf",
        "sink",
        "sofa",
        "table",
    }
    if any(term in normalized for term in fixture_terms):
        return ""
    families = {
        "dish": {"dish", "dishware", "dishsponge", "plate", "bowl", "cup", "mug", "teacup"},
        "food": {"food", "potato", "irishpotato", "apple", "fruit", "vegetable", "bread"},
        "electronics": {
            "electronics",
            "remote",
            "remotecontrol",
            "tvremote",
            "cellphone",
            "phone",
            "laptop",
        },
        "linen": {"linen", "pillow", "cushion", "towel", "blanket", "cloth"},
        "toy": {"toy", "ball", "basketball", "baseballbat"},
        "book": {"book", "notebook", "newspaper"},
    }
    for family, members in families.items():
        if normalized in members or any(normalized.startswith(member) for member in members):
            return family
    return ""


def _object_box_from_visibility(visibility: dict[str, Any]) -> dict[str, Any] | None:
    boxes = [
        item
        for item in visibility.get("boxes") or []
        if isinstance(item, dict) and item.get("source") in {"segmentation", "highlight_diff"}
    ]
    if not boxes:
        return None
    return max(boxes, key=lambda item: int(item.get("pixels") or 0))


def _apply_robot_pose_to_qpos(state: dict[str, Any]) -> None:
    pose = state.get("robot_pose") or {}
    qpos = list(state.get("qpos") or [])
    model_stats = state.get("model_stats") or {}
    if not qpos or int(model_stats.get("nq") or len(qpos)) != len(qpos):
        raise ValueError("saved backend state does not contain a usable qpos vector")
    from scripts.molmo_cleanup import molmospaces_subprocess_worker as worker

    model, data = worker._load_model_data_for_state(state)  # noqa: SLF001
    worker._apply_qpos(data, qpos)  # noqa: SLF001
    worker._set_robot_pose(model, data, pose)  # noqa: SLF001
    worker.mujoco.mj_forward(model, data)
    state["qpos"] = [float(value) for value in data.qpos]


def _raw_fpv_observation_from_response(response: dict[str, Any]) -> dict[str, Any]:
    raw = response.get("raw_fpv_observation")
    if isinstance(raw, dict):
        return raw
    compact = response.get("agent_facing_compact_state")
    if isinstance(compact, dict) and isinstance(compact.get("raw_fpv_observation"), dict):
        return compact["raw_fpv_observation"]
    return {}


def _iter_trace_rows(trace_path: Path) -> list[dict[str, Any]]:
    return read_jsonl_objects(trace_path, label="RAW-FPV private-label trace")


def _load_json(path: Path) -> dict[str, Any]:
    return read_json_object(path, label="MolmoSpaces backend state")


def _output_run_dir(output_root: Path, run_id: str) -> Path:
    if run_id:
        return output_root / _safe_filename(run_id)
    stamp = dt.datetime.now(dt.timezone(dt.timedelta(hours=8))).strftime("%Y%m%d_%H%M%S")
    return output_root / stamp


def _run_id_for_path(path: Path) -> str:
    parts = [part for part in path.parts[-4:] if part not in {"output", "household"}]
    return _safe_filename("-".join(parts))


def _safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", str(value)).strip("_") or "item"


def _utc_timestamp() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def _console_summary(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": report.get("status"),
        "manifest": (report.get("artifacts") or {}).get("manifest"),
        "label_count": report.get("label_count"),
        "labeled_frame_count": report.get("labeled_frame_count"),
        "unique_labeled_object_count": report.get("unique_labeled_object_count"),
        "report_json": str(Path(str(report.get("output_dir", ""))) / "report.json"),
    }


def _positive_int_arg(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected a positive integer; got {value!r}") from None
    if parsed <= 0:
        raise argparse.ArgumentTypeError(f"expected a positive integer; got {value!r}")
    return parsed


def _non_negative_int_arg(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"expected a non-negative integer; got {value!r}"
        ) from None
    if parsed < 0:
        raise argparse.ArgumentTypeError(f"expected a non-negative integer; got {value!r}")
    return parsed


if __name__ == "__main__":
    raise SystemExit(main())
