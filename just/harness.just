# Self-improvement loop runner for the AI2-THOR navigator skill.
#
# Each run spawns a fresh `just code::cc` agent in a tmux session, sends the
# task, monitors via the MCP trace.jsonl, captures metrics, and tears down.
# Curated logbook lives in harness/PLAN.md.
#
# Preferred entrypoints:
# - just harness::run <task>          run one iteration on a task
# - just harness::navigator <task>    explicit navigator-harness alias
# - just harness::molmo-cleanup-codex-perf  live Codex cleanup performance lane
# - just harness::molmo-realworld-cleanup  ADR-0003 public/private cleanup harness
# - just harness::molmo-realworld-agent-mcp  ADR-0003 MCP smoke agent harness
# - just harness::molmo-realworld-agent-dogfood-kit  ADR-0003 direct-agent kit smoke
# - just harness::molmo-realworld-openclaw-dogfood-kit  ADR-0003 OpenClaw minimum-gate kit smoke
# - just harness::molmo-realworld-openclaw-visual-dogfood-kit  ADR-0003 OpenClaw visual kit smoke
# - just harness::molmo-realworld-raw-fpv  ADR-0013 raw FPV-only observation evidence
# - just harness::molmo-planner-proof-bundle-runner  proof-request dry-run handoff
# - just harness::molmo-planner-proof-bundle-execute-rerun  local GPU proof-bundle execution
# - just harness::molmo-planner-manipulation-probe  ADR-0014 planner-backed manipulation proof gate
# - just harness::molmo-visual-grounding-benchmark  perception-isolated HTTP grounding harness
# - just harness::molmo-isaac-runtime-preflight  Isaac Lab local runtime setup gate
# - just harness::molmo-isaac-runtime-smoke  strict Isaac Lab renderer/USD smoke gate
# - just harness::molmo-isaac-cleanup-smoke  strict Isaac Lab cleanup report gate
# - just harness::molmo-isaac-prepared-cleanup-smoke  prepare semantic USD + strict cleanup gate
# - just harness::regression          capture/analyze baseline vs candidate
# - just harness::list-tasks          show available task definitions
# - just harness::history             show the cross-run summary from PLAN.md

set working-directory := '..'
set positional-arguments
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
    #!/usr/bin/env bash
    set -euo pipefail
    source scripts/dev/coding_agent_env.sh
    roboclaws_load_dotenv .env
    roboclaws_assert_claude_code_network_allowed "Claude Code navigator harness"
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
        bash scripts/dev/network_status.sh --assert-off-work "OpenClaw regression harness"
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
      .venv/bin/python scripts/regression/analyze_refactor_regression.py \
        --baseline "{{baseline}}" \
        --candidate "{{candidate}}"
      exit 0
    fi

    stamp="$(date -u +%Y%m%dT%H%M%SZ)"
    short_sha="$(git rev-parse --short HEAD)"
    baseline_label="baseline-${stamp}"
    candidate_label="candidate-${short_sha}-${stamp}"

    .venv/bin/python scripts/regression/capture_refactor_regression.py \
      --suite "$suites" \
      --label "$baseline_label" \
      --scenes "{{scenes}}" \
      --seeds "{{seeds}}" \
      --agents "{{agents}}" \
      --steps "{{steps}}" \
      --model "{{model}}" \
      "${allow_args[@]}"

    .venv/bin/python scripts/regression/capture_refactor_regression.py \
      --suite "$suites" \
      --label "$candidate_label" \
      --scenes "{{scenes}}" \
      --seeds "{{seeds}}" \
      --agents "{{agents}}" \
      --steps "{{steps}}" \
      --model "{{model}}" \
      "${allow_args[@]}"

    .venv/bin/python scripts/regression/analyze_refactor_regression.py \
      --baseline "output/refactor-regression/${baseline_label}/results.jsonl" \
      --candidate "output/refactor-regression/${candidate_label}/results.jsonl"

# Real simulator regression harness with mock provider. This may download or
# launch AI2-THOR locally; use verify::mock for pure unit/mock tests.
sim scenes="FloorPlan201" seeds="1,2" steps="20" agents="2" model="mock":
    just harness::regression mock "" "" "{{scenes}}" "{{seeds}}" "{{steps}}" "{{agents}}" "{{model}}"

# Local OpenClaw/Gateway regression harness. Requires local preflight and keys.
openclaw scenes="FloorPlan201" seeds="1" steps="20" agents="2" model="mock":
    just harness::regression local-openclaw "" "" "{{scenes}}" "{{seeds}}" "{{steps}}" "{{agents}}" "{{model}}"

