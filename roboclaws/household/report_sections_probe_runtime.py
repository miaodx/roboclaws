from __future__ import annotations

import html
from typing import Any


def planner_probe_diagnostics_section(evidence: dict[str, Any]) -> str:
    diagnostics = evidence.get("runtime_diagnostics") or {}
    if not diagnostics:
        return ""
    modules = diagnostics.get("modules") or {}
    rows = []
    for module_name, module_info in sorted(modules.items()):
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(module_name))}</td>"
            f"<td>{html.escape(str(module_info.get('available', False)))}</td>"
            f"<td>{html.escape(str(module_info.get('version') or ''))}</td>"
            "</tr>"
        )
    module_table = (
        '<div class="table-wrap"><table><thead><tr><th>Module</th><th>Available</th>'
        "<th>Version</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
    )
    summary = (
        f"python={diagnostics.get('python_version', '')}; "
        f"executable={diagnostics.get('python_executable', '')}; "
        f"faulthandler={diagnostics.get('faulthandler_enabled', False)}; "
        f"renderer_adapter={diagnostics.get('renderer_adapter_enabled', False)}; "
        f"renderer_device={diagnostics.get('renderer_device_id', '')}; "
        f"MUJOCO_GL={diagnostics.get('mujoco_gl_env', '')}; "
        f"PYOPENGL_PLATFORM={diagnostics.get('pyopengl_platform_env', '')}; "
        f"CUDA_HOME={diagnostics.get('cuda_home_env', '')}; "
        f"TORCH_CUDA_ARCH_LIST={diagnostics.get('torch_cuda_arch_list_env', '')}"
    )
    torch_info = diagnostics.get("torch") or {}
    torch_summary = (
        f"torch={torch_info.get('version', '')}; "
        f"torch_cuda={torch_info.get('cuda_version', '')}; "
        f"torch_cuda_available={torch_info.get('cuda_available', False)}; "
        f"torch_cuda_home={torch_info.get('cpp_extension_cuda_home', '')}"
    )
    return (
        '<section class="panel"><h2>Runtime Diagnostics</h2>'
        f'<p class="note">{html.escape(summary)}</p>'
        f'<p class="note">{html.escape(torch_summary)}</p>{module_table}</section>'
    )


def planner_probe_cuda_memory_section(evidence: dict[str, Any]) -> str:
    diagnostics = evidence.get("runtime_diagnostics") or {}
    cuda = diagnostics.get("cuda_memory") or {}
    snapshots = _planner_probe_cuda_memory_snapshots(evidence)
    if not cuda and not snapshots:
        return ""
    current = cuda.get("current_snapshot") or (snapshots[-1] if snapshots else {})
    free_memory = _memory_pair(current.get("free_bytes"), current.get("total_bytes"))
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('CUDA', 'available' if cuda.get('available') else 'missing')}"
        f"{_metric('Device count', cuda.get('device_count', 0))}"
        f"{_metric('Current device', _cuda_device_label(current, cuda))}"
        f"{_metric('Free memory', free_memory)}"
        f"{_metric('Torch allocated', _format_bytes(current.get('torch_allocated_bytes')))}"
        f"{_metric('Torch reserved', _format_bytes(current.get('torch_reserved_bytes')))}"
        "</div>"
    )
    env_note = (
        f"CUDA_VISIBLE_DEVICES={diagnostics.get('cuda_visible_devices_env', '')}; "
        f"PYTORCH_CUDA_ALLOC_CONF={diagnostics.get('pytorch_cuda_alloc_conf_env', '')}"
    )
    rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('elapsed_s', '')))}</td>"
        f"<td>{html.escape(str(item.get('stage', '')))}</td>"
        f"<td>{html.escape(_cuda_device_label(item, cuda))}</td>"
        f"<td>{html.escape(_memory_pair(item.get('free_bytes'), item.get('total_bytes')))}</td>"
        f"<td>{html.escape(_format_bytes(item.get('torch_allocated_bytes')))}</td>"
        f"<td>{html.escape(_format_bytes(item.get('torch_reserved_bytes')))}</td>"
        f"<td>{html.escape(str(item.get('error') or item.get('error_type') or ''))}</td>"
        "</tr>"
        for item in snapshots
    )
    if not rows:
        rows = '<tr><td colspan="7">No stage snapshots recorded.</td></tr>'
    table = (
        '<div class="table-wrap"><table><thead><tr><th>Elapsed s</th><th>Stage</th>'
        "<th>Device</th><th>Free / total</th><th>Torch allocated</th>"
        "<th>Torch reserved</th><th>Error</th></tr></thead><tbody>"
        + rows
        + "</tbody></table></div>"
    )
    note = (
        "CUDA memory headroom is runtime evidence only. OOM-blocked artifacts "
        "still do not satisfy strict planner-backed cleanup readiness."
    )
    return (
        '<section class="panel"><h2>CUDA Memory Headroom</h2>'
        f'<p class="note">{html.escape(note)}</p>'
        f'<p class="note">{html.escape(env_note)}</p>{metrics}{table}</section>'
    )


