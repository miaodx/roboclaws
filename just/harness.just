# Self-improvement loop runner for the AI2-THOR navigator skill.
#
# Each run spawns a fresh `just code::cc` agent in a tmux session, sends the
# task, monitors via the MCP trace.jsonl, captures metrics, and tears down.
# Curated logbook lives in harness/PLAN.md.
#
# Preferred entrypoints:
# - just harness::run <task>          run one iteration on a task
# - just harness::navigator <task>    explicit navigator-harness alias
# - just harness::molmo-cleanup       deterministic MolmoSpaces cleanup artifact
# - just harness::molmo-real-cleanup  real MolmoSpaces/MuJoCo cleanup artifact
# - just harness::molmo-robot-visual  real MolmoSpaces/RBY1M visual artifact
# - just harness::molmo-agent-bridge  Molmo cleanup MCP bridge smoke + comparison
# - just harness::molmo-agent-bridge-visual  Molmo cleanup MCP bridge visual smoke + comparison
# - just harness::molmo-realworld-cleanup  ADR-0003 public/private cleanup harness
# - just harness::molmo-realworld-agent-mcp  ADR-0003 MCP smoke agent harness
# - just harness::molmo-realworld-agent-dogfood-kit  ADR-0003 direct-agent kit smoke
# - just harness::molmo-realworld-openclaw-dogfood-kit  ADR-0003 OpenClaw minimum-gate kit smoke
# - just harness::molmo-realworld-openclaw-visual-dogfood-kit  ADR-0003 OpenClaw visual kit smoke
# - just harness::molmo-realworld-raw-fpv  ADR-0013 raw FPV-only observation evidence
# - just harness::molmo-planner-proof-bundle-runner  proof-request dry-run handoff
# - just harness::molmo-planner-proof-bundle-execute-rerun  local GPU proof-bundle execution
# - just harness::molmo-planner-manipulation-probe  ADR-0014 planner-backed manipulation proof gate
# - just harness::regression          capture/analyze baseline vs candidate
# - just harness::list-tasks          show available task definitions
# - just harness::history             show the cross-run summary from PLAN.md

set working-directory := '..'
timestamp_cmd := "TZ=Asia/Shanghai date +%m%d_%H%M"

default:
    @just --list harness

# Run one iteration of the harness on a named task.
# `task` is REQUIRED (no default — see PLAN.md for why curated experiments
# beat default-task convenience). `cap` is the wall-clock cap in seconds.
#
# Examples:
#   just harness::run photo-living-room
#   just harness::run photo-living-room 600
run task cap="900":
    just harness::navigator "{{task}}" "{{cap}}"

# Explicit name for the coding-agent / AI2-THOR navigator harness.
navigator task cap="900":
    bash harness/run-next.sh "{{task}}" "{{cap}}"

# Capture and compare refactor-regression suites.
#
# mode:
#   mock           direct VLM suites with mock provider
#   local-openclaw local-only OpenClaw/Gateway suites; requires local preflight
#
# If baseline and candidate are both provided, they must be results.jsonl paths
# and only analysis runs. If both are empty, this captures a fresh baseline and
# candidate on the current checkout to smoke the harness plumbing.
regression mode="mock" baseline="" candidate="" scenes="FloorPlan201" seeds="1,2" steps="20" agents="2" model="mock":
    #!/usr/bin/env bash
    set -euo pipefail

    case "{{mode}}" in
      mock)
        suites="explore-vlm,territory-vlm,coverage-vlm"
        allow_args=()
        ;;
      local-openclaw|openclaw)
        suites="openclaw-demo,territory-openclaw,coverage-openclaw,openclaw-autonomous"
        allow_args=(--allow-local)
        ;;
      *)
        echo "error: unsupported regression mode '{{mode}}' (expected mock|local-openclaw)" >&2
        exit 1
        ;;
    esac

    if [[ -n "{{baseline}}" || -n "{{candidate}}" ]]; then
      if [[ -z "{{baseline}}" || -z "{{candidate}}" ]]; then
        echo "error: provide both baseline and candidate results.jsonl paths, or neither" >&2
        exit 1
      fi
      .venv/bin/python scripts/analyze_refactor_regression.py \
        --baseline "{{baseline}}" \
        --candidate "{{candidate}}"
      exit 0
    fi

    stamp="$(date -u +%Y%m%dT%H%M%SZ)"
    short_sha="$(git rev-parse --short HEAD)"
    baseline_label="baseline-${stamp}"
    candidate_label="candidate-${short_sha}-${stamp}"

    .venv/bin/python scripts/capture_refactor_regression.py \
      --suite "$suites" \
      --label "$baseline_label" \
      --scenes "{{scenes}}" \
      --seeds "{{seeds}}" \
      --agents "{{agents}}" \
      --steps "{{steps}}" \
      --model "{{model}}" \
      "${allow_args[@]}"

    .venv/bin/python scripts/capture_refactor_regression.py \
      --suite "$suites" \
      --label "$candidate_label" \
      --scenes "{{scenes}}" \
      --seeds "{{seeds}}" \
      --agents "{{agents}}" \
      --steps "{{steps}}" \
      --model "{{model}}" \
      "${allow_args[@]}"

    .venv/bin/python scripts/analyze_refactor_regression.py \
      --baseline "output/refactor-regression/${baseline_label}/results.jsonl" \
      --candidate "output/refactor-regression/${candidate_label}/results.jsonl"

