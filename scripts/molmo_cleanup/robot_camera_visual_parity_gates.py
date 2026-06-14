from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class _GateConfig:
    required_scene_count: int
    required_seed_count: int
    chase_regression_tolerance: float


@dataclass(frozen=True)
class _ProbeSummary:
    rows: list[dict[str, Any]]
    comparable: list[dict[str, Any]]
    fpv_improved: list[dict[str, Any]]
    fpv_worse: list[dict[str, Any]]
    chase_regressions: list[dict[str, Any]]
    scene_signatures: list[str]
    seeds: list[int]


def prepared_scale_square_default_gate_check(
    render_domain_probe_matrix: dict[str, Any],
    *,
    required_scene_count: int,
    required_seed_count: int,
    chase_regression_tolerance: float = 1.0,
) -> dict[str, Any]:
    config = _GateConfig(required_scene_count, required_seed_count, chase_regression_tolerance)
    rows = _material_probe_rows(
        render_domain_probe_matrix,
        lambda label: "prepared_scale_square_gate" in label,
    )
    summary = _probe_summary(rows, config)
    baseline_render_statuses = _active_baseline_render_statuses(render_domain_probe_matrix)
    blockers = [
        *_common_probe_blockers(
            summary,
            config,
            missing_reason="no_prepared_scale_square_probe",
            not_all_reason="not_all_prepared_probes_comparable",
            probe_count_key="prepared_probe_count",
        ),
        *_fpv_blockers(summary),
        *_prepared_chase_blockers(summary, config),
        *_baseline_render_blockers(baseline_render_statuses),
    ]
    status = _prepared_status(summary, blockers)
    return {
        "status": status,
        "comparison_only": status != "prepared_scale_square_default_ready",
        "default_candidate": status == "prepared_scale_square_default_ready",
        "prepared_probe_count": len(summary.rows),
        **_common_summary_payload(summary, config),
        "chase_regression_diagnostics": [
            _chase_regression_diagnostic(row, config.chase_regression_tolerance)
            for row in summary.chase_regressions
        ],
        "blockers": blockers,
        "probes": [_prepared_probe_payload(row) for row in summary.rows],
        "recommended_next_action": _prepared_recommended_next_action(status, summary, config),
        "interpretation": (
            "This gate decides whether the opt-in prepared USD texture scale/fallback "
            "squaring evidence is strong enough to become default rendering behavior."
        ),
    }


def combined_material_light_default_gate_check(
    render_domain_probe_matrix: dict[str, Any],
    *,
    required_scene_count: int,
    required_seed_count: int,
    chase_regression_tolerance: float = 1.0,
) -> dict[str, Any]:
    config = _GateConfig(required_scene_count, required_seed_count, chase_regression_tolerance)
    rows = _material_probe_rows(
        render_domain_probe_matrix,
        lambda label: "scale_square" in label and "rotx" in label,
    )
    summary = _probe_summary(rows, config)
    blockers = [
        *_common_probe_blockers(
            summary,
            config,
            missing_reason="no_combined_material_light_probe",
            not_all_reason="not_all_combined_probes_comparable",
            probe_count_key="probe_count",
        ),
        *_fpv_blockers(summary),
        *_simple_chase_blockers(summary, config),
    ]
    status = _combined_status(summary, blockers)
    return {
        "status": status,
        "comparison_only": status != "combined_material_light_default_ready",
        "default_candidate": status == "combined_material_light_default_ready",
        "probe_count": len(summary.rows),
        **_common_summary_payload(summary, config),
        "blockers": blockers,
        "probes": [_basic_probe_payload(row) for row in summary.rows],
        "interpretation": (
            "This gate tracks combined prepared scale-square material conversion plus "
            "directional-light orientation probes. It needs held-out scene/seed coverage "
            "before default rendering promotion."
        ),
    }


