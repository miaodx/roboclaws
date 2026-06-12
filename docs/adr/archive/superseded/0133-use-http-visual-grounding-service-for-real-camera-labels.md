# 0133. Use HTTP Visual Grounding Service For Real Camera Labels

Date: 2026-05-25

## Status

Superseded by [ADR-0138](../../0138-use-detector-only-visual-grounding-sidecar.md).

## Context

ADR-0126 introduced Model-Declared Observations as the bridge from public camera
evidence to cleanup handles. The existing `camera-labels` lane is still backed
by deterministic simulated camera-model evidence, while the next comparison
needs real visual grounding pipelines over the same RAW_FPV evidence.

## Decision

Roboclaws will keep `world-labels`, `camera-raw`, and `camera-labels` as input
contract profiles, and represent the candidate source as pipeline/provenance
metadata.
Real visual grounding will be integrated through an HTTP service boundary rather
than an in-process Python import or a new public MCP capability tool.

The cleanup runtime will treat a real grounding model as an External Visual
Grounding Service: it receives public camera evidence and returns model-declared
candidate evidence such as category, image region, confidence, and producer
metadata. Roboclaws then applies the public destination hint resolver to produce
the normalized cleanup candidate shape used by existing sim/API lanes.

The service boundary will be HTTP. The first contract should support uploading
the FPV image bytes in JSON with observation metadata and category hints,
because the service may run on a different machine. The formal service contract
should not depend on local artifact paths. The service may suggest a destination
fixture, but Roboclaws will treat that as evidence only; the public destination
hint resolver owns the final normalized candidate destination. Service failures
must remain visible as pipeline failures with zero fabricated candidates and
must not silently fall back to simulator-state labels unless the run explicitly
selected the simulator pipeline.

Live Codex cleanup runs should use the same server-side integration path. The
Codex agent should continue calling `observe` and `declare_visual_candidates`;
Roboclaws owns the external grounding-service call behind that tool boundary so
agent containers do not need direct access to image artifact paths, grounding
service credentials, or model-host network details.

The HTTP schema should stay provider-neutral and pipeline-aware. Grounding DINO,
YOLOE, or a fixed/custom YOLO model may act as bbox proposers. Qwen3-VL and
MiMo v2 Omni should first fit as refiner adapters that validate, relabel,
reject, or enrich proposed regions. They may also be tested as direct replacement
producers, but that is a comparison mode rather than the recommended first
path. Qwen3-VL support may be designed around its available Transformers, vLLM,
or SGLang serving routes, but Roboclaws should not require a direct Qwen3-VL
implementation or add Qwen3-VL runtime dependencies to the core cleanup
environment before local access and performance are proven. A Qwen3-VL
Transformers smoke probe is acceptable as a sidecar experiment, but it must not
block the fake HTTP contract phase or the first proposer benchmark phase.

Visual-grounding selection should not depend only on end-to-end cleanup probes.
Roboclaws should add a perception-isolated benchmark corpus and harness that
replays fixed RAW_FPV observations, category hints, and public fixture context
through proposer-only, proposer-plus-refiner, and direct-producer pipelines.
Only promising pipelines need expensive live cleanup runs.

## Consequences

- Real visual grounding pipelines can run on different machines, GPUs, or
  dependency environments without changing the cleanup runtime.
- The default public MCP cleanup surface stays stable; models remain perception
  producers rather than cleanup capability tools.
- `camera-labels visual_grounding=sim` can remain a pipeline-control baseline,
  while `camera-labels visual_grounding=<pipeline-id>` can compare real camera
  grounding against `world-labels` and `camera-raw`.
- Reports and checkers should preserve pipeline stage provenance and distinguish
  Visual Grounding Quality from Destination Hint Quality.
- HTTP credentials, if used, are runtime configuration and must not appear in
  reports; reports should record provider id, model id, version, status, and
  latency instead.
- Grounding DINO and YOLOE can be compared as proposers; Qwen3-VL and MiMo v2
  Omni can be compared as refiners and optional direct producers without
  changing the cleanup MCP contract or direct cleanup runtime dependencies.
- Perception-only benchmarks become a required selection tool before promoting
  any pipeline to the normal end-to-end cleanup matrix.
- The implementation plan lives in
  `docs/plans/molmospaces-http-visual-grounding-service.md`.
