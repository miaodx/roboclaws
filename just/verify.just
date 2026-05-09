# Verification gate dispatcher.
#
# `verify::*` is the umbrella for confidence gates. It delegates scenario
# execution to `harness::*` where the gate drives a system under test.
#
# Preferred entrypoints:
# - just verify::static            lint/format/whitespace
# - just verify::mock              static + fast unit/mock tests
# - just verify::contract          focused fixture/schema/report contracts
# - just verify::regression-mock   baseline/candidate regression harness
# - just verify::local-sim         real AI2-THOR regression harness
# - just verify::local-openclaw    real OpenClaw/Gateway regression harness
# - just verify::navigator <task>  coding-agent navigator harness
# - just verify::molmo-cleanup     MolmoSpaces cleanup contract + harness
# - just verify::molmo-prompt-cleanup  prompt-driven public cleanup proof
# - just verify::molmo-real-cleanup    real MolmoSpaces/MuJoCo cleanup proof
# - just verify::molmo-robot-visual    real MolmoSpaces/RBY1M visual proof
# - just verify::molmo-agent-bridge    current-contract Molmo MCP bridge proof
# - just verify::molmo-agent-bridge-visual  current-contract MCP bridge visual proof
# - just verify::molmo-realworld-cleanup  ADR-0003 public/private cleanup proof
# - just verify::molmo-realworld-agent-mcp  ADR-0003 MCP smoke-agent proof
# - just verify::molmo-realworld-agent-dogfood-kit  ADR-0003 direct-agent kit proof
# - just verify::molmo-realworld-openclaw-dogfood-kit  ADR-0003 OpenClaw minimum-gate kit proof
# - just verify::molmo-realworld-openclaw-visual-dogfood-kit  ADR-0010 OpenClaw visual report proof
# - just verify::molmo-realworld-raw-fpv  ADR-0013 raw FPV-only observation proof
# - just verify::molmo-planner-proof-bundle-runner  proof-request dry-run handoff
# - just verify::molmo-planner-proof-bundle-execute-rerun  local GPU proof-bundle execution
# - just verify::molmo-planner-manipulation-probe  ADR-0014 planner manipulation proof gate
# - just verify::full-local <task> all local gates, including navigator

set working-directory := '..'

standalone_pytest := "./scripts/run_pytest_standalone.sh"

default:
    @just --list verify

# L0: static checks only.
static:
    #!/usr/bin/env bash
    set -euo pipefail
    .venv/bin/ruff check .
    .venv/bin/ruff format --check .
    git diff --check

# L1: static checks plus fast unit/mock tests.
mock:
    #!/usr/bin/env bash
    set -euo pipefail
    just verify::static
    just dev::test fast

# L2: focused fixture/schema/report contracts.
contract:
    {{standalone_pytest}} -q \
      tests/test_refactor_regression_contracts.py \
      tests/test_run_artifacts.py \
      tests/test_capture_refactor_regression.py \
      tests/test_analyze_refactor_regression.py \
      tests/test_render_autonomous_replay.py \
      tests/test_reporter.py

# L3: mock-provider baseline/candidate refactor-regression harness.
regression-mock baseline="" candidate="" scenes="FloorPlan201" seeds="1,2" steps="20" agents="2" model="mock":
    just harness::regression mock "{{baseline}}" "{{candidate}}" "{{scenes}}" "{{seeds}}" "{{steps}}" "{{agents}}" "{{model}}"

# L4: local simulator harness using AI2-THOR with mock provider.
local-sim scenes="FloorPlan201" seeds="1,2" steps="20" agents="2" model="mock":
    just harness::sim "{{scenes}}" "{{seeds}}" "{{steps}}" "{{agents}}" "{{model}}"

# L5: local OpenClaw/Gateway/provider harness.
local-openclaw scenes="FloorPlan201" seeds="1" steps="20" agents="2" model="mock":
    just harness::openclaw "{{scenes}}" "{{seeds}}" "{{steps}}" "{{agents}}" "{{model}}"

# L6: coding-agent navigator harness.
navigator task cap="900":
    just harness::navigator "{{task}}" "{{cap}}"

# Focused MolmoSpaces cleanup pilot gate.
molmo-cleanup:
    #!/usr/bin/env bash
    set -euo pipefail
    {{standalone_pytest}} -q \
      tests/test_molmo_cleanup_scenario.py \
      tests/test_molmo_cleanup_scoring.py \
      tests/test_molmo_cleanup_backend.py \
      tests/test_molmo_cleanup_mcp_contract.py \
      tests/test_molmo_cleanup_report.py \
      tests/test_molmo_cleanup_demo.py \
      tests/test_verify_just_recipes.py
    just harness::molmo-cleanup

