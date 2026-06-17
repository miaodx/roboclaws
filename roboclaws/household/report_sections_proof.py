from __future__ import annotations

import html
from collections.abc import Callable
from typing import Any

from roboclaws.household.planner_proof_quality import (
    format_quality_tier_counts,
    planner_proof_quality_evidence,
    planner_proof_quality_summary,
)
from roboclaws.household.semantic_timeline import semantic_subphase_text

ViewFigureRenderer = Callable[[Any, str], str]


def manipulation_provenance_section(run_result: dict[str, Any]) -> str:
    evidence = run_result.get("manipulation_evidence") or {}
    if not evidence:
        return ""
    blockers = evidence.get("blockers") or []
    summary = evidence.get("evidence_note") or ""
    badges = "".join(
        (
            _badge("Status", evidence.get("status", "unknown")),
            _badge("Primitive", evidence.get("primitive_provenance", "unknown")),
            _badge("Planner backed", evidence.get("planner_backed", False)),
            _badge("Strict proof", evidence.get("strict_proof_eligible", False)),
            _badge("API semantic edits", evidence.get("api_semantic_state_edits", "unknown")),
        )
    )
    requirements = evidence.get("strict_proof_requirements") or []
    requirements_list = "".join(f"<li>{html.escape(str(item))}</li>" for item in requirements)
    blocker_text = ""
    if blockers:
        blocker_text = f'<p class="note">Capability blocker count: {len(blockers)}.</p>'
    return (
        '<section class="panel manipulation-provenance">'
        "<h2>Manipulation Provenance</h2>"
        f'<p class="note">{html.escape(str(summary))}</p>'
        f'<div class="badges">{badges}</div>'
        f"{blocker_text}"
        f'<ul class="requirements">{requirements_list}</ul>'
        "</section>"
    )


def attached_planner_proof_section(
    run_result: dict[str, Any],
    *,
    view_figure: ViewFigureRenderer,
) -> str:
    proof = run_result.get("planner_backed_manipulation_proof") or {}
    if not proof:
        return ""
    if proof.get("schema") == "planner_backed_cleanup_proof_bundle_v1":
        return _attached_planner_proof_bundle_section(
            run_result,
            proof,
            view_figure=view_figure,
        )
    diagnostics = proof.get("runtime_diagnostics") or {}
    images = proof.get("image_artifacts") or {}
    quality = planner_proof_quality_evidence(proof)
    note = (
        proof.get("evidence_note")
        or "Strict standalone planner-backed manipulation proof attached for review."
    )
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Status', proof.get('status', 'unknown'))}"
        f"{_metric('Embodiment', proof.get('embodiment', 'unknown'))}"
        f"{_metric('Proof Quality', quality.get('quality_tier', 'unknown'))}"
        f"{_metric('Steps', proof.get('steps_executed', 'n/a'))}"
        f"{_metric('Qpos delta', proof.get('max_abs_qpos_delta', 'n/a'))}"
        f"{_metric('Containment proven', 'yes' if quality.get('containment_proven') else 'no')}"
        "</div>"
    )
    badges = "".join(
        (
            _badge("Strict proof", proof.get("strict_proof_eligible", False)),
            _badge("Planner backed", proof.get("planner_backed", False)),
            _badge("Multi-step motion", quality.get("multi_step_motion", False)),
            _badge("Cleanup primitive", run_result.get("primitive_provenance", "unknown")),
            _badge("Renderer adapter", diagnostics.get("renderer_adapter_enabled", False)),
        )
    )
    views = (
        '<div class="views">'
        f"{view_figure(images.get('initial'), 'Planner Initial')}"
        f"{view_figure(images.get('final'), 'Planner Final')}"
        "</div>"
    )
    return (
        '<section class="panel attached-planner-proof">'
        "<h2>Attached Planner-Backed Proof</h2>"
        f'<p class="note">{html.escape(str(note))} Cleanup object moves in this '
        f"artifact remain {html.escape(str(run_result.get('primitive_provenance', 'unknown')))}."
        "</p>"
        f'<p class="note"><strong>Proof Quality:</strong> '
        f"{html.escape(str(quality.get('quality_tier', 'unknown')))}. "
        f"{html.escape(str(quality.get('evidence_note', '')))}</p>"
        f'{metrics}<div class="badges">{badges}</div>{views}</section>'
    )


