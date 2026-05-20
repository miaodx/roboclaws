"""Regression tests for `just/code.just` ↔ `just/mcp.just` wiring.

Locks in the fix for the 2026-04-28 bug where `just code::cc` registered the
MCP server with a corrupted URL (``http://host=127.0.0.1:port=18788/mcp``)
because the `cc` recipe passed ``host="..." port="..."`` after the recipe
name. In `just`, tokens after a recipe name are positional — ``name=value``
becomes the literal value of the next positional parameter, prefix and all.

Also pins the cross-module wiring: `code::cc` and `code::codex` must call
the shared `mcp::up` / `mcp::down` recipes rather than duplicating the
lifecycle logic.
"""

from __future__ import annotations

import re
from pathlib import Path

from roboclaws.devtools.commands import resolve_task_run


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "justfile").is_file():
            return parent
    raise AssertionError("could not locate repo root")


REPO_ROOT = _repo_root()
JUST_DIR = REPO_ROOT / "just"
CODE_JUST = JUST_DIR / "code.just"
AGENT_JUST = JUST_DIR / "agent.just"
MCP_JUST = JUST_DIR / "mcp.just"
MOLMO_JUST = JUST_DIR / "molmo.just"
HARNESS_RUN = REPO_ROOT / "harness" / "run.sh"
LIVE_CODEX_RUNNER = REPO_ROOT / "scripts" / "molmo_cleanup" / "run_live_codex_cleanup.py"
CODING_AGENT_ENV = REPO_ROOT / "scripts" / "dev" / "coding_agent_env.sh"
CODING_AGENT_DOCKERFILE = REPO_ROOT / "Dockerfile.coding-agents"
CODING_AGENT_DOCKER_SH = REPO_ROOT / "scripts" / "dev" / "coding_agent_docker.sh"
CODING_AGENT_TOOLCHAIN = REPO_ROOT / "scripts" / "dev" / "coding_agent_toolchain.env"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"

# Matches an inter-recipe call to mcp::up and captures the trailing argument
# list up to end-of-line. Excludes the recipe definition header.
_MCP_UP_CALL = re.compile(r"just mcp::up\s+([^\n]+?)(?:\)|$)", re.MULTILINE)


def _inter_recipe_calls() -> list[str]:
    text = CODE_JUST.read_text(encoding="utf-8")
    return [m.group(1).strip() for m in _MCP_UP_CALL.finditer(text)]


def test_just_files_exist() -> None:
    assert CODE_JUST.is_file(), f"missing {CODE_JUST}"
    assert MCP_JUST.is_file(), f"missing {MCP_JUST}"


def test_cc_and_codex_call_mcp_up_with_positional_args() -> None:
    calls = _inter_recipe_calls()
    assert len(calls) >= 2, f"expected cc + codex to both call mcp::up, found {len(calls)}: {calls}"
    for call in calls:
        for forbidden in ("scene=", "host=", "port="):
            assert forbidden not in call, (
                f"`just mcp::up` invocation uses `{forbidden}` named-arg syntax: "
                f"{call!r}. After a recipe name, just treats `name=value` as the "
                'literal positional value — use `"{{scene}}" "{{host}}" "{{port}}"` '
                "instead. See 2026-04-28 bug: corrupt MCP URL like "
                "http://host=127.0.0.1:port=18788/mcp."
            )


def test_mcp_url_template_is_well_formed() -> None:
    """The URL template inside mcp::up must produce a clean http://host:port/mcp."""
    text = MCP_JUST.read_text(encoding="utf-8")
    # Only match literal-URL assignments, not capture-from-subshell ones.
    matches = re.findall(r'mcp_url="(http://[^"]+)"', text)
    assert matches, "expected mcp_url assignments in mcp.just"
    for url in matches:
        assert url == "http://{{host}}:{{port}}/mcp", f"unexpected mcp_url template: {url!r}"


def test_code_just_does_not_duplicate_mcp_lifecycle() -> None:
    """`code.just` must delegate to mcp::up / mcp::down, not redefine them."""
    text = CODE_JUST.read_text(encoding="utf-8")
    # No standalone recipe headers for mcp_up / mcp_down (and no top-level
    # state vars duplicating the mcp module).
    forbidden_headers = (
        re.compile(r"^mcp_up\s", re.MULTILINE),
        re.compile(r"^mcp_down:", re.MULTILINE),
        re.compile(r"^server_pid_file\s*:=", re.MULTILINE),
    )
    for pattern in forbidden_headers:
        assert not pattern.search(text), (
            f"code.just defines `{pattern.pattern}` but should delegate to "
            f"just/mcp.just. Move the lifecycle to mcp.just."
        )


