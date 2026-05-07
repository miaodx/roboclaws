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
      tests/test_molmo_cleanup_demo.py \
      tests/test_verify_just_recipes.py
    just harness::molmo-prompt-cleanup

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