# Live Codex cleanup timing lane. This is the local Docker-backed Codex route
# with the normal world-labels profile and per-tool robot-view timeline capture
# disabled explicitly.
molmo-cleanup-codex-perf *overrides:
    #!/usr/bin/env bash
    set -euo pipefail
    args=("$@")
    seed="7"
    output_dir="output/molmo/codex-perf-harness"
    task="帮我收拾这个房间"
    generated_mess_count="10"
    host="127.0.0.1"
    port="18788"
    map_bundle="auto"
    robot_views="off"
    for arg in "${args[@]}"; do
      if [[ "$arg" != *=* ]]; then
        echo "error: override '$arg' is not key=value" >&2
        exit 1
      fi
      key="${arg%%=*}"
      value="${arg#*=}"
      key="${key#--}"
      key="${key//-/_}"
      case "$key" in
        seed|output_dir|task|prompt|generated_mess_count|host|port|map_bundle|robot_views)
          ;;
        *)
          echo "error: unsupported override key '$key'" >&2
          exit 1
          ;;
      esac
      if [[ "$key" == "prompt" ]]; then
        key="task"
      fi
      printf -v "$key" '%s' "$value"
    done
    cmd=(just molmo::cleanup "codex-live" "world-labels" "$seed" \
      "$output_dir" "$task" "$generated_mess_count" "$host" "$port" "$map_bundle" "skill" "$robot_views")
    if [[ "${ROBOCLAWS_JUST_TRACE:-}" == "1" ]]; then
      printf 'just'
      for arg in "${cmd[@]:1}"; do
        printf '\t%s' "$arg"
      done
      printf '\n'
      exit 0
    fi
    exec "${cmd[@]}"

# ADR-0003 real-world-style cleanup harness. The default runs the real
# MolmoSpaces subprocess backend over three mess seeds, with the agent limited
# to metric map, room-level fixture hints, and robot-local observed handles.
# Phase 15 requests 10 hidden generated objects by default.
# It also records RBY1M robot views so report.html has the current visual
# review surface.
molmo-realworld-cleanup seeds="1 2 3" output_dir="output/molmo-realworld-cleanup-harness" task="帮我收拾这个房间" generated_mess_count="10":
    #!/usr/bin/env bash
    set -euo pipefail
    stamp="$({{timestamp_cmd}})"
    run_root="{{output_dir}}/${stamp}"
    mkdir -p "$run_root"
    echo "==> run root: ${run_root}"
    for seed in {{seeds}}; do
      run_dir="${run_root}/seed-${seed}"
      .venv/bin/python examples/molmo_cleanup/molmospaces_realworld_cleanup.py \
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
    .venv/bin/python scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py \
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
      .venv/bin/python scripts/molmo_cleanup/run_molmo_realworld_agent_mcp_smoke.py \
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
    .venv/bin/python scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py \
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
    .venv/bin/python scripts/molmo_cleanup/run_molmo_realworld_agent_mcp_smoke.py \
      --seed "{{seed}}" \
      --backend api_semantic_synthetic \
      --task "{{task}}" \
      --policy realworld_contract_smoke_agent \
      --output-dir "$run_dir"
    .venv/bin/python scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py \
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
    .venv/bin/python scripts/molmo_cleanup/run_molmo_realworld_agent_mcp_smoke.py \
      --seed "{{seed}}" \
      --backend api_semantic_synthetic \
      --task "{{task}}" \
      --policy openclaw_agent \
      --output-dir "$run_dir"
    .venv/bin/python scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py \
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
    .venv/bin/python scripts/molmo_cleanup/run_molmo_realworld_agent_mcp_smoke.py \
      --seed "{{seed}}" \
      --backend molmospaces_subprocess \
      --task "{{task}}" \
      --policy openclaw_agent \
      --generated-mess-count "{{generated_mess_count}}" \
      --include-robot \
      --robot-name rby1m \
      --record-robot-views \
      --output-dir "$run_dir"
    .venv/bin/python scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py \
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
    .venv/bin/python examples/molmo_cleanup/molmospaces_realworld_cleanup.py \
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
    .venv/bin/python scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py \
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
    .venv/bin/python examples/molmo_cleanup/molmospaces_realworld_cleanup.py \
      --seed "{{seed}}" \
      --backend api_semantic_synthetic \
      --task "{{task}}" \
      --fixture-hint-mode room_only \
      --generated-mess-count "{{generated_mess_count}}" \
      --output-dir "${cleanup_dir}"
    .venv/bin/python scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py \
      --expect-task "{{task}}" \
      --expect-backend api_semantic_synthetic \
      --min-generated-mess-count 5 \
      --require-advisory-scoring \
      "${cleanup_dir}/run_result.json"
    .venv/bin/python scripts/molmo_cleanup/run_molmo_planner_proof_bundle_from_requests.py \
      "${cleanup_dir}/run_result.json" \
      --output-dir "${bundle_dir}" \
      --runner-python .venv/bin/python \
      --embodiment rby1m \
      --probe-mode execute \
      --steps 2 \
      --timeout-s 600
    .venv/bin/python scripts/molmo_cleanup/check_molmo_planner_proof_bundle_runner_result.py \
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
    .venv/bin/python examples/molmo_cleanup/molmospaces_realworld_cleanup.py \
      --seed "{{seed}}" \
      --backend molmospaces_subprocess \
      --task "{{task}}" \
      --fixture-hint-mode room_only \
      --include-robot \
      --record-robot-views \
      --generated-mess-count "{{generated_mess_count}}" \
      --output-dir "${cleanup_dir}"
    .venv/bin/python scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py \
      --expect-task "{{task}}" \
      --expect-backend molmospaces_subprocess \
      --min-generated-mess-count "{{min_generated_mess_count}}" \
      --require-robot-views \
      --require-advisory-scoring \
      "${cleanup_dir}/run_result.json"
    .venv/bin/python scripts/molmo_cleanup/run_molmo_planner_proof_bundle_from_requests.py \
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
    .venv/bin/python scripts/molmo_cleanup/check_molmo_planner_proof_bundle_runner_result.py \
      --require-proof-outputs \
      --require-cleanup-rerun-output \
      "${bundle_dir}"
    .venv/bin/python scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py \
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
    .venv/bin/python scripts/molmo_cleanup/run_molmo_planner_manipulation_probe.py \
      --output-dir "$run_dir" \
      --embodiment "{{embodiment}}" \
      --probe-mode "{{probe_mode}}" \
      --steps "{{steps}}"
    .venv/bin/python scripts/molmo_cleanup/check_molmo_planner_manipulation_probe.py \
      --accept-blocked-capability \
      "${run_dir}/run_result.json"

