from __future__ import annotations

import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace

from roboclaws.molmo_cleanup.ci_live_reports import (
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
        "mimo-v2.5-pro",
        "mimo-v2-omni",
        "kimi-k2.6-camera-raw",
        "mimo-v2-omni-camera-raw",
    ]
    assert {
        entry.name: (entry.provider_profile, entry.model, entry.secret_env, entry.profile)
        for entry in MODEL_ENTRIES
    } == {
        "kimi-k2.6": ("kimi-anthropic", "kimi-k2.6", "KIMI_API_KEY", "world-labels"),
        "mimo-v2.5-pro": (
            "mimo-anthropic",
            "mimo-v2.5-pro",
            "MIMO_TP_KEY",
            "world-labels",
        ),
        "mimo-v2-omni": (
            "mimo-anthropic",
            "mimo-v2-omni",
            "MIMO_TP_KEY",
            "world-labels",
        ),
        "kimi-k2.6-camera-raw": (
            "kimi-anthropic",
            "kimi-k2.6",
            "KIMI_API_KEY",
            "camera-raw",
        ),
        "mimo-v2-omni-camera-raw": (
            "mimo-anthropic",
            "mimo-v2-omni",
            "MIMO_TP_KEY",
            "camera-raw",
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
        "ROBOCLAWS_CLAUDE_PROVIDER": "kimi-anthropic",
    }
    assert payload["profile"] == "world-labels"
    assert payload["generated_mess_count"] == 5
    assert payload["command"][:5] == [
        "just",
        "task::run",
        "household-cleanup",
        "claude",
        "world-labels",
    ]
    assert payload["rerun_command"].startswith(
        "ROBOCLAWS_CLAUDE_PROVIDER=kimi-anthropic "
        "ROBOCLAWS_CLAUDE_MODEL=kimi-k2.6 "
        "just task::run household-cleanup claude world-labels"
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
            "kimi-k2.6-camera-raw",
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
    status_path = tmp_path / "site" / "molmo" / "live" / "kimi-k2.6-camera-raw" / "status.json"
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    assert payload["entry"] == "kimi-k2.6-camera-raw"
    assert payload["label"] == "Kimi K2.6 RAW_FPV"
    assert payload["model"] == "kimi-k2.6"
    assert payload["profile"] == "camera-raw"
    assert payload["generated_mess_count"] == 10
    assert payload["command"][:5] == [
        "just",
        "task::run",
        "household-cleanup",
        "claude",
        "camera-raw",
    ]
    assert "generated_mess_count=10" in payload["command"]
    assert "generated_mess_count=10" in payload["rerun_command"]
    assert "just task::run household-cleanup claude camera-raw" in payload["rerun_command"]


def test_dry_run_camera_raw_generated_mess_count_override(tmp_path: Path) -> None:
    run_matrix = _load_module(RUN_MATRIX_PATH, "run_ci_live_cleanup_matrix")

    status = run_matrix.main(
        [
            "--entry",
            "mimo-v2-omni-camera-raw",
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
    status_path = tmp_path / "site" / "molmo" / "live" / "mimo-v2-omni-camera-raw" / "status.json"
    payload = json.loads(status_path.read_text(encoding="utf-8"))
    assert payload["generated_mess_count"] == 12
    assert "generated_mess_count=12" in payload["command"]


def test_failed_live_entry_publishes_partial_seed_diagnostics(tmp_path: Path, monkeypatch) -> None:
    run_matrix = _load_module(RUN_MATRIX_PATH, "run_ci_live_cleanup_matrix")
    entry = entry_by_name("kimi-k2.6")
    output_dir = tmp_path / "runs"
    publish_root = tmp_path / "site" / "molmo" / "live"
    args = SimpleNamespace(
        output_dir=output_dir,
        seed=7,
        generated_mess_count=5,
        profile="world-labels",
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
        profile="world-labels",
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
    assert "--dangerously-skip-permissions" in command
    assert (tmp_path / "run" / "claude-version.txt").read_text(encoding="utf-8") == (
        "2.1.143 (Claude Code)\n"
    )


def test_live_claude_workspace_exposes_skill_at_task_relative_path(
    tmp_path: Path, monkeypatch
) -> None:
    run_claude = _load_module(RUN_CLAUDE_PATH, "run_live_claude_cleanup")
    workspace = tmp_path / "agent-workspace"
    monkeypatch.setenv("ROBOCLAWS_CODE_AGENT_WORKSPACE", str(workspace))

    prepared_workspace, task_dir = run_claude._prepare_agent_workspace(
        repo_root=REPO_ROOT,
        task_name="household-cleanup",
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
        task_name="household-cleanup",
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
            "world-labels",
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
            "world-labels",
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
        profile="world-labels",
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
        profile="world-labels",
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
        entry_name="kimi-k2.6-camera-raw",
        seed=7,
    )
    assert (camera_raw_published / "report.html").is_file()

    success = base_status(
        entry_by_name("kimi-k2.6"),
        seed=7,
        generated_mess_count=5,
        profile="world-labels",
        task="帮我收拾这个房间",
    )
    success.update(
        {
            "status": "success",
            "report_path": report_path_for_entry("kimi-k2.6", seed=7),
        }
    )
    skipped = base_status(
        entry_by_name("mimo-v2.5-pro"),
        seed=7,
        generated_mess_count=5,
        profile="world-labels",
        task="帮我收拾这个房间",
    )
    skipped.update({"status": "skipped", "reason": "missing required secret/env MIMO_TP_KEY"})
    camera_raw = base_status(
        entry_by_name("kimi-k2.6-camera-raw"),
        seed=7,
        generated_mess_count=5,
        profile="camera-raw",
        task="帮我收拾这个房间",
    )
    camera_raw.update(
        {
            "status": "success",
            "report_path": report_path_for_entry("kimi-k2.6-camera-raw", seed=7),
        }
    )
    write_status(status_path_for_entry(live_root, "kimi-k2.6"), success)
    write_status(status_path_for_entry(live_root, "mimo-v2.5-pro"), skipped)
    write_status(status_path_for_entry(live_root, "kimi-k2.6-camera-raw"), camera_raw)
    write_manifest(live_root)
    live_index = write_live_index(live_root)
    live_html = live_index.read_text(encoding="utf-8")
    assert "MolmoSpaces Live Cleanup Reports" in live_html
    assert "kimi-k2.6/seed-7/report.html" in live_html
    assert "kimi-k2.6-camera-raw/seed-7/report.html" in live_html
    assert "Kimi K2.6 RAW_FPV" in live_html
    assert "camera-raw" in live_html
    assert "Rerun locally" in live_html

    out = write_pages_index.write_index(tmp_path / "site", include_molmo_live=True)
    html = out.read_text(encoding="utf-8")
    assert "MolmoSpaces Live Cleanup (main-only / opt-in CI)" in html
    assert "molmo/live/" in html
    assert "molmo/live/kimi-k2.6/seed-7/report.html" in html
    assert "molmo/live/kimi-k2.6-camera-raw/seed-7/report.html" in html
    assert "Kimi K2.6 RAW_FPV" in html
    assert "camera-raw" in html
    assert "MiMo v2.5 Pro" in html
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
        profile="world-labels",
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
