"""Static regression checks for the navigator harness shell wiring."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
HARNESS_RUN = REPO_ROOT / "harness" / "run.sh"
HARNESS_NEXT = REPO_ROOT / "harness" / "run-next.sh"
HARNESS_JUST = REPO_ROOT / "just" / "harness.just"
CODE_JUST = REPO_ROOT / "just" / "code.just"


def test_harness_just_keeps_claude_default_and_forwards_agent() -> None:
    text = HARNESS_JUST.read_text(encoding="utf-8")

    assert 'run task cap="900" agent="claude":' in text
    assert 'bash harness/run-next.sh "{{task}}" "{{cap}}" "{{agent}}"' in text


def test_run_next_validates_and_forwards_agent() -> None:
    text = HARNESS_NEXT.read_text(encoding="utf-8")

    assert 'AGENT="${3:-claude}"' in text
    assert "claude|codex" in text
    assert 'exec bash harness/run.sh "$next" "$TASK_FILE" "$TIME_CAP" "$AGENT"' in text


def test_run_sh_has_agent_specific_session_and_launch_paths() -> None:
    text = HARNESS_RUN.read_text(encoding="utf-8")

    assert 'AGENT="${4:-claude}"' in text
    assert 'SESSION="roboclaws-harness-$RUN_ID-$AGENT"' in text
    assert 'LAUNCH_CMD="cd $REPO_Q && just code::cc"' in text
    assert "just code::codex" in text
    assert "CODEX_MODEL" in text
    assert "CODEX_REASONING_EFFORT" in text
    assert "CODEX_INITIAL_PROMPT_FILE" in text
    assert "kickoff prompt passed to Codex at launch" in text
    assert "Executor scope: this robot-control session" in text
    assert "Do not edit files, stage changes, or run git commands" in text
    kickoff_line = next(line for line in text.splitlines() if line.startswith("KICKOFF="))
    assert "atomic git commit" not in kickoff_line
    assert "outer harness operator" not in kickoff_line


def test_metrics_include_agent_identity_and_all_current_tools() -> None:
    text = HARNESS_RUN.read_text(encoding="utf-8")

    for field in (
        "task: $TASK_NAME",
        "agent: $AGENT",
        "model_label: $MODEL_LABEL",
        "elapsed_seconds: $ELAPSED",
        "total_tool_calls: $TOOL_CALLS",
        "blocked_moves: $BLOCKED",
        "trace: $TRACE",
        "snapshot_dir: $SNAPSHOT_DIR",
    ):
        assert field in text

    for tool in ("scene_objects", "goto", "observe", "observe_archived", "move", "done"):
        assert f'trace_count_request_tool "$TRACE" {tool}' in text
        assert f"  {tool}: $" in text


def test_run_sh_prints_post_run_atomic_commit_prompt() -> None:
    text = HARNESS_RUN.read_text(encoding="utf-8")

    assert "post-run bookkeeping" in text
    assert "update harness/runs-log and harness/PLAN.md" in text
    assert "one atomic git commit for run_id=$RUN_ID" in text


def test_code_codex_accepts_harness_model_overrides() -> None:
    text = CODE_JUST.read_text(encoding="utf-8")

    assert "CODEX_MODEL" in text
    assert "CODEX_REASONING_EFFORT" in text
    assert "CODEX_INITIAL_PROMPT_FILE" in text
    assert "model_reasoning_effort=" in text
    assert 'codex "${codex_args[@]}" "$codex_initial_prompt"' in text