def test_code_agent_launches_default_to_full_permissions() -> None:
    """Direct Codex / Claude Code just recipes should not launch in read-only mode."""
    text = CODE_JUST.read_text(encoding="utf-8")

    assert 'codex_full_permission_args := "--dangerously-bypass-approvals-and-sandbox"' in text
    assert (
        'claude_full_permission_args := "--dangerously-skip-permissions '
        '--permission-mode bypassPermissions"'
    ) in text
    assert "scripts/dev/coding_agent_docker.sh ensure" in text
    assert 'docker_codex=("$repo_root/scripts/dev/coding_agent_docker.sh" run codex)' in text
    assert '"${docker_codex[@]}" "${codex_model_args[@]}" {{codex_full_permission_args}}' in text
    assert 'docker_claude=("$repo_root/scripts/dev/coding_agent_docker.sh" run claude)' in text
    assert (
        'claude_command=("${docker_claude[@]}" "${claude_model_args[@]}" '
        "{{claude_full_permission_args}})"
    ) in text
    assert "command -v codex" not in text
    assert "command -v claude" not in text
    assert 'export ROBOCLAWS_CODE_AGENT_DOCKER_ISOLATED_WORKSPACE="' in text
    assert 'export ROBOCLAWS_CODE_AGENT_DOCKER_TASK="' in text
    assert 'export ROBOCLAWS_CODE_AGENT_DOCKER_SKILLS="' in text
    assert "ROBOCLAWS_CODE_AGENT_DOCKER_SKILLS:-${skill_name}" in text
    assert "Switching CWD to isolated task workspace" in text
    assert "cd demo" not in text
    assert 'for entry in "${claude_env_args[@]}"; do' in text
    assert 'export "$entry"' in text
    assert "codex --yolo" not in text
    assert re.search(r"^\s+codex\s*$", text, re.MULTILINE) is None
    assert re.search(r"^\s+claude\s*$", text, re.MULTILINE) is None