def planner_probe_curobo_memory_profile_section(evidence: dict[str, Any]) -> str:
    profile = evidence.get("curobo_memory_profile") or {}
    if not profile:
        return ""
    after = profile.get("after") or {}
    policy = after.get("policy") or {}
    planners = after.get("planners") or {}
    first_planner = next(iter(planners.values()), {})
    metrics = (
        '<div class="metric-grid">'
        f"{_metric('Profile', profile.get('profile', 'unknown'))}"
        f"{_metric('Applied', _yes_no(profile.get('applied')))}"
        f"{_metric('Batch size', policy.get('batch_size', 'unknown'))}"
        f"{_metric('Max batches', policy.get('max_batch_plan_attempts', 'unknown'))}"
        f"{_metric('Collision avoidance', _yes_no(policy.get('enable_collision_avoidance')))}"
        f"{_metric('Trajopt seeds', first_planner.get('num_trajopt_seeds', 'unknown'))}"
        "</div>"
    )
    before = profile.get("before") or {}
    rows = _curobo_profile_rows(
        "policy",
        before.get("policy") or {},
        policy,
        ("batch_size", "max_batch_plan_attempts", "enable_collision_avoidance"),
    )
    before_planners = before.get("planners") or {}
    for planner_name, planner_after in sorted(planners.items()):
        rows.extend(
            _curobo_profile_rows(
                f"{planner_name}_planner",
                before_planners.get(planner_name) or {},
                planner_after,
                (
                    "num_trajopt_seeds",
                    "num_ik_seeds",
                    "max_attempts",
                    "trajopt_tsteps",
                    "enable_finetune_trajopt",
                ),
            )
        )
    table_rows = "".join(rows) or '<tr><td colspan="4">No profile values recorded.</td></tr>'
    table = (
        '<div class="table-wrap"><table><thead><tr><th>Scope</th><th>Setting</th>'
        f"<th>Before</th><th>After</th></tr></thead><tbody>{table_rows}</tbody></table></div>"
    )
    note = (
        "CuRobo memory profile is probe-local runtime evidence. Tuning state is "
        "visible before target readiness or cleanup primitive replacement is considered."
    )
    return (
        '<section class="panel"><h2>CuRobo Memory Profile</h2>'
        f'<p class="note">{html.escape(note)}</p>{metrics}{table}</section>'
    )


