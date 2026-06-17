from __future__ import annotations

import html
from pathlib import Path
from typing import Any

from roboclaws.household.scene_camera_report_figures import _standalone_review_section
from roboclaws.household.scene_camera_report_format import _image_modal_html
from roboclaws.household.scene_camera_report_sections_contract import (
    _anchor_section,
    _backend_swap_geometry_section,
    _contact_sheet_section,
    _failure_section,
    _intrinsics_contract_section,
    _pose_contract_section,
    _room_scale_section,
    _runtime_section,
    _summary_section,
    _transform_section,
)
from roboclaws.household.scene_camera_report_sections_diagnostics import (
    _candidate_visual_diagnostics_section,
    _lighting_tone_provenance_section,
    _native_isaac_render_diagnostics_section,
    _projection_diagnostics_section,
    _render_domain_contract_probe_section,
    _render_domain_source_section,
    _render_domain_view_triage_section,
    _room_wall_light_diagnostics_section,
    _shadow_parity_probe_section,
    _visual_diagnostics_section,
)


def report_html(manifest: dict[str, Any], *, output_dir: Path) -> str:
    title = "MolmoSpaces / Isaac Scene Camera Comparison"
    body = "\n".join(
        [
            _summary_section(title, manifest),
            _standalone_review_section(manifest, output_dir=output_dir),
            _contact_sheet_section(manifest, output_dir=output_dir),
            _pose_contract_section(manifest),
            _intrinsics_contract_section(manifest),
            _room_scale_section(manifest),
            _backend_swap_geometry_section(manifest),
            _transform_section(manifest),
            _projection_diagnostics_section(manifest),
            _visual_diagnostics_section(manifest),
            _room_wall_light_diagnostics_section(manifest),
            _candidate_visual_diagnostics_section(manifest),
            _native_isaac_render_diagnostics_section(manifest),
            _lighting_tone_provenance_section(manifest),
            _shadow_parity_probe_section(manifest),
            _render_domain_source_section(manifest),
            _render_domain_view_triage_section(manifest),
            _render_domain_contract_probe_section(manifest),
            _anchor_section(manifest),
            _runtime_section(manifest),
            _failure_section(manifest),
        ]
    )
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html.escape(title)}</title>
  <style>
    body {{
      margin: 0;
      font-family: system-ui, -apple-system, Segoe UI, sans-serif;
      background: #eef2f6;
      color: #20242c;
    }}
    main {{ max-width: 1360px; margin: 0 auto; padding: 20px 20px 42px; }}
    h1 {{ margin: 0; font-size: 28px; letter-spacing: 0; }}
    h2 {{ margin: 0 0 12px; font-size: 20px; letter-spacing: 0; }}
    h3 {{ margin: 0 0 8px; font-size: 16px; letter-spacing: 0; }}
    .summary {{
      background: #20242c;
      color: #f8fafc;
      border-radius: 8px;
      padding: 18px;
    }}
    .summary p {{ color: #dbe5ef; max-width: 980px; margin: 8px 0; }}
    .eyebrow {{
      margin: 0 0 6px;
      color: #a7d8cf;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: .08em;
      text-transform: uppercase;
    }}
    .badges {{ display: flex; flex-wrap: wrap; gap: 8px; }}
    .badge {{
      background: #fff;
      border: 1px solid #d9dde6;
      border-radius: 6px;
      padding: 7px 10px;
      overflow-wrap: anywhere;
    }}
    .summary .badge {{
      background: rgba(255,255,255,.09);
      border-color: rgba(255,255,255,.18);
      color: #e9edf4;
    }}
    .panel {{
      background: #fff;
      border: 1px solid #d8dee8;
      border-radius: 8px;
      padding: 16px;
      margin-top: 14px;
    }}
    .note {{ color: #565f70; margin: 0 0 12px; }}
    .warning-note {{
      color: #7a2e0e;
      background: #fff7ed;
      border: 1px solid #fed7aa;
      border-radius: 6px;
      padding: 10px 12px;
      margin: 0 0 12px;
    }}
    .table-wrap {{ overflow-x: auto; border: 1px solid #d9dde6; border-radius: 8px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{
      padding: 9px 10px;
      text-align: left;
      border-bottom: 1px solid #e5e8ee;
      font-size: 14px;
      overflow-wrap: anywhere;
    }}
    th {{ background: #eef1f5; font-weight: 650; }}
    .status-degraded {{ color: #b45309; font-weight: 700; }}
    .status-ok {{ color: #047857; font-weight: 700; }}
    .comparison-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
      gap: 12px;
    }}
    .review-panel {{
      border-color: #aab7c7;
      box-shadow: 0 1px 2px rgba(15, 23, 42, .08);
    }}
    .review-panel h2 {{ margin-bottom: 6px; }}
    .contact-sheet {{
      width: 100%;
      max-height: 960px;
      object-fit: contain;
      background: #f8fafc;
      border: 1px solid #d9dde6;
      border-radius: 6px;
    }}
    figure {{
      margin: 0;
      background: #fff;
      border: 1px solid #d9dde6;
      border-radius: 6px;
      padding: 10px;
    }}
    img {{ width: 100%; height: auto; display: block; }}
    .image-open-button {{
      appearance: none;
      display: block;
      width: 100%;
      margin: 0;
      padding: 0;
      border: 0;
      background: transparent;
      cursor: zoom-in;
      text-align: inherit;
    }}
    .crop-grid {{
      display: grid;
      grid-template-columns: repeat(3, 72px);
      gap: 6px;
      align-items: start;
    }}
    .crop-thumb {{
      display: grid;
      gap: 3px;
      font-size: 10px;
      color: #647083;
    }}
    .crop-image {{
      width: 72px;
      height: 72px;
      object-fit: cover;
      border: 1px solid #d9dde6;
      border-radius: 4px;
      background: #f8fafc;
    }}
    .image-modal {{
      width: min(96vw, 1440px);
      max-height: 94vh;
      padding: 0;
      border: 1px solid #334155;
      border-radius: 8px;
      background: #0f172a;
      color: #f8fafc;
    }}
    .image-modal::backdrop {{ background: rgba(15, 23, 42, .72); }}
    .image-modal-header {{
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      padding: 10px 12px;
      border-bottom: 1px solid rgba(255, 255, 255, .14);
      font-size: 14px;
    }}
    .image-modal-title {{ overflow-wrap: anywhere; }}
    .image-modal-close {{
      border: 1px solid rgba(255, 255, 255, .3);
      border-radius: 6px;
      background: rgba(255, 255, 255, .08);
      color: #f8fafc;
      padding: 5px 9px;
      cursor: pointer;
    }}
    .image-modal img {{
      width: 100%;
      max-height: calc(94vh - 48px);
      object-fit: contain;
      background: #020617;
    }}
    figcaption {{
      display: grid;
      gap: 3px;
      margin-top: 8px;
      color: #565f70;
      font-size: 14px;
    }}
    figcaption strong {{ color: #20242c; }}
    figcaption span {{ color: #647083; font-size: 12px; }}
    .missing {{
      display: grid;
      place-items: center;
      min-height: 220px;
      border: 1px dashed #cbd5e1;
      border-radius: 6px;
      color: #647083;
      background: #f8fafc;
    }}
    @media (max-width: 720px) {{
      main {{ padding: 18px 12px 36px; }}
      .comparison-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body><main>{body}</main>{_image_modal_html()}</body>
</html>
"""