# Real simulator regression harness with mock provider. This may download or
# launch AI2-THOR locally; use verify::mock for pure unit/mock tests.
sim scenes="FloorPlan201" seeds="1,2" steps="20" agents="2" model="mock":
    just harness::regression mock "" "" "{{scenes}}" "{{seeds}}" "{{steps}}" "{{agents}}" "{{model}}"

# Local OpenClaw/Gateway regression harness. Requires local preflight and keys.
openclaw scenes="FloorPlan201" seeds="1" steps="20" agents="2" model="mock":
    just harness::regression local-openclaw "" "" "{{scenes}}" "{{seeds}}" "{{steps}}" "{{agents}}" "{{model}}"

# Deterministic MolmoSpaces-shaped cleanup artifact harness.
molmo-cleanup seed="7" output_dir="output/molmo-cleanup-harness":
    #!/usr/bin/env bash
    set -euo pipefail
    stamp="$({{timestamp_cmd}})"
    run_dir="{{output_dir}}/${stamp}"
    mkdir -p "$run_dir"
    echo "==> run dir: ${run_dir}"
    .venv/bin/python examples/molmospaces_cleanup_demo.py \
      --seed "{{seed}}" \
      --output-dir "$run_dir"
    .venv/bin/python scripts/check_molmospaces_cleanup_result.py \
      --require-semantic-acceptability \
      "${run_dir}/run_result.json"

# Prompt-driven public-policy MolmoSpaces cleanup harness.
molmo-prompt-cleanup seed="7" output_dir="output/molmo-prompt-cleanup-harness" task="帮我整理这个房间":
    #!/usr/bin/env bash
    set -euo pipefail
    stamp="$({{timestamp_cmd}})"
    run_dir="{{output_dir}}/${stamp}"
    mkdir -p "$run_dir"
    echo "==> run dir: ${run_dir}"
    .venv/bin/python examples/molmospaces_cleanup_demo.py \
      --seed "{{seed}}" \
      --planner public_heuristic \
      --task "{{task}}" \
      --output-dir "$run_dir"
    .venv/bin/python scripts/check_molmospaces_cleanup_result.py \
      --require-public-planner \
      --expect-task "{{task}}" \
      --require-semantic-acceptability \
      "${run_dir}/run_result.json"

# Prompt-driven public-policy cleanup against a real upstream MolmoSpaces/MuJoCo scene.
molmo-real-cleanup seed="7" output_dir="output/molmo-real-cleanup-harness" task="帮我整理这个房间":
    #!/usr/bin/env bash
    set -euo pipefail
    stamp="$({{timestamp_cmd}})"
    run_dir="{{output_dir}}/${stamp}"
    mkdir -p "$run_dir"
    echo "==> run dir: ${run_dir}"
    .venv/bin/python examples/molmospaces_cleanup_demo.py \
      --seed "{{seed}}" \
      --backend molmospaces_subprocess \
      --planner public_heuristic \
      --task "{{task}}" \
      --output-dir "$run_dir"
    .venv/bin/python scripts/check_molmospaces_cleanup_result.py \
      --require-public-planner \
      --expect-task "{{task}}" \
      --expect-backend molmospaces_subprocess \
      --require-semantic-substeps \
      --require-semantic-acceptability \
      "${run_dir}/run_result.json"