def cleanup_primitive_gate_section(run_result: dict[str, Any]) -> str:
    evidence = run_result.get("cleanup_primitive_evidence") or {}
    if not evidence:
        return ""
    objects = evidence.get("objects") or []
    rows = []
    for item in objects:
        object_id = html.escape(str(item.get("object_id", "")))
        for step in item.get("subphases") or []:
            label = _display_subphase_from_evidence(step)
            planner_evidence = step.get("planner_primitive_evidence") or {}
            planner_evidence_summary = _planner_primitive_evidence_summary(planner_evidence)
            binding_summary = _planner_primitive_binding_summary(step)
            rows.append(
                "<tr>"
                f"<td>{object_id}</td>"
                f"<td>{html.escape(str(label))}</td>"
                f"<td>{html.escape(str(step.get('detail', '')))}</td>"
                f"<td>{html.escape(str(step.get('phase', '')))}</td>"
                f"<td>{html.escape(str(step.get('primitive_provenance', '')))}</td>"
                f"<td>{html.escape(planner_evidence_summary)}</td>"
                f"<td>{html.escape(binding_summary)}</td>"
                f"<td>{html.escape(str(step.get('state_sync_provenance') or ''))}</td>"
                f"<td>{html.escape(str(step.get('state_mutation') or ''))}</td>"
                "</tr>"
            )
    table = (
        '<div class="table-wrap"><table><thead><tr><th>Object</th>'
        "<th>Display subphase</th><th>Subphase role</th><th>Raw phase</th>"
        "<th>Primitive provenance</th>"
        "<th>Planner evidence</th><th>Binding</th><th>State sync</th>"
        "<th>State mutation</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
    )
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Status', evidence.get('status', 'unknown'))}"
        f"{_metric('Objects', evidence.get('object_count', 0))}"
        f"{_metric('Subphases', evidence.get('subphase_count', 0))}"
        f"{_metric('Blockers', len(evidence.get('blockers') or []))}"
        "</div>"
    )
    badges = "".join(
        (
            _badge("Planner-backed cleanup", evidence.get("planner_backed", False)),
            _badge("Strict proof", evidence.get("strict_proof_eligible", False)),
        )
    )
    note = evidence.get("evidence_note") or (
        "Strict cleanup primitive proof requires every displayed cleanup subphase "
        "to be planner_backed."
    )
    return (
        '<section class="panel cleanup-primitive-gate">'
        "<h2>Cleanup Primitive Gate</h2>"
        f'<p class="note">{html.escape(str(note))}</p>'
        f'{metrics}<div class="badges">{badges}</div>{table}</section>'
    )


def planner_cleanup_bridge_section(run_result: dict[str, Any]) -> str:
    evidence = run_result.get("planner_cleanup_bridge_evidence") or {}
    if not evidence:
        return ""
    target = evidence.get("target_runtime") or {}
    cleanup = evidence.get("cleanup_primitives") or {}
    blockers = evidence.get("blockers") or []
    blocker_rows = "".join(
        (
            "<tr>"
            f"<td>{html.escape(str(item.get('code', '')))}</td>"
            f"<td>{html.escape(str(item.get('message', '')))}</td>"
            "</tr>"
        )
        for item in blockers
    )
    if blocker_rows:
        blockers_table = (
            '<div class="table-wrap"><table><thead><tr><th>Blocker</th>'
            "<th>Message</th></tr></thead><tbody>"
            f"{blocker_rows}</tbody></table></div>"
        )
    else:
        blockers_table = '<p class="note">No bridge blockers recorded.</p>'
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Status', evidence.get('status', 'unknown'))}"
        f"{_metric('Target proof', target.get('embodiment', 'missing'))}"
        f"{_metric('Cleanup gate', cleanup.get('status', 'missing'))}"
        f"{_metric('Subphases', cleanup.get('subphase_count', 0))}"
        "</div>"
    )
    badges = "".join(
        (
            _badge("Target RBY1M/CuRobo ready", evidence.get("target_runtime_ready", False)),
            _badge("Cleanup primitives ready", evidence.get("cleanup_primitives_ready", False)),
            _badge("Bridge ready", evidence.get("planner_backed", False)),
        )
    )
    note = evidence.get("evidence_note") or (
        "Planner cleanup bridge readiness joins target runtime proof with cleanup subphase "
        "primitive provenance."
    )
    return (
        '<section class="panel planner-cleanup-bridge">'
        "<h2>Planner Cleanup Bridge</h2>"
        f'<p class="note">{html.escape(str(note))}</p>'
        f'{metrics}<div class="badges">{badges}</div>{blockers_table}</section>'
    )