# ADR-0133 perception-isolated visual-grounding benchmark. This calls the
# configured HTTP grounding service over fixed public RAW_FPV-style fixtures and
# checks provenance, overlays, and private-label separation. Start the fake
# service first for the CI-safe route:
#   .venv/bin/python scripts/visual_grounding/serve_visual_grounding_service.py --pipeline fake-http
molmo-visual-grounding-benchmark *overrides:
    #!/usr/bin/env bash
    set -euo pipefail
    args=("$@")
    pipeline="${VISUAL_GROUNDING_PIPELINE_ID:-fake-http}"
    output_dir="output/visual-grounding-benchmark"
    corpus="harness/visual_grounding/smoke_corpus.json"
    matrix=""
    base_url="${VISUAL_GROUNDING_BASE_URL:-}"
    timeout_s="${VISUAL_GROUNDING_TIMEOUT_S:-20}"
    include_private_label_details="false"
    require_success="true"
    require_candidates="false"
    positional_pipeline_set="false"
    pipeline_override_set="false"
    for arg in "${args[@]}"; do
      if [[ "$arg" != *=* ]]; then
        if [[ "$positional_pipeline_set" == "false" ]]; then
          pipeline="$arg"
          positional_pipeline_set="true"
          pipeline_override_set="true"
          continue
        fi
        echo "error: override '$arg' is not key=value" >&2
        exit 1
      fi
      key="${arg%%=*}"
      value="${arg#*=}"
      key="${key#--}"
      key="${key//-/_}"
      case "$key" in
        pipeline|pipelines|output_dir|corpus|matrix|base_url|timeout_s|\
        include_private_label_details|require_success|require_candidates)
          ;;
        *)
          echo "error: unsupported override key '$key'" >&2
          exit 1
          ;;
      esac
      case "$key" in
        pipeline|pipelines) pipeline="$value"; pipeline_override_set="true" ;;
        output_dir) output_dir="$value" ;;
        corpus) corpus="$value" ;;
        matrix) matrix="$value" ;;
        base_url) base_url="$value" ;;
        timeout_s) timeout_s="$value" ;;
        include_private_label_details) include_private_label_details="$value" ;;
        require_success) require_success="$value" ;;
        require_candidates) require_candidates="$value" ;;
      esac
    done
    stamp="$({{timestamp_cmd}})"
    run_dir="${output_dir}/${stamp}"
    mkdir -p "$run_dir"
    echo "==> run dir: ${run_dir}"
    cmd=(.venv/bin/python scripts/visual_grounding/run_visual_grounding_benchmark.py \
      --corpus "$corpus" \
      --output-dir "$run_dir" \
      --timeout-s "$timeout_s")
    if [[ -z "$matrix" || "$pipeline_override_set" == "true" ]]; then
      cmd+=(--pipeline "$pipeline")
    fi
    if [[ -n "$matrix" ]]; then
      cmd+=(--matrix "$matrix")
    fi
    if [[ -n "$base_url" ]]; then
      cmd+=(--base-url "$base_url")
    fi
    if [[ "$include_private_label_details" == "true" ]]; then
      cmd+=(--include-private-label-details)
    fi
    "${cmd[@]}"
    check_cmd=(.venv/bin/python scripts/visual_grounding/check_visual_grounding_benchmark_result.py \
      "$run_dir")
    if [[ "$pipeline" != *","* && ( -z "$matrix" || "$pipeline_override_set" == "true" ) ]]; then
      check_cmd+=(--expect-pipeline "$pipeline")
    fi
    if [[ "$require_success" == "true" ]]; then
      check_cmd+=(--require-success)
    fi
    if [[ "$require_candidates" == "true" ]]; then
      check_cmd+=(--require-candidates)
    fi
    if [[ "$include_private_label_details" == "true" ]]; then
      check_cmd+=(--allow-private-label-details)
    fi
    "${check_cmd[@]}"