# Real upstream MolmoSpaces cleanup with an actual RBY1M robot, FPV/chase/map,
# and a reviewable HTML timeline.
molmo-robot-visual seed="7" output_dir="output/molmo-robot-visual-harness" task="帮我整理这个房间":
    #!/usr/bin/env bash
    set -euo pipefail
    stamp="$({{timestamp_cmd}})"
    run_dir="{{output_dir}}/${stamp}"
    mkdir -p "$run_dir"
    echo "==> run dir: ${run_dir}"
    .venv/bin/python examples/molmospaces_cleanup_demo.py \
      --seed "{{seed}}" \
      --backend molmospaces_subprocess \
      --planner public_heuristic \
      --task "{{task}}" \
      --include-robot \
      --robot-name rby1m \
      --record-robot-views \
      --output-dir "$run_dir"
    .venv/bin/python scripts/check_molmospaces_cleanup_result.py \
      --require-public-planner \
      --expect-task "{{task}}" \
      --expect-backend molmospaces_subprocess \
      --expect-robot rby1m \
      --require-robot-views \
      --require-semantic-substeps \
      --require-semantic-acceptability \
      "${run_dir}/run_result.json"

# Current-contract Molmo MCP bridge smoke. This runs the existing public
# rule-based cleanup once, then drives the same semantic tool loop through the
# Molmo FastMCP wrapper without launching a live coding agent.
molmo-agent-bridge seed="7" output_dir="output/molmo-agent-bridge-harness" rule_dir="output/molmo-agent-bridge-rule" task="帮我整理这个房间":
    #!/usr/bin/env bash
    set -euo pipefail
    stamp="$({{timestamp_cmd}})"
    run_dir="{{output_dir}}/${stamp}"
    rule_run_dir="{{rule_dir}}/${stamp}"
    mkdir -p "$run_dir" "$rule_run_dir"
    echo "==> run dir: ${run_dir}"
    echo "==> rule dir: ${rule_run_dir}"
    .venv/bin/python examples/molmospaces_cleanup_demo.py \
      --seed "{{seed}}" \
      --planner public_heuristic \
      --task "{{task}}" \
      --output-dir "$rule_run_dir"
    .venv/bin/python scripts/run_molmo_agent_bridge_smoke.py \
      --seed "{{seed}}" \
      --task "{{task}}" \
      --output-dir "$run_dir"
    .venv/bin/python scripts/check_molmo_agent_bridge_result.py \
      --expect-policy contract_smoke_agent \
      --require-agent-driven \
      --require-clean \
      --require-semantic-acceptability \
      --compare-rule-result "${rule_run_dir}/run_result.json" \
      "${run_dir}/run_result.json"

# Current-contract Molmo MCP bridge visual harness. This uses the real
# MolmoSpaces subprocess backend plus RBY1M robot-view capture, then compares the
# bridge result against the public-rule visual baseline.
molmo-agent-bridge-visual seed="7" output_dir="output/molmo-agent-bridge-visual-harness" rule_dir="output/molmo-agent-bridge-visual-rule" task="帮我整理这个房间":
    #!/usr/bin/env bash
    set -euo pipefail
    stamp="$({{timestamp_cmd}})"
    run_dir="{{output_dir}}/${stamp}"
    rule_run_dir="{{rule_dir}}/${stamp}"
    mkdir -p "$run_dir" "$rule_run_dir"
    echo "==> run dir: ${run_dir}"
    echo "==> rule dir: ${rule_run_dir}"
    .venv/bin/python examples/molmospaces_cleanup_demo.py \
      --seed "{{seed}}" \
      --backend molmospaces_subprocess \
      --planner public_heuristic \
      --task "{{task}}" \
      --include-robot \
      --robot-name rby1m \
      --record-robot-views \
      --output-dir "$rule_run_dir"
    .venv/bin/python scripts/run_molmo_agent_bridge_smoke.py \
      --seed "{{seed}}" \
      --task "{{task}}" \
      --backend molmospaces_subprocess \
      --include-robot \
      --robot-name rby1m \
      --record-robot-views \
      --output-dir "$run_dir"
    .venv/bin/python scripts/check_molmo_agent_bridge_result.py \
      --expect-policy contract_smoke_agent \
      --expect-backend molmospaces_subprocess \
      --expect-robot rby1m \
      --require-agent-driven \
      --require-clean \
      --require-robot-views \
      --require-semantic-acceptability \
      --compare-rule-result "${rule_run_dir}/run_result.json" \
      "${run_dir}/run_result.json"

