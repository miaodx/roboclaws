# Agent driver facade.
#
# `agent::*` answers "who or what drives the robot?" and delegates to the
# lower-level implementation modules. Keep this layer one-way: agent recipes
# must not call task recipes.

set working-directory := '..'

default:
    @just --list agent

# Codex CLI drives AI2-THOR through the navigation MCP server.
codex-nav scene="FloorPlan201" host="127.0.0.1" port="18788":
    just code::codex "{{scene}}" "{{host}}" "{{port}}"

# Claude Code drives AI2-THOR through the navigation MCP server.
claude-nav scene="FloorPlan201" host="127.0.0.1" port="18788":
    just code::cc "{{scene}}" "{{host}}" "{{port}}"

# OpenClaw Gateway runs the navigation demo.
openclaw-nav agents="2" steps="10" provider="kimi" output_dir="output/openclaw/nav":
    just openclaw::run "nav" "{{agents}}" "{{steps}}" "{{provider}}" "{{output_dir}}"

# OpenClaw Gateway runs the chair/sofa photo task.
openclaw-photo provider="kimi" output_dir="output/openclaw-photo-task" max_moves="200" wall_budget="900" scene="FloorPlan201":
    just openclaw::run "photo" "1" "10" "{{provider}}" "output/openclaw/photo" "" "0" "" "{{output_dir}}" "{{max_moves}}" "{{wall_budget}}" "{{scene}}"

# OpenClaw Gateway runs the territory game.
openclaw-territory agents="2" steps="60" provider="kimi" output_dir="output/openclaw/territory" souls="":
    just openclaw::run "territory" "{{agents}}" "{{steps}}" "{{provider}}" "{{output_dir}}" "{{souls}}"

# OpenClaw Gateway runs the cooperative coverage game.
openclaw-coverage agents="2" steps="60" provider="kimi" output_dir="output/openclaw/coverage" souls="":
    just openclaw::run "coverage" "{{agents}}" "{{steps}}" "{{provider}}" "{{output_dir}}" "{{souls}}"

# OpenClaw browser Control UI.
openclaw-ui provider="mimo" model="" image_model="" observe_mode="" plugin="false" clean="false" reuse="false" xvfb="false" xvfb_args="":
    just chat::run "{{provider}}" "{{model}}" "{{image_model}}" "{{observe_mode}}" "{{plugin}}" "{{clean}}" "{{reuse}}" "{{xvfb}}" "{{xvfb_args}}"

# Direct VLM provider drives the territory game.
vlm-territory model="kimi-coding" agents="2" steps="20" souls="" output_dir="output/kimi/territory":
    just vlm::run "territory" "{{model}}" "{{agents}}" "{{steps}}" "{{souls}}" "{{output_dir}}"

# Direct VLM provider drives the cooperative coverage game.
vlm-coverage model="kimi-coding" agents="2" steps="20" souls="" output_dir="output/kimi/coverage":
    just vlm::run "coverage" "{{model}}" "{{agents}}" "{{steps}}" "{{souls}}" "{{output_dir}}"

# Python example script with the mock model drives the territory game.
script-territory agents="2" steps="20" output_dir="output/script/territory":
    #!/usr/bin/env bash
    set -euo pipefail
    xvfb-run -a .venv/bin/python -u examples/territory_game.py \
      --backend vlm --model mock --agents "{{agents}}" --steps "{{steps}}" \
      --output-dir "{{output_dir}}"

# Python example script with the mock model drives the cooperative coverage game.
script-coverage agents="2" steps="20" output_dir="output/script/coverage":
    #!/usr/bin/env bash
    set -euo pipefail
    xvfb-run -a .venv/bin/python -u examples/coverage_game.py \
      --backend vlm --model mock --agents "{{agents}}" --steps "{{steps}}" \
      --output-dir "{{output_dir}}"