def planner_proof_requests_section(run_result: dict[str, Any]) -> str:
    manifest = run_result.get("planner_proof_requests") or {}
    if not manifest:
        return ""
    requests = manifest.get("requests") or []
    rows = "".join(_planner_proof_request_row(request) for request in requests)
    if rows:
        table = (
            '<div class="table-wrap"><table><thead><tr>'
            "<th>Request</th><th>Status</th><th>Object</th><th>Source</th>"
            "<th>Target</th><th>Tools</th><th>Planner object</th>"
            "<th>Planner target</th><th>Blockers</th></tr></thead><tbody>"
            f"{rows}</tbody></table></div>"
        )
    else:
        table = '<p class="note">No planner proof requests recorded.</p>'
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Requests', manifest.get('request_count', len(requests)))}"
        f"{_metric('Ready', manifest.get('ready_count', 0))}"
        f"{_metric('Blocked', len(manifest.get('blockers') or []))}"
        "</div>"
    )
    note = manifest.get("evidence_note") or (
        "Private post-run handoff for local planner proof generation; not Agent View."
    )
    return (
        '<section class="panel planner-proof-requests">'
        "<h2>Planner Proof Requests</h2>"
        f'<p class="note">{html.escape(str(note))}</p>'
        f"{metrics}{table}</section>"
    )


def _attached_planner_proof_bundle_section(
    run_result: dict[str, Any],
    bundle: dict[str, Any],
    *,
    view_figure: ViewFigureRenderer,
) -> str:
    attachments = [item for item in bundle.get("attachments") or [] if isinstance(item, dict)]
    if not attachments:
        return ""
    quality_summary = (
        bundle.get("proof_quality_summary")
        if isinstance(bundle.get("proof_quality_summary"), dict)
        else planner_proof_quality_summary(attachments)
    )
    note = (
        bundle.get("evidence_note")
        or "Multiple strict standalone planner-backed manipulation proofs attached."
    )
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Status', bundle.get('status', 'unknown'))}"
        f"{_metric('Proofs', bundle.get('proof_count', len(attachments)))}"
        f"{_metric('Proof Quality', format_quality_tier_counts(quality_summary))}"
        f"{_metric('Min steps', quality_summary.get('min_steps_executed', 0))}"
        f"{_metric('Cleanup primitive', run_result.get('primitive_provenance', 'unknown'))}"
        "</div>"
    )
    badges = "".join(
        (
            _badge("Strict proof bundle", bundle.get("strict_proof_eligible", False)),
            _badge("Planner backed", bundle.get("planner_backed", False)),
        )
    )
    rows = []
    views = []
    for attachment in attachments:
        proof_id = str(attachment.get("proof_id") or "proof")
        binding = attachment.get("cleanup_primitive_binding") or {}
        images = attachment.get("image_artifacts") or {}
        quality = planner_proof_quality_evidence(attachment)
        rows.append(
            "<tr>"
            f"<td>{html.escape(proof_id)}</td>"
            f"<td>{html.escape(str(binding.get('object_id', '')))}</td>"
            f"<td>{html.escape(str(binding.get('target_receptacle_id', '')))}</td>"
            f"<td>{html.escape(str(attachment.get('embodiment', 'unknown')))}</td>"
            f"<td>{html.escape(str(quality.get('quality_tier', 'unknown')))}</td>"
            f"<td>{html.escape(str(attachment.get('steps_executed', 'n/a')))}</td>"
            f"<td>{html.escape(str(quality.get('containment_proven', False)))}</td>"
            "</tr>"
        )
        views.append(
            '<div class="proof-view-pair">'
            f"{view_figure(images.get('initial'), f'{proof_id} Planner Initial')}"
            f"{view_figure(images.get('final'), f'{proof_id} Planner Final')}"
            "</div>"
        )
    table = (
        '<div class="table-wrap"><table><thead><tr><th>Proof</th><th>Object</th>'
        "<th>Target</th><th>Embodiment</th><th>Quality</th><th>Steps</th>"
        "<th>Containment proven</th></tr></thead><tbody>"
        f"{''.join(rows)}</tbody></table></div>"
    )
    return (
        '<section class="panel attached-planner-proof">'
        "<h2>Attached Planner-Backed Proofs</h2>"
        f'<p class="note">{html.escape(str(note))}</p>'
        f'<p class="note"><strong>Proof Quality:</strong> '
        f"{html.escape(format_quality_tier_counts(quality_summary))}. "
        "Attached planner proofs classify robot-motion strength separately from "
        "final cleanup containment.</p>"
        f'{metrics}<div class="badges">{badges}</div>{table}'
        f'<div class="views">{"".join(views)}</div></section>'
    )