# ADR-0003 real-world-style cleanup harness. The default runs the real
# MolmoSpaces subprocess backend over three mess seeds, with the agent limited
# to metric map, room-level fixture hints, and robot-local observed handles.
# Phase 15 requests 10 hidden generated objects by default.
# It also records RBY1M robot views so report.html has the same review surface
# as the current-contract visual bridge report.
molmo-realworld-cleanup seeds="1 2 3" output_dir="output/molmo-realworld-cleanup-harness" task="帮我收拾这个房间" generated_mess_count="10":
    #!/usr/bin/env bash
    set -euo pipefail
    stamp="$({{timestamp_cmd}})"
    run_root="{{output_dir}}/${stamp}"
    mkdir -p "$run_root"
    echo "==> run root: ${run_root}"
    for seed in {{seeds}}; do
      run_dir="${run_root}/seed-${seed}"
      .venv/bin/python examples/molmospaces_realworld_cleanup.py \
        --seed "${seed}" \
        --backend molmospaces_subprocess \
        --task "{{task}}" \
        --fixture-hint-mode room_only \
        --generated-mess-count "{{generated_mess_count}}" \
        --include-robot \
        --robot-name rby1m \
        --record-robot-views \
        --output-dir "${run_dir}"
    done
    seed_csv="$(printf '%s' "{{seeds}}" | tr ' ' ',')"
    .venv/bin/python scripts/check_molmo_realworld_cleanup_result.py \
      --expect-task "{{task}}" \
      --expect-backend molmospaces_subprocess \
      --expect-seeds "${seed_csv}" \
      --min-generated-mess-count "{{generated_mess_count}}" \
      --require-robot-views \
      --require-advisory-scoring \
      "${run_root}"

# ADR-0003 real-world MCP smoke agent harness. This uses the stricter public
# contract through MCP tools: metric_map, fixture_hints, waypoint observe, and
# observed object handles. It intentionally does not expose scene_objects.
molmo-realworld-agent-mcp seeds="1" output_dir="output/molmo-realworld-agent-mcp-harness" task="帮我收拾这个房间" generated_mess_count="10":
    #!/usr/bin/env bash
    set -euo pipefail
    stamp="$({{timestamp_cmd}})"
    run_root="{{output_dir}}/${stamp}"
    mkdir -p "$run_root"
    echo "==> run root: ${run_root}"
    for seed in {{seeds}}; do
      run_dir="${run_root}/seed-${seed}"
      .venv/bin/python scripts/run_molmo_realworld_agent_mcp_smoke.py \
        --seed "${seed}" \
        --backend molmospaces_subprocess \
        --task "{{task}}" \
        --generated-mess-count "{{generated_mess_count}}" \
        --include-robot \
        --robot-name rby1m \
        --record-robot-views \
        --output-dir "${run_dir}"
    done
    seed_csv="$(printf '%s' "{{seeds}}" | tr ' ' ',')"
    .venv/bin/python scripts/check_molmo_realworld_cleanup_result.py \
      --expect-task "{{task}}" \
      --expect-backend molmospaces_subprocess \
      --expect-policy realworld_contract_smoke_agent \
      --expect-mcp-server molmo_cleanup_realworld \
      --expect-seeds "${seed_csv}" \
      --min-generated-mess-count "{{generated_mess_count}}" \
      --require-robot-views \
      --require-advisory-scoring \
      "${run_root}"