# Isaac Lab local runtime preflight. This records host readiness and writes a
# reproducible install script. It creates .venv-isaaclab/ only when both
# install=true and accept_nvidia_eula=true are supplied.
molmo-isaac-runtime-preflight *overrides:
    #!/usr/bin/env bash
    set -euo pipefail
    args=("$@")
    output_dir="output/isaaclab/preflight"
    runtime_dir=".venv-isaaclab"
    python="3.12"
    python_executable=""
    isaaclab_source=""
    stamp=""
    min_free_gb="80"
    skip_gpu_probe="false"
    install="false"
    accept_nvidia_eula="false"
    strict="false"
    for arg in "${args[@]}"; do
      if [[ "$arg" != *=* ]]; then
        echo "error: override '$arg' is not key=value" >&2
        exit 1
      fi
      key="${arg%%=*}"
      value="${arg#*=}"
      key="${key#--}"
      key="${key//-/_}"
      case "$key" in
        output_dir|runtime_dir|python|python_executable|isaaclab_source|stamp|\
        min_free_gb|skip_gpu_probe|install|accept_nvidia_eula|strict)
          ;;
        *)
          echo "error: unsupported override key '$key'" >&2
          exit 1
          ;;
      esac
      printf -v "$key" '%s' "$value"
    done
    cmd=(.venv/bin/python scripts/isaac_lab_cleanup/check_isaac_lab_runtime.py \
      --output-dir "$output_dir" \
      --runtime-dir "$runtime_dir" \
      --python "$python" \
      --min-free-gb "$min_free_gb")
    if [[ -n "$python_executable" ]]; then
      cmd+=(--python-executable "$python_executable")
    fi
    if [[ -n "$isaaclab_source" ]]; then
      cmd+=(--isaaclab-source "$isaaclab_source")
    fi
    if [[ -n "$stamp" ]]; then
      cmd+=(--stamp "$stamp")
    fi
    if [[ "$skip_gpu_probe" == "true" ]]; then
      cmd+=(--skip-gpu-probe)
    fi
    if [[ "$install" == "true" ]]; then
      cmd+=(--install)
    fi
    if [[ "$accept_nvidia_eula" == "true" ]]; then
      cmd+=(--accept-nvidia-eula)
    fi
    if [[ "$strict" == "true" ]]; then
      cmd+=(--strict)
    fi
    "${cmd[@]}"

# Install MolmoSpaces USD object packages referenced by Isaac diagnostics. This
# keeps upstream molmo_spaces_isaac as asset tooling and downloads only the
# missing object archives needed by local scene evidence unless all_objects=true.
molmo-isaac-usd-references *overrides:
    #!/usr/bin/env bash
    set -euo pipefail
    args=("$@")
    install_dir="output/isaaclab/molmospaces-usd"
    cache_dir="${HOME}/.molmospaces"
    source="thor"
    version=""
    state_path=""
    asset_path=""
    package=""
    output_path="output/isaaclab/molmospaces-usd/usd_reference_install.json"
    use_r2="true"
    dry_run="false"
    all_objects="false"
    for arg in "${args[@]}"; do
      if [[ "$arg" != *=* ]]; then
        echo "error: override '$arg' is not key=value" >&2
        exit 1
      fi
      key="${arg%%=*}"
      value="${arg#*=}"
      key="${key#--}"
      key="${key//-/_}"
      case "$key" in
        install_dir|cache_dir|source|version|state_path|asset_path|package|\
        output_path|use_r2|dry_run|all_objects)
          ;;
        *)
          echo "error: unsupported override key '$key'" >&2
          exit 1
          ;;
      esac
      printf -v "$key" '%s' "$value"
    done
    cmd=(.venv/bin/python scripts/isaac_lab_cleanup/install_molmospaces_usd_references.py \
      --install-dir "$install_dir" \
      --cache-dir "$cache_dir" \
      --source "$source" \
      --output-path "$output_path")
    if [[ -n "$version" ]]; then
      cmd+=(--version "$version")
    fi
    if [[ "$use_r2" == "true" ]]; then
      cmd+=(--use-r2)
    else
      cmd+=(--no-use-r2)
    fi
    if [[ "$dry_run" == "true" ]]; then
      cmd+=(--dry-run)
    fi
    if [[ "$all_objects" == "true" ]]; then
      cmd+=(--all-objects)
    fi
    if [[ -n "$state_path" ]]; then
      IFS=', ' read -r -a state_path_args <<< "$state_path"
      for item in "${state_path_args[@]}"; do
        [[ -n "$item" ]] && cmd+=(--state-path "$item")
      done
    fi
    if [[ -n "$asset_path" ]]; then
      IFS=', ' read -r -a asset_path_args <<< "$asset_path"
      for item in "${asset_path_args[@]}"; do
        [[ -n "$item" ]] && cmd+=(--asset-path "$item")
      done
    fi
    if [[ -n "$package" ]]; then
      IFS=', ' read -r -a package_args <<< "$package"
      for item in "${package_args[@]}"; do
        [[ -n "$item" ]] && cmd+=(--package "$item")
      done
    fi
    "${cmd[@]}"