def test_pinned_coding_agent_docker_toolchain_is_the_ci_source() -> None:
    """CI should run Claude Code live agents through the pinned coding-agent image."""
    code_text = CODE_JUST.read_text(encoding="utf-8")
    dockerfile_text = CODING_AGENT_DOCKERFILE.read_text(encoding="utf-8")
    docker_script_text = CODING_AGENT_DOCKER_SH.read_text(encoding="utf-8")
    toolchain_text = CODING_AGENT_TOOLCHAIN.read_text(encoding="utf-8")
    ci_text = CI_WORKFLOW.read_text(encoding="utf-8")

    assert "docker-build:" in code_text
    assert 'docker-install-wrappers shim_dir=".tmp/coding-agent-bin":' in code_text
    assert "scripts/dev/coding_agent_docker.sh install-wrappers" in code_text

    assert (
        "ARG ROBOCLAWS_NODE_IMAGE=node:22-bookworm-slim@sha256:"
        "689c11043dad91472750cd824c97dd5e2318e9dd6f954e492fe7af0135d33ceb"
    ) in dockerfile_text
    assert "ARG CODEX_NPM_PACKAGE=@openai/codex@0.130.0" in dockerfile_text
    assert "ARG CLAUDE_CODE_NPM_PACKAGE=@anthropic-ai/claude-code@2.1.143" in dockerfile_text
    assert 'npm install -g "${CODEX_NPM_PACKAGE}" "${CLAUDE_CODE_NPM_PACKAGE}"' in (dockerfile_text)

    assert "ROBOCLAWS_CODEX_NPM_PACKAGE:=@openai/codex@0.130.0" in toolchain_text
    assert (
        "ROBOCLAWS_CODE_AGENT_NODE_IMAGE:=node:22-bookworm-slim@sha256:"
        "689c11043dad91472750cd824c97dd5e2318e9dd6f954e492fe7af0135d33ceb"
    ) in toolchain_text
    assert "ROBOCLAWS_CLAUDE_CODE_NPM_PACKAGE:=@anthropic-ai/claude-code@2.1.143" in toolchain_text
    assert "roboclaws-coding-agents:codex-0.130.0-claude-2.1.143" in toolchain_text

    assert "install-wrappers" in docker_script_text
    assert "exec docker" in docker_script_text
    assert "normalized_skill_names" in docker_script_text
    assert "prepare_isolated_workspace" in docker_script_text
    assert "ROBOCLAWS_CODE_AGENT_DOCKER_ISOLATED_WORKSPACE" in docker_script_text
    assert "ROBOCLAWS_CODE_AGENT_DOCKER_TASK" in docker_script_text
    assert "ROBOCLAWS_CODE_AGENT_DOCKER_SKILLS" in docker_script_text
    assert "ROBOCLAWS_CODE_AGENT_DOCKER_USE_HOST_CODEX_HOME" not in docker_script_text
    assert "ROBOCLAWS_CODE_AGENT_DOCKER_USE_HOST_CODEX_AUTH" not in docker_script_text
    assert "ROBOCLAWS_CODE_AGENT_DOCKER_HOST_CODEX_HOME" not in docker_script_text
    assert "ROBOCLAWS_CODE_AGENT_DOCKER_CODEX_HOME" not in docker_script_text
    assert "prepare_codex_home_from_host_auth" not in docker_script_text
    assert "ROBOCLAWS_CODE_AGENT_DOCKER_DISABLE_CODEX_SYSTEM_SKILLS" in docker_script_text
    assert "prepare_empty_codex_skills_dir" in docker_script_text
    assert "CODEX_API_KEY" in docker_script_text
    assert "auth.json" not in docker_script_text
    assert "config.toml" not in docker_script_text
    assert "without host agents, hooks, or skills" not in docker_script_text
    assert '-v "${sanitized_codex_home}:/home/agent/.codex"' not in docker_script_text
    assert ':/home/agent/.codex/skills:ro"' in docker_script_text
    assert '-v "${host_codex_home}:/home/agent/.codex"' not in docker_script_text
    assert '-e "CODEX_HOME=/home/agent/.codex"' not in docker_script_text
    assert "ROBOCLAWS_CODE_AGENT_DOCKER_ISOLATED_NAV_WORKSPACE" in docker_script_text
    assert '-v "${isolated_workspace}:/workspace"' in docker_script_text
    assert 'cp -a "${skill_src}" "${skill_dst}"' in docker_script_text
    assert ":/workspace/skills/${skill}:ro" not in docker_script_text
    expected_workdir = (
        'container_workdir="${ROBOCLAWS_CODE_AGENT_DOCKER_CONTAINER_WORKDIR:-/workspace/task}"'
    )
    assert expected_workdir in docker_script_text
    assert "ANTHROPIC_BASE_URL" in docker_script_text
    assert "MIMO_TP_KEY" in docker_script_text

    assert "Build pinned coding-agent CLI image" in ci_text
    assert "scripts/dev/coding_agent_docker.sh build" in ci_text
    assert "scripts/dev/coding_agent_docker.sh install-wrappers .tmp/coding-agent-bin" in ci_text
    assert 'echo "$PWD/.tmp/coding-agent-bin" >> "$GITHUB_PATH"' in ci_text
    assert ".tmp/coding-agent-bin/codex" not in ci_text
    assert "codex-provider-smoke" not in ci_text
    assert "molmo_official_codex" not in ci_text
    assert 'npm install -g "$CODEX_NPM_PACKAGE" "$CLAUDE_CODE_NPM_PACKAGE"' not in ci_text
    assert "vars.CODEX_NPM_PACKAGE" not in ci_text
    assert "vars.CLAUDE_CODE_NPM_PACKAGE" not in ci_text


def test_code_agent_mcp_server_receives_selected_model_for_observe_auto() -> None:
    """Direct MCP runs must know the model so text-only profiles avoid raw images."""
    code_text = CODE_JUST.read_text(encoding="utf-8")
    env_text = CODING_AGENT_ENV.read_text(encoding="utf-8")

    assert (
        'claude_model="$(roboclaws_code_agent_model '
        'ROBOCLAWS_CLAUDE_MODEL ROBOCLAWS_CLAUDE_PROVIDER)"'
    ) in code_text
    assert (
        'codex_model="$(roboclaws_code_agent_model ROBOCLAWS_CODEX_MODEL ROBOCLAWS_CODEX_PROVIDER)"'
    ) in code_text
    assert ('roboclaws_code_agent_prepare_mcp_env "$claude_model" "$claude_provider"') in code_text
    assert ('roboclaws_code_agent_prepare_mcp_env "$codex_model" "$codex_provider"') in code_text
    assert 'export MODEL="$model"' in env_text
    assert "mimo-v2.5|mimo-v2.5-pro" in env_text
    assert "MCP observe(auto) will not inline raw images" in env_text