# ADR-0003 direct-agent dogfood kit smoke. This does not launch Codex/Claude;
# it proves the stricter skill/server/checker path against the synthetic backend
# before local external-agent dogfood.
molmo-realworld-agent-dogfood-kit seed="7" output_dir="output/molmo-realworld-agent-dogfood-kit" task="帮我收拾这个房间":
    #!/usr/bin/env bash
    set -euo pipefail
    stamp="$({{timestamp_cmd}})"
    run_dir="{{output_dir}}/${stamp}"
    mkdir -p "$run_dir"
    echo "==> run dir: ${run_dir}"
    .venv/bin/python scripts/run_molmo_realworld_agent_mcp_smoke.py \
      --seed "{{seed}}" \
      --backend api_semantic_synthetic \
      --task "{{task}}" \
      --policy realworld_contract_smoke_agent \
      --output-dir "$run_dir"
    .venv/bin/python scripts/check_molmo_realworld_cleanup_result.py \
      --expect-task "{{task}}" \
      --expect-backend api_semantic_synthetic \
      --expect-policy realworld_contract_smoke_agent \
      --expect-mcp-server molmo_cleanup_realworld \
      --min-generated-mess-count 5 \
      --require-agent-driven \
      --require-clean-agent-run \
      --require-advisory-scoring \
      "${run_dir}/run_result.json"

# ADR-0003 OpenClaw dogfood kit smoke. This does not launch Gateway; it proves
# the OpenClaw-labeled artifact shape and minimum checker before a local Gateway
# attempt supplies real OpenClaw evidence.
molmo-realworld-openclaw-dogfood-kit seed="7" output_dir="output/molmo-realworld-openclaw-dogfood-kit" task="帮我收拾这个房间":
    #!/usr/bin/env bash
    set -euo pipefail
    stamp="$({{timestamp_cmd}})"
    run_dir="{{output_dir}}/${stamp}"
    mkdir -p "$run_dir"
    echo "==> run dir: ${run_dir}"
    .venv/bin/python scripts/run_molmo_realworld_agent_mcp_smoke.py \
      --seed "{{seed}}" \
      --backend api_semantic_synthetic \
      --task "{{task}}" \
      --policy openclaw_agent \
      --output-dir "$run_dir"
    .venv/bin/python scripts/check_molmo_realworld_cleanup_result.py \
      --expect-task "{{task}}" \
      --expect-backend api_semantic_synthetic \
      --expect-policy openclaw_agent \
      --expect-mcp-server molmo_cleanup_realworld \
      --min-generated-mess-count 5 \
      --require-agent-driven \
      --require-openclaw-minimum \
      --require-advisory-scoring \
      "${run_dir}/run_result.json"

# ADR-0010 OpenClaw visual dogfood kit smoke. This does not launch Gateway; it
# proves OpenClaw-labeled ADR-0003 artifacts still render the real
# MolmoSpaces/RBY1M Robot View Timeline through the shared report underlay.
molmo-realworld-openclaw-visual-dogfood-kit seed="7" output_dir="output/molmo-realworld-openclaw-visual-dogfood-kit" task="帮我收拾这个房间" generated_mess_count="10":
    #!/usr/bin/env bash
    set -euo pipefail
    stamp="$({{timestamp_cmd}})"
    run_dir="{{output_dir}}/${stamp}"
    mkdir -p "$run_dir"
    echo "==> run dir: ${run_dir}"
    .venv/bin/python scripts/run_molmo_realworld_agent_mcp_smoke.py \
      --seed "{{seed}}" \
      --backend molmospaces_subprocess \
      --task "{{task}}" \
      --policy openclaw_agent \
      --generated-mess-count "{{generated_mess_count}}" \
      --include-robot \
      --robot-name rby1m \
      --record-robot-views \
      --output-dir "$run_dir"
    .venv/bin/python scripts/check_molmo_realworld_cleanup_result.py \
      --expect-task "{{task}}" \
      --expect-backend molmospaces_subprocess \
      --expect-policy openclaw_agent \
      --expect-mcp-server molmo_cleanup_realworld \
      --min-generated-mess-count "{{generated_mess_count}}" \
      --require-agent-driven \
      --require-openclaw-minimum \
      --require-clean-agent-run \
      --require-robot-views \
      --require-advisory-scoring \
      "${run_dir}/run_result.json"

