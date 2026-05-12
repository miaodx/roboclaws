# Human-facing task facade.
#
# `task::*` answers "what outcome do I want?" and delegates downward to
# `agent::*`, `molmo::*`, `harness::*`, or `verify::*`. Keep this layer one-way:
# lower-level modules must not call task recipes.

set working-directory := '..'

default:
    @just --list task

# Navigate a room. driver: codex | claude | openclaw.
navigate driver="openclaw" scene="FloorPlan201" agents="2" steps="10" provider="kimi" output_dir="output/openclaw/nav" host="127.0.0.1" port="18788":
    #!/usr/bin/env bash
    set -euo pipefail
    driver="{{driver}}"
    driver="${driver#driver=}"
    case "$driver" in
      codex)
        just agent::codex-nav "{{scene}}" "{{host}}" "{{port}}"
        ;;
      claude|claudecode|cc)
        just agent::claude-nav "{{scene}}" "{{host}}" "{{port}}"
        ;;
      openclaw)
        just agent::openclaw-nav "{{agents}}" "{{steps}}" "{{provider}}" "{{output_dir}}"
        ;;
      *)
        echo "error: unsupported navigate driver '$driver' (expected codex|claude|openclaw)" >&2
        exit 1
        ;;
    esac

# Open the OpenClaw browser Control UI.
control-ui driver="openclaw" provider="mimo" model="" image_model="" observe_mode="" plugin="false" clean="false" reuse="false" xvfb="false" xvfb_args="":
    #!/usr/bin/env bash
    set -euo pipefail
    driver="{{driver}}"
    driver="${driver#driver=}"
    case "$driver" in
      openclaw)
        just agent::openclaw-ui "{{provider}}" "{{model}}" "{{image_model}}" "{{observe_mode}}" "{{plugin}}" "{{clean}}" "{{reuse}}" "{{xvfb}}" "{{xvfb_args}}"
        ;;
      *)
        echo "error: unsupported control-ui driver '$driver' (expected openclaw)" >&2
        exit 1
        ;;
    esac

# Photograph chairs/sofas. driver: openclaw.
photo-chairs driver="openclaw" provider="kimi" output_dir="output/openclaw-photo-task" max_moves="200" wall_budget="900" scene="FloorPlan201":
    #!/usr/bin/env bash
    set -euo pipefail
    driver="{{driver}}"
    driver="${driver#driver=}"
    case "$driver" in
      openclaw)
        just agent::openclaw-photo "{{provider}}" "{{output_dir}}" "{{max_moves}}" "{{wall_budget}}" "{{scene}}"
        ;;
      *)
        echo "error: unsupported photo-chairs driver '$driver' (expected openclaw)" >&2
        exit 1
        ;;
    esac

# Territory game. driver: vlm | openclaw | script.
territory driver="vlm" model="kimi-coding" agents="2" steps="20" provider="kimi" output_dir="":
    #!/usr/bin/env bash
    set -euo pipefail
    driver="{{driver}}"
    driver="${driver#driver=}"
    output_dir="{{output_dir}}"
    output_dir="${output_dir#output_dir=}"
    case "$driver" in
      vlm)
        if [[ -z "$output_dir" ]]; then output_dir="output/kimi/territory"; fi
        just agent::vlm-territory "{{model}}" "{{agents}}" "{{steps}}" "" "$output_dir"
        ;;
      openclaw)
        if [[ -z "$output_dir" ]]; then output_dir="output/openclaw/territory"; fi
        just agent::openclaw-territory "{{agents}}" "{{steps}}" "{{provider}}" "$output_dir"
        ;;
      script)
        if [[ -z "$output_dir" ]]; then output_dir="output/script/territory"; fi
        just agent::script-territory "{{agents}}" "{{steps}}" "$output_dir"
        ;;
      *)
        echo "error: unsupported territory driver '$driver' (expected vlm|openclaw|script)" >&2
        exit 1
        ;;
    esac