# Strict local Isaac Lab runtime smoke. This intentionally fails until the
# worker proves a real Isaac renderer capture and USD stage load; import-only or
# placeholder evidence is rejected by the checker.
molmo-isaac-runtime-smoke *overrides:
    #!/usr/bin/env bash
    set -euo pipefail
    args=("$@")
    runtime_python=".venv-isaaclab/bin/python"
    output_dir="output/isaaclab/runtime-smoke"
    stamp=""
    scene_source="procthor-10k-val"
    scene_index="0"
    scene_usd_path=""
    generated_scene_kind="roboclaws_smoke"
    seed="7"
    generated_mess_count="1"
    map_bundle="assets/maps/molmospaces-procthor-val-0-7"
    include_robot="true"
    robot_name="simple_camera_rig"
    require_real_rendering="true"
    require_usd_stage_loaded="true"
    require_local_scene_usd="false"
    require_usd_scene_index="true"
    require_selected_usd_bindings="true"
    require_robot_view_images="true"
    require_nonblank_image="true"
    enable_segmentation="false"
    require_segmentation_evidence="false"
    segmentation_data_types=""
    segmentation_semantic_filter=""
    accept_nvidia_eula="true"
    for arg in "${args[@]}"; do
      if [[ "$arg" != *=* ]]; then
        echo "error: override '$arg' is not key=value" >&2
        exit 1
      fi
      key="${arg%%=*}"
      value="${arg#*=}"
      key="${key#--}"
      key="${key//-/_}"
      case "$key" in
        runtime_python|output_dir|stamp|scene_source|scene_index|seed|\
        scene_usd_path|generated_scene_kind|generated_mess_count|map_bundle|include_robot|robot_name|\
        require_real_rendering|require_usd_stage_loaded|require_local_scene_usd|\
        require_usd_scene_index|\
        require_selected_usd_bindings|require_robot_view_images|require_nonblank_image|\
        enable_segmentation|require_segmentation_evidence|segmentation_data_types|\
        segmentation_semantic_filter|\
        accept_nvidia_eula)
          ;;
        *)
          echo "error: unsupported override key '$key'" >&2
          exit 1
          ;;
      esac
      printf -v "$key" '%s' "$value"
    done
    if [[ -z "$stamp" ]]; then
      stamp="$({{timestamp_cmd}})"
    fi
    run_dir="${output_dir}/${stamp}"
    state_path="${run_dir}/state.json"
    init_result="${run_dir}/init_result.json"
    robot_views_result="${run_dir}/robot_views_result.json"
    mkdir -p "$run_dir"
    if [[ "$accept_nvidia_eula" == "true" ]]; then
      export OMNI_KIT_ACCEPT_EULA="YES"
    fi
    worker_cmd=("$runtime_python" scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py \
      --state-path "$state_path" \
      init \
      --run-dir "$run_dir" \
      --seed "$seed" \
      --scene-source "$scene_source" \
      --scene-index "$scene_index" \
      --generated-scene-kind "$generated_scene_kind" \
      --generated-mess-count "$generated_mess_count" \
      --runtime-mode real)
    if [[ -n "$scene_usd_path" ]]; then
      worker_cmd+=(--scene-usd-path "$scene_usd_path")
    fi
    if [[ "$include_robot" == "true" ]]; then
      worker_cmd+=(--include-robot --robot-name "$robot_name")
    fi
    if [[ "$enable_segmentation" == "true" || "$require_segmentation_evidence" == "true" ]]; then
      worker_cmd+=(--enable-segmentation)
      if [[ -n "$segmentation_data_types" ]]; then
        IFS=', ' read -r -a segmentation_type_args <<< "$segmentation_data_types"
        for data_type in "${segmentation_type_args[@]}"; do
          if [[ -n "$data_type" ]]; then
            worker_cmd+=(--segmentation-data-type "$data_type")
          fi
        done
      fi
      if [[ -n "$segmentation_semantic_filter" ]]; then
        IFS=', ' read -r -a semantic_filter_args <<< "$segmentation_semantic_filter"
        for instance_name in "${semantic_filter_args[@]}"; do
          if [[ -n "$instance_name" ]]; then
            worker_cmd+=(--segmentation-semantic-filter "$instance_name")
          fi
        done
      fi
    fi
    if [[ -n "$map_bundle" ]]; then
      worker_cmd+=(--map-bundle-dir "$map_bundle")
    fi
    "${worker_cmd[@]}" 2>&1 | tee "$init_result"
    if [[ ! -s "$state_path" ]]; then
      echo "error: Isaac runtime smoke init did not write state: ${state_path}" >&2
      exit 1
    fi
    robot_views_cmd=("$runtime_python" scripts/isaac_lab_cleanup/isaac_lab_backend_worker.py \
      --state-path "$state_path" \
      robot_views \
      --output-dir "${run_dir}/robot_views" \
      --label "runtime_smoke")
    "${robot_views_cmd[@]}" 2>&1 | tee "$robot_views_result"
    check_cmd=(.venv/bin/python scripts/isaac_lab_cleanup/check_isaac_lab_runtime_smoke_result.py \
      --init-result "$init_result" \
      --state-path "$state_path" \
      --robot-views-result "$robot_views_result")
    if [[ "$require_real_rendering" == "true" ]]; then
      check_cmd+=(--require-real-rendering)
    fi
    if [[ "$require_usd_stage_loaded" == "true" ]]; then
      check_cmd+=(--require-usd-stage-loaded)
    fi
    if [[ "$require_local_scene_usd" == "true" ]]; then
      check_cmd+=(--require-local-scene-usd)
    fi
    if [[ "$require_usd_scene_index" == "true" ]]; then
      check_cmd+=(--require-usd-scene-index)
    fi
    if [[ "$require_selected_usd_bindings" == "true" ]]; then
      check_cmd+=(--require-selected-usd-bindings)
    fi
    if [[ "$require_robot_view_images" == "true" ]]; then
      check_cmd+=(--require-robot-view-images)
    fi
    if [[ "$require_nonblank_image" == "true" ]]; then
      check_cmd+=(--require-nonblank-image)
    fi
    if [[ "$require_segmentation_evidence" == "true" ]]; then
      check_cmd+=(--require-segmentation-evidence)
    fi
    "${check_cmd[@]}"