# ADR-0013 raw FPV-only evidence harness. This intentionally proves perception
# boundary and report artifacts, not camera-only cleanup success.
molmo-realworld-raw-fpv seed="7" output_dir="output/molmo-realworld-raw-fpv-harness" task="帮我收拾这个房间" generated_mess_count="10":
    #!/usr/bin/env bash
    set -euo pipefail
    stamp="$({{timestamp_cmd}})"
    run_dir="{{output_dir}}/${stamp}"
    mkdir -p "$run_dir"
    echo "==> run dir: ${run_dir}"
    .venv/bin/python examples/molmospaces_realworld_cleanup.py \
      --seed "{{seed}}" \
      --backend molmospaces_subprocess \
      --task "{{task}}" \
      --fixture-hint-mode room_only \
      --perception-mode raw_fpv_only \
      --generated-mess-count "{{generated_mess_count}}" \
      --include-robot \
      --robot-name rby1m \
      --record-robot-views \
      --output-dir "$run_dir"
    .venv/bin/python scripts/check_molmo_realworld_cleanup_result.py \
      --expect-task "{{task}}" \
      --expect-backend molmospaces_subprocess \
      --min-generated-mess-count "{{generated_mess_count}}" \
      --require-robot-views \
      --require-advisory-scoring \
      --require-raw-fpv-observations \
      "${run_dir}/run_result.json"

# ADR-0042 proof-bundle runner dry-run handoff. This proves fresh ADR-0003
# cleanup artifacts produce checked planner proof commands without executing
# local GPU planner probes.
molmo-planner-proof-bundle-runner output_dir="output/molmo-planner-proof-bundle-runner-harness" seed="7" task="帮我收拾这个房间" generated_mess_count="10":
    #!/usr/bin/env bash
    set -euo pipefail
    stamp="$({{timestamp_cmd}})"
    run_root="{{output_dir}}/${stamp}"
    cleanup_dir="${run_root}/cleanup"
    bundle_dir="${run_root}/proof_bundle"
    mkdir -p "$run_root"
    echo "==> run root: ${run_root}"
    .venv/bin/python examples/molmospaces_realworld_cleanup.py \
      --seed "{{seed}}" \
      --backend api_semantic_synthetic \
      --task "{{task}}" \
      --fixture-hint-mode room_only \
      --generated-mess-count "{{generated_mess_count}}" \
      --output-dir "${cleanup_dir}"
    .venv/bin/python scripts/check_molmo_realworld_cleanup_result.py \
      --expect-task "{{task}}" \
      --expect-backend api_semantic_synthetic \
      --min-generated-mess-count 5 \
      --require-advisory-scoring \
      "${cleanup_dir}/run_result.json"
    .venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py \
      "${cleanup_dir}/run_result.json" \
      --output-dir "${bundle_dir}" \
      --runner-python .venv/bin/python \
      --embodiment rby1m \
      --probe-mode execute \
      --steps 2 \
      --timeout-s 600
    .venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py \
      "${bundle_dir}"

