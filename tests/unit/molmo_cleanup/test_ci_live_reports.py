from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

from roboclaws.household.ci_live_reports import (
    MODEL_ENTRIES,
    base_status,
    diagnostic_path_for_entry,
    entry_by_name,
    publish_diagnostic_seed_run,
    publish_seed_run,
    report_path_for_entry,
    status_path_for_entry,
    write_live_index,
    write_manifest,
    write_status,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
RUN_MATRIX_PATH = REPO_ROOT / "scripts" / "molmo_cleanup" / "run_ci_live_cleanup_matrix.py"
RUN_CODEX_PATH = REPO_ROOT / "scripts" / "molmo_cleanup" / "run_live_codex_cleanup.py"
RUN_CLAUDE_PATH = REPO_ROOT / "scripts" / "molmo_cleanup" / "run_live_claude_cleanup.py"
ASSEMBLE_LIVE_PAGES_PATH = REPO_ROOT / "scripts" / "molmo_cleanup" / "assemble_ci_live_pages.py"
PAGES_INDEX_PATH = REPO_ROOT / "scripts" / "reports" / "write_pages_index.py"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_ci_live_model_entries_match_provider_profiles() -> None:
    assert [entry.name for entry in MODEL_ENTRIES] == [
        "kimi-k2.6",
        "mimo-v2.5",
        "kimi-k2.6-camera-raw-fpv",
        "mimo-v2.5-camera-raw-fpv",
    ]
    assert {
        entry.name: (entry.provider_profile, entry.model, entry.secret_env, entry.profile)
        for entry in MODEL_ENTRIES
    } == {
        "kimi-k2.6": ("kimi-anthropic", "kimi-k2.6", "KIMI_API_KEY", "world-public-labels"),
        "mimo-v2.5": (
            "mimo-tp-anthropic",
            "mimo-v2.5",
            "MIMO_TP_KEY",
            "world-public-labels",
        ),
        "kimi-k2.6-camera-raw-fpv": (
            "kimi-anthropic",
            "kimi-k2.6",
            "KIMI_API_KEY",
            "camera-raw-fpv",
        ),
        "mimo-v2.5-camera-raw-fpv": (
            "mimo-tp-anthropic",
            "mimo-v2.5",
            "MIMO_TP_KEY",
            "camera-raw-fpv",
        ),
    }


def test_dry_run_matrix_writes_status_and_manifest(tmp_path: Path) -> None:
    run_matrix = _load_module(RUN_MATRIX_PATH, "run_ci_live_cleanup_matrix")

    status = run_matrix.main(
        [
            "--entry",
            "kimi-k2.6",
            "--dry-run",
            "--skip-uv-sync",
            "--skip-prewarm",
            "--skip-version-check",
            "--output-dir",
            str(tmp_path / "runs"),
            "--published-dir",
            str(tmp_path / "site" / "molmo" / "live"),
        ]
    )

    assert status == 0
    status_path = tmp_path / "site" / "molmo" / "live" / "kimi-k2.6" / "status.json"
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    assert payload["status"] == "dry_run"
    assert payload["env"] == {
        "ROBOCLAWS_CLAUDE_MODEL": "kimi-k2.6",
        "ROBOCLAWS_PROVIDER_PROFILE": "kimi-anthropic",
        "ROBOCLAWS_PROVIDER_TIMING_PROXY": "1",
    }
    assert payload["profile"] == "world-public-labels"
    assert payload["generated_mess_count"] == 5
    assert payload["command"][:9] == [
        "just",
        "run::surface",
        "surface=household-world",
        "world=molmospaces/val_0",
        "backend=mujoco",
        "intent=cleanup",
        "agent_engine=claude-code",
        "provider_profile=kimi-anthropic",
        "evidence_lane=world-public-labels",
    ]
    assert payload["rerun_command"].startswith(
        "ROBOCLAWS_PROVIDER_PROFILE=kimi-anthropic "
        "ROBOCLAWS_CLAUDE_MODEL=kimi-k2.6 "
        "ROBOCLAWS_PROVIDER_TIMING_PROXY=1 "
        "just run::surface surface=household-world world=molmospaces/val_0 "
        "backend=mujoco intent=cleanup agent_engine=claude-code "
        "provider_profile=kimi-anthropic evidence_lane=world-public-labels"
    )
    manifest = json.loads(
        (tmp_path / "site" / "molmo" / "live" / "live-report-manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["schema"] == "molmo_live_ci_report_manifest_v1"
    assert manifest["entries"][0]["entry"] == "kimi-k2.6"


def test_dry_run_camera_raw_entry_uses_entry_profile(tmp_path: Path) -> None:
    run_matrix = _load_module(RUN_MATRIX_PATH, "run_ci_live_cleanup_matrix")

    status = run_matrix.main(
        [
            "--entry",
            "kimi-k2.6-camera-raw-fpv",
            "--dry-run",
            "--skip-uv-sync",
            "--skip-prewarm",
            "--skip-version-check",
            "--output-dir",
            str(tmp_path / "runs"),
            "--published-dir",
            str(tmp_path / "site" / "molmo" / "live"),
        ]
    )

    assert status == 0
    status_path = tmp_path / "site" / "molmo" / "live" / "kimi-k2.6-camera-raw-fpv" / "status.json"
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    assert payload["entry"] == "kimi-k2.6-camera-raw-fpv"
    assert payload["label"] == "Kimi K2.6 RAW_FPV"
    assert payload["model"] == "kimi-k2.6"
    assert payload["profile"] == "camera-raw-fpv"
    assert payload["generated_mess_count"] == 10
    assert payload["command"][:9] == [
        "just",
        "run::surface",
        "surface=household-world",
        "world=molmospaces/val_0",
        "backend=mujoco",
        "intent=cleanup",
        "agent_engine=claude-code",
        "provider_profile=kimi-anthropic",
        "evidence_lane=camera-raw-fpv",
    ]
    assert "relocation_count=10" in payload["command"]
    assert "relocation_count=10" in payload["rerun_command"]
    assert "just run::surface surface=household-world" in payload["rerun_command"]


def test_dry_run_camera_raw_generated_mess_count_override(tmp_path: Path) -> None:
    run_matrix = _load_module(RUN_MATRIX_PATH, "run_ci_live_cleanup_matrix")

    status = run_matrix.main(
        [
            "--entry",
            "mimo-v2.5-camera-raw-fpv",
            "--generated-mess-count",
            "12",
            "--dry-run",
            "--skip-uv-sync",
            "--skip-prewarm",
            "--skip-version-check",
            "--output-dir",
            str(tmp_path / "runs"),
            "--published-dir",
            str(tmp_path / "site" / "molmo" / "live"),
        ]
    )

    assert status == 0
    status_path = tmp_path / "site" / "molmo" / "live" / "mimo-v2.5-camera-raw-fpv" / "status.json"
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    assert payload["generated_mess_count"] == 12
    assert "relocation_count=12" in payload["command"]


def test_ci_live_matrix_preserves_provider_timing_proxy_escape_hatch(
    tmp_path: Path,
    monkeypatch,
) -> None:
    run_matrix = _load_module(RUN_MATRIX_PATH, "run_ci_live_cleanup_matrix")
    monkeypatch.setenv("ROBOCLAWS_PROVIDER_TIMING_PROXY", "0")

    status = run_matrix.main(
        [
            "--entry",
            "kimi-k2.6",
            "--dry-run",
            "--skip-uv-sync",
            "--skip-prewarm",
            "--skip-version-check",
            "--output-dir",
            str(tmp_path / "runs"),
            "--published-dir",
            str(tmp_path / "site" / "molmo" / "live"),
        ]
    )

    assert status == 0
    payload = json.loads(
        (tmp_path / "site" / "molmo" / "live" / "kimi-k2.6" / "status.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["env"]["ROBOCLAWS_PROVIDER_TIMING_PROXY"] == "0"
    assert payload["rerun_command"].startswith(
        "ROBOCLAWS_PROVIDER_PROFILE=kimi-anthropic "
        "ROBOCLAWS_CLAUDE_MODEL=kimi-k2.6 "
        "ROBOCLAWS_PROVIDER_TIMING_PROXY=0 "
    )


def test_failed_live_entry_publishes_partial_seed_diagnostics(tmp_path: Path, monkeypatch) -> None:
    run_matrix = _load_module(RUN_MATRIX_PATH, "run_ci_live_cleanup_matrix")
    entry = entry_by_name("kimi-k2.6")
    output_dir = tmp_path / "runs"
    publish_root = tmp_path / "site" / "molmo" / "live"
    args = SimpleNamespace(
        output_dir=output_dir,
        seed=7,
        generated_mess_count=5,
        profile="world-public-labels",
        task="帮我收拾这个房间",
        host="127.0.0.1",
        port=18788,
        just_bin="just",
        dry_run=False,
        continue_on_error=False,
    )

    monkeypatch.setenv("KIMI_API_KEY", "test-key")

    def fake_run_checked(_command, **_kwargs):
        seed_dir = output_dir / entry.name / "0513_2217" / "seed-7"
        seed_dir.mkdir(parents=True)
        (seed_dir / "live_status.json").write_text('{"phase":"failed"}\n', encoding="utf-8")
        (seed_dir / "claude-events.jsonl").write_text(
            '{"type":"result","is_error":true}\n',
            encoding="utf-8",
        )
        (seed_dir / "claude.stderr.log").write_text("provider failed\n", encoding="utf-8")
        raise RuntimeError("provider failed")

    monkeypatch.setattr(run_matrix, "_run_checked", fake_run_checked)

    status = run_matrix._run_entry(entry, args, publish_root=publish_root)

    assert status["status"] == "failed"
    assert status["diagnostic_path"] == diagnostic_path_for_entry(entry.name, seed=7)
    diagnostic_root = publish_root / entry.name / "diagnostics" / "seed-7"
    assert (diagnostic_root / "diagnostics.html").is_file()
    assert (diagnostic_root / "claude-events.jsonl").read_text(encoding="utf-8")
    payload = json.loads((publish_root / entry.name / "status.json").read_text(encoding="utf-8"))
    assert payload["diagnostic_path"] == status["diagnostic_path"]


def test_live_claude_print_command_uses_verbose_for_stream_json(
    tmp_path: Path, monkeypatch
) -> None:
    run_claude = _load_module(RUN_CLAUDE_PATH, "run_live_claude_cleanup")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    args = SimpleNamespace(
        run_dir=run_dir,
        status_path=tmp_path / "status.json",
        repo_root=REPO_ROOT,
        client_url="http://127.0.0.1:18788/mcp",
        host="127.0.0.1",
        port=18788,
        lock_path=tmp_path / "runner.lock",
        claude_bin="claude",
        claude_provider_summary="test provider",
        kickoff_prompt="clean the room",
        backend="molmospaces_subprocess",
        policy="claude_agent",
        task="帮我收拾这个房间",
        min_generated_mess_count="5",
        profile="world-public-labels",
        server_arg=[],
        claude_model_arg=["--model", "kimi-k2.6"],
        claude_env=[],
        checker_visual_arg=[],
    )
    runner = run_claude.LiveClaudeCleanupRunner(args)

    monkeypatch.setattr(
        run_claude.subprocess,
        "run",
        lambda *_, **__: SimpleNamespace(stdout="2.1.143 (Claude Code)\n", stderr=""),
    )
    captured: dict[str, list[str]] = {}

    def fake_run_and_tee(command, **_kwargs):
        captured["command"] = command
        return 0

    monkeypatch.setattr(run_claude, "_run_and_tee", fake_run_and_tee)

    runner._run_claude()

    command = captured["command"]
    assert command[:5] == ["claude", "-p", "--verbose", "--output-format", "stream-json"]
    assert command[command.index("--mcp-config") + 1] == "/workspace/task/claude-mcp-config.json"
    mcp_config_path = run_dir / "claude-mcp-config.json"
    mcp_config = json.loads(mcp_config_path.read_text(encoding="utf-8"))
    assert mcp_config == {
        "mcpServers": {
            "roboclaws": {
                "type": "http",
                "url": "http://127.0.0.1:18788/mcp",
            }
        }
    }
    assert "--strict-mcp-config" in command
    assert "--bare" in command
    assert "--no-session-persistence" in command
    assert "--dangerously-skip-permissions" in command
    assert (tmp_path / "run" / "claude-version.txt").read_text(encoding="utf-8") == (
        "2.1.143 (Claude Code)\n"
    )


def test_live_claude_writes_live_timing_and_model_call_metrics(tmp_path: Path) -> None:
    run_claude = _load_module(RUN_CLAUDE_PATH, "run_live_claude_cleanup")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    args = SimpleNamespace(
        run_dir=run_dir,
        status_path=tmp_path / "status.json",
        repo_root=REPO_ROOT,
        client_url="http://127.0.0.1:18788/mcp",
        host="127.0.0.1",
        port=18788,
        lock_path=tmp_path / "runner.lock",
        claude_bin="claude",
        claude_provider_summary="mimo-tp-anthropic",
        kickoff_prompt="clean the room",
        backend="molmospaces_subprocess",
        policy="claude_agent",
        task="帮我收拾这个房间",
        min_generated_mess_count="5",
        profile="world-public-labels",
        server_arg=[],
        claude_model_arg=[],
        claude_env=[],
        checker_visual_arg=[],
    )
    runner = run_claude.LiveClaudeCleanupRunner(args)
    runner.started_at_epoch = 9.0
    runner.live_timing.update(
        {
            "started_at_epoch": 9.0,
            "server_start_epoch": 10.0,
            "server_ready_epoch": 11.0,
            "claude_exec_start_epoch": 12.0,
            "claude_exec_end_epoch": 22.0,
            "server_finished_epoch": 25.0,
            "checker_start_epoch": 26.0,
            "checker_end_epoch": 27.0,
        }
    )
    (run_dir / "trace.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"event": "request", "tool": "done", "wallclock_elapsed": 1.0}),
                json.dumps(
                    {
                        "event": "response",
                        "tool": "done",
                        "wallclock_elapsed": 2.0,
                        "response": {"ok": True},
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (run_dir / "claude-events.jsonl").write_text(
        json.dumps(
            {
                "type": "result",
                "usage": {"input_tokens": 100, "output_tokens": 20},
                "duration_s": 3.5,
            }
        )
        + "\n",
        encoding="utf-8",
    )

    runner._write_live_timing("finished", 0)

    timing = json.loads((run_dir / "live_timing.json").read_text(encoding="utf-8"))
    assert timing["runtime"] == "claude-code"
    assert timing["runner_timing"]["claude_exec_elapsed_s"] == 10.0
    assert timing["mcp_trace_timing"]["tool_call_count"] == 1
    rows = [
        json.loads(line)
        for line in (run_dir / "model_call_metrics.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    assert rows[0]["schema"] == "roboclaws_model_call_metric_v1"
    assert rows[0]["agent_engine"] == "claude-code"
    assert rows[0]["input_tokens"] == 100


def test_live_claude_provider_timing_proxy_rewrites_anthropic_base_url(
    tmp_path: Path,
    monkeypatch,
) -> None:
    run_claude = _load_module(RUN_CLAUDE_PATH, "run_live_claude_cleanup")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    args = SimpleNamespace(
        run_dir=run_dir,
        status_path=tmp_path / "status.json",
        repo_root=REPO_ROOT,
        client_url="http://127.0.0.1:18788/mcp",
        host="127.0.0.1",
        port=18788,
        lock_path=tmp_path / "runner.lock",
        claude_bin="claude",
        claude_provider_summary="mimo-tp-anthropic model=mimo-v2.5",
        kickoff_prompt="clean the room",
        backend="molmospaces_subprocess",
        policy="claude_agent",
        task="帮我收拾这个房间",
        min_generated_mess_count="5",
        profile="world-public-labels",
        server_arg=[],
        claude_model_arg=["--model", "mimo-v2.5"],
        claude_env=["ANTHROPIC_BASE_URL=https://provider.example.test/anthropic"],
        checker_visual_arg=[],
    )
    runner = run_claude.LiveClaudeCleanupRunner(args)
    env = {"ROBOCLAWS_PROVIDER_TIMING_PROXY": "1"}

    async def fake_start_provider_timing_proxy(**kwargs):
        return SimpleNamespace(
            bind_url="http://127.0.0.1:18888",
            upstream_base_url=kwargs["upstream_base_url"],
            metrics_path=run_dir / "provider_request_metrics.jsonl",
            ready_path=run_dir / "provider_timing_proxy.ready.json",
            process=SimpleNamespace(returncode=0),
        )

    monkeypatch.setattr(
        run_claude,
        "start_provider_timing_proxy",
        fake_start_provider_timing_proxy,
    )

    for item in args.claude_env:
        key, _sep, value = item.partition("=")
        env[key] = value
    runner._configure_provider_timing_proxy(env)

    assert env["ANTHROPIC_BASE_URL"] == "http://127.0.0.1:18888/anthropic"
    assert env["ROBOCLAWS_TIMING_PROXY_UPSTREAM_BASE_URL"] == (
        "https://provider.example.test/anthropic"
    )
    assert runner.live_timing["provider_timing_proxy"]["enabled"] is True
    assert runner.live_timing["provider_timing_proxy"]["provider_profile"] == "mimo-tp-anthropic"
    assert runner.live_timing["provider_timing_proxy"]["metrics_path"].endswith(
        "provider_request_metrics.jsonl"
    )


def test_live_claude_workspace_exposes_skill_at_task_relative_path(
    tmp_path: Path, monkeypatch
) -> None:
    run_claude = _load_module(RUN_CLAUDE_PATH, "run_live_claude_cleanup")
    workspace = tmp_path / "agent-workspace"
    monkeypatch.setenv("ROBOCLAWS_CODE_AGENT_WORKSPACE", str(workspace))

    prepared_workspace, task_dir = run_claude._prepare_agent_workspace(
        repo_root=REPO_ROOT,
        run_id="household-world.cleanup",
        skill_name="molmo-realworld-cleanup",
    )

    assert prepared_workspace == workspace
    assert (task_dir / "skills" / "molmo-realworld-cleanup" / "SKILL.md").is_file()
    assert (task_dir / "skills").readlink() == Path("..") / "skills"
    assert (workspace / "skills" / "molmo-realworld-cleanup" / "SKILL.md").is_file()
    readme = (task_dir / "README.md").read_text(encoding="utf-8")
    assert "skills/molmo-realworld-cleanup/SKILL.md" in readme


def test_live_codex_normalizes_relative_docker_workspace(tmp_path: Path, monkeypatch) -> None:
    run_codex = _load_module(RUN_CODEX_PATH, "run_live_codex_cleanup")
    repo_root = tmp_path / "repo"
    skill_dir = repo_root / "skills" / "molmo-realworld-cleanup"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# cleanup skill\n", encoding="utf-8")
    monkeypatch.delenv("ROBOCLAWS_CODE_AGENT_WORKSPACE", raising=False)
    monkeypatch.setenv(
        "ROBOCLAWS_CODE_AGENT_DOCKER_WORKSPACE",
        "output/molmo/live/seed-7/agent-docker-workspace",
    )

    prepared_workspace, task_dir = run_codex._prepare_agent_workspace(
        repo_root=repo_root,
        run_id="household-world.cleanup",
        skill_name="molmo-realworld-cleanup",
    )

    assert prepared_workspace == (repo_root / "output/molmo/live/seed-7/agent-docker-workspace")
    assert prepared_workspace.is_absolute()
    assert (task_dir / "skills" / "molmo-realworld-cleanup" / "SKILL.md").is_file()
    assert (task_dir / "skills").is_dir()
    assert not (task_dir / "skills").is_symlink()


def test_live_agent_runners_default_to_longer_server_startup_timeout(tmp_path: Path) -> None:
    run_codex = _load_module(RUN_CODEX_PATH, "run_live_codex_cleanup")
    run_claude = _load_module(RUN_CLAUDE_PATH, "run_live_claude_cleanup")

    codex_args = run_codex.parse_args(
        [
            "--run-dir",
            str(tmp_path / "codex-run"),
            "--repo-root",
            str(REPO_ROOT),
            "--status-path",
            str(tmp_path / "codex-status.json"),
            "--client-url",
            "http://127.0.0.1:18788/mcp",
            "--host",
            "127.0.0.1",
            "--port",
            "18788",
            "--lock-path",
            str(tmp_path / "codex.lock"),
            "--tmux-session",
            "roboclaws-test",
            "--codex-bin",
            "codex",
            "--kickoff-prompt",
            "clean",
            "--backend",
            "molmospaces_subprocess",
            "--policy",
            "codex_agent",
            "--task",
            "帮我收拾这个房间",
            "--min-generated-mess-count",
            "5",
            "--profile",
            "world-public-labels",
        ]
    )
    claude_args = run_claude.parse_args(
        [
            "--run-dir",
            str(tmp_path / "claude-run"),
            "--repo-root",
            str(REPO_ROOT),
            "--status-path",
            str(tmp_path / "claude-status.json"),
            "--client-url",
            "http://127.0.0.1:18788/mcp",
            "--host",
            "127.0.0.1",
            "--port",
            "18788",
            "--lock-path",
            str(tmp_path / "claude.lock"),
            "--claude-bin",
            "claude",
            "--kickoff-prompt",
            "clean",
            "--backend",
            "molmospaces_subprocess",
            "--policy",
            "claude_agent",
            "--task",
            "帮我收拾这个房间",
            "--min-generated-mess-count",
            "5",
            "--profile",
            "world-public-labels",
        ]
    )

    assert codex_args.server_startup_timeout_s == 600.0
    assert claude_args.server_startup_timeout_s == 600.0


def test_live_codex_wait_for_mcp_ready_uses_configured_timeout(tmp_path: Path, monkeypatch) -> None:
    run_codex = _load_module(RUN_CODEX_PATH, "run_live_codex_cleanup")
    args = SimpleNamespace(
        run_dir=tmp_path / "run",
        status_path=tmp_path / "status.json",
        host="127.0.0.1",
        port=18788,
        server_startup_timeout_s=200.0,
    )
    runner = run_codex.LiveCodexCleanupRunner(args)
    runner.server_proc = SimpleNamespace(poll=lambda: None)
    ticks = iter([0.0, 100.0, 130.0])
    checks = {"count": 0}

    def fake_port_accepting(_host: str, _port: int) -> bool:
        checks["count"] += 1
        return checks["count"] == 2

    monkeypatch.setattr(run_codex.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(run_codex.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(run_codex, "_port_accepting", fake_port_accepting)

    runner._wait_for_mcp_ready()

    assert checks["count"] == 2


def test_live_claude_wait_for_mcp_ready_uses_configured_timeout(
    tmp_path: Path, monkeypatch
) -> None:
    run_claude = _load_module(RUN_CLAUDE_PATH, "run_live_claude_cleanup")
    args = SimpleNamespace(
        run_dir=tmp_path / "run",
        status_path=tmp_path / "status.json",
        host="127.0.0.1",
        port=18788,
        server_startup_timeout_s=200.0,
    )
    runner = run_claude.LiveClaudeCleanupRunner(args)
    runner.server_proc = SimpleNamespace(poll=lambda: None)
    ticks = iter([0.0, 100.0, 130.0])
    checks = {"count": 0}

    def fake_port_accepting(_host: str, _port: int) -> bool:
        checks["count"] += 1
        return checks["count"] == 2

    monkeypatch.setattr(run_claude.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(run_claude.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(run_claude, "_port_accepting", fake_port_accepting)

    runner._wait_for_mcp_ready()

    assert checks["count"] == 2


def test_live_codex_failure_status_includes_reason(tmp_path: Path, monkeypatch) -> None:
    run_codex = _load_module(RUN_CODEX_PATH, "run_live_codex_cleanup")
    args = SimpleNamespace(
        run_dir=tmp_path / "run",
        status_path=tmp_path / "live_status.json",
    )
    runner = run_codex.LiveCodexCleanupRunner(args)

    monkeypatch.setattr(runner, "_acquire_lock", lambda: None)
    monkeypatch.setattr(runner, "_start_server", lambda: None)
    monkeypatch.setattr(
        runner,
        "_wait_for_mcp_ready",
        lambda: (_ for _ in ()).throw(RuntimeError("startup failed")),
    )
    monkeypatch.setattr(runner, "_cleanup_server", lambda: None)

    assert runner.run() == 1
    payload = json.loads(args.status_path.read_text(encoding="utf-8"))
    assert payload["phase"] == "failed"
    assert payload["exit_status"] == 1
    assert payload["reason"] == "startup failed"


def test_live_codex_prompts_block_plan_tool() -> None:
    run_codex = _load_module(RUN_CODEX_PATH, "run_live_codex_cleanup")

    prompt = run_codex._codex_live_prompt("clean")

    assert "do not call update_plan" in prompt
    assert "do not create todo/checklist" in prompt
    assert "Do not call read_mcp_resource" in prompt
    assert "Do not call exec_command" in prompt
    assert "coding/developer tool" in prompt
    assert "server=cleanup" in prompt
    assert "namespace cleanup" in prompt
    assert "declared Codex MCP server" not in prompt
    assert "server named cleanup" not in prompt
    assert "never use mcp__cleanup__" in prompt
    assert "mcp__roboclaws__" in prompt
    assert "roboclaws__" in prompt
    assert "use place_inside for" in prompt
    assert "call close_receptacle with the same fixture_id" in prompt
    assert "required_tool next" in prompt


def test_live_codex_turn_idle_timeout_uses_env_default(monkeypatch) -> None:
    run_codex = _load_module(RUN_CODEX_PATH, "run_live_codex_cleanup")

    monkeypatch.delenv("ROBOCLAWS_CODEX_TURN_IDLE_TIMEOUT_S", raising=False)
    assert run_codex._codex_turn_idle_timeout_s(None) == 300.0
    assert run_codex._codex_turn_idle_timeout_s(12.5) == 12.5

    monkeypatch.setenv("ROBOCLAWS_CODEX_TURN_IDLE_TIMEOUT_S", "7")
    assert run_codex._codex_turn_idle_timeout_s(None) == 7.0

    monkeypatch.setenv("ROBOCLAWS_CODEX_TURN_IDLE_TIMEOUT_S", "bad")
    assert run_codex._codex_turn_idle_timeout_s(None) == 300.0


def test_live_codex_idle_turn_fails_without_continuation(tmp_path: Path, monkeypatch) -> None:
    run_codex = _load_module(RUN_CODEX_PATH, "run_live_codex_cleanup")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    agent_dir = tmp_path / "agent"
    agent_dir.mkdir()
    args = SimpleNamespace(
        run_dir=run_dir,
        status_path=tmp_path / "status.json",
        repo_root=REPO_ROOT,
        client_url="http://127.0.0.1:18788/mcp",
        codex_bin="codex",
        codex_provider_summary="mify model=xiaomi/mimo-v2.5",
        codex_turn_idle_timeout_s=3.0,
        kickoff_prompt="clean",
        codex_model_arg=[],
        backend="molmospaces_subprocess",
        policy="codex_agent",
        profile="camera-raw-fpv",
    )
    runner = run_codex.LiveCodexCleanupRunner(args)
    runner.server_proc = SimpleNamespace(poll=lambda: None)
    calls: list[tuple[list[str], float | None]] = []
    workspace_kwargs: dict[str, object] = {}

    def fake_prepare_agent_workspace(
        *, repo_root: Path, run_id: str, skill_name: str, workspace: Path | None = None
    ):
        workspace_kwargs.update(
            {
                "repo_root": repo_root,
                "run_id": run_id,
                "skill_name": skill_name,
                "workspace": workspace,
            }
        )
        return agent_dir, agent_dir

    def fake_subprocess_run(*_args, **_kwargs):
        return SimpleNamespace(returncode=0)

    def fake_run_and_tee(command, *, stdout_path, stderr_path, idle_timeout_s=None, **_kwargs):
        calls.append((command, idle_timeout_s))
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        stderr_path.parent.mkdir(parents=True, exist_ok=True)
        stdout_path.write_text(
            '{"type":"error","message":"stream disconnected before completion: '
            'idle timeout waiting for SSE"}\n',
            encoding="utf-8",
        )
        stderr_path.write_text(
            "codex turn idle timeout after 3s; terminating process group and failing live run\n",
            encoding="utf-8",
        )
        return run_codex.CODEX_TURN_IDLE_TIMEOUT_EXIT_STATUS

    monkeypatch.setattr(run_codex, "_prepare_agent_workspace", fake_prepare_agent_workspace)
    monkeypatch.setattr(run_codex.subprocess, "run", fake_subprocess_run)
    monkeypatch.setattr(run_codex, "_run_and_tee", fake_run_and_tee)

    try:
        runner._run_codex()
    except run_codex.LiveAgentRunFailure as exc:
        assert exc.failure.reason == "idle_timeout"
        assert exc.failure.retryable is False
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("expected idle timeout to fail the live run")

    assert len(calls) == 1
    assert workspace_kwargs["run_id"] == "household-world.cleanup"
    assert calls[0][1] == 3.0
    assert "Continue the same active cleanup MCP session" not in calls[0][0][-1]
    assert "codex_recoverable_errors" not in runner.live_timing


def test_live_codex_explicit_operator_handoff_pauses_without_killing_server(
    tmp_path: Path, monkeypatch
) -> None:
    run_codex = _load_module(RUN_CODEX_PATH, "run_live_codex_cleanup")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    agent_dir = tmp_path / "agent"
    agent_dir.mkdir()
    args = SimpleNamespace(
        run_dir=run_dir,
        status_path=tmp_path / "live_status.json",
        repo_root=REPO_ROOT,
        client_url="http://127.0.0.1:18788/mcp",
        codex_bin="codex",
        codex_model="gpt-5.5",
        codex_provider_summary="codex-router-responses model=gpt-5.5",
        codex_turn_idle_timeout_s=3.0,
        kickoff_prompt=("到达第一个 waypoint 点，等待，不要推出，我计划手动调整下位置"),
        codex_model_arg=[],
        backend="isaaclab_subprocess",
        task_surface="household-world",
        intent="open-ended",
        skill_name="household-open-task",
        policy="codex_agent",
        task="到达第一个 waypoint 点，等待，不要推出，我计划手动调整下位置",
        min_generated_mess_count="0",
        profile="world-public-labels",
    )
    runner = run_codex.LiveCodexCleanupRunner(args)
    runner.server_proc = SimpleNamespace(poll=lambda: None)
    calls: list[list[str]] = []

    def fake_prepare_agent_workspace(
        *, repo_root: Path, run_id: str, skill_name: str, workspace: Path | None = None
    ):
        return agent_dir, agent_dir

    def fake_subprocess_run(*_args, **_kwargs):
        return SimpleNamespace(returncode=0)

    def fake_run_and_tee(command, *, stdout_path, stderr_path, **_kwargs):
        calls.append(command)
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        stderr_path.parent.mkdir(parents=True, exist_ok=True)
        stdout_path.write_text(
            json.dumps(
                {
                    "type": "item.completed",
                    "item": {
                        "type": "agent_message",
                        "text": "我现在停止，不调用 done，等待你手动调整位置。",
                    },
                }
            )
            + "\n",
            encoding="utf-8",
        )
        (agent_dir / "codex-last-message.md").write_text(
            "我现在停止，不调用 done，等待你手动调整位置。",
            encoding="utf-8",
        )
        return 0

    monkeypatch.setattr(run_codex, "_prepare_agent_workspace", fake_prepare_agent_workspace)
    monkeypatch.setattr(run_codex.subprocess, "run", fake_subprocess_run)
    monkeypatch.setattr(run_codex, "_run_and_tee", fake_run_and_tee)

    runner._run_codex()

    assert runner.operator_handoff_active is True
    assert len(calls) == 1
    payload = json.loads(args.status_path.read_text(encoding="utf-8"))
    assert payload["phase"] == "paused"
    assert payload["reason"] == "operator_handoff_requested"
    assert payload["resume_available"] is True
    assert "MCP server remains alive" in payload["detail"]


def test_live_codex_no_done_without_operator_handoff_still_fails(
    tmp_path: Path, monkeypatch
) -> None:
    run_codex = _load_module(RUN_CODEX_PATH, "run_live_codex_cleanup")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    agent_dir = tmp_path / "agent"
    agent_dir.mkdir()
    args = SimpleNamespace(
        run_dir=run_dir,
        status_path=tmp_path / "live_status.json",
        repo_root=REPO_ROOT,
        client_url="http://127.0.0.1:18788/mcp",
        codex_bin="codex",
        codex_model="gpt-5.5",
        codex_provider_summary="codex-router-responses model=gpt-5.5",
        kickoff_prompt="找到一瓶水",
        codex_model_arg=[],
        backend="molmospaces_subprocess",
        task_surface="household-world",
        intent="open-ended",
        skill_name="household-open-task",
        policy="codex_agent",
        task="找到一瓶水",
        min_generated_mess_count="0",
        profile="world-public-labels",
    )
    runner = run_codex.LiveCodexCleanupRunner(args)
    runner.server_proc = SimpleNamespace(poll=lambda: None)

    def fake_prepare_agent_workspace(
        *, repo_root: Path, run_id: str, skill_name: str, workspace: Path | None = None
    ):
        return agent_dir, agent_dir

    def fake_subprocess_run(*_args, **_kwargs):
        return SimpleNamespace(returncode=0)

    def fake_run_and_tee(_command, *, stdout_path, stderr_path, **_kwargs):
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        stderr_path.parent.mkdir(parents=True, exist_ok=True)
        (agent_dir / "codex-last-message.md").write_text(
            "我还没有找到目标，先停在这里。",
            encoding="utf-8",
        )
        return 0

    monkeypatch.setattr(run_codex, "_prepare_agent_workspace", fake_prepare_agent_workspace)
    monkeypatch.setattr(run_codex.subprocess, "run", fake_subprocess_run)
    monkeypatch.setattr(run_codex, "_run_and_tee", fake_run_and_tee)

    try:
        runner._run_codex()
    except RuntimeError as exc:
        assert str(exc) == "Codex exec ended without done after one live-agent turn"
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("expected no-done run to fail without explicit handoff")

    assert runner.operator_handoff_active is False


def test_live_codex_provider_timing_proxy_rewrites_provider_base_url(
    tmp_path: Path,
    monkeypatch,
) -> None:
    run_codex = _load_module(RUN_CODEX_PATH, "run_live_codex_cleanup")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    args = SimpleNamespace(
        run_dir=run_dir,
        status_path=tmp_path / "status.json",
        repo_root=REPO_ROOT,
        client_url="http://127.0.0.1:18788/mcp",
        codex_bin="codex",
        codex_model="gpt-5.5",
        codex_provider_summary="codex-router-responses model=gpt-5.5",
        kickoff_prompt="clean",
        codex_model_arg=[
            "-c",
            'model="gpt-5.5"',
            "-c",
            'model_provider="codex-router-responses"',
            "-c",
            'model_providers.codex-router-responses.base_url="https://provider.example.test/v1"',
            "-c",
            'model_providers.codex-router-responses.wire_api="responses"',
        ],
        backend="molmospaces_subprocess",
        policy="codex_agent",
        profile="world-public-labels",
    )
    runner = run_codex.LiveCodexCleanupRunner(args)
    env = {"ROBOCLAWS_PROVIDER_TIMING_PROXY": "1"}

    async def fake_start_provider_timing_proxy(**kwargs):
        return SimpleNamespace(
            bind_url="http://127.0.0.1:18888",
            upstream_base_url=kwargs["upstream_base_url"],
            metrics_path=run_dir / "provider_request_metrics.jsonl",
            ready_path=run_dir / "provider_timing_proxy.ready.json",
            process=SimpleNamespace(returncode=0),
        )

    monkeypatch.setattr(
        run_codex,
        "start_provider_timing_proxy",
        fake_start_provider_timing_proxy,
    )

    runner._configure_provider_timing_proxy(env)

    assert 'model_providers.codex-router-responses.base_url="http://127.0.0.1:18888/v1"' in (
        runner.args.codex_model_arg
    )
    assert env["ROBOCLAWS_TIMING_PROXY_UPSTREAM_BASE_URL"] == "https://provider.example.test/v1"
    assert env["ROBOCLAWS_CODEX_DISABLE_RESPONSES_WEBSOCKETS"] == "1"
    assert runner.live_timing["provider_timing_proxy"]["enabled"] is True
    assert runner.live_timing["provider_timing_proxy"]["provider_profile"] == "codex-router-responses"
    assert runner.live_timing["provider_timing_proxy"]["responses_websockets_disabled"] is True


def test_live_codex_tool_binding_failure_is_non_retryable(tmp_path: Path, monkeypatch) -> None:
    run_codex = _load_module(RUN_CODEX_PATH, "run_live_codex_cleanup")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    agent_dir = tmp_path / "agent"
    agent_dir.mkdir()
    args = SimpleNamespace(
        run_dir=run_dir,
        status_path=tmp_path / "status.json",
        repo_root=REPO_ROOT,
        client_url="http://127.0.0.1:18788/mcp",
        codex_bin="codex",
        codex_provider_summary="mify model=xiaomi/mimo-v2.5",
        kickoff_prompt="clean",
        codex_model_arg=[],
        backend="molmospaces_subprocess",
        policy="codex_agent",
        profile="world-public-labels",
    )
    runner = run_codex.LiveCodexCleanupRunner(args)
    runner.server_proc = SimpleNamespace(poll=lambda: None)
    calls: list[list[str]] = []

    def fake_prepare_agent_workspace(
        *, repo_root: Path, run_id: str, skill_name: str, workspace: Path | None = None
    ):
        return agent_dir, agent_dir

    def fake_subprocess_run(*_args, **_kwargs):
        return SimpleNamespace(returncode=0)

    def fake_run_and_tee(command, *, stdout_path, stderr_path, **_kwargs):
        calls.append(command)
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        stderr_path.parent.mkdir(parents=True, exist_ok=True)
        stdout_path.write_text(
            '{"type":"error","message":"function_call name '
            "'_iv9s__mcp__roboclaws____update_plan' is not declared in tools\"}\n",
            encoding="utf-8",
        )
        stderr_path.write_text(
            "unsupported call: _iv9s__mcp__roboclaws____update_plan\n",
            encoding="utf-8",
        )
        return 1

    monkeypatch.setattr(run_codex, "_prepare_agent_workspace", fake_prepare_agent_workspace)
    monkeypatch.setattr(run_codex.subprocess, "run", fake_subprocess_run)
    monkeypatch.setattr(run_codex, "_run_and_tee", fake_run_and_tee)

    try:
        runner._run_codex()
    except run_codex.LiveAgentRunFailure as exc:
        assert exc.failure.reason == "tool_binding_failure"
        assert exc.failure.retryable is False
        assert exc.failure.resume_available is False
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("expected tool-binding failure")

    assert len(calls) == 1
    assert "do not call update_plan" in calls[0][-1]
    assert "Do not call read_mcp_resource" in calls[0][-1]
    assert "Do not call exec_command" in calls[0][-1]
    assert "server=cleanup" in calls[0][-1]
    assert "namespace cleanup" in calls[0][-1]
    assert "server named cleanup" not in calls[0][-1]
    assert "never use mcp__cleanup__" in calls[0][-1]
    assert "mcp__roboclaws__" in calls[0][-1]
    assert "roboclaws__" in calls[0][-1]


def test_live_codex_provider_transient_failure_is_retryable(tmp_path: Path, monkeypatch) -> None:
    run_codex = _load_module(RUN_CODEX_PATH, "run_live_codex_cleanup")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    agent_dir = tmp_path / "agent"
    agent_dir.mkdir()
    args = SimpleNamespace(
        run_dir=run_dir,
        status_path=tmp_path / "status.json",
        repo_root=REPO_ROOT,
        client_url="http://127.0.0.1:18788/mcp",
        codex_bin="codex",
        codex_provider_summary="mify model=xiaomi/mimo-v2.5",
        kickoff_prompt="clean",
        codex_model_arg=[],
        backend="molmospaces_subprocess",
        policy="codex_agent",
        profile="camera-raw-fpv",
    )
    runner = run_codex.LiveCodexCleanupRunner(args)
    runner.server_proc = SimpleNamespace(poll=lambda: None)
    calls: list[list[str]] = []

    def fake_prepare_agent_workspace(
        *, repo_root: Path, run_id: str, skill_name: str, workspace: Path | None = None
    ):
        return agent_dir, agent_dir

    def fake_subprocess_run(*_args, **_kwargs):
        return SimpleNamespace(returncode=0)

    def fake_run_and_tee(command, *, stdout_path, stderr_path, **_kwargs):
        calls.append(command)
        stdout_path.parent.mkdir(parents=True, exist_ok=True)
        stderr_path.parent.mkdir(parents=True, exist_ok=True)
        stdout_path.write_text(
            '{"type":"error","message":"exceeded retry limit, last status: '
            '429 Too Many Requests"}\n',
            encoding="utf-8",
        )
        stderr_path.write_text("", encoding="utf-8")
        return 1

    monkeypatch.setattr(run_codex, "_prepare_agent_workspace", fake_prepare_agent_workspace)
    monkeypatch.setattr(run_codex.subprocess, "run", fake_subprocess_run)
    monkeypatch.setattr(run_codex, "_run_and_tee", fake_run_and_tee)

    try:
        runner._run_codex()
    except run_codex.LiveAgentRunFailure as exc:
        assert exc.failure.reason == "provider_transient_failure"
        assert exc.failure.provider_reason == "rate_limit"
        assert exc.failure.retryable is True
        assert exc.failure.resume_available is True
    else:  # pragma: no cover - defensive assertion
        raise AssertionError("expected provider transient failure")

    assert len(calls) == 1
    assert "codex_recoverable_errors" not in runner.live_timing
    assert runner.live_timing["codex_events"]["type_counts"]["error"] == 1


def test_live_codex_world_labels_checker_defaults_to_official_nav2_floor(
    tmp_path: Path, monkeypatch
) -> None:
    run_codex = _load_module(RUN_CODEX_PATH, "run_live_codex_cleanup")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "run_result.json").write_text("{}", encoding="utf-8")
    args = SimpleNamespace(
        run_dir=run_dir,
        status_path=tmp_path / "status.json",
        repo_root=REPO_ROOT,
        task="帮我收拾这个房间",
        backend="molmospaces_subprocess",
        policy="codex_agent",
        profile="world-public-labels",
        min_generated_mess_count="5",
        checker_visual_arg=[],
    )
    runner = run_codex.LiveCodexCleanupRunner(args)
    captured: dict[str, list[str]] = {}

    def fake_run_and_tee(command, **_kwargs):
        captured["command"] = command
        return 0

    monkeypatch.setattr(run_codex, "_run_and_tee", fake_run_and_tee)

    runner._check_result()

    command = captured["command"]
    assert "--require-waypoint-honesty" in command
    assert "--require-real-robot-alignment" in command
    assert command[command.index("--min-semantic-accepted-count") + 1] == "5"
    assert command[command.index("--min-sweep-coverage") + 1] == "1.0"
    assert command[-1] == str(run_dir / "run_result.json")


def test_live_codex_world_labels_checker_does_not_duplicate_recipe_flags(
    tmp_path: Path, monkeypatch
) -> None:
    run_codex = _load_module(RUN_CODEX_PATH, "run_live_codex_cleanup")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "run_result.json").write_text("{}", encoding="utf-8")
    args = SimpleNamespace(
        run_dir=run_dir,
        status_path=tmp_path / "status.json",
        repo_root=REPO_ROOT,
        task="帮我收拾这个房间",
        backend="molmospaces_subprocess",
        policy="codex_agent",
        profile="world-public-labels",
        min_generated_mess_count="5",
        checker_visual_arg=[
            "--require-waypoint-honesty",
            "--require-real-robot-alignment",
            "--min-semantic-accepted-count",
            "5",
            "--min-sweep-coverage",
            "1.0",
        ],
    )
    runner = run_codex.LiveCodexCleanupRunner(args)
    captured: dict[str, list[str]] = {}

    def fake_run_and_tee(command, **_kwargs):
        captured["command"] = command
        return 0

    monkeypatch.setattr(run_codex, "_run_and_tee", fake_run_and_tee)

    runner._check_result()

    command = captured["command"]
    assert command.count("--require-waypoint-honesty") == 1
    assert command.count("--require-real-robot-alignment") == 1
    assert command.count("--min-semantic-accepted-count") == 1
    assert command.count("--min-sweep-coverage") == 1


def test_live_codex_camera_raw_checker_defaults_to_generated_mess_success_threshold(
    tmp_path: Path, monkeypatch
) -> None:
    run_codex = _load_module(RUN_CODEX_PATH, "run_live_codex_cleanup")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "run_result.json").write_text("{}", encoding="utf-8")
    args = SimpleNamespace(
        run_dir=run_dir,
        status_path=tmp_path / "status.json",
        repo_root=REPO_ROOT,
        task="帮我收拾这个房间",
        backend="molmospaces_subprocess",
        policy="codex_agent",
        profile="camera-raw-fpv",
        min_generated_mess_count="5",
        checker_visual_arg=[],
    )
    runner = run_codex.LiveCodexCleanupRunner(args)
    captured: dict[str, list[str]] = {}

    def fake_run_and_tee(command, **_kwargs):
        captured["command"] = command
        return 0

    monkeypatch.setattr(run_codex, "_run_and_tee", fake_run_and_tee)

    runner._check_result()

    command = captured["command"]
    assert "--require-clean-agent-run" in command
    assert command[command.index("--min-model-declared-observations") + 1] == "4"
    assert command[command.index("--min-model-declared-actions") + 1] == "4"
    assert command[command.index("--min-semantic-accepted-count") + 1] == "4"
    assert command[command.index("--min-sweep-coverage") + 1] == "1.0"


def test_live_codex_map_build_checker_uses_map_task_identity(
    tmp_path: Path, monkeypatch
) -> None:
    run_codex = _load_module(RUN_CODEX_PATH, "run_live_codex_cleanup")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "run_result.json").write_text("{}", encoding="utf-8")
    args = SimpleNamespace(
        run_dir=run_dir,
        status_path=tmp_path / "status.json",
        repo_root=REPO_ROOT,
        intent="map-build",
        task="帮我建立这个房间的 Runtime Metric Map",
        backend="molmospaces_subprocess",
        policy="codex_agent",
        profile="world-public-labels",
        min_generated_mess_count="5",
        checker_visual_arg=["--require-runtime-metric-map"],
    )
    runner = run_codex.LiveCodexCleanupRunner(args)
    captured: dict[str, list[str]] = {}

    def fake_run_and_tee(command, **_kwargs):
        captured["command"] = command
        return 0

    monkeypatch.setattr(run_codex, "_run_and_tee", fake_run_and_tee)

    runner._check_result()

    command = captured["command"]
    assert command[command.index("--expect-task-name") + 1] == "household-world.map-build"
    assert "--require-runtime-metric-map" in command
    assert "--require-clean-agent-run" not in command
    assert "--min-semantic-accepted-count" not in command
    assert command[-1] == str(run_dir / "run_result.json")


def test_live_claude_camera_raw_checker_requires_all_generated_mess_actions(
    tmp_path: Path, monkeypatch
) -> None:
    run_claude = _load_module(RUN_CLAUDE_PATH, "run_live_claude_cleanup")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    (run_dir / "run_result.json").write_text("{}", encoding="utf-8")
    args = SimpleNamespace(
        run_dir=run_dir,
        status_path=tmp_path / "status.json",
        repo_root=REPO_ROOT,
        client_url="http://127.0.0.1:18788/mcp",
        host="127.0.0.1",
        port=18788,
        lock_path=tmp_path / "runner.lock",
        claude_bin="claude",
        claude_provider_summary="test provider",
        kickoff_prompt="clean the room",
        backend="molmospaces_subprocess",
        policy="claude_agent",
        task="帮我收拾这个房间",
        min_generated_mess_count="5",
        profile="camera-raw-fpv",
        server_arg=[],
        claude_model_arg=["--model", "kimi-k2.6"],
        claude_env=[],
        checker_visual_arg=[
            "--require-raw-fpv-observations",
            "--require-model-declared-observations",
            "--min-model-declared-observations",
            "5",
            "--min-model-declared-actions",
            "5",
            "--min-semantic-accepted-count",
            "5",
            "--min-sweep-coverage",
            "1.0",
        ],
    )
    runner = run_claude.LiveClaudeCleanupRunner(args)
    captured: dict[str, list[str]] = {}

    def fake_run_and_tee(command, **_kwargs):
        captured["command"] = command
        return 0

    monkeypatch.setattr(run_claude, "_run_and_tee", fake_run_and_tee)

    runner._check_result()

    command = captured["command"]
    assert "--require-clean-agent-run" in command
    assert command[command.index("--min-model-declared-observations") + 1] == "4"
    assert command[command.index("--min-model-declared-actions") + 1] == "4"
    assert command[command.index("--min-semantic-accepted-count") + 1] == "4"


def test_live_claude_tee_keeps_artifact_when_console_is_nonblocking() -> None:
    run_claude = _load_module(RUN_CLAUDE_PATH, "run_live_claude_cleanup")

    class NonBlockingConsole(io.BytesIO):
        def write(self, _payload):
            raise BlockingIOError("console buffer full")

    artifact = io.BytesIO()

    run_claude._tee_stream(io.BytesIO(b'{"type":"result"}\n'), [artifact, NonBlockingConsole()])

    assert artifact.getvalue() == b'{"type":"result"}\n'


def test_live_codex_tee_keeps_artifact_when_console_is_nonblocking() -> None:
    run_codex = _load_module(RUN_CODEX_PATH, "run_live_codex_cleanup")

    class NonBlockingConsole(io.BytesIO):
        def write(self, _payload):
            raise BlockingIOError("console buffer full")

    artifact = io.BytesIO()

    run_codex._tee_stream(io.BytesIO(b'{"type":"result"}\n'), [artifact, NonBlockingConsole()])

    assert artifact.getvalue() == b'{"type":"result"}\n'


def test_publish_seed_run_and_pages_index_render_molmo_live_tiles(tmp_path: Path) -> None:
    write_pages_index = _load_module(PAGES_INDEX_PATH, "write_pages_index")

    source_seed = tmp_path / "source" / "0513_1447" / "seed-7"
    source_seed.mkdir(parents=True)
    (source_seed / "run_result.json").write_text("{}", encoding="utf-8")
    (source_seed / "report.html").write_text("<!doctype html>", encoding="utf-8")

    live_root = tmp_path / "site" / "molmo" / "live"
    published = publish_seed_run(
        source_seed_dir=source_seed,
        publish_root=live_root,
        entry_name="kimi-k2.6",
        seed=7,
    )
    assert (published / "report.html").is_file()
    camera_raw_published = publish_seed_run(
        source_seed_dir=source_seed,
        publish_root=live_root,
        entry_name="kimi-k2.6-camera-raw-fpv",
        seed=7,
    )
    assert (camera_raw_published / "report.html").is_file()

    success = base_status(
        entry_by_name("kimi-k2.6"),
        seed=7,
        generated_mess_count=5,
        profile="world-public-labels",
        task="帮我收拾这个房间",
    )
    success.update(
        {
            "status": "success",
            "report_path": report_path_for_entry("kimi-k2.6", seed=7),
        }
    )
    skipped = base_status(
        entry_by_name("mimo-v2.5"),
        seed=7,
        generated_mess_count=5,
        profile="world-public-labels",
        task="帮我收拾这个房间",
    )
    skipped.update({"status": "skipped", "reason": "missing required secret/env MIMO_TP_KEY"})
    camera_raw = base_status(
        entry_by_name("kimi-k2.6-camera-raw-fpv"),
        seed=7,
        generated_mess_count=5,
        profile="camera-raw-fpv",
        task="帮我收拾这个房间",
    )
    camera_raw.update(
        {
            "status": "success",
            "report_path": report_path_for_entry("kimi-k2.6-camera-raw-fpv", seed=7),
        }
    )
    write_status(status_path_for_entry(live_root, "kimi-k2.6"), success)
    write_status(status_path_for_entry(live_root, "mimo-v2.5"), skipped)
    write_status(status_path_for_entry(live_root, "kimi-k2.6-camera-raw-fpv"), camera_raw)
    write_manifest(live_root)
    live_index = write_live_index(live_root)
    live_html = live_index.read_text(encoding="utf-8")
    assert "MolmoSpaces Live Cleanup Reports" in live_html
    assert "kimi-k2.6/seed-7/report.html" in live_html
    assert "kimi-k2.6-camera-raw-fpv/seed-7/report.html" in live_html
    assert "Kimi K2.6 RAW_FPV" in live_html
    assert "camera-raw-fpv" in live_html
    assert "Rerun locally" in live_html

    out = write_pages_index.write_index(tmp_path / "site", include_molmo_live=True)
    html = out.read_text(encoding="utf-8")
    assert "MolmoSpaces Live Cleanup (main-only / opt-in CI)" in html
    assert "molmo/live/" in html
    assert "molmo/live/kimi-k2.6/seed-7/report.html" in html
    assert "molmo/live/kimi-k2.6-camera-raw-fpv/seed-7/report.html" in html
    assert "Kimi K2.6 RAW_FPV" in html
    assert "camera-raw-fpv" in html
    assert "MiMo v2.5" in html
    assert "missing required secret/env MIMO_TP_KEY" in html


def test_publish_diagnostic_seed_run_and_pages_index_link_failed_tile(tmp_path: Path) -> None:
    write_pages_index = _load_module(PAGES_INDEX_PATH, "write_pages_index")

    source_seed = tmp_path / "source" / "0513_2217" / "seed-7"
    source_seed.mkdir(parents=True)
    (source_seed / "live_status.json").write_text('{"phase":"failed"}\n', encoding="utf-8")
    (source_seed / "claude.stderr.log").write_text("provider failed\n", encoding="utf-8")

    live_root = tmp_path / "site" / "molmo" / "live"
    published = publish_diagnostic_seed_run(
        source_seed_dir=source_seed,
        publish_root=live_root,
        entry_name="kimi-k2.6",
        seed=7,
    )
    assert (published / "diagnostics.html").is_file()

    failed = base_status(
        entry_by_name("kimi-k2.6"),
        seed=7,
        generated_mess_count=5,
        profile="world-public-labels",
        task="帮我收拾这个房间",
    )
    failed.update(
        {
            "status": "failed",
            "reason": "provider failed",
            "diagnostic_path": diagnostic_path_for_entry("kimi-k2.6", seed=7),
        }
    )
    write_status(status_path_for_entry(live_root, "kimi-k2.6"), failed)
    write_manifest(live_root)
    live_index = write_live_index(live_root)
    live_html = live_index.read_text(encoding="utf-8")
    assert "kimi-k2.6/diagnostics/seed-7/diagnostics.html" in live_html

    out = write_pages_index.write_index(tmp_path / "site", include_molmo_live=True)
    html = out.read_text(encoding="utf-8")
    assert "molmo/live/kimi-k2.6/diagnostics/seed-7/diagnostics.html" in html
    assert "Kimi K2.6 diagnostics" in html


def test_pages_index_without_live_manifest_renders_household_placeholder(tmp_path: Path) -> None:
    write_pages_index = _load_module(PAGES_INDEX_PATH, "write_pages_index")

    out = write_pages_index.write_index(tmp_path / "site", include_molmo_live=True)
    html = out.read_text(encoding="utf-8")

    assert "Household Reports" in html
    assert "No published household cleanup reports are available yet." in html
    assert "openclaw/demo/report.html" not in html
    assert "territory/report.html" not in html


def test_assemble_ci_live_pages_runs_without_site_packages(tmp_path: Path) -> None:
    source_root = tmp_path / "molmo-live-src"
    live_root = tmp_path / "site" / "molmo" / "live"
    status = base_status(
        entry_by_name("kimi-k2.6"),
        seed=7,
        generated_mess_count=5,
        profile="world-public-labels",
        task="帮我收拾这个房间",
    )
    status.update({"status": "skipped", "reason": "fixture"})
    write_status(status_path_for_entry(source_root, "kimi-k2.6"), status)

    result = subprocess.run(
        [
            sys.executable,
            "-S",
            str(ASSEMBLE_LIVE_PAGES_PATH),
            str(source_root),
            str(live_root),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert (live_root / "live-report-manifest.json").is_file()
    assert (live_root / "index.html").is_file()
