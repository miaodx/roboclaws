---
phase: "04"
slug: refactor-regression-harnesses-for-vlm-territory-coverage-and
status: planned
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-23
---

# Phase 04 — Validation Strategy

> Per-phase validation contract for refactor regression safety.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest |
| **Config file** | none |
| **Quick run command** | `pytest tests/test_refactor_regression_contracts.py tests/test_capture_refactor_regression.py tests/test_analyze_refactor_regression.py -q` |
| **Full suite command** | `env -i PATH=\".venv/bin:/usr/bin:/bin\" HOME=$HOME KIMI_API_KEY=\"$KIMI_API_KEY\" .venv/bin/pytest -q` |
| **Estimated runtime** | ~60 seconds for the focused slice, longer for the full suite |

---

## Sampling Rate

- **After every implementation task:** run the smallest relevant pytest slice
- **After every plan wave:** run the full focused regression-harness slice
- **Before `$gsd-verify-work`:** full suite must be green
- **Max feedback latency:** 60 seconds for unit feedback

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | A-08 | T-04-01/T-04-02 | Exact contracts are frozen with tiny fixtures and the suite scaffold stays monkeypatchable | unit | `pytest tests/test_refactor_regression_contracts.py tests/test_capture_refactor_regression.py -q` | `roboclaws/regression.py` | ⬜ pending |
| 04-02-01 | 02 | 2 | A-08 | T-04-03/T-04-04 | Direct-VLM and game suites reuse existing runners, preserve append-only rows, and expose stable pairing coordinates | unit | `pytest tests/test_capture_refactor_regression.py tests/test_refactor_regression_contracts.py -q` | `scripts/capture_refactor_regression.py` | ⬜ pending |
| 04-03-01 | 03 | 3 | A-08 | T-04-05/T-04-06/T-04-07 | OpenClaw suites stay local-dev only, extract structured metrics only, and never require live Gateway calls in tests | unit | `pytest tests/test_capture_refactor_regression.py tests/test_openclaw_demo.py tests/test_openclaw_nav_autonomous.py tests/test_render_autonomous_replay.py -q` | `scripts/capture_refactor_regression.py` | ⬜ pending |
| 04-04-01 | 04 | 4 | A-08 | T-04-08/T-04-09/T-04-10 | Baseline-vs-candidate analyzer pairs rows correctly, enforces suite thresholds, and documents the local baseline workflow truthfully | unit | `pytest tests/test_analyze_refactor_regression.py -q` | `scripts/analyze_refactor_regression.py` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠ flaky*

---

## Wave 0 Requirements

- [x] Existing pytest infrastructure and replay fixtures are sufficient; no Wave 0 scaffold is required.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Refresh one real direct-VLM baseline and compare a candidate run within the configured thresholds | A-08 | Requires real provider latency/cost behavior the cloud cannot prove | On a local workstation, `set -a && source .env && set +a`, then run `scripts/capture_refactor_regression.py` twice against the same direct-VLM suite coordinates (baseline then candidate). For the first proof these may be same-commit workflow-proof runs; record that explicitly, then run `scripts/analyze_refactor_regression.py` and record the artifact paths in `04-LOCAL-PROBE-RESULTS.md` |
| Refresh one OpenClaw push-model baseline (`openclaw-demo` or territory/coverage with `--backend openclaw`) and compare it against a candidate refactor run | A-08 | Requires Docker, AI2-THOR, a real Gateway token, and real model/tool behavior | `set -a && source .env && set +a`, run the capture harness locally with `--allow-local` on one push-model OpenClaw suite, compare the candidate run, and record termination mode, provider health, coordinate tuple, and artifact paths in `04-LOCAL-PROBE-RESULTS.md` |
| Refresh one autonomous OpenClaw baseline and confirm transcript/tool metrics stay within threshold | A-08 | Requires the shipped MCP tool surface, real Gateway behavior, and real `run_result.json` / `summary.json` artifacts | `set -a && source .env && set +a`, capture one `openclaw-autonomous` baseline and one candidate run locally, compare them with `scripts/analyze_refactor_regression.py`, and record `terminated_by`, `transcript_source`, `tool_calls_by_type`, `frames_unseen_by_agent`, the coordinate tuple, and artifact paths in `04-LOCAL-PROBE-RESULTS.md` |

---

## Validation Sign-Off

- [x] Every plan has an automated verify command or an explicit manual-only gate
- [x] The manual-only checks are confined to cloud-impossible real VLM / Gateway behavior
- [x] Phase 02.6 frozen contracts remain additive-only
- [x] No watch-mode flags
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** planned
