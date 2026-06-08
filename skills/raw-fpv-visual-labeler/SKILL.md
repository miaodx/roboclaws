---
name: raw-fpv-visual-labeler
description: Label visible cleanup-relevant movable objects from grouped RAW-FPV frames without creating executable cleanup handles.
---

# RAW-FPV Visual Labeler

Use this skill only for perception-only RAW-FPV labeling probes. It consumes
public robot FPV frame evidence and emits structured visual labels for review
and offline scoring. It does not call cleanup tools, does not create
`observed_*` handles, and does not authorize navigation, pick, place, or `done`.

## Inputs

Use 3-6 neighboring RAW-FPV frames from the same waypoint, sweep segment, or
source observation neighborhood when available. Each frame may include only:

- public frame id;
- image artifact;
- public waypoint or room context already visible to the cleanup agent;
- optional public semantic-map planning hints marked non-executable.

Never include private labels, generated hidden target ids, acceptable
destination truth, executable observed-object handles, detector candidates, or
camera-label producer candidates.

## Output

Return strict JSON:

```json
{
  "schema": "raw_fpv_visual_labeler_response_v1",
  "labels": [
    {
      "evidence_frame_id": "run/raw_fpv_001",
      "category": "mug",
      "category_family": "dish",
      "coarse_region": "middle_right",
      "confidence": 0.82,
      "is_cleanup_relevant": true,
      "bbox": [0.62, 0.5, 0.12, 0.15],
      "surface_hint": "table",
      "reason_not_actionable": ""
    }
  ]
}
```

Required per label:

- `evidence_frame_id`
- `category`
- `category_family`
- `coarse_region`
- `confidence`
- `is_cleanup_relevant`

Optional per label:

- `bbox`
- `surface_hint`
- `reason_not_actionable`

Allowed category families are `food`, `dish`, `book`, `linen`, `toy`, and
`electronics`. Fixtures and surfaces such as tables, beds, counters, shelves,
sinks, cabinets, and floors may be mentioned only as `surface_hint` or as
`is_cleanup_relevant=false`; they are not object hits.

## Boundary

These labels are perception evidence. The cleanup agent must not consume them
as executable handles in `camera-raw-fpv`. A later assisted RAW-FPV or
`camera-grounded-labels` producer decision would need its own contract change.