# Strict local Isaac Lab cleanup report smoke. This uses the existing
# household-cleanup backend selector, then applies report-level Isaac gates so a
# full cleanup run cannot pass with fake runtime, placeholder visuals, or
# unbound selected USD handles.
molmo-isaac-cleanup-smoke *overrides:
    #!/usr/bin/env bash
    set -euo pipefail
    args=("$@")
    runtime_python=".venv-isaaclab/bin/python"
    output_dir="output/isaaclab/cleanup-smoke"
    stamp=""
    seed="7"
    task="帮我收拾这个房间"
    scene_source="procthor-10k-val"
    scene_index="0"
    scene_usd_path=""
    generated_mess_count="1"
    map_bundle="scene-index"
    robot_name="simple_camera_rig"
    require_real_runtime="true"
    require_scene_loaded="true"
    require_local_scene_usd="true"
    require_selected_usd_bindings="true"
    require_robot_view_provenance="true"
    require_canonical_robot_view_camera_control="true"
    require_segmentation_evidence="false"
    segmentation_data_types=""
    segmentation_semantic_filter=""
    require_snapshot_provenance="true"
    accept_nvidia_eula="true"
    for arg in "${args[@]}"; do
      if [[ "$arg" != *=* ]]; then
        echo "error: override '$arg' is not key=value" >&2
        exit 1
      fi
      key="${arg%%=*}"
      value="${arg#*=}"
      key="${key#--}"
      key="${key//-/_}"
      case "$key" in
        runtime_python|output_dir|stamp|seed|task|prompt|scene_source|scene_index|\
        scene_usd_path|generated_mess_count|map_bundle|robot_name|\
        require_real_runtime|require_scene_loaded|require_local_scene_usd|\
        require_selected_usd_bindings|require_robot_view_provenance|\
        require_canonical_robot_view_camera_control|\
        require_segmentation_evidence|segmentation_data_types|segmentation_semantic_filter|\
        require_snapshot_provenance|accept_nvidia_eula)
          ;;
        *)
          echo "error: unsupported override key '$key'" >&2
          exit 1
          ;;
      esac
      if [[ "$key" == "prompt" ]]; then
        key="task"
      fi
      printf -v "$key" '%s' "$value"
    done
    if [[ -z "$stamp" ]]; then
      stamp="$({{timestamp_cmd}})"
    fi
    if [[ "$require_local_scene_usd" == "true" && -z "$scene_usd_path" ]]; then
      echo "error: require_local_scene_usd=true needs scene_usd_path=<caller-supplied MolmoSpaces/local USD>" >&2
      exit 1
    fi
    run_dir="${output_dir}/${stamp}"
    mkdir -p "$run_dir"
    export ROBOCLAWS_ISAACLAB_PYTHON="$runtime_python"
    export ROBOCLAWS_ISAACLAB_RUNTIME_MODE="real"
    if [[ "$accept_nvidia_eula" == "true" ]]; then
      export OMNI_KIT_ACCEPT_EULA="YES"
    fi
    run_cmd=(.venv/bin/python examples/molmo_cleanup/molmospaces_realworld_cleanup.py \
      --output-dir "$run_dir" \
      --seed "$seed" \
      --task "$task" \
      --backend isaaclab_subprocess \
      --cleanup-profile world-labels \
      --fixture-hint-mode room_only \
      --generated-mess-count "$generated_mess_count" \
      --scene-source "$scene_source" \
      --scene-index "$scene_index" \
      --include-robot \
      --robot-name "$robot_name" \
      --record-robot-views)
    case "$map_bundle" in
      scene-index|none|"")
        ;;
      *)
        run_cmd+=(--map-bundle-dir "$map_bundle" --require-map-bundle)
        ;;
    esac
    if [[ -n "$scene_usd_path" ]]; then
      run_cmd+=(--isaac-scene-usd-path "$scene_usd_path")
    fi
    if [[ "$require_segmentation_evidence" == "true" ]]; then
      run_cmd+=(--isaac-enable-segmentation)
      if [[ -n "$segmentation_data_types" ]]; then
        IFS=', ' read -r -a segmentation_type_args <<< "$segmentation_data_types"
        for data_type in "${segmentation_type_args[@]}"; do
          if [[ -n "$data_type" ]]; then
            run_cmd+=(--isaac-segmentation-data-type "$data_type")
          fi
        done
      fi
      if [[ -n "$segmentation_semantic_filter" ]]; then
        IFS=', ' read -r -a semantic_filter_args <<< "$segmentation_semantic_filter"
        for instance_name in "${semantic_filter_args[@]}"; do
          if [[ -n "$instance_name" ]]; then
            run_cmd+=(--isaac-segmentation-semantic-filter "$instance_name")
          fi
        done
      fi
    fi
    "${run_cmd[@]}"
    check_cmd=(.venv/bin/python scripts/molmo_cleanup/check_molmo_realworld_cleanup_result.py \
      "$run_dir" \
      --expect-backend isaaclab_subprocess \
      --expect-policy deterministic_sweep_baseline \
      --expect-profile world-labels \
      --min-generated-mess-count "$generated_mess_count" \
      --require-robot-views \
      --require-advisory-scoring \
      --min-semantic-accepted-count "$generated_mess_count" \
      --min-sweep-coverage 1.0 \
      --require-waypoint-honesty \
      --require-real-robot-alignment \
      --require-isaac-runtime \
      --require-isaac-semantic-pose \
      --require-isaac-scene-index-map-context)
    if [[ "$require_real_runtime" == "true" ]]; then
      check_cmd+=(--require-isaac-real-runtime)
    fi
    if [[ "$require_scene_loaded" == "true" ]]; then
      check_cmd+=(--require-isaac-scene-loaded)
    fi
    if [[ "$require_local_scene_usd" == "true" ]]; then
      check_cmd+=(--require-isaac-local-scene-usd)
    fi
    if [[ "$require_selected_usd_bindings" == "true" ]]; then
      check_cmd+=(--require-isaac-selected-usd-bindings)
    fi
    if [[ "$require_robot_view_provenance" == "true" ]]; then
      check_cmd+=(--require-isaac-robot-view-provenance)
    fi
    if [[ "$require_canonical_robot_view_camera_control" == "true" ]]; then
      check_cmd+=(--require-canonical-robot-view-camera-control)
    fi
    if [[ "$require_segmentation_evidence" == "true" ]]; then
      check_cmd+=(--require-isaac-segmentation-evidence)
    fi
    if [[ "$require_snapshot_provenance" == "true" ]]; then
      check_cmd+=(--require-isaac-snapshot-provenance)
    fi
    "${check_cmd[@]}"

