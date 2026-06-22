# Cross-Environment Map Waypoint Source Of Truth

Source plan:
`docs/plans/2026-06-20-cross-environment-map-waypoint-source-of-truth.md`

Latest user intent: approved implementation after plan discussion.

Current slice: Slice 1 implemented; Slice 2 next. The full plan is not
complete; Slices 2-5 remain pending.

Completed:

- Added strict `validate_base_navigation_map_v1_bundle()` product gate.
- B1 base-map generation and Digital Twin sidecar generation now call the
  strict validator.
- Current MolmoSpaces bundle strict-validation gaps are explicit test evidence,
  not silent fallback behavior.

Last proof:

```bash
./scripts/dev/run_pytest_standalone.sh -q \
  tests/contract/maps/test_nav2_map_bundle_contract.py \
  tests/contract/maps/test_b1_map12_base_navigation_map.py \
  tests/contract/maps/test_b1_map12_base_navigation_sidecar.py

ruff check \
  roboclaws/maps \
  scripts/maps/build_b1_map12_base_navigation_map.py \
  scripts/maps/augment_b1_map12_base_navigation_map.py \
  tests/contract/maps/test_nav2_map_bundle_contract.py \
  tests/contract/maps/test_b1_map12_base_navigation_map.py \
  tests/contract/maps/test_b1_map12_base_navigation_sidecar.py
```

Next action:

Implement Slice 2: extract the canonical area-based `BaseWaypointBuilder` and
validator without changing simulator generation yet.

Pending:

- Slice 2: canonical area-based `BaseWaypointBuilder`.
- Slice 3: MolmoSpaces source-map builder split.
- Slice 4: remove Agent View snapshot fallback.
- Slice 5: runtime contract cleanup.

No-touch scope:

- Existing unrelated refactor/python-quality files.
- Existing unrelated live runtime / JSON source / report changes.
- Existing untracked SDK storage active note.