def _planner_primitive_evidence_summary(evidence: Any) -> str:
    if not isinstance(evidence, dict) or not evidence:
        return ""
    executor = str(evidence.get("executor") or "unknown")
    status = str(evidence.get("status") or "unknown")
    payload = evidence.get("evidence") if isinstance(evidence.get("evidence"), dict) else {}
    run_id = str(payload.get("planner_run_id") or payload.get("run_id") or "")
    if run_id:
        return f"{executor} {status} {run_id}"
    return f"{executor} {status}"


def _planner_primitive_binding_summary(step: dict[str, Any]) -> str:
    if not step.get("planner_primitive_evidence"):
        return ""
    object_match = step.get("object_id_matches")
    target_match = step.get("target_receptacle_id_matches")
    if object_match is True and target_match is True:
        return "object+target"
    if object_match is True:
        return "object"
    failures = []
    if object_match is False:
        failures.append("object mismatch")
    if target_match is False:
        failures.append("target mismatch")
    return ", ".join(failures)


def _planner_proof_request_row(request: dict[str, Any]) -> str:
    binding = request.get("binding") if isinstance(request.get("binding"), dict) else {}
    probe_args = request.get("planner_probe_args") or {}
    planner_object = (
        binding.get("planner_object_id") or probe_args.get("--cleanup-planner-object-id") or ""
    )
    planner_target = (
        binding.get("planner_target_receptacle_id")
        or probe_args.get("--cleanup-planner-target-receptacle-id")
        or ""
    )
    blockers = ", ".join(
        str(item.get("code") or item.get("message") or "")
        for item in request.get("blockers") or []
        if isinstance(item, dict)
    )
    tools = ", ".join(str(item) for item in request.get("tools") or [])
    status = "ready" if request.get("ready") else "blocked"
    return (
        "<tr>"
        f"<td>{html.escape(str(request.get('request_id', '')))}</td>"
        f"<td>{html.escape(status)}</td>"
        f"<td>{html.escape(str(request.get('object_id', '')))}</td>"
        f"<td>{html.escape(str(request.get('source_receptacle_id', '')))}</td>"
        f"<td>{html.escape(str(request.get('target_receptacle_id', '')))}</td>"
        f"<td>{html.escape(tools)}</td>"
        f"<td>{html.escape(str(planner_object))}</td>"
        f"<td>{html.escape(str(planner_target))}</td>"
        f"<td>{html.escape(blockers)}</td>"
        "</tr>"
    )


def _display_subphase_from_evidence(step: dict[str, Any]) -> str:
    label = step.get("label")
    if label:
        return str(label)
    return semantic_subphase_text(step.get("phase"))


def _metric(label: str, value: Any) -> str:
    return (
        '<div class="metric">'
        f"<span>{html.escape(str(label))}</span>"
        f"<strong>{html.escape(str(value))}</strong>"
        "</div>"
    )


def _badge(label: str, value: Any) -> str:
    return (
        f'<span class="badge">{html.escape(str(label))}: '
        f"<strong>{html.escape(str(value))}</strong></span>"
    )