def planner_probe_curobo_extension_cache_section(evidence: dict[str, Any]) -> str:
    diagnostics = evidence.get("runtime_diagnostics") or {}
    cache = diagnostics.get("curobo_extension_cache") or {}
    extensions = cache.get("extensions") or {}
    if not extensions:
        return ""
    rows = []
    lock_count = 0
    so_count = 0
    for name, item in sorted(extensions.items()):
        if item.get("lock_exists"):
            lock_count += 1
        if item.get("so_exists"):
            so_count += 1
        files = item.get("files") or []
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(name))}</td>"
            f"<td>{html.escape(str(item.get('build_dir', '')))}</td>"
            f"<td>{html.escape(_yes_no(item.get('so_exists')))}</td>"
            f"<td>{html.escape(_yes_no(item.get('lock_exists')))}</td>"
            f"<td>{len(files)}</td>"
            f"<td>{html.escape(_curobo_cache_file_detail(files))}</td>"
            "</tr>"
        )
    summary = (
        '<div class="metric-grid">'
        f"{_metric('Configured dir', cache.get('configured_dir') or 'default')}"
        f"{_metric('Extensions', len(extensions))}"
        f"{_metric('Compiled .so', f'{so_count}/{len(extensions)}')}"
        f"{_metric('Locks', lock_count)}"
        "</div>"
    )
    table = (
        '<div class="table-wrap"><table><thead><tr><th>Extension</th>'
        "<th>Build dir</th><th>.so</th><th>Lock</th><th>Files</th><th>Detail</th>"
        "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
    )
    note = (
        "CuRobo planner imports JIT-compile several Torch CUDA extensions. "
        "This panel makes stale locks and missing binaries visible before strict readiness."
    )
    return (
        '<section class="panel"><h2>CuRobo Extension Cache</h2>'
        f'<p class="note">{html.escape(note)}</p>{summary}{table}</section>'
    )


def planner_probe_warp_compatibility_section(evidence: dict[str, Any]) -> str:
    diagnostics = evidence.get("runtime_diagnostics") or {}
    warp = diagnostics.get("warp_compatibility") or {}
    if not warp:
        return ""
    adapter = warp.get("adapter") or {}
    summary = (
        '<div class="metric-grid">'
        f"{_metric('Warp', 'available' if warp.get('available') else 'missing')}"
        f"{_metric('Version', warp.get('version') or 'unknown')}"
        f"{_metric('warp.torch', _yes_no(warp.get('has_torch_attr')))}"
        f"{_metric('Adapter applied', _yes_no(adapter.get('applied')))}"
        "</div>"
    )
    rows = [
        ("has_device_from_torch", warp.get("has_device_from_torch")),
        ("has_from_torch", warp.get("has_from_torch")),
        ("has_stream_from_torch", warp.get("has_stream_from_torch")),
        ("adapter_reason", adapter.get("reason", "")),
        ("adapter_provided", ", ".join(adapter.get("provided") or [])),
    ]
    table_rows = "".join(
        "<tr>"
        f"<td>{html.escape(str(name))}</td>"
        f"<td>{html.escape(_yes_no(value) if isinstance(value, bool) else str(value))}</td>"
        "</tr>"
        for name, value in rows
        if value not in (None, "", [])
    )
    table = (
        '<div class="table-wrap"><table><thead><tr><th>Signal</th><th>Value</th>'
        "</tr></thead><tbody>" + table_rows + "</tbody></table></div>"
    )
    note = (
        "Warp compatibility is probe-local runtime evidence. It makes any "
        "adapter visible before strict RBY1M/CuRobo readiness is considered."
    )
    return (
        '<section class="panel"><h2>Warp Compatibility</h2>'
        f'<p class="note">{html.escape(note)}</p>{summary}{table}</section>'
    )


def planner_probe_worker_stages_section(evidence: dict[str, Any]) -> str:
    events = evidence.get("worker_stage_events") or []
    if not events:
        return ""
    rows = []
    for item in events:
        rows.append(
            "<tr>"
            f"<td>{html.escape(str(item.get('elapsed_s', '')))}</td>"
            f"<td>{html.escape(str(item.get('event', '')))}</td>"
            f"<td>{html.escape(str(item.get('stage', '')))}</td>"
            f"<td>{html.escape(_worker_stage_detail(item))}</td>"
            "</tr>"
        )
    last_stage = evidence.get("last_worker_stage") or events[-1].get("stage")
    note = (
        "Worker stage events are emitted before expensive RBY1M/CuRobo warmup "
        "and execution steps, so timeout artifacts preserve the last observed stage."
    )
    summary = (
        '<div class="metric-grid">'
        f"{_metric('Events', len(events))}"
        f"{_metric('Last stage', last_stage or 'unknown')}"
        "</div>"
    )
    table = (
        '<div class="table-wrap"><table><thead><tr><th>Elapsed s</th>'
        "<th>Event</th><th>Stage</th><th>Detail</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table></div>"
    )
    return (
        '<section class="panel"><h2>Worker Stage Timeline</h2>'
        f'<p class="note">{html.escape(note)}</p>{summary}{table}</section>'
    )


