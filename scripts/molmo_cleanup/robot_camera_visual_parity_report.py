from __future__ import annotations

import html
import json
from typing import Any


def render_visual_parity_report(manifest: dict[str, Any]) -> str:
    checks = _dict(manifest.get("checks"))
    four_check = _dict(manifest.get("four_check_audit"))
    report_side = _dict(manifest.get("report_side_visual_parity"))
    default_rendering = _dict(manifest.get("default_rendering_visual_parity"))
    visual_samples = _render_visual_samples(_list_dicts(manifest.get("visual_samples")))
    render_difference_probe_batch = _render_render_difference_probe_batch(
        _dict(manifest.get("render_difference_probe_batch"))
    )
    capture_quality_summary = _render_capture_quality_summary(manifest)
    object_audit_rows = _render_object_visual_parity_audit_rows(manifest)
    four_check_rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('check_id') or ''))}</td>"
        f"<td>{html.escape(str(item.get('status') or ''))}</td>"
        f"<td>{html.escape(str(item.get('source_status') or item.get('probe_status') or ''))}</td>"
        f"<td>{html.escape(str(item.get('decision') or ''))}</td>"
        "</tr>"
        for item in four_check.get("rows") or []
        if isinstance(item, dict)
    )
    rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(check_id)}</td>"
        f"<td>{html.escape(str(_dict(check).get('status') or ''))}</td>"
        f"<td>{html.escape(str(_dict(check).get('interpretation') or ''))}</td>"
        "</tr>"
        for check_id, check in checks.items()
    )
    baseline_rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('path') or ''))}</td>"
        f"<td>{html.escape(str(item.get('scene_signature') or ''))}</td>"
        f"<td>{html.escape(_capture_quality_cell(item))}</td>"
        f"<td>{html.escape(str(item.get('fpv_mean_abs_rgb_avg') or ''))}</td>"
        f"<td>{html.escape(str(item.get('chase_mean_abs_rgb_avg') or ''))}</td>"
        f"<td>{html.escape(str(item.get('object_parity_status') or ''))}</td>"
        f"<td>{html.escape(str(item.get('object_parity_high_priority_gap_count') or ''))}</td>"
        f"<td>{html.escape(str(item.get('object_render_gate_status') or ''))}</td>"
        f"<td>{html.escape(str(item.get('object_gate_failure_count') or ''))}</td>"
        f"<td>{html.escape(str(item.get('render_gate_status') or ''))}</td>"
        "</tr>"
        for item in manifest.get("baselines") or []
        if isinstance(item, dict)
    )
    probe_rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(str(item.get('label') or ''))}</td>"
        f"<td>{html.escape(str(item.get('probe_kind') or ''))}</td>"
        f"<td>{html.escape(str(item.get('scene_signature') or ''))}</td>"
        f"<td>{html.escape(_capture_quality_cell(item))}</td>"
        f"<td>{html.escape(str(item.get('fpv_mean_abs_rgb_avg') or ''))}</td>"
        f"<td>{html.escape(str(item.get('object_parity_status') or ''))}</td>"
        f"<td>{html.escape(str(item.get('object_parity_high_priority_gap_count') or ''))}</td>"
        f"<td>{html.escape(str(item.get('object_render_gate_status') or ''))}</td>"
        f"<td>{html.escape(str(item.get('object_gate_failure_count') or ''))}</td>"
        f"<td>{html.escape(str(item.get('render_gate_status') or ''))}</td>"
        "</tr>"
        for item in manifest.get("probes") or []
        if isinstance(item, dict)
    )
    baseline_header = (
        "<tr><th>Manifest</th><th>Scene</th><th>Capture Quality</th><th>FPV</th><th>Chase</th>"
        "<th>Object Parity</th><th>Object Gaps</th><th>Object/Render Gate</th>"
        "<th>Gate Failures</th><th>Render Gate</th></tr>"
    )
    probe_header = (
        "<tr><th>Label</th><th>Kind</th><th>Scene</th><th>Capture Quality</th><th>FPV</th>"
        "<th>Object Parity</th><th>Object Gaps</th><th>Object/Render Gate</th>"
        "<th>Gate Failures</th><th>Render Gate</th></tr>"
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Robot Camera Visual Parity</title>
  <style>
    body {{ font-family: system-ui, sans-serif; margin: 24px; line-height: 1.45; }}
    table {{ border-collapse: collapse; width: 100%; margin: 16px 0; }}
    th, td {{ border: 1px solid #ccc; padding: 6px 8px; text-align: left; vertical-align: top; }}
    th {{ background: #f3f3f3; }}
    code {{ background: #f6f6f6; padding: 1px 4px; }}
    .visual-samples {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
      gap: 18px;
    }}
    .sample {{ border: 1px solid #d7d7d7; padding: 12px; background: #fafafa; }}
    .sample h3 {{ margin: 0 0 6px; font-size: 16px; }}
    .view-grid {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 10px;
      margin-top: 8px;
    }}
    figure {{ margin: 0; }}
    img {{
      display: block;
      width: 100%;
      height: auto;
      border: 1px solid #ccc;
      background: #111;
      cursor: zoom-in;
    }}
    figcaption {{ color: #555; font-size: 12px; margin-top: 4px; }}
    .muted {{ color: #666; }}
    .lightbox {{
      align-items: center;
      background: rgb(0 0 0 / 0.86);
      display: none;
      inset: 0;
      justify-content: center;
      padding: 28px;
      position: fixed;
      z-index: 1000;
    }}
    .lightbox[aria-hidden="false"] {{ display: flex; }}
    .lightbox__figure {{
      max-height: 94vh;
      max-width: min(1200px, 96vw);
    }}
    .lightbox__figure img {{
      border-color: #444;
      cursor: default;
      max-height: 88vh;
      object-fit: contain;
      width: auto;
      max-width: 100%;
    }}
    .lightbox__figure figcaption {{
      color: #f3f3f3;
      font-size: 14px;
      margin-top: 8px;
      text-align: center;
    }}
    .lightbox__close {{
      background: #fff;
      border: 0;
      border-radius: 4px;
      color: #111;
      cursor: pointer;
      font: inherit;
      padding: 8px 12px;
      position: fixed;
      right: 24px;
      top: 18px;
    }}
  </style>
</head>
<body>
  <h1>Robot Camera Visual Parity</h1>
  <p>Status: <code>{html.escape(str(manifest.get("status")))}</code></p>
  <p>Report-side visual parity:
    <code>{html.escape(str(report_side.get("status") or ""))}</code>
    ({html.escape(str(report_side.get("policy_scope") or ""))})
  </p>
  <p>Default-rendering visual parity:
    <code>{html.escape(str(default_rendering.get("status") or ""))}</code>
    ({html.escape(str(default_rendering.get("policy_scope") or ""))})
  </p>
  <p>{html.escape(str(manifest.get("recommended_next_action") or ""))}</p>
  <h2>Four-Check Audit</h2>
  <p>{html.escape(str(four_check.get("interpretation") or ""))}</p>
  <table>
    <thead>
      <tr><th>Check</th><th>Status</th><th>Source Status</th><th>Decision</th></tr>
    </thead>
    <tbody>{four_check_rows}</tbody>
  </table>
  <h2>Visual Samples</h2>
  {visual_samples}
  <h2>Capture Quality Probe Metadata</h2>
  {capture_quality_summary}
  <h2>Render Difference Probe Batch</h2>
  {render_difference_probe_batch}
  <h2>Checks</h2>
  <table><thead><tr><th>Check</th><th>Status</th><th>Interpretation</th></tr></thead><tbody>{rows}</tbody></table>
  <h2>Baselines</h2>
  <table><thead>{baseline_header}</thead><tbody>{baseline_rows}</tbody></table>
  <h2>Probes</h2>
  <table><thead>{probe_header}</thead><tbody>{probe_rows}</tbody></table>
  <h2>Object Visual Parity Audit</h2>
  {object_audit_rows}
  <div
    class="lightbox"
    data-lightbox
    aria-hidden="true"
    role="dialog"
    aria-modal="true"
    aria-label="Image preview"
  >
    <button class="lightbox__close" type="button" data-lightbox-close>Close</button>
    <figure class="lightbox__figure">
      <img data-lightbox-image alt="">
      <figcaption data-lightbox-caption></figcaption>
    </figure>
  </div>
  <script>
    (() => {{
      const lightbox = document.querySelector("[data-lightbox]");
      if (!lightbox) return;
      const preview = lightbox.querySelector("[data-lightbox-image]");
      const caption = lightbox.querySelector("[data-lightbox-caption]");
      const closeButton = lightbox.querySelector("[data-lightbox-close]");

      const close = () => {{
        lightbox.setAttribute("aria-hidden", "true");
        preview.removeAttribute("src");
        preview.setAttribute("alt", "");
        caption.textContent = "";
      }};

      const open = (image) => {{
        const figureCaption = image.closest("figure")?.querySelector("figcaption");
        const label = figureCaption?.textContent || image.getAttribute("alt") || "Image preview";
        preview.setAttribute("src", image.currentSrc || image.src);
        preview.setAttribute("alt", image.getAttribute("alt") || label);
        caption.textContent = label;
        lightbox.setAttribute("aria-hidden", "false");
        closeButton.focus();
      }};

      document.querySelectorAll("img:not([data-lightbox-image])").forEach((image) => {{
        image.setAttribute("role", "button");
        image.setAttribute("tabindex", "0");
        image.setAttribute("title", "Open image preview");
        image.addEventListener("click", () => open(image));
        image.addEventListener("keydown", (event) => {{
          if (event.key === "Enter" || event.key === " ") {{
            event.preventDefault();
            open(image);
          }}
        }});
      }});

      closeButton.addEventListener("click", close);
      lightbox.addEventListener("click", (event) => {{
        if (event.target === lightbox) close();
      }});
      document.addEventListener("keydown", (event) => {{
        if (event.key === "Escape" && lightbox.getAttribute("aria-hidden") === "false") {{
          close();
        }}
      }});
    }})();
  </script>
</body>
</html>
"""


def _render_object_visual_parity_audit_rows(manifest: dict[str, Any]) -> str:
    rows = []
    sources = [("baseline", item) for item in _list_dicts(manifest.get("baselines"))]
    sources.extend(("probe", item) for item in _list_dicts(manifest.get("probes")))
    for source_kind, summary in sources:
        audit = _dict(summary.get("object_visual_parity_audit"))
        for category in _list_dicts(audit.get("category_status_summary")):
            rows.append(
                "<tr>"
                f"<td>{html.escape(source_kind)}</td>"
                f"<td>{html.escape(str(summary.get('label') or summary.get('path') or ''))}</td>"
                f"<td>{html.escape(str(summary.get('scene_signature') or ''))}</td>"
                f"<td>{html.escape(str(audit.get('status') or ''))}</td>"
                f"<td>{html.escape(str(category.get('category') or ''))}</td>"
                f"<td>{html.escape(str(category.get('item_count') or 0))}</td>"
                + _json_counts_cell(category, "binding_status_counts")
                + _json_counts_cell(category, "category_status_counts")
                + _json_counts_cell(category, "state_status_counts")
                + _json_counts_cell(category, "object_gate_status_counts")
                + _json_counts_cell(category, "rgb_view_evidence_status_counts")
                + _json_counts_cell(category, "render_contract_status_counts")
                + "</tr>"
            )
    if not rows:
        return "<p class='muted'>No object visual parity category summaries were recorded.</p>"
    return (
        "<table><thead><tr><th>Source</th><th>Manifest</th><th>Scene</th>"
        "<th>Audit Status</th><th>Category</th><th>Items</th><th>Binding</th>"
        "<th>Category Status</th><th>State</th><th>Object Gate</th>"
        "<th>RGB Evidence</th><th>Render</th></tr></thead><tbody>"
        + "\n".join(rows)
        + "</tbody></table>"
    )


def _render_capture_quality_summary(manifest: dict[str, Any]) -> str:
    sources = [("baseline", item) for item in _list_dicts(manifest.get("baselines"))]
    sources.extend(("probe", item) for item in _list_dicts(manifest.get("probes")))
    rows = []
    for source_kind, item in sources:
        capture_quality = _dict(item.get("capture_quality_probe"))
        if not capture_quality:
            continue
        anti_aliasing = _dict(capture_quality.get("anti_aliasing"))
        tonemap_operator = _dict(capture_quality.get("tonemap_operator"))
        exposure_bias = _dict(capture_quality.get("exposure_bias"))
        colorcorr_gain = _dict(capture_quality.get("colorcorr_gain"))
        denoise = _dict(capture_quality.get("denoise"))
        taa = _dict(capture_quality.get("taa"))
        rows.append(
            "<tr>"
            f"<td>{html.escape(source_kind)}</td>"
            f"<td>{html.escape(str(item.get('label') or item.get('path') or ''))}</td>"
            f"<td>{html.escape(str(item.get('probe_kind') or 'baseline'))}</td>"
            f"<td>{html.escape(_resolution_label(capture_quality.get('render_resolution_requested')))}</td>"
            f"<td>{html.escape(_resolution_label(capture_quality.get('render_resolution_saved')))}</td>"
            f"<td>{html.escape(_resolution_label(capture_quality.get('metric_resolution')))}</td>"
            f"<td>{html.escape(str(capture_quality.get('saved_image_mode') or ''))}</td>"
            f"<td>{html.escape(str(capture_quality.get('metric_image_mode') or ''))}</td>"
            f"<td>{html.escape(str(capture_quality.get('downsample_filter') or ''))}</td>"
            f"<td>{html.escape(str(capture_quality.get('render_settle_frames') or 0))}</td>"
            f"<td>{html.escape(str(anti_aliasing.get('status') or ''))}</td>"
            f"<td>{html.escape(str(tonemap_operator.get('status') or ''))}</td>"
            f"<td>{html.escape(str(exposure_bias.get('status') or ''))}</td>"
            f"<td>{html.escape(str(colorcorr_gain.get('status') or ''))}</td>"
            f"<td>{html.escape(str(denoise.get('status') or ''))}</td>"
            f"<td>{html.escape(str(taa.get('status') or ''))}</td>"
            f"<td>{html.escape(str(capture_quality.get('policy_classification') or ''))}</td>"
            "</tr>"
        )
    if not rows:
        return "<p class='muted'>No capture-quality probe metadata was recorded.</p>"
    return (
        "<p class='muted'>Direct high-resolution review images and downsampled "
        "same-size metrics are tracked separately here. These rows do not promote "
        "native renderer defaults.</p>"
        "<table><thead><tr><th>Source</th><th>Manifest</th><th>Kind</th>"
        "<th>Render Size</th><th>Saved Size</th><th>Metric Size</th>"
        "<th>Saved Mode</th><th>Metric Mode</th><th>Filter</th><th>Settle</th>"
        "<th>AA</th><th>Tone Op</th><th>Exposure</th><th>Colorcorr</th>"
        "<th>Denoise</th><th>TAA</th><th>Policy</th></tr></thead><tbody>"
        + "\n".join(rows)
        + "</tbody></table>"
    )


def _render_render_difference_probe_batch(batch: dict[str, Any]) -> str:
    rows = []
    for row in _list_dicts(batch.get("ranked_rows")):
        native = _dict(row.get("native_settings_used"))
        residual_classes = html.escape(
            json.dumps(row.get("residual_class_distribution") or {}, sort_keys=True)
        )
        rows.append(
            "<tr>"
            f"<td>{_html_value(row.get('rank'))}</td>"
            f"<td>{_html_value(row.get('label'))}</td>"
            f"<td>{_html_value(row.get('probe_kind'))}</td>"
            f"<td>{_html_value(row.get('fpv_mean_abs_rgb_delta_vs_baseline'))}</td>"
            f"<td>{_html_value(row.get('chase_mean_abs_rgb_delta_vs_baseline'))}</td>"
            f"<td>{_html_value(_resolution_label(row.get('render_resolution_requested')))}</td>"
            f"<td>{_html_value(_resolution_label(row.get('render_resolution_saved')))}</td>"
            f"<td>{_html_value(_resolution_label(row.get('metric_resolution')))}</td>"
            f"<td>{_html_value(row.get('metric_image_mode'))}<br>"
            f"<code>filter={_html_value(row.get('downsample_filter'))}</code></td>"
            f"<td>{_html_value(row.get('render_settle_frames'))}</td>"
            f"<td>{_html_value(row.get('policy_classification'))}</td>"
            f"<td>{_html_value(row.get('classification_reason'))}</td>"
            f"<td>{residual_classes}</td>"
            f"<td>{_html_value(native.get('status'))}<br>"
            f"<code>changed={_html_value(native.get('default_render_settings_changed'))}</code>"
            f"<br><code>aa={_html_value(_dict(_dict(row.get('capture_quality_settings')).get('anti_aliasing')).get('status'))}</code>"
            f"<br><code>exposure={_html_value(_dict(_dict(row.get('capture_quality_settings')).get('exposure_bias')).get('status'))}</code>"
            f"<br><code>colorcorr={_html_value(_dict(_dict(row.get('capture_quality_settings')).get('colorcorr_gain')).get('status'))}</code>"
            f"<br><code>denoise={_html_value(_dict(_dict(row.get('capture_quality_settings')).get('denoise')).get('status'))}</code>"
            "</td>"
            "</tr>"
        )
    if not rows:
        return "<p class='muted'>No render-difference probe manifests were provided.</p>"
    return (
        "<p class='muted'>" + html.escape(str(batch.get("interpretation") or "")) + "</p>"
        "<table><thead><tr><th>Rank</th><th>Label</th><th>Kind</th>"
        "<th>FPV Delta</th><th>Chase Delta</th><th>Render Size</th>"
        "<th>Saved Size</th><th>Metric Size</th><th>Metric Mode</th>"
        "<th>Settle</th><th>Candidate Status</th>"
        "<th>Reason</th><th>Residual Classes</th><th>Native Settings</th></tr></thead><tbody>"
        + "\n".join(rows)
        + "</tbody></table>"
    )


def _capture_quality_cell(item: dict[str, Any]) -> str:
    capture_quality = _dict(item.get("capture_quality_probe"))
    if not capture_quality:
        return ""
    parts = [
        f"render={_resolution_label(capture_quality.get('render_resolution_requested'))}",
        f"saved={_resolution_label(capture_quality.get('render_resolution_saved'))}",
        f"metric={_resolution_label(capture_quality.get('metric_resolution'))}",
        f"metric_mode={capture_quality.get('metric_image_mode') or ''}",
        f"settle={capture_quality.get('render_settle_frames')}",
    ]
    if capture_quality.get("downsample_filter"):
        parts.append(f"filter={capture_quality.get('downsample_filter')}")
    tonemap_operator = _dict(capture_quality.get("tonemap_operator"))
    if tonemap_operator:
        parts.append(f"tone_op={tonemap_operator.get('status') or ''}")
    return "; ".join(parts)


def _resolution_label(value: Any) -> str:
    resolution = _dict(value)
    width = resolution.get("width")
    height = resolution.get("height")
    return f"{width}x{height}" if width and height else ""


def _html_value(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _json_counts_cell(item: dict[str, Any], key: str) -> str:
    return "<td>" + html.escape(json.dumps(item.get(key) or {}, sort_keys=True)) + "</td>"


def _render_visual_samples(samples: list[dict[str, Any]]) -> str:
    if not samples:
        return "<p class='muted'>No image samples were available in the input manifests.</p>"
    cards = []
    for sample in samples:
        title = " / ".join(
            part
            for part in (
                str(sample.get("kind") or ""),
                str(sample.get("label") or ""),
                str(sample.get("location_label") or ""),
            )
            if part
        )
        metrics = f"FPV {sample.get('fpv_mean_abs_rgb')}, chase {sample.get('chase_mean_abs_rgb')}"
        missing = _list_strings(sample.get("missing_images"))
        missing_note = (
            "<p class='muted'>Missing images: " + html.escape(", ".join(missing)) + "</p>"
            if missing
            else ""
        )
        cards.append(
            "<section class='sample'>"
            f"<h3>{html.escape(title)}</h3>"
            f"<p class='muted'>{html.escape(str(sample.get('scene_signature') or ''))}</p>"
            f"<p>{html.escape(metrics)}</p>"
            + _render_visual_sample_view(sample, "fpv")
            + _render_visual_sample_view(sample, "chase")
            + missing_note
            + "</section>"
        )
    return "<div class='visual-samples'>" + "\n".join(cards) + "</div>"


def _render_visual_sample_view(sample: dict[str, Any], view: str) -> str:
    images = _dict(_dict(sample.get("images")).get(view))
    mujoco = images.get("mujoco")
    isaac = images.get("isaac")
    if not mujoco and not isaac:
        return ""
    residual = sample.get(f"{view}_residual_class") or ""
    view_note = ""
    view_badge = ""
    if view == "chase":
        source_note = " / ".join(
            part
            for part in (
                str(sample.get("chase_mujoco_source") or ""),
                str(sample.get("chase_isaac_source") or ""),
            )
            if part
        )
        note = str(sample.get("chase_contract_note") or "")
        if source_note:
            note = f"{note} Sources: {source_note}."
        view_note = f"<p class='muted'>{html.escape(note)}</p>" if note else ""
        if not sample.get("chase_same_camera_contract"):
            view_badge = " non-comparable auxiliary"
    cells = []
    for backend, path in (("MuJoCo", mujoco), ("Isaac", isaac)):
        if not path:
            continue
        cells.append(
            "<figure>"
            f"<img src='{html.escape(str(path), quote=True)}' "
            f"alt='{html.escape(backend)} {html.escape(view.upper())}'>"
            f"<figcaption>{html.escape(backend)} {html.escape(view.upper())}</figcaption>"
            "</figure>"
        )
    return (
        f"<h4>{html.escape(view.upper())} "
        f"<span class='muted'>{html.escape(str(residual) + view_badge)}</span></h4>"
        + view_note
        + "<div class='view-grid'>"
        + "\n".join(cells)
        + "</div>"
    )


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