# Prepare a flattened MolmoSpaces semantic USD, then run the strict Isaac
# cleanup smoke against that prepared artifact. This keeps the explicit
# prepared-scene boundary out of public household-cleanup defaults.
molmo-isaac-prepared-cleanup-smoke *overrides:
    #!/usr/bin/env bash
    set -euo pipefail
    args=("$@")
    runtime_python=".venv-isaaclab/bin/python"
    output_dir="output/isaaclab/prepared-cleanup-smoke"
    stamp=""
    scene_usd_path=""
    prepared_scene_usd_path=""
    summary_path=""
    cleanup_stamp="cleanup"
    seed="7"
    task="帮我收拾这个房间"
    scene_source="procthor-10k-val"
    scene_index="0"
    generated_mess_count="1"
    map_bundle="scene-index"
    robot_name="simple_camera_rig"
    label_containers="true"
    require_prepare_ready="true"
    require_segmentation_evidence="true"
    segmentation_data_types="semantic_segmentation"
    segmentation_semantic_filter="usd_prim_path"
    accept_nvidia_eula="true"
    for arg in "${args[@]}"; do
      if [[ "$arg" != *=* ]]; then
        echo "error: override '$arg' is not key=value" >&2
        exit 1
      fi
      key="${arg%%=*}"
      value="${arg#*=}"
      key="${key#--}"
      key="${key//-/_}"
      case "$key" in
        runtime_python|output_dir|stamp|scene_usd_path|prepared_scene_usd_path|\
        summary_path|cleanup_stamp|seed|task|prompt|scene_source|scene_index|\
        generated_mess_count|map_bundle|robot_name|label_containers|\
        require_prepare_ready|require_segmentation_evidence|\
        segmentation_data_types|segmentation_semantic_filter|accept_nvidia_eula)
          ;;
        *)
          echo "error: unsupported override key '$key'" >&2
          exit 1
          ;;
      esac
      if [[ "$key" == "prompt" ]]; then
        key="task"
      fi
      printf -v "$key" '%s' "$value"
    done
    if [[ -z "$scene_usd_path" ]]; then
      echo "error: scene_usd_path=<raw MolmoSpaces scene USD> is required" >&2
      exit 1
    fi
    if [[ -z "$stamp" ]]; then
      stamp="$({{timestamp_cmd}})"
    fi
    run_root="${output_dir}/${stamp}"
    if [[ -z "$prepared_scene_usd_path" ]]; then
      prepared_scene_usd_path="${run_root}/scene_semantic.usda"
    fi
    if [[ -z "$summary_path" ]]; then
      summary_path="${run_root}/summary.json"
    fi
    mkdir -p "$run_root"
    if [[ "$accept_nvidia_eula" == "true" ]]; then
      export OMNI_KIT_ACCEPT_EULA="YES"
    fi
    prep_cmd=("$runtime_python" scripts/isaac_lab_cleanup/prepare_molmospaces_flattened_semantic_usd.py \
      --scene-usd-path "$scene_usd_path" \
      --output-usd-path "$prepared_scene_usd_path" \
      --summary-output "$summary_path")
    if [[ "$label_containers" == "true" ]]; then
      prep_cmd+=(--label-containers)
    else
      prep_cmd+=(--no-label-containers)
    fi
    "${prep_cmd[@]}"
    if [[ "$require_prepare_ready" == "true" ]]; then
      .venv/bin/python scripts/isaac_lab_cleanup/check_prepared_semantic_usd_summary.py \
        "$summary_path"
    fi
    cleanup_cmd=(just harness::molmo-isaac-cleanup-smoke \
      output_dir="$run_root" \
      stamp="$cleanup_stamp" \
      runtime_python="$runtime_python" \
      scene_usd_path="$prepared_scene_usd_path" \
      seed="$seed" \
      task="$task" \
      scene_source="$scene_source" \
      scene_index="$scene_index" \
      generated_mess_count="$generated_mess_count" \
      map_bundle="$map_bundle" \
      robot_name="$robot_name" \
      require_real_runtime=true \
      require_scene_loaded=true \
      require_local_scene_usd=true \
      require_selected_usd_bindings=true \
      require_robot_view_provenance=true \
      require_canonical_robot_view_camera_control=true \
      require_segmentation_evidence="$require_segmentation_evidence" \
      segmentation_data_types="$segmentation_data_types" \
      segmentation_semantic_filter="$segmentation_semantic_filter" \
      require_snapshot_provenance=true \
      accept_nvidia_eula="$accept_nvidia_eula")
    exec "${cleanup_cmd[@]}"

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