# ADR-0044 local-dev proof-bundle execution gate. This executes real RBY1M/CuRobo
# planner probes against the real MolmoSpaces cleanup scene and reruns cleanup
# with their proof outputs, so keep it out of default CI.
molmo-planner-proof-bundle-execute-rerun output_dir="output/molmo-planner-proof-bundle-execute-rerun" seed="7" task="帮我收拾这个房间" generated_mess_count="10" min_generated_mess_count="5" steps="2" timeout_s="600":
    #!/usr/bin/env bash
    set -euo pipefail
    stamp="$({{timestamp_cmd}})"
    run_root="{{output_dir}}/${stamp}"
    cleanup_dir="${run_root}/cleanup"
    bundle_dir="${run_root}/proof_bundle"
    rerun_dir="${run_root}/cleanup_rerun"
    torch_extensions_dir="${run_root}/torch_extensions"
    mkdir -p "$run_root"
    echo "==> run root: ${run_root}"
    .venv/bin/python examples/molmospaces_realworld_cleanup.py \
      --seed "{{seed}}" \
      --backend molmospaces_subprocess \
      --task "{{task}}" \
      --fixture-hint-mode room_only \
      --include-robot \
      --record-robot-views \
      --generated-mess-count "{{generated_mess_count}}" \
      --output-dir "${cleanup_dir}"
    .venv/bin/python scripts/check_molmo_realworld_cleanup_result.py \
      --expect-task "{{task}}" \
      --expect-backend molmospaces_subprocess \
      --min-generated-mess-count "{{min_generated_mess_count}}" \
      --require-robot-views \
      --require-advisory-scoring \
      "${cleanup_dir}/run_result.json"
    .venv/bin/python scripts/run_molmo_planner_proof_bundle_from_requests.py \
      "${cleanup_dir}/run_result.json" \
      --output-dir "${bundle_dir}" \
      --runner-python .venv/bin/python \
      --embodiment rby1m \
      --probe-mode execute \
      --steps "{{steps}}" \
      --timeout-s "{{timeout_s}}" \
      --torch-extensions-dir "${torch_extensions_dir}" \
      --execute-probes \
      --rerun-cleanup \
      --cleanup-output-dir "${rerun_dir}"
    .venv/bin/python scripts/check_molmo_planner_proof_bundle_runner_result.py \
      --require-proof-outputs \
      --require-cleanup-rerun-output \
      "${bundle_dir}"
    .venv/bin/python scripts/check_molmo_realworld_cleanup_result.py \
      --expect-task "{{task}}" \
      --expect-backend molmospaces_subprocess \
      --min-generated-mess-count "{{min_generated_mess_count}}" \
      --require-robot-views \
      --require-advisory-scoring \
      --require-planner-proof-attachment \
      --require-planner-backed-cleanup-primitives \
      --require-planner-cleanup-bridge-ready \
      "${rerun_dir}/run_result.json"

# ADR-0014 planner-backed manipulation proof gate. The default is a safe
# config-import probe that records blocked-capability evidence; use
# --probe-mode execute plus the strict checker when local planner execution is
# ready to be accepted as real manipulation proof.
molmo-planner-manipulation-probe output_dir="output/molmo-planner-manipulation-probe-harness" embodiment="franka" probe_mode="config_import" steps="2":
    #!/usr/bin/env bash
    set -euo pipefail
    stamp="$({{timestamp_cmd}})"
    run_dir="{{output_dir}}/${stamp}"
    mkdir -p "$run_dir"
    echo "==> run dir: ${run_dir}"
    .venv/bin/python scripts/run_molmo_planner_manipulation_probe.py \
      --output-dir "$run_dir" \
      --embodiment "{{embodiment}}" \
      --probe-mode "{{probe_mode}}" \
      --steps "{{steps}}"
    .venv/bin/python scripts/check_molmo_planner_manipulation_probe.py \
      --accept-blocked-capability \
      "${run_dir}/run_result.json"

# List task files available under harness/tasks/.
list-tasks:
    #!/usr/bin/env bash
    set -euo pipefail
    if ! ls harness/tasks/*.txt >/dev/null 2>&1; then
      echo "no tasks yet — drop one at harness/tasks/<name>.txt"
      exit 0
    fi
    echo "Available tasks (harness/tasks/):"
    for f in harness/tasks/*.txt; do
      base=$(basename "$f" .txt)
      first_line=$(head -1 "$f")
      printf "  %-30s %s\n" "$base" "${first_line:0:80}"
    done

# Show the run index table from PLAN.md plus per-run files in runs-log/.
# The PLAN.md index is the canonical "H: predicted | A: actual" view;
# runs-log/ files carry the full per-run analysis.
history:
    #!/usr/bin/env bash
    set -euo pipefail
    last_header=$(grep -nE '^\| Run ' harness/PLAN.md 2>/dev/null | head -1 | cut -d: -f1)
    if [[ -n "$last_header" ]]; then
      echo "## Run index (from harness/PLAN.md):"
      echo
      tail -n +"$last_header" harness/PLAN.md | awk '
        /^\|/ { print; next }
        { exit }
      '
    fi
    if ls harness/runs-log/*.md >/dev/null 2>&1; then
      echo
      echo "## Per-run files (harness/runs-log/):"
      ls -1 harness/runs-log/*.md | sed 's|^|  |'
    fi