def view_specific_prepared_scale_square_tone_gate_check(
    render_domain_probe_matrix: dict[str, Any],
    *,
    required_scene_count: int,
    required_seed_count: int,
    chase_regression_tolerance: float = 1.0,
) -> dict[str, Any]:
    config = _GateConfig(required_scene_count, required_seed_count, chase_regression_tolerance)
    rows = _tone_probe_rows(
        render_domain_probe_matrix,
        lambda label: "prepared_scale_square_view_rgb" in label,
    )
    summary = _probe_summary(rows, config)
    required_views = ("fpv", "chase")
    missing_view_gain_rows = _missing_view_gain_rows(summary.rows, required_views=required_views)
    blockers = [
        *_common_probe_blockers(
            summary,
            config,
            missing_reason="no_view_specific_prepared_scale_square_tone_probe",
            not_all_reason="not_all_view_specific_probes_comparable",
            probe_count_key="probe_count",
        ),
        *_fpv_blockers(summary),
        *_view_gain_blockers(missing_view_gain_rows),
        *_simple_chase_blockers(summary, config),
    ]
    formal_comparison_gate_ready = bool(summary.rows and not blockers)
    status = _view_specific_status(summary, blockers)
    return {
        "status": status,
        "comparison_only": True,
        "formal_comparison_gate_ready": formal_comparison_gate_ready,
        "ready_for_review": formal_comparison_gate_ready,
        "policy_scope": (
            "report_side_comparison_only"
            if formal_comparison_gate_ready
            else "comparison_only_probe"
        ),
        "default_rendering_candidate": False,
        "probe_count": len(summary.rows),
        **_common_summary_payload(summary, config),
        "view_rgb_gain_profile_count": len(summary.rows) - len(missing_view_gain_rows),
        "required_view_rgb_gain_views": list(required_views),
        "blockers": blockers,
        "probes": [
            _view_specific_probe_payload(row, required_views=required_views) for row in summary.rows
        ],
        "recommended_next_action": _view_specific_recommended_next_action(
            formal_comparison_gate_ready
        ),
        "interpretation": (
            "This gate evaluates prepared scale-square plus view-specific tone compensation. "
            "It can clear the auxiliary chase side effect as report-side comparison evidence, "
            "but it is not a default-rendering policy."
        ),
    }


def _material_probe_rows(
    render_domain_probe_matrix: dict[str, Any],
    predicate: Any,
) -> list[dict[str, Any]]:
    matrix = _dict(render_domain_probe_matrix.get("probe_matrix"))
    return [row for row in _list_dicts(matrix.get("material_response")) if predicate(_label(row))]


def _tone_probe_rows(
    render_domain_probe_matrix: dict[str, Any],
    predicate: Any,
) -> list[dict[str, Any]]:
    matrix = _dict(render_domain_probe_matrix.get("probe_matrix"))
    return [row for row in _list_dicts(matrix.get("tone_color")) if predicate(_label(row))]


def _label(row: dict[str, Any]) -> str:
    return str(row.get("label") or "").lower()


def _probe_summary(rows: list[dict[str, Any]], config: _GateConfig) -> _ProbeSummary:
    comparable = [row for row in rows if row.get("comparable")]
    return _ProbeSummary(
        rows=rows,
        comparable=comparable,
        fpv_improved=[row for row in comparable if row.get("fpv_improved")],
        fpv_worse=[row for row in comparable if row.get("fpv_worse")],
        chase_regressions=[
            row
            for row in comparable
            if _exceeds_chase_tolerance(row, config.chase_regression_tolerance)
        ],
        scene_signatures=sorted({str(row.get("scene_signature") or "") for row in comparable}),
        seeds=_seeds_from_rows(comparable),
    )


def _seeds_from_rows(rows: list[dict[str, Any]]) -> list[int]:
    return sorted(
        {
            seed
            for seed in (
                _seed_from_scene_signature(str(row.get("scene_signature") or "")) for row in rows
            )
            if seed is not None
        }
    )


def _exceeds_chase_tolerance(row: dict[str, Any], tolerance: float) -> bool:
    chase_delta = _float_or_none(row.get("chase_delta"))
    return chase_delta is not None and chase_delta > tolerance


def _common_probe_blockers(
    summary: _ProbeSummary,
    config: _GateConfig,
    *,
    missing_reason: str,
    not_all_reason: str,
    probe_count_key: str,
) -> list[dict[str, Any]]:
    blockers: list[dict[str, Any]] = []
    _add_missing_probe_blocker(blockers, summary, missing_reason)
    _add_not_all_comparable_blocker(blockers, summary, not_all_reason, probe_count_key)
    _add_scene_corpus_blocker(blockers, summary, config)
    _add_seed_corpus_blocker(blockers, summary, config)
    _add_fpv_improvement_blocker(blockers, summary)
    return blockers


def _add_missing_probe_blocker(
    blockers: list[dict[str, Any]],
    summary: _ProbeSummary,
    reason: str,
) -> None:
    if not summary.rows:
        blockers.append({"reason": reason})