# Prompt-driven public-policy MolmoSpaces cleanup gate.
molmo-prompt-cleanup:
    #!/usr/bin/env bash
    set -euo pipefail
    {{standalone_pytest}} -q \
      tests/test_molmo_cleanup_policy.py \
      tests/test_molmo_cleanup_semantic_acceptability.py \
      tests/test_molmo_cleanup_demo.py \
      tests/test_verify_just_recipes.py
    just harness::molmo-prompt-cleanup

# Real upstream MolmoSpaces/MuJoCo prompt-cleanup gate. Requires the isolated
# Python 3.11 MolmoSpaces runtime; set ROBOCLAWS_MOLMOSPACES_PYTHON if needed.
molmo-real-cleanup:
    #!/usr/bin/env bash
    set -euo pipefail
    {{standalone_pytest}} -q \
      tests/test_molmo_cleanup_policy.py \
      tests/test_molmo_cleanup_demo.py \
      tests/test_verify_just_recipes.py
    just harness::molmo-real-cleanup

# Real upstream MolmoSpaces/MuJoCo robot visual gate. Requires the isolated
# Python 3.11 MolmoSpaces runtime and local robot assets.
molmo-robot-visual:
    #!/usr/bin/env bash
    set -euo pipefail
    {{standalone_pytest}} -q \
      tests/test_molmo_cleanup_policy.py \
      tests/test_molmo_cleanup_demo.py \
      tests/test_molmo_cleanup_report.py \
      tests/test_molmo_cleanup_subprocess_backend.py \
      tests/test_verify_just_recipes.py
    just harness::molmo-robot-visual

# Current-contract Molmo MCP bridge gate. Real Codex/Claude/OpenClaw dogfood is
# local-operator evidence; this focused gate proves the server, skill, reports,
# checker, and rule-based comparison stay wired.
molmo-agent-bridge:
    #!/usr/bin/env bash
    set -euo pipefail
    {{standalone_pytest}} -q \
      tests/test_molmo_cleanup_mcp_server.py \
      tests/test_molmo_cleanup_semantic_acceptability.py \
      tests/test_molmo_cleanup_agent_server.py \
      tests/test_check_molmo_agent_bridge_result.py \
      tests/test_molmo_mcp_smoke_shared_semantic_loop.py \
      tests/test_molmo_cleanup_report.py \
      tests/test_verify_just_recipes.py
    just harness::molmo-agent-bridge

# Current-contract Molmo MCP bridge visual gate. Requires the isolated Python
# 3.11 MolmoSpaces runtime and local robot assets.
molmo-agent-bridge-visual:
    #!/usr/bin/env bash
    set -euo pipefail
    {{standalone_pytest}} -q \
      tests/test_molmo_cleanup_mcp_server.py \
      tests/test_molmo_cleanup_semantic_acceptability.py \
      tests/test_molmo_cleanup_agent_server.py \
      tests/test_check_molmo_agent_bridge_result.py \
      tests/test_molmo_cleanup_report.py \
      tests/test_molmo_cleanup_subprocess_backend.py \
      tests/test_verify_just_recipes.py
    just harness::molmo-agent-bridge-visual

# ADR-0003 public/private cleanup gate. Requires the isolated Python 3.11
# MolmoSpaces runtime for the harness; focused tests use the synthetic backend.
molmo-realworld-cleanup generated_mess_count="10":
    #!/usr/bin/env bash
    set -euo pipefail
    {{standalone_pytest}} -q \
      tests/test_molmo_realworld_contract.py \
      tests/test_molmospaces_realworld_cleanup.py \
      tests/test_check_molmo_realworld_cleanup_result.py \
      tests/test_molmo_cleanup_report.py \
      tests/test_verify_just_recipes.py
    just harness::molmo-realworld-cleanup "1 2 3" "output/molmo-realworld-cleanup-harness" "帮我收拾这个房间" "{{generated_mess_count}}"

# ADR-0003 real-world MCP smoke-agent gate. Requires the isolated Python 3.11
# MolmoSpaces runtime for the harness; focused tests use the synthetic backend.
molmo-realworld-agent-mcp generated_mess_count="10":
    #!/usr/bin/env bash
    set -euo pipefail
    {{standalone_pytest}} -q \
      tests/test_molmo_realworld_mcp_server.py \
      tests/test_check_molmo_realworld_cleanup_result.py \
      tests/test_molmo_mcp_smoke_shared_semantic_loop.py \
      tests/test_verify_just_recipes.py
    just harness::molmo-realworld-agent-mcp "1" "output/molmo-realworld-agent-mcp-harness" "帮我收拾这个房间" "{{generated_mess_count}}"