def _planner_probe_cuda_memory_snapshots(evidence: dict[str, Any]) -> list[dict[str, Any]]:
    snapshots = list(evidence.get("cuda_memory_snapshots") or [])
    if snapshots:
        return snapshots
    return [
        item["cuda_memory"]
        for item in evidence.get("worker_stage_events") or []
        if item.get("event") == "cuda_memory_snapshot" and item.get("cuda_memory")
    ]


def _cuda_device_label(snapshot: dict[str, Any], diagnostics: dict[str, Any]) -> str:
    device_name = snapshot.get("device_name")
    if not device_name:
        devices = diagnostics.get("devices") or []
        current_index = snapshot.get("device_index", diagnostics.get("current_device_index"))
        device = next((item for item in devices if item.get("index") == current_index), {})
        device_name = device.get("name")
    device_index = snapshot.get("device_index", diagnostics.get("current_device_index", ""))
    if device_name:
        return f"{device_index}: {device_name}"
    return str(device_index)


def _memory_pair(free_bytes: Any, total_bytes: Any) -> str:
    if free_bytes is None and total_bytes is None:
        return "unknown"
    return f"{_format_bytes(free_bytes)} / {_format_bytes(total_bytes)}"


def _format_bytes(value: Any) -> str:
    if value in (None, ""):
        return "unknown"
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return str(value)
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    unit = units[0]
    for unit in units:
        if abs(amount) < 1024.0 or unit == units[-1]:
            break
        amount /= 1024.0
    if unit == "B":
        return str(int(amount))
    return f"{amount:.1f} {unit}"


def _curobo_profile_rows(
    scope: str,
    before: dict[str, Any],
    after: dict[str, Any],
    keys: tuple[str, ...],
) -> list[str]:
    rows = []
    for key in keys:
        rows.append(
            "<tr>"
            f"<td>{html.escape(scope)}</td>"
            f"<td>{html.escape(key)}</td>"
            f"<td>{html.escape(str(before.get(key, '')))}</td>"
            f"<td>{html.escape(str(after.get(key, '')))}</td>"
            "</tr>"
        )
    return rows


def _curobo_cache_file_detail(files: list[dict[str, Any]]) -> str:
    if not files:
        return ""
    return "; ".join(f"{item.get('name')}:{item.get('size_bytes')}" for item in files[:6])


def _worker_stage_detail(item: dict[str, Any]) -> str:
    details = []
    for key in (
        "embodiment",
        "probe_mode",
        "upstream_policy_class",
        "steps",
        "steps_executed",
        "max_abs_qpos_delta",
    ):
        value = item.get(key)
        if value not in (None, ""):
            details.append(f"{key}={value}")
    cuda_memory = item.get("cuda_memory")
    if isinstance(cuda_memory, dict):
        details.append(f"cuda_free={_format_bytes(cuda_memory.get('free_bytes'))}")
        details.append(f"torch_reserved={_format_bytes(cuda_memory.get('torch_reserved_bytes'))}")
    return "; ".join(details)


def _metric(label: str, value: Any) -> str:
    return (
        '<div class="metric">'
        f"<span>{html.escape(str(label))}</span>"
        f"<strong>{html.escape(str(value))}</strong>"
        "</div>"
    )


def _yes_no(value: Any) -> str:
    return "yes" if bool(value) else "no"