def _add_not_all_comparable_blocker(
    blockers: list[dict[str, Any]],
    summary: _ProbeSummary,
    reason: str,
    probe_count_key: str,
) -> None:
    if len(summary.comparable) != len(summary.rows):
        blockers.append(
            {
                "reason": reason,
                probe_count_key: len(summary.rows),
                "comparable_probe_count": len(summary.comparable),
            }
        )


def _add_scene_corpus_blocker(
    blockers: list[dict[str, Any]],
    summary: _ProbeSummary,
    config: _GateConfig,
) -> None:
    if len(summary.scene_signatures) < config.required_scene_count:
        blockers.append(
            {
                "reason": "needs_broader_scene_corpus",
                "scene_signature_count": len(summary.scene_signatures),
                "required_scene_count": config.required_scene_count,
            }
        )


def _add_seed_corpus_blocker(
    blockers: list[dict[str, Any]],
    summary: _ProbeSummary,
    config: _GateConfig,
) -> None:
    if len(summary.seeds) < config.required_seed_count:
        blockers.append(
            {
                "reason": "needs_broader_seed_corpus",
                "seed_count": len(summary.seeds),
                "required_seed_count": config.required_seed_count,
            }
        )


def _add_fpv_improvement_blocker(
    blockers: list[dict[str, Any]],
    summary: _ProbeSummary,
) -> None:
    if len(summary.fpv_improved) != len(summary.comparable):
        blockers.append(
            {
                "reason": "not_all_comparable_probes_improve_fpv",
                "fpv_improved_count": len(summary.fpv_improved),
                "comparable_probe_count": len(summary.comparable),
            }
        )


def _fpv_blockers(summary: _ProbeSummary) -> list[dict[str, Any]]:
    if not summary.fpv_worse:
        return []
    return [
        {
            "reason": "fpv_regression",
            "labels": [row.get("label") for row in summary.fpv_worse],
        }
    ]


def _prepared_chase_blockers(
    summary: _ProbeSummary,
    config: _GateConfig,
) -> list[dict[str, Any]]:
    if not summary.chase_regressions:
        return []
    return [
        {
            "reason": "chase_regression",
            "tolerance": config.chase_regression_tolerance,
            "labels": [row.get("label") for row in summary.chase_regressions],
            "diagnostic_classes": sorted(
                {
                    _classify_chase_regression(row, config.chase_regression_tolerance)
                    for row in summary.chase_regressions
                }
            ),
        }
    ]


def _simple_chase_blockers(
    summary: _ProbeSummary,
    config: _GateConfig,
) -> list[dict[str, Any]]:
    if not summary.chase_regressions:
        return []
    return [
        {
            "reason": "chase_regression",
            "tolerance": config.chase_regression_tolerance,
            "labels": [row.get("label") for row in summary.chase_regressions],
        }
    ]


def _baseline_render_blockers(statuses: list[str]) -> list[dict[str, Any]]:
    if not statuses:
        return []
    return [{"reason": "render_domain_residuals_active", "baseline_render_statuses": statuses}]