# ADR-0003 direct-agent dogfood kit gate. Real Codex/Claude/OpenClaw dogfood is
# local evidence; this focused gate proves the stricter skill, server setup,
# checker, and synthetic artifact shape stay wired.
molmo-realworld-agent-dogfood-kit:
    #!/usr/bin/env bash
    set -euo pipefail
    {{standalone_pytest}} -q \
      tests/test_molmo_realworld_agent_server.py \
      tests/test_molmo_realworld_mcp_server.py \
      tests/test_check_molmo_realworld_cleanup_result.py \
      tests/test_verify_just_recipes.py
    just harness::molmo-realworld-agent-dogfood-kit

# ADR-0003 OpenClaw dogfood kit gate. Real Gateway dogfood is local evidence;
# this focused gate proves the OpenClaw minimum checker and artifact shape.
molmo-realworld-openclaw-dogfood-kit:
    #!/usr/bin/env bash
    set -euo pipefail
    {{standalone_pytest}} -q \
      tests/test_molmo_realworld_mcp_server.py \
      tests/test_check_molmo_realworld_cleanup_result.py \
      tests/test_verify_just_recipes.py
    just harness::molmo-realworld-openclaw-dogfood-kit

# ADR-0010 OpenClaw visual dogfood kit gate. Real Gateway dogfood is local
# evidence; this focused gate proves the OpenClaw-labeled visual report shape.
molmo-realworld-openclaw-visual-dogfood-kit generated_mess_count="10":
    #!/usr/bin/env bash
    set -euo pipefail
    {{standalone_pytest}} -q \
      tests/test_molmo_realworld_mcp_server.py \
      tests/test_check_molmo_realworld_cleanup_result.py \
      tests/test_molmo_cleanup_report.py \
      tests/test_verify_just_recipes.py
    just harness::molmo-realworld-openclaw-visual-dogfood-kit "7" "output/molmo-realworld-openclaw-visual-dogfood-kit" "帮我收拾这个房间" "{{generated_mess_count}}"

# ADR-0013 raw FPV-only observation gate. Requires the isolated Python 3.11
# MolmoSpaces runtime and local robot assets for the harness evidence.
molmo-realworld-raw-fpv generated_mess_count="10":
    #!/usr/bin/env bash
    set -euo pipefail
    {{standalone_pytest}} -q \
      tests/test_molmo_realworld_contract.py \
      tests/test_molmo_realworld_mcp_server.py \
      tests/test_molmo_cleanup_report.py \
      tests/test_check_molmo_realworld_cleanup_result.py \
      tests/test_verify_just_recipes.py
    just harness::molmo-realworld-raw-fpv "7" "output/molmo-realworld-raw-fpv-harness" "帮我收拾这个房间" "{{generated_mess_count}}"

# ADR-0042 proof-bundle runner dry-run handoff. Real planner execution remains
# an explicit local-dev follow-up outside this default verify gate.
molmo-planner-proof-bundle-runner:
    #!/usr/bin/env bash
    set -euo pipefail
    {{standalone_pytest}} -q \
      tests/test_verify_just_recipes.py \
      tests/test_run_molmo_planner_proof_bundle_from_requests.py \
      tests/test_check_molmo_planner_proof_bundle_runner_result.py
    just harness::molmo-planner-proof-bundle-runner

# ADR-0044 local-dev proof-bundle execution gate. Requires local CUDA and
# MolmoSpaces/RBY1M/CuRobo runtime; not part of default CI.
molmo-planner-proof-bundle-execute-rerun:
    #!/usr/bin/env bash
    set -euo pipefail
    {{standalone_pytest}} -q \
      tests/test_verify_just_recipes.py \
      tests/test_run_molmo_planner_proof_bundle_from_requests.py \
      tests/test_check_molmo_planner_proof_bundle_runner_result.py \
      tests/test_check_molmo_realworld_cleanup_result.py
    just harness::molmo-planner-proof-bundle-execute-rerun

# ADR-0014 planner-backed manipulation proof gate. Default verification accepts
# explicit blocked-capability evidence; strict planner-backed proof uses the
# checker --require-planner-backed flag outside this default gate.
molmo-planner-manipulation-probe:
    #!/usr/bin/env bash
    set -euo pipefail
    {{standalone_pytest}} -q \
      tests/test_molmo_cleanup_report.py \
      tests/test_molmo_manipulation_provenance.py \
      tests/test_check_molmo_planner_manipulation_probe.py \
      tests/test_verify_just_recipes.py
    just harness::molmo-planner-manipulation-probe

# Full local confidence ladder. This intentionally requires a navigator task
# so the slowest gate is explicit rather than accidental.
full-local task cap="900":
    #!/usr/bin/env bash
    set -euo pipefail
    just verify::mock
    just verify::contract
    just verify::regression-mock
    just verify::local-sim
    just verify::local-openclaw
    just verify::navigator "{{task}}" "{{cap}}"