# Cooperative coverage game. driver: vlm | openclaw | script.
coverage driver="vlm" model="kimi-coding" agents="2" steps="20" provider="kimi" output_dir="":
    #!/usr/bin/env bash
    set -euo pipefail
    driver="{{driver}}"
    driver="${driver#driver=}"
    output_dir="{{output_dir}}"
    output_dir="${output_dir#output_dir=}"
    case "$driver" in
      vlm)
        if [[ -z "$output_dir" ]]; then output_dir="output/kimi/coverage"; fi
        just agent::vlm-coverage "{{model}}" "{{agents}}" "{{steps}}" "" "$output_dir"
        ;;
      openclaw)
        if [[ -z "$output_dir" ]]; then output_dir="output/openclaw/coverage"; fi
        just agent::openclaw-coverage "{{agents}}" "{{steps}}" "{{provider}}" "$output_dir"
        ;;
      script)
        if [[ -z "$output_dir" ]]; then output_dir="output/script/coverage"; fi
        just agent::script-coverage "{{agents}}" "{{steps}}" "$output_dir"
        ;;
      *)
        echo "error: unsupported coverage driver '$driver' (expected vlm|openclaw|script)" >&2
        exit 1
        ;;
    esac

# Cheap MolmoSpaces cleanup contract check.
cleanup-quick-check driver="mcp-smoke" runtime="synthetic" evidence="semantic" seed="7" output_dir="output/molmo/quick-check" task="帮我收拾这个房间" generated_mess_count="10":
    just molmo::quick-check "{{driver}}" "{{runtime}}" "{{evidence}}" "{{seed}}" "{{output_dir}}" "{{task}}" "{{generated_mess_count}}"

# Reviewable MolmoSpaces cleanup report.
cleanup-report driver="direct" seeds="1 2 3" output_dir="output/molmo/review-report" task="帮我收拾这个房间" generated_mess_count="10" runtime="molmospaces" evidence="visual":
    #!/usr/bin/env bash
    set -euo pipefail
    driver="{{driver}}"
    driver="${driver#driver=}"
    selected_seeds="{{seeds}}"
    case "$driver" in
      codex-live|claude-live|openclaw-live)
        if [[ "$(wc -w <<<"$selected_seeds" | tr -d ' ')" != "1" ]]; then
          selected_seeds="7"
        fi
        ;;
    esac
    case "$driver" in
      direct|mcp-smoke|openclaw-smoke|codex-live|claude-live|openclaw-live)
        just molmo::cleanup "$driver" "{{runtime}}" "{{evidence}}" "$selected_seeds" "{{output_dir}}" "{{task}}" "{{generated_mess_count}}"
        ;;
      *)
        echo "error: unsupported cleanup-report driver '$driver'" >&2
        echo "       expected direct|mcp-smoke|openclaw-smoke|codex-live|claude-live|openclaw-live" >&2
        exit 1
        ;;
    esac

# Raw FPV-only MolmoSpaces cleanup evidence.
cleanup-raw-fpv seed="7" output_dir="output/molmo/raw-fpv-report" task="帮我收拾这个房间" generated_mess_count="10":
    just molmo::raw-fpv-report "{{seed}}" "{{output_dir}}" "{{task}}" "{{generated_mess_count}}"

# Planner proof handoff. mode: dry-run | execute-rerun.
planner-proof mode="dry-run":
    #!/usr/bin/env bash
    set -euo pipefail
    mode="{{mode}}"
    mode="${mode#mode=}"
    case "$mode" in
      dry-run|dry_run)
        just harness::molmo-planner-proof-bundle-runner
        ;;
      execute-rerun|execute_rerun|local)
        just harness::molmo-planner-proof-bundle-execute-rerun
        ;;
      *)
        echo "error: unsupported planner-proof mode '$mode' (expected dry-run|execute-rerun)" >&2
        exit 1
        ;;
    esac

# Run the focused verification gate for an outcome.
check what="mock":
    #!/usr/bin/env bash
    set -euo pipefail
    what="{{what}}"
    what="${what#what=}"
    case "$what" in
      static|mock|contract|regression-mock|local-sim|local-openclaw)
        just verify::"$what"
        ;;
      cleanup-report)
        just verify::molmo-realworld-cleanup
        ;;
      cleanup-quick-check)
        just verify::molmo-realworld-agent-dogfood-kit
        ;;
      cleanup-raw-fpv)
        just verify::molmo-realworld-raw-fpv
        ;;
      planner-proof)
        just verify::molmo-planner-proof-bundle-runner
        ;;
      *)
        echo "error: unsupported check target '$what'" >&2
        exit 1
        ;;
    esac
