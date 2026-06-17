from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "molmo_cleanup" / "run_raw_fpv_perception_probe.py"
LABEL_SCRIPT_PATH = REPO_ROOT / "scripts" / "molmo_cleanup" / "generate_raw_fpv_private_labels.py"
SWEEP_SCRIPT_PATH = REPO_ROOT / "scripts" / "molmo_cleanup" / "generate_raw_fpv_sweep_corpus.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("run_raw_fpv_perception_probe", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_label_module():
    spec = importlib.util.spec_from_file_location(
        "generate_raw_fpv_private_labels", LABEL_SCRIPT_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _load_sweep_module():
    spec = importlib.util.spec_from_file_location(
        "generate_raw_fpv_sweep_corpus", SWEEP_SCRIPT_PATH
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_raw_fpv_probe_rejects_invalid_numeric_config() -> None:
    probe = _load_module()

    for flag, value in (
        ("--max-frames-per-source", "0"),
        ("--threshold", "0"),
        ("--max-candidates", "0"),
        ("--max-candidates", "4"),
        ("--timeout-s", "0"),
        ("--timeout-s", "nan"),
    ):
        try:
            probe.parse_args([flag, value])
        except SystemExit as exc:
            assert exc.code == 2
        else:  # pragma: no cover - argparse should exit for invalid input
            raise AssertionError(f"expected invalid {flag}={value} to fail at parse time")


def test_raw_fpv_probe_accepts_valid_numeric_config() -> None:
    probe = _load_module()

    args = probe.parse_args(
        [
            "--max-frames-per-source",
            "1",
            "--threshold",
            "1",
            "--max-candidates",
            "3",
            "--timeout-s",
            "0.5",
        ]
    )

    assert args.max_frames_per_source == 1
    assert args.threshold == 1
    assert args.max_candidates == 3
    assert args.timeout_s == 0.5


def test_raw_fpv_probe_keeps_private_labels_out_of_prompt_inputs(tmp_path: Path) -> None:
    probe = _load_module()
    run_dir = _raw_run_dir(tmp_path)
    labels = _write_private_labels(
        tmp_path / "private_labels.json",
        frame_id="household-cleanup-codex-camera-raw-0606_1537-seed-7/raw_fpv_001",
        object_id="private_plate_001",
        category="plate",
        bbox=[0.1, 0.2, 0.2, 0.2],
    )
    predictions = _write_predictions(
        tmp_path / "predictions.json",
        frame_id="household-cleanup-codex-camera-raw-0606_1537-seed-7/raw_fpv_001",
        category="plate",
        bbox=[0.1, 0.2, 0.2, 0.2],
        coarse_region="upper_left",
    )

    report = probe.run_probe(
        probe.parse_args(
            [
                "--raw-run-dir",
                str(run_dir),
                "--contrast-run-dir",
                str(tmp_path / "missing-contrast"),
                "--private-labels",
                str(labels),
                "--predictions",
                str(predictions),
                "--output-dir",
                str(tmp_path / "out"),
                "--run-id",
                "privacy",
                "--prompt-variant",
                "baseline_json",
            ]
        )
    )

    prompt_inputs = json.loads(Path(report["artifacts"]["prompt_inputs"]).read_text())
    prompt_text = json.dumps(prompt_inputs, sort_keys=True)
    score = json.loads(Path(report["artifacts"]["private_score"]).read_text())

    assert report["status"] == "partial"
    assert report["privacy"]["private_labels_in_prompt_inputs"] is False
    assert report["privacy"]["agent_facing_input_contains_executable_prior_handles"] is False
    assert "private_plate_001" not in prompt_text
    assert "private_plate_001" in json.dumps(score)


def test_raw_fpv_probe_scores_live_like_top_candidate_and_duplicates(tmp_path: Path) -> None:
    probe = _load_module()
    run_dir = _raw_run_dir(tmp_path, observation_ids=("raw_fpv_001", "raw_fpv_002"))
    labels = tmp_path / "private_labels.json"
    labels.write_text(
        json.dumps(
            {
                "schema": "raw_fpv_private_label_manifest_v1",
                "labels": [
                    {
                        "frame_id": (
                            "household-cleanup-codex-camera-raw-0606_1537-seed-7/raw_fpv_001"
                        ),
                        "source_observation_id": "raw_fpv_001",
                        "object_id": "private_plate_001",
                        "category": "plate",
                        "bbox": [0.1, 0.2, 0.2, 0.2],
                    },
                    {
                        "frame_id": (
                            "household-cleanup-codex-camera-raw-0606_1537-seed-7/raw_fpv_002"
                        ),
                        "source_observation_id": "raw_fpv_002",
                        "object_id": "private_plate_001",
                        "category": "plate",
                        "bbox": [0.11, 0.21, 0.2, 0.2],
                    },
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    predictions = tmp_path / "predictions.json"
    predictions.write_text(
        json.dumps(
            {
                "schema": "raw_fpv_probe_predictions_v1",
                "predictions": [
                    {
                        "variant_id": "baseline_json",
                        "frame_id": (
                            "household-cleanup-codex-camera-raw-0606_1537-seed-7/raw_fpv_001"
                        ),
                        "response": _response("raw_fpv_001", "plate", [0.1, 0.2, 0.2, 0.2]),
                    },
                    {
                        "variant_id": "baseline_json",
                        "frame_id": (
                            "household-cleanup-codex-camera-raw-0606_1537-seed-7/raw_fpv_002"
                        ),
                        "response": _response("raw_fpv_002", "plate", [0.11, 0.21, 0.2, 0.2]),
                    },
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    report = probe.run_probe(
        probe.parse_args(
            [
                "--raw-run-dir",
                str(run_dir),
                "--contrast-run-dir",
                str(tmp_path / "missing-contrast"),
                "--private-labels",
                str(labels),
                "--predictions",
                str(predictions),
                "--output-dir",
                str(tmp_path / "out"),
                "--run-id",
                "duplicates",
                "--prompt-variant",
                "baseline_json",
                "--threshold",
                "2",
            ]
        )
    )

    metrics = report["matrix"][0]["metrics"]
    live_like = metrics["live_like_top_candidate"]

    assert metrics["strict_bbox_unique_confirmable_count"] == 1
    assert metrics["coarse_unique_confirmable_count"] == 1
    assert metrics["unique_confirmable_count"] == 1
    assert metrics["duplicate_count"] >= 1
    assert live_like["strict_bbox_threshold_met"] is False
    assert live_like["coarse_threshold_met"] is False
    assert report["route_recommendation"] == "prefer_camera_grounded_labels"


def test_raw_fpv_probe_reports_coarse_locality_route(tmp_path: Path) -> None:
    probe = _load_module()
    run_dir = _raw_run_dir(tmp_path)
    labels = _write_private_labels(
        tmp_path / "private_labels.json",
        frame_id="household-cleanup-codex-camera-raw-0606_1537-seed-7/raw_fpv_001",
        object_id="private_book_001",
        category="book",
        bbox=[0.7, 0.7, 0.1, 0.1],
    )
    predictions = tmp_path / "predictions.json"
    predictions.write_text(
        json.dumps(
            {
                "schema": "raw_fpv_probe_predictions_v1",
                "predictions": [
                    {
                        "variant_id": "baseline_json",
                        "frame_id": (
                            "household-cleanup-codex-camera-raw-0606_1537-seed-7/raw_fpv_001"
                        ),
                        "response": {
                            "schema": "raw_fpv_probe_response_v1",
                            "candidates": [
                                {
                                    "source_observation_id": "raw_fpv_001",
                                    "category": "book",
                                    "evidence_note": "book visible on lower right shelf",
                                    "confidence": 0.8,
                                    "locality": {
                                        "coarse_region": "lower_right",
                                        "surface_hint": "shelf",
                                    },
                                }
                            ],
                        },
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    report = probe.run_probe(
        probe.parse_args(
            [
                "--raw-run-dir",
                str(run_dir),
                "--contrast-run-dir",
                str(tmp_path / "missing-contrast"),
                "--private-labels",
                str(labels),
                "--predictions",
                str(predictions),
                "--output-dir",
                str(tmp_path / "out"),
                "--run-id",
                "coarse",
                "--prompt-variant",
                "baseline_json",
                "--threshold",
                "1",
            ]
        )
    )

    metrics = report["matrix"][0]["metrics"]

    assert metrics["strict_bbox_unique_confirmable_count"] == 0
    assert metrics["coarse_unique_confirmable_count"] == 1
    assert report["route_recommendation"] == "try_live_coarse_locality_contract"
    assert Path(report["artifacts"]["html_report"]).is_file()


def test_raw_fpv_probe_merges_multiple_private_label_manifests(tmp_path: Path) -> None:
    probe = _load_module()
    run_dir = _raw_run_dir(tmp_path, observation_ids=("raw_fpv_001", "raw_fpv_002"))
    frame_prefix = "household-cleanup-codex-camera-raw-0606_1537-seed-7"
    first = _write_private_labels(
        tmp_path / "private_labels_a.json",
        frame_id=f"{frame_prefix}/raw_fpv_001",
        object_id="private_plate_001",
        category="plate",
        bbox=[0.1, 0.2, 0.2, 0.2],
    )
    second = _write_private_labels(
        tmp_path / "private_labels_b.json",
        frame_id=f"{frame_prefix}/raw_fpv_002",
        object_id="private_book_001",
        category="book",
        bbox=[0.5, 0.5, 0.2, 0.2],
    )
    frames = probe.collect_observation_frames(
        raw_run_dirs=(run_dir,),
        contrast_run_dirs=(),
        max_frames_per_source=4,
    )

    labels = probe.load_probe_labels(
        (first, second),
        frames=frames,
        contrast_run_dirs=(),
        default_hidden_target=True,
    )

    assert sorted(label.object_id for label in labels) == [
        "private_book_001",
        "private_plate_001",
    ]


def test_raw_fpv_probe_aliases_unique_sweep_frame_labels_by_observation_id(
    tmp_path: Path,
) -> None:
    probe = _load_module()
    run_dir = tmp_path / "output" / "molmo" / "raw-fpv-sweep-corpus" / "current-run"
    robot_views = run_dir / "robot_views"
    robot_views.mkdir(parents=True)
    Image.new("RGB", (120, 90), color=(80, 20, 20)).save(robot_views / "0001_raw_fpv_001.fpv.png")
    (run_dir / "raw_fpv_observations.json").write_text(
        json.dumps(
            {
                "schema": "raw_fpv_public_sweep_observations_v1",
                "raw_fpv_observations": [
                    {
                        "observation_id": "raw_fpv_001",
                        "waypoint_id": "generated_exploration_001",
                        "room_id": "generated_area",
                        "image_artifacts": {"fpv": "robot_views/0001_raw_fpv_001.fpv.png"},
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    label_path = _write_visible_labels(
        tmp_path / "all_visible_labels.json",
        frame_id="molmo-raw-fpv-sweep-corpus-other-run/raw_fpv_001",
        object_id="visible_mug_001",
        category="mug",
        category_family="dish",
        bbox=[0.1, 0.2, 0.2, 0.2],
    )
    frames = probe.collect_observation_frames(
        raw_run_dirs=(run_dir,),
        contrast_run_dirs=(),
        max_frames_per_source=4,
    )

    labels = probe.load_probe_labels(
        (label_path,),
        frames=frames,
        contrast_run_dirs=(),
        default_hidden_target=False,
    )

    assert len(labels) == 1
    assert labels[0].frame_id == frames[0].frame_id


def test_raw_fpv_probe_builds_visual_labeler_frame_groups(tmp_path: Path) -> None:
    probe = _load_module()
    run_dir = _raw_run_dir(
        tmp_path,
        observation_ids=(
            "raw_fpv_001",
            "raw_fpv_002",
            "raw_fpv_003",
            "raw_fpv_004",
        ),
    )
    frames = probe.collect_observation_frames(
        raw_run_dirs=(run_dir,),
        contrast_run_dirs=(),
        max_frames_per_source=8,
    )

    public_inputs = probe.build_public_inputs(frames, runtime_map_prior={}, max_candidates=3)
    groups = public_inputs["variants"]["raw_fpv_visual_labeler"]["frame_groups"]

    assert public_inputs["visual_labeler_contract"]["skill_id"] == "raw-fpv-visual-labeler"
    assert groups
    assert groups[0]["grouping_basis"] in {
        "source_waypoint_neighborhood",
        "short_source_waypoint_neighborhood",
        "source_observation_neighborhood",
    }
    assert 3 <= len(groups[0]["frames"]) <= 6
    group_text = json.dumps(groups, sort_keys=True)
    assert "private_plate_001" not in group_text
    assert "observed_" not in group_text
    assert "anchor_fixture_" not in group_text


def test_raw_fpv_visual_labeler_provider_groups_images_and_fans_out_predictions(
    tmp_path: Path,
    monkeypatch,
) -> None:
    probe = _load_module()
    run_dir = _raw_run_dir(
        tmp_path,
        observation_ids=(
            "raw_fpv_001",
            "raw_fpv_002",
            "raw_fpv_003",
        ),
    )
    frames = probe.collect_observation_frames(
        raw_run_dirs=(run_dir,),
        contrast_run_dirs=(),
        max_frames_per_source=8,
    )
    public_inputs = probe.build_public_inputs(frames, runtime_map_prior={}, max_candidates=3)
    calls: list[dict[str, object]] = []

    monkeypatch.setenv("CODEX_BASE_URL", "https://codex.example.test/v1")
    monkeypatch.setenv("CODEX_API_KEY", "test-key")

    def fake_call_responses_api(**kwargs):
        calls.append(kwargs)
        assert len(kwargs["image_paths"]) == 3
        return {
            "output_text": json.dumps(
                {
                    "schema": "raw_fpv_visual_labeler_response_v1",
                    "labels": [
                        {
                            "evidence_frame_id": frames[0].frame_id,
                            "category": "mug",
                            "category_family": "dish",
                            "coarse_region": "center",
                            "confidence": 0.8,
                            "is_cleanup_relevant": True,
                        },
                        {
                            "evidence_frame_id": frames[1].frame_id,
                            "category": "table",
                            "category_family": "fixture",
                            "coarse_region": "center",
                            "confidence": 0.8,
                            "is_cleanup_relevant": False,
                        },
                    ],
                }
            )
        }

    monkeypatch.setattr(probe, "_call_responses_api", fake_call_responses_api)

    status, errors, predictions = probe.execute_provider_variant(
        variant_id="raw_fpv_visual_labeler",
        public_inputs=public_inputs,
        output_dir=tmp_path / "responses",
        provider="codex-router-responses",
        model="test-model",
        timeout_s=1.0,
    )

    assert status == "provider_ok"
    assert errors == []
    assert len(calls) == 1
    assert set(predictions) == {frame.frame_id for frame in frames}
    assert len(predictions[frames[0].frame_id]["labels"]) == 1
    assert len(predictions[frames[1].frame_id]["labels"]) == 1
    assert predictions[frames[2].frame_id]["labels"] == []


def test_raw_fpv_visual_labeler_requires_codex_base_url(monkeypatch) -> None:
    probe = _load_module()

    monkeypatch.delenv("CODEX_BASE_URL", raising=False)
    monkeypatch.setenv("CODEX_API_KEY", "test-key")

    assert probe._provider_config("codex-router-responses") == {
        "error": {"type": "missing_env", "env": "CODEX_BASE_URL"}
    }


def test_raw_fpv_visual_labeler_requires_codex_api_key(monkeypatch) -> None:
    probe = _load_module()

    monkeypatch.setenv("CODEX_BASE_URL", "https://codex.example.test/v1")
    monkeypatch.delenv("CODEX_API_KEY", raising=False)

    assert probe._provider_config("codex-router-responses") == {
        "error": {"type": "missing_env", "env": "CODEX_API_KEY"}
    }


def test_raw_fpv_visual_labeler_scores_split_visible_quality(tmp_path: Path) -> None:
    probe = _load_module()
    run_dir = _raw_run_dir(tmp_path)
    frame_id = "household-cleanup-codex-camera-raw-0606_1537-seed-7/raw_fpv_001"
    hidden_labels = _write_private_labels(
        tmp_path / "hidden_labels.json",
        frame_id=frame_id,
        object_id="private_plate_001",
        category="plate",
        bbox=[0.1, 0.2, 0.2, 0.2],
    )
    visible_labels = _write_visible_labels(
        tmp_path / "visible_labels.json",
        frame_id=frame_id,
        object_id="visible_mug_001",
        category="mug",
        category_family="dish",
        bbox=[0.62, 0.5, 0.12, 0.15],
    )
    predictions = tmp_path / "predictions.json"
    predictions.write_text(
        json.dumps(
            {
                "schema": "raw_fpv_probe_predictions_v1",
                "predictions": [
                    {
                        "variant_id": "raw_fpv_visual_labeler",
                        "frame_id": frame_id,
                        "response": {
                            "schema": "raw_fpv_visual_labeler_response_v1",
                            "labels": [
                                {
                                    "evidence_frame_id": frame_id,
                                    "category": "cup",
                                    "category_family": "dish",
                                    "coarse_region": "middle_right",
                                    "confidence": 0.82,
                                    "is_cleanup_relevant": True,
                                    "bbox": [0.62, 0.5, 0.12, 0.15],
                                    "surface_hint": "table",
                                },
                                {
                                    "evidence_frame_id": frame_id,
                                    "category": "table",
                                    "category_family": "fixture",
                                    "coarse_region": "center",
                                    "confidence": 0.9,
                                    "is_cleanup_relevant": False,
                                    "surface_hint": "table",
                                    "reason_not_actionable": "fixture surface only",
                                },
                            ],
                        },
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    report = probe.run_probe(
        probe.parse_args(
            [
                "--raw-run-dir",
                str(run_dir),
                "--contrast-run-dir",
                str(tmp_path / "missing-contrast"),
                "--private-labels",
                str(hidden_labels),
                "--all-visible-labels",
                str(visible_labels),
                "--predictions",
                str(predictions),
                "--output-dir",
                str(tmp_path / "out"),
                "--run-id",
                "visual-labeler",
                "--prompt-variant",
                "raw_fpv_visual_labeler",
            ]
        )
    )

    metrics = report["matrix"][0]["metrics"]
    visible = metrics["visible_movable_label_quality"]

    assert report["status"] == "success"
    assert report["truth_scope"]["visible_movable_quality_claim"] == "scoreable"
    assert "visible_movable_label_quality" in metrics
    assert "hidden_target_recovery" in metrics
    assert visible["unique_matched_object_count"] == 1
    assert visible["surface_hint_only_count"] == 1
    assert visible["fixtures_surfaces_scored_as_hints_only"] is True
    assert visible["category_match_tiers"]["semantic"] == 1


def test_raw_fpv_probe_reports_truth_sparse_when_only_hidden_targets(tmp_path: Path) -> None:
    probe = _load_module()
    run_dir = _raw_run_dir(tmp_path)
    labels = _write_private_labels(
        tmp_path / "private_labels.json",
        frame_id="household-cleanup-codex-camera-raw-0606_1537-seed-7/raw_fpv_001",
        object_id="private_plate_001",
        category="plate",
        bbox=[0.1, 0.2, 0.2, 0.2],
    )

    report = probe.run_probe(
        probe.parse_args(
            [
                "--raw-run-dir",
                str(run_dir),
                "--contrast-run-dir",
                str(tmp_path / "missing-contrast"),
                "--private-labels",
                str(labels),
                "--output-dir",
                str(tmp_path / "out"),
                "--run-id",
                "truth-sparse",
                "--prompt-variant",
                "baseline_json",
            ]
        )
    )

    metrics = report["matrix"][0]["metrics"]

    assert report["status"] == "partial"
    assert report["truth_scope"]["scope"] == "hidden_targets_only"
    assert metrics["visible_movable_label_quality"]["status"] == "truth_sparse"


def test_raw_fpv_visual_labeler_recommends_visible_truth_when_sparse(tmp_path: Path) -> None:
    probe = _load_module()
    run_dir = _raw_run_dir(tmp_path)
    labels = _write_private_labels(
        tmp_path / "private_labels.json",
        frame_id="household-cleanup-codex-camera-raw-0606_1537-seed-7/raw_fpv_001",
        object_id="private_plate_001",
        category="plate",
        bbox=[0.1, 0.2, 0.2, 0.2],
    )

    report = probe.run_probe(
        probe.parse_args(
            [
                "--raw-run-dir",
                str(run_dir),
                "--contrast-run-dir",
                str(tmp_path / "missing-contrast"),
                "--private-labels",
                str(labels),
                "--output-dir",
                str(tmp_path / "out"),
                "--run-id",
                "visual-truth-sparse",
                "--prompt-variant",
                "raw_fpv_visual_labeler",
            ]
        )
    )

    assert report["route_recommendation"] == "needs_all_visible_movable_truth"


def test_raw_fpv_probe_category_match_tiers() -> None:
    probe = _load_module()

    assert probe.category_match_tier("plate", "plate") == "exact"
    assert probe.category_match_tier("cup", "mug") == "semantic"
    assert probe.category_match_tier("dish", "plate") == "coarse_family"
    assert probe.category_match_tier("book", "remote control") == "mismatch"


def test_private_label_generator_reads_only_pre_cleanup_sweep(tmp_path: Path) -> None:
    labels = _load_label_module()
    trace_path = tmp_path / "trace.jsonl"
    trace_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event": "response",
                        "tool": "observe",
                        "response": {
                            "raw_fpv_observation": _raw_observation(
                                "raw_fpv_001",
                                "robot_views/0001_raw_fpv_001.fpv.png",
                            )
                        },
                    }
                ),
                json.dumps({"event": "request", "tool": "pick", "request": {}}),
                json.dumps(
                    {
                        "event": "response",
                        "tool": "observe",
                        "response": {
                            "raw_fpv_observation": _raw_observation(
                                "raw_fpv_002",
                                "robot_views/0002_raw_fpv_002.fpv.png",
                            )
                        },
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    observations = labels.first_sweep_observations_from_trace(trace_path)

    assert [item["observation_id"] for item in observations] == ["raw_fpv_001"]
    assert observations[0]["robot_pose"]["x"] == 1.25
    assert observations[0]["image_artifact"] == "robot_views/0001_raw_fpv_001.fpv.png"


def test_private_label_generator_rejects_non_positive_render_dimensions() -> None:
    labels = _load_label_module()

    try:
        labels.parse_args(["--render-width", "0"])
    except SystemExit as exc:
        assert exc.code == 2
    else:  # pragma: no cover - argparse should exit for invalid input
        raise AssertionError("expected invalid render width to fail at parse time")

    try:
        labels.parse_args(["--render-height", "-1"])
    except SystemExit as exc:
        assert exc.code == 2
    else:  # pragma: no cover - argparse should exit for invalid input
        raise AssertionError("expected invalid render height to fail at parse time")


def test_private_label_generator_rejects_invalid_pixel_and_observation_limits() -> None:
    labels = _load_label_module()

    try:
        labels.parse_args(["--min-object-pixels", "0"])
    except SystemExit as exc:
        assert exc.code == 2
    else:  # pragma: no cover - argparse should exit for invalid input
        raise AssertionError("expected invalid pixel threshold to fail at parse time")

    try:
        labels.parse_args(["--max-observations", "-1"])
    except SystemExit as exc:
        assert exc.code == 2
    else:  # pragma: no cover - argparse should exit for invalid input
        raise AssertionError("expected invalid observation limit to fail at parse time")


def test_private_label_generator_accepts_valid_numeric_config() -> None:
    labels = _load_label_module()

    args = labels.parse_args(
        [
            "--render-width",
            "1280",
            "--render-height",
            "720",
            "--min-object-pixels",
            "5",
            "--max-observations",
            "0",
        ]
    )

    assert args.render_width == 1280
    assert args.render_height == 720
    assert args.min_object_pixels == 5
    assert args.max_observations == 0


def test_private_label_generator_full_trace_keeps_later_observations(tmp_path: Path) -> None:
    labels = _load_label_module()
    trace_path = tmp_path / "trace.jsonl"
    trace_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "event": "response",
                        "tool": "observe",
                        "response": {"raw_fpv_observation": _raw_observation("raw_fpv_001", "")},
                    }
                ),
                json.dumps({"event": "request", "tool": "pick", "request": {}}),
                json.dumps(
                    {
                        "event": "response",
                        "tool": "observe",
                        "response": {"raw_fpv_observation": _raw_observation("raw_fpv_002", "")},
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    observations = labels.observations_from_trace(
        labels._iter_trace_rows(trace_path), replay_mode="full_trace"
    )

    assert [item["observation_id"] for item in observations] == [
        "raw_fpv_001",
        "raw_fpv_002",
    ]


def test_private_label_generator_extracts_private_placement_bindings() -> None:
    labels = _load_label_module()
    bindings = labels.placement_bindings_from_trace(
        [
            {
                "event": "response",
                "tool": "place_inside",
                "response": {
                    "ok": True,
                    "object_id": "observed_007",
                    "placement_diagnostic": {
                        "object_id": "book_private_001",
                        "receptacle_id": "shelf_private_001",
                        "relation": "inside",
                    },
                },
            }
        ]
    )

    assert bindings == {
        "observed_007": {
            "private_object_id": "book_private_001",
            "receptacle_id": "shelf_private_001",
            "relation": "inside",
            "place_tool": "place_inside",
        }
    }


def test_private_label_generator_reconstructs_generated_mess_manifest() -> None:
    labels = _load_label_module()
    state = {
        "seed": 7,
        "scene_source": "procthor-10k-val",
        "scene_index": 0,
        "private_manifest": {
            "success_threshold": 5,
            "targets": [
                {
                    "object_id": "plate_private_001",
                    "valid_receptacle_ids": ["sink_private_001"],
                }
            ],
        },
        "mess_placement_diagnostics": [
            {
                "object_id": "plate_private_001",
                "object_category": "Plate",
                "receptacle_id": "table_private_001",
                "relation": "on",
            }
        ],
    }

    manifest = labels.generated_mess_manifest_from_state(state)

    assert manifest["schema"] == "roboclaws_generated_mess_manifest_v1"
    assert manifest["targets"] == [
        {
            "object_id": "plate_private_001",
            "category": "Plate",
            "target_receptacle_id": "sink_private_001",
            "valid_receptacle_ids": ["sink_private_001"],
            "start_receptacle_id": "table_private_001",
            "relation": "on",
            "placement_index": 0,
        }
    ]


def test_private_label_generator_normalizes_bbox_and_grid_region() -> None:
    labels = _load_label_module()

    bbox = labels.normalize_box_xywh([270, 180, 539, 359], width=540, height=360)

    assert bbox == [0.5, 0.5, 0.5, 0.5]
    assert labels.coarse_regions_from_bbox(bbox) == ["lower_right"]


def test_private_label_generator_cleanup_visible_scope_selects_cleanup_family_objects() -> None:
    labels = _load_label_module()
    state = {
        "selected_object_ids": ["private_plate_001"],
        "objects": {
            "private_plate_001": {"category": "Plate"},
            "visible_book_001": {"category": "Book"},
            "fixture_bookcase_001": {"category": "Bookcase"},
            "fixture_table_001": {"category": "DiningTable"},
        },
    }

    assert labels.label_object_ids_for_scope(state, label_scope="generated-targets") == [
        "private_plate_001"
    ]
    assert labels.label_object_ids_for_scope(state, label_scope="cleanup-visible-movable") == [
        "private_plate_001",
        "visible_book_001",
    ]


def test_raw_fpv_probe_reads_public_sweep_observation_manifest(tmp_path: Path) -> None:
    probe = _load_module()
    run_dir = tmp_path / "raw-fpv-sweep"
    robot_views = run_dir / "robot_views"
    robot_views.mkdir(parents=True)
    Image.new("RGB", (120, 90), color=(80, 20, 20)).save(robot_views / "0001_raw_fpv_001.fpv.png")
    (run_dir / "raw_fpv_observations.json").write_text(
        json.dumps(
            {
                "schema": "raw_fpv_public_sweep_observations_v1",
                "raw_fpv_observations": [
                    {
                        "observation_id": "raw_fpv_001",
                        "waypoint_id": "generated_exploration_001",
                        "room_id": "generated_area",
                        "image_artifacts": {"fpv": "robot_views/0001_raw_fpv_001.fpv.png"},
                        "public_contract_note": "no private scoring truth",
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )

    frames = probe.collect_observation_frames(
        raw_run_dirs=(run_dir,),
        contrast_run_dirs=(),
        max_frames_per_source=4,
    )

    assert len(frames) == 1
    assert frames[0].frame_id.endswith("raw-fpv-sweep/raw_fpv_001")
    assert frames[0].source_kind == "raw_failure"


def test_raw_fpv_sweep_corpus_public_observation_excludes_private_target_ids() -> None:
    sweep = _load_sweep_module()
    observation = sweep._public_observation(
        observation_id="raw_fpv_001",
        waypoint={"waypoint_id": "generated_exploration_001", "room_id": "generated_area"},
        yaw=-45.0,
        pitch=0.0,
        view={"camera_control_contract": {"robot_pose": {"x": 1.0}}},
        image_artifact="robot_views/0001_raw_fpv_001.fpv.png",
    )

    text = json.dumps(observation, sort_keys=True)

    assert observation["structured_detections_available"] is False
    assert observation["image_artifacts"]["fpv"] == "robot_views/0001_raw_fpv_001.fpv.png"
    assert "private_plate_001" not in text
    assert "observed_" not in text
    assert "anchor_fixture_" not in text


def test_raw_fpv_sweep_corpus_rejects_non_positive_render_dimensions() -> None:
    sweep = _load_sweep_module()

    try:
        sweep.parse_args(["--render-width", "0"])
    except SystemExit as exc:
        assert exc.code == 2
    else:  # pragma: no cover - argparse should exit for invalid input
        raise AssertionError("expected invalid render width to fail at parse time")

    try:
        sweep.parse_args(["--render-height", "-1"])
    except SystemExit as exc:
        assert exc.code == 2
    else:  # pragma: no cover - argparse should exit for invalid input
        raise AssertionError("expected invalid render height to fail at parse time")


def test_raw_fpv_sweep_corpus_rejects_invalid_pixel_and_waypoint_limits() -> None:
    sweep = _load_sweep_module()

    try:
        sweep.parse_args(["--min-object-pixels", "0"])
    except SystemExit as exc:
        assert exc.code == 2
    else:  # pragma: no cover - argparse should exit for invalid input
        raise AssertionError("expected invalid pixel threshold to fail at parse time")

    try:
        sweep.parse_args(["--max-waypoints", "-1"])
    except SystemExit as exc:
        assert exc.code == 2
    else:  # pragma: no cover - argparse should exit for invalid input
        raise AssertionError("expected invalid waypoint limit to fail at parse time")


def test_raw_fpv_sweep_corpus_accepts_valid_numeric_config() -> None:
    sweep = _load_sweep_module()

    args = sweep.parse_args(
        [
            "--render-width",
            "1280",
            "--render-height",
            "720",
            "--min-object-pixels",
            "5",
            "--max-waypoints",
            "0",
        ]
    )

    assert args.render_width == 1280
    assert args.render_height == 720
    assert args.min_object_pixels == 5
    assert args.max_waypoints == 0


def test_raw_fpv_sweep_corpus_labels_from_private_focus_only() -> None:
    sweep = _load_sweep_module()

    class Backend:
        def _read_state(self) -> dict:
            return {
                "selected_object_ids": ["private_plate_001"],
                "objects": {
                    "private_plate_001": {"category": "Plate"},
                    "private_table_001": {"category": "DiningTable"},
                },
            }

        def write_robot_views_with_resolution(self, *args: object, **kwargs: object) -> dict:
            assert kwargs["focus_object_id"] == "private_plate_001"
            return {
                "focus": {
                    "object_category": "Plate",
                    "object_location_relation": "on",
                    "receptacle_category": "table",
                    "fpv_visibility": {
                        "boxes": [
                            {
                                "source": "segmentation",
                                "pixels": 100,
                                "bbox": [12, 18, 35, 44],
                            }
                        ]
                    },
                }
            }

    labels = sweep._labels_from_view_focuses(
        backend=Backend(),
        frame_id="sweep/raw_fpv_001",
        observation_id="raw_fpv_001",
        targets=[{"object_id": "private_plate_001", "category": "Plate"}],
        output_dir=Path("unused"),
        label_prefix="0001_raw_fpv_001",
        min_object_pixels=12,
        width=120,
        height=90,
        yaw=0.0,
        pitch=0.0,
    )

    assert labels == [
        {
            "frame_id": "sweep/raw_fpv_001",
            "source_observation_id": "raw_fpv_001",
            "object_id": "private_plate_001",
            "category": "Plate",
            "bbox": [0.1, 0.2, 0.2, 0.3],
            "coarse_regions": ["middle_left"],
            "surface_hint": "table",
            "label_source": "private_molmospaces_public_sweep_fpv_segmentation",
            "private": True,
            "hidden_target": True,
            "pixel_bbox": [12, 18, 35, 44],
            "object_pixels": 100,
        }
    ]


def test_raw_fpv_sweep_corpus_all_visible_scope_labels_cleanup_family_objects() -> None:
    sweep = _load_sweep_module()
    state = {
        "selected_object_ids": ["private_plate_001"],
        "objects": {
            "private_plate_001": {"category": "Plate"},
            "visible_mug_001": {"category": "Mug"},
            "fixture_table_001": {"category": "DiningTable"},
        },
    }

    assert sweep.label_object_ids_for_scope(state, label_scope="cleanup-visible-movable") == [
        "private_plate_001",
        "visible_mug_001",
    ]


def _raw_run_dir(
    base: Path,
    *,
    observation_ids: tuple[str, ...] = ("raw_fpv_001",),
) -> Path:
    run_dir = base / "household-cleanup" / "codex-camera-raw" / "0606_1537" / "seed-7"
    robot_views = run_dir / "robot_views"
    robot_views.mkdir(parents=True)
    observations = []
    for index, observation_id in enumerate(observation_ids, start=1):
        name = f"{index:04d}_{observation_id}.fpv.png"
        Image.new("RGB", (120, 90), color=(index * 30, 20, 80)).save(robot_views / name)
        observations.append(
            {
                "observation_id": observation_id,
                "waypoint_id": f"generated_exploration_{index:03d}",
                "room_id": "generated_area",
                "perception_mode": "raw_fpv_only",
                "structured_detections_available": False,
                "image_artifacts": {"fpv": f"robot_views/{name}"},
            }
        )
    (run_dir / "agent_view.json").write_text(
        json.dumps({"raw_fpv_observations": observations}) + "\n",
        encoding="utf-8",
    )
    return run_dir


def _raw_observation(observation_id: str, image_artifact: str) -> dict[str, object]:
    return {
        "observation_id": observation_id,
        "waypoint_id": "generated_exploration_001",
        "room_id": "generated_area",
        "image_artifacts": {"fpv": image_artifact},
        "robot_view_label": observation_id,
        "camera_control_contract": {
            "robot_pose": {
                "x": 1.25,
                "y": 2.5,
                "z": 0.0,
                "theta": 0.0,
                "head_yaw": 0.0,
                "head_pitch": 0.25,
            }
        },
    }


def _write_private_labels(
    path: Path,
    *,
    frame_id: str,
    object_id: str,
    category: str,
    bbox: list[float],
) -> Path:
    path.write_text(
        json.dumps(
            {
                "schema": "raw_fpv_private_label_manifest_v1",
                "labels": [
                    {
                        "frame_id": frame_id,
                        "source_observation_id": frame_id.rsplit("/", 1)[-1],
                        "object_id": object_id,
                        "category": category,
                        "bbox": bbox,
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _write_visible_labels(
    path: Path,
    *,
    frame_id: str,
    object_id: str,
    category: str,
    category_family: str,
    bbox: list[float],
) -> Path:
    path.write_text(
        json.dumps(
            {
                "schema": "raw_fpv_private_label_manifest_v1",
                "provenance": {"scorer_only": True, "truth_scope": "all_visible_movable"},
                "labels": [
                    {
                        "frame_id": frame_id,
                        "source_observation_id": frame_id.rsplit("/", 1)[-1],
                        "object_id": object_id,
                        "category": category,
                        "category_family": category_family,
                        "bbox": bbox,
                        "hidden_target": False,
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _write_predictions(
    path: Path,
    *,
    frame_id: str,
    category: str,
    bbox: list[float],
    coarse_region: str,
) -> Path:
    observation_id = frame_id.rsplit("/", 1)[-1]
    path.write_text(
        json.dumps(
            {
                "schema": "raw_fpv_probe_predictions_v1",
                "predictions": [
                    {
                        "variant_id": "baseline_json",
                        "frame_id": frame_id,
                        "response": _response(observation_id, category, bbox, coarse_region),
                    }
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _response(
    observation_id: str,
    category: str,
    bbox: list[float],
    coarse_region: str = "upper_left",
) -> dict[str, object]:
    return {
        "schema": "raw_fpv_probe_response_v1",
        "candidates": [
            {
                "source_observation_id": observation_id,
                "category": category,
                "evidence_note": f"{category} visible in current frame",
                "confidence": 0.9,
                "locality": {
                    "bbox": bbox,
                    "coarse_region": coarse_region,
                    "surface_hint": "table",
                },
            }
        ],
    }
