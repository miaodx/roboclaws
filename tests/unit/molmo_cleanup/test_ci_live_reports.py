from __future__ import annotations

import importlib.util
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
    write_manifest,
    write_status,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
RUN_MATRIX_PATH = REPO_ROOT / "scripts" / "molmo_cleanup" / "run_ci_live_cleanup_matrix.py"
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
    ]
    assert entry_by_name("kimi-k2.6").provider_profile == "kimi-anthropic"
    assert entry_by_name("kimi-k2.6").secret_env == "KIMI_API_KEY"
    assert entry_by_name("mimo-v2-omni").provider_profile == "mimo-anthropic"
    assert entry_by_name("mimo-v2-omni").secret_env == "MIMO_TP_KEY"


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
    assert payload["command"][:4] == ["just", "task::run", "molmo-cleanup", "claude"]
    manifest = json.loads(
        (tmp_path / "site" / "molmo" / "live" / "live-report-manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert manifest["schema"] == "molmo_live_ci_report_manifest_v1"
    assert manifest["entries"][0]["entry"] == "kimi-k2.6"


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

    monkeypatch.setattr(run_claude.subprocess, "run", lambda *_, **__: None)
    captured: dict[str, list[str]] = {}

    def fake_run_and_tee(command, **_kwargs):
        captured["command"] = command
        return 0

    monkeypatch.setattr(run_claude, "_run_and_tee", fake_run_and_tee)

    runner._run_claude()

    command = captured["command"]
    assert command[:5] == ["claude", "-p", "--verbose", "--output-format", "stream-json"]
    mcp_config_path = Path(command[command.index("--mcp-config") + 1])
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
    write_status(status_path_for_entry(live_root, "kimi-k2.6"), success)
    write_status(status_path_for_entry(live_root, "mimo-v2.5-pro"), skipped)
    write_manifest(live_root)

    out = write_pages_index.write_index(tmp_path / "site", include_molmo_live=True)
    html = out.read_text(encoding="utf-8")
    assert "MolmoSpaces Live Cleanup" in html
    assert "molmo/live/kimi-k2.6/seed-7/report.html" in html
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

    out = write_pages_index.write_index(tmp_path / "site", include_molmo_live=True)
    html = out.read_text(encoding="utf-8")
    assert "molmo/live/kimi-k2.6/diagnostics/seed-7/diagnostics.html" in html
    assert "Kimi K2.6 diagnostics" in html