def test_photo_coding_agent_routes_use_photo_skill_only() -> None:
    """Photo coding-agent tasks should not inherit the base navigator skill."""
    agent_text = AGENT_JUST.read_text(encoding="utf-8")
    code_text = CODE_JUST.read_text(encoding="utf-8")
    mcp_text = MCP_JUST.read_text(encoding="utf-8")

    assert "photo-chairs:codex|photo-chairs:claude" in agent_text
    assert 'code::codex "$scene" "$host" "$port" photo-chairs capture-object-photo 1' in (
        agent_text
    )
    assert 'code::cc "$scene" "$host" "$port" photo-chairs capture-object-photo 1' in (agent_text)
    assert 'skill_name="${skill_name#skills/}"' in code_text
    assert 'ln -sfn "$repo_root/skills/$skill_name"' in code_text
    assert "ROBOCLAWS_CODE_AGENT_DOCKER_TASK:-${task_name}" in code_text
    assert "ROBOCLAWS_CODE_AGENT_DOCKER_SKILLS:-${skill_name}" in code_text
    assert "allow_privileged_tools" in mcp_text
    assert "server_args+=(--allow-privileged-tools)" in mcp_text


def test_photo_task_facade_accepts_coding_agent_drivers() -> None:
    codex = resolve_task_run(("photo-chairs", "codex"))
    claude = resolve_task_run(("photo-chairs", "claude"))

    assert codex.argv == ("just", "agent::run", "photo-chairs", "codex", "visual")
    assert claude.argv == ("just", "agent::run", "photo-chairs", "claude", "visual")


def test_molmo_codex_live_waits_for_server_and_runs_prompted_exec() -> None:
    """Molmo Codex reports should be runnable without a manual prompt paste."""
    text = MOLMO_JUST.read_text(encoding="utf-8")
    runner_text = LIVE_CODEX_RUNNER.read_text(encoding="utf-8")

    assert "scripts/dev/coding_agent_docker.sh ensure" in text
    assert 'scripts/dev/coding_agent_docker.sh install-wrappers "$docker_shim_dir"' in text
    assert "ROBOCLAWS_CODE_AGENT_DOCKER_SKILLS:-molmo-realworld-cleanup" in text
    assert "wait_for_mcp_ready" in text
    assert 'tmux new-session -d -s "$session_name"' in text
    assert '"exec"' in runner_text
    assert '"--json"' in runner_text
    assert '"--output-last-message"' in runner_text
    assert "ROBOCLAWS_CODE_AGENT_DOCKER_WORKSPACE" in runner_text
    assert 'env.setdefault("ROBOCLAWS_CODE_AGENT_DOCKER_ISOLATED_WORKSPACE", "1")' in (runner_text)
    expected_agent_cd = (
        'agent_cd = "/workspace/task" if container_isolated else str(agent_task_dir)'
    )
    assert expected_agent_cd in runner_text
    assert "*self.args.codex_model_arg" in runner_text
    assert 'FULL_PERMISSION_ARG = "--dangerously-bypass-approvals-and-sandbox"' in runner_text
    assert '"--cd"' in runner_text
    assert 'kickoff_prompt="Read skills/molmo-realworld-cleanup/SKILL.md.' in text


def test_molmo_codex_live_copies_task_skill_into_docker_workspace() -> None:
    runner_text = LIVE_CODEX_RUNNER.read_text(encoding="utf-8")
    docker_text = (REPO_ROOT / "scripts" / "dev" / "coding_agent_docker.sh").read_text(
        encoding="utf-8"
    )

    assert 'env.setdefault(\n            "ROBOCLAWS_CODE_AGENT_DOCKER_WORKSPACE",' in runner_text
    assert 'workspace=Path(env["ROBOCLAWS_CODE_AGENT_DOCKER_WORKSPACE"])' in runner_text
    assert "shutil.copytree(source_skill_dir, workspace_skill_dir)" in runner_text
    assert "shutil.copytree(skills_dir, task_skills_dir)" in runner_text
    assert '.symlink_to(repo_root / "skills"' not in runner_text
    assert 'cp -a "${skill_src}" "${skill_dst}"' in docker_text
    assert ":/workspace/skills/${skill}:ro" not in docker_text


def test_other_just_files_do_not_launch_bare_coding_agents() -> None:
    """Keep future wrappers from bypassing the full-permission code recipes."""
    for path in JUST_DIR.glob("*.just"):
        if path == CODE_JUST:
            continue
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if re.match(r"^(codex|claude)\s+mcp(\s|$)", stripped):
                continue
            assert not re.match(r"^(codex|claude)(\s|$)", stripped), (
                f"{path.relative_to(JUST_DIR.parent)} launches a coding agent directly: "
                f"{stripped!r}. Route through just code::codex / code::cc or use the "
                "full-permission defaults from just/code.just."
            )


def test_navigator_harness_inherits_full_permission_code_recipe() -> None:
    text = HARNESS_RUN.read_text(encoding="utf-8")

    assert "just code::cc" in text
    assert "default full-permission launch args" in text