def _view_gain_blockers(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not rows:
        return []
    return [{"reason": "missing_backend_view_rgb_gain", "rows": rows}]


def _active_baseline_render_statuses(render_domain_probe_matrix: dict[str, Any]) -> list[str]:
    return [
        status
        for status in _list_strings(render_domain_probe_matrix.get("baseline_render_statuses"))
        if status and status != "render_domain_delta_resolved"
    ]


def _prepared_status(summary: _ProbeSummary, blockers: list[dict[str, Any]]) -> str:
    if not summary.rows:
        return "not_evaluated"
    if summary.fpv_worse:
        return "do_not_promote"
    if summary.comparable and len(summary.fpv_improved) == len(summary.comparable) and not blockers:
        return "prepared_scale_square_default_ready"
    if summary.comparable and summary.fpv_improved:
        return "comparison_only_not_default"
    return "neutral_do_not_promote"


def _combined_status(summary: _ProbeSummary, blockers: list[dict[str, Any]]) -> str:
    if not summary.rows:
        return "not_evaluated"
    if summary.fpv_worse:
        return "do_not_promote"
    if (
        summary.comparable
        and _all_comparable_improve_fpv(summary)
        and not summary.chase_regressions
    ):
        return "combined_material_light_default_ready" if not blockers else "needs_broader_corpus"
    return "comparison_only_not_default"


def _view_specific_status(summary: _ProbeSummary, blockers: list[dict[str, Any]]) -> str:
    if not summary.rows:
        return "not_evaluated"
    if (
        summary.comparable
        and _all_comparable_improve_fpv(summary)
        and not summary.chase_regressions
    ):
        return (
            "view_specific_report_comparison_gate_ready"
            if not blockers
            else "comparison_only_needs_broader_gate"
        )
    if summary.fpv_worse:
        return "do_not_promote"
    return "comparison_only_not_default"


def _all_comparable_improve_fpv(summary: _ProbeSummary) -> bool:
    return len(summary.fpv_improved) == len(summary.comparable)


def _common_summary_payload(summary: _ProbeSummary, config: _GateConfig) -> dict[str, Any]:
    return {
        "comparable_probe_count": len(summary.comparable),
        "fpv_improved_count": len(summary.fpv_improved),
        "fpv_worse_count": len(summary.fpv_worse),
        "chase_regression_count": len(summary.chase_regressions),
        "scene_signature_count": len(summary.scene_signatures),
        "scene_signatures": summary.scene_signatures,
        "seed_count": len(summary.seeds),
        "seeds": summary.seeds,
        "required_scene_count": config.required_scene_count,
        "required_seed_count": config.required_seed_count,
        "chase_regression_tolerance": config.chase_regression_tolerance,
    }


def _prepared_probe_payload(row: dict[str, Any]) -> dict[str, Any]:
    payload = _basic_probe_payload(row)
    payload["paired_view_diagnostics_status"] = _dict(row.get("paired_view_diagnostics")).get(
        "status"
    )
    return payload


def _basic_probe_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "label": row.get("label"),
        "path": row.get("path"),
        "scene_signature": row.get("scene_signature"),
        "fpv_delta": row.get("fpv_delta"),
        "chase_delta": row.get("chase_delta"),
        "fpv_improved": row.get("fpv_improved"),
        "comparable": row.get("comparable"),
    }


def _view_specific_probe_payload(
    row: dict[str, Any],
    *,
    required_views: tuple[str, ...],
) -> dict[str, Any]:
    payload = _basic_probe_payload(row)
    payload["view_rgb_gain_views"] = _view_rgb_gain_views(row)
    payload["has_required_view_rgb_gain"] = _has_required_view_rgb_gains(
        row,
        required_views=required_views,
    )
    return payload


def _prepared_recommended_next_action(
    status: str,
    summary: _ProbeSummary,
    config: _GateConfig,
) -> str:
    if status == "prepared_scale_square_default_ready":
        return "Prepared scale-square is ready for default-rendering review."
    return _prepared_scale_square_next_action(
        summary.chase_regressions,
        config.chase_regression_tolerance,
    )


def _view_specific_recommended_next_action(formal_comparison_gate_ready: bool) -> str:
    if formal_comparison_gate_ready:
        return (
            "Review whether view-specific report-side tone compensation should become a "
            "formal comparison gate. Do not promote it to default rendering; keep "
            "RAW_FPV FPV as the policy/input metric and chase as auxiliary report evidence."
        )
    return (
        "Keep view-specific tone comparison-only until all comparable probes improve "
        "FPV, stay within chase tolerance, and cover the required corpus."
    )


def _missing_view_gain_rows(
    rows: list[dict[str, Any]],
    *,
    required_views: tuple[str, ...],
) -> list[dict[str, Any]]:
    return [
        {
            "label": row.get("label"),
            "available_views": _view_rgb_gain_views(row),
            "required_views": list(required_views),
        }
        for row in rows
        if not _has_required_view_rgb_gains(row, required_views=required_views)
    ]


def _classify_chase_regression(
    row: dict[str, Any],
    chase_regression_tolerance: float,
) -> str:
    chase_delta = _float_or_none(row.get("chase_delta"))
    if chase_delta is None or chase_delta <= chase_regression_tolerance:
        return "no_chase_regression"
    diagnostics = _dict(row.get("paired_view_diagnostics"))
    if diagnostics.get("status") != "paired_view_diagnostics_loaded":
        return "unclassified_chase_regression"
    chase = _dict(_dict(diagnostics.get("views")).get("chase"))
    edge_delta_avg = _float_or_none(chase.get("edge_abs_diff_delta_avg"))
    luminance_gap_delta_avg = _float_or_none(chase.get("luminance_gap_delta_avg"))
    edge_regression_count = int(chase.get("edge_regression_count") or 0)
    luminance_gap_regression_count = int(chase.get("luminance_gap_regression_count") or 0)
    if edge_delta_avg is not None and edge_delta_avg > 0.5:
        return "edge_geometry_regression"
    if _is_tone_luminance_side_effect(
        edge_regression_count=edge_regression_count,
        luminance_gap_regression_count=luminance_gap_regression_count,
        luminance_gap_delta_avg=luminance_gap_delta_avg,
    ):
        return "tone_luminance_side_effect"
    return "mixed_or_unclassified_chase_regression"


def _is_tone_luminance_side_effect(
    *,
    edge_regression_count: int,
    luminance_gap_regression_count: int,
    luminance_gap_delta_avg: float | None,
) -> bool:
    return (
        edge_regression_count == 0
        and luminance_gap_regression_count > 0
        and luminance_gap_delta_avg is not None
        and luminance_gap_delta_avg > 1.0
    )


def _chase_regression_diagnostic(
    row: dict[str, Any],
    chase_regression_tolerance: float,
) -> dict[str, Any]:
    diagnostics = _dict(row.get("paired_view_diagnostics"))
    views = _dict(diagnostics.get("views"))
    chase = _dict(views.get("chase"))
    fpv = _dict(views.get("fpv"))
    return {
        "label": row.get("label"),
        "path": row.get("path"),
        "scene_signature": row.get("scene_signature"),
        "chase_delta": row.get("chase_delta"),
        "tolerance": chase_regression_tolerance,
        "diagnostic_class": _classify_chase_regression(row, chase_regression_tolerance),
        "paired_view_status": diagnostics.get("status"),
        "chase": _chase_diagnostic_payload(chase),
        "fpv": {
            "mean_abs_rgb_delta_avg": fpv.get("mean_abs_rgb_delta_avg"),
            "regressed_location_count": fpv.get("regressed_location_count"),
            "improved_location_count": fpv.get("improved_location_count"),
        },
    }


def _chase_diagnostic_payload(chase: dict[str, Any]) -> dict[str, Any]:
    return {
        "paired_location_count": chase.get("paired_location_count"),
        "mean_abs_rgb_delta_avg": chase.get("mean_abs_rgb_delta_avg"),
        "edge_abs_diff_delta_avg": chase.get("edge_abs_diff_delta_avg"),
        "luminance_gap_delta_avg": chase.get("luminance_gap_delta_avg"),
        "isaac_luminance_delta_avg": chase.get("isaac_luminance_delta_avg"),
        "regressed_location_count": chase.get("regressed_location_count"),
        "improved_location_count": chase.get("improved_location_count"),
        "edge_regression_count": chase.get("edge_regression_count"),
        "luminance_gap_regression_count": chase.get("luminance_gap_regression_count"),
        "top_regressions": chase.get("top_regressions"),
    }


def _prepared_scale_square_next_action(
    chase_regressions: list[dict[str, Any]],
    chase_regression_tolerance: float,
) -> str:
    diagnostic_classes = {
        _classify_chase_regression(row, chase_regression_tolerance) for row in chase_regressions
    }
    if diagnostic_classes == {"tone_luminance_side_effect"}:
        return (
            "Keep prepared scale-square comparison-only: FPV improves under the frozen "
            "head-camera contract, while the auxiliary chase regression is currently "
            "classified as a tone/luminance side effect. Resolve or explicitly gate the "
            "remaining render-domain residuals before promoting default rendering."
        )
    return (
        "Keep prepared scale-square comparison-only until FPV gain, chase "
        "non-regression tolerance, and remaining render-domain residual gates pass."
    )


def _view_rgb_gain_views(row: dict[str, Any]) -> list[str]:
    source = _dict(row.get("rgb_gain_source"))
    backend_view_gain = _dict(source.get("backend_view_rgb_gain"))
    views = set()
    for gains_by_view in backend_view_gain.values():
        if isinstance(gains_by_view, dict):
            views.update(str(view) for view in gains_by_view)
    return sorted(views)


def _has_required_view_rgb_gains(
    row: dict[str, Any],
    *,
    required_views: tuple[str, ...],
) -> bool:
    views = set(_view_rgb_gain_views(row))
    return all(view in views for view in required_views)


def _seed_from_scene_signature(scene_signature: str) -> int | None:
    parts = scene_signature.split("|")
    if len(parts) < 3:
        return None
    try:
        return int(parts[2])
    except ValueError:
        return None


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list_dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _list_strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None]
