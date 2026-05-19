from __future__ import annotations

import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "dev" / "convert_commit_identity.sh"


def _git(repo: Path, *args: str, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _commit(repo: Path, message: str, timestamp: int, filename: str, content: str) -> str:
    path = repo / filename
    path.write_text(content, encoding="utf-8")
    _git(repo, "add", filename)
    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "Original Author",
            "GIT_AUTHOR_EMAIL": "author@example.test",
            "GIT_AUTHOR_DATE": f"{timestamp} +0800",
            "GIT_COMMITTER_NAME": "Original Committer",
            "GIT_COMMITTER_EMAIL": "committer@example.test",
            "GIT_COMMITTER_DATE": f"{timestamp + 17} +0700",
        }
    )
    return _git(repo, "commit", "-m", message, env=env)


def _make_repo_with_merge(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.name", "Local User")
    _git(repo, "config", "user.email", "local@example.test")
    _git(repo, "config", "commit.gpgSign", "false")

    _commit(repo, "base commit", 1_700_000_000, "base.txt", "base\n")
    _git(repo, "checkout", "-b", "feature")
    _commit(repo, "feature commit\n\nfeature body", 1_700_000_100, "feature.txt", "feature\n")
    _git(repo, "checkout", "main")
    _commit(repo, "main commit", 1_700_000_200, "main.txt", "main\n")

    env = os.environ.copy()
    env.update(
        {
            "GIT_AUTHOR_NAME": "Merge Author",
            "GIT_AUTHOR_EMAIL": "merge-author@example.test",
            "GIT_AUTHOR_DATE": "1700000300 +0530",
            "GIT_COMMITTER_NAME": "Merge Committer",
            "GIT_COMMITTER_EMAIL": "merge-committer@example.test",
            "GIT_COMMITTER_DATE": "1700000400 +0400",
        }
    )
    _git(repo, "merge", "--no-ff", "feature", "-m", "merge feature", env=env)
    return repo


def _run_converter(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--source",
            "HEAD",
            "--output-ref",
            "refs/heads/mi-export",
        ],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def _run_converter_with_default_source(repo: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--output-ref",
            "refs/heads/mi-export",
        ],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def test_convert_commit_identity_defaults_to_origin_main(tmp_path: Path) -> None:
    repo = _make_repo_with_merge(tmp_path)
    origin_main = _git(repo, "rev-parse", "HEAD")
    _git(repo, "update-ref", "refs/remotes/origin/main", origin_main)
    _commit(repo, "local unexported work", 1_700_000_500, "local.txt", "local only\n")

    result = _run_converter_with_default_source(repo)

    assert "source ref: origin/main" in result.stdout
    assert f"original tip SHA: {origin_main}" in result.stdout
    subprocess.run(
        ["git", "diff", "--quiet", "origin/main", "refs/heads/mi-export"],
        cwd=repo,
        check=True,
    )
    diff_from_head = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "refs/heads/mi-export"],
        cwd=repo,
    )
    assert diff_from_head.returncode == 1


def test_convert_commit_identity_is_deterministic_and_non_destructive(tmp_path: Path) -> None:
    repo = _make_repo_with_merge(tmp_path)
    source_tip = _git(repo, "rev-parse", "HEAD")
    branch_before = _git(repo, "branch", "--show-current")
    status_before = _git(repo, "status", "--short")
    config_before = (repo / ".git" / "config").read_text(encoding="utf-8")

    first = _run_converter(repo)
    first_tip = _git(repo, "rev-parse", "refs/heads/mi-export")
    second = _run_converter(repo)
    second_tip = _git(repo, "rev-parse", "refs/heads/mi-export")

    assert "source ref: HEAD" in first.stdout
    assert "output ref: refs/heads/mi-export" in first.stdout
    assert f"original tip SHA: {source_tip}" in first.stdout
    assert f"converted tip SHA: {first_tip}" in first.stdout
    assert "git diff --quiet" in first.stdout
    assert second_tip == first_tip
    assert f"converted tip SHA: {second_tip}" in second.stdout

    assert _git(repo, "branch", "--show-current") == branch_before
    assert _git(repo, "status", "--short") == status_before
    assert (repo / ".git" / "config").read_text(encoding="utf-8") == config_before
    assert _git(repo, "rev-parse", "HEAD") == source_tip

    subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "refs/heads/mi-export"],
        cwd=repo,
        check=True,
    )

    identities = _git(
        repo,
        "log",
        "--format=%an <%ae>%x00%cn <%ce>",
        "refs/heads/mi-export",
    ).splitlines()
    assert identities
    assert all(
        line == "miaodongxu <miaodongxu@xiaomi.com>\0miaodongxu <miaodongxu@xiaomi.com>"
        for line in identities
    )

    source_parent_counts = _git(repo, "rev-list", "--parents", "HEAD").splitlines()
    output_parent_counts = _git(repo, "rev-list", "--parents", "refs/heads/mi-export").splitlines()
    assert [len(line.split()) for line in output_parent_counts] == [
        len(line.split()) for line in source_parent_counts
    ]
    assert len(output_parent_counts[0].split()) == 3

    source_dates = _git(
        repo,
        "log",
        "--reverse",
        "--topo-order",
        "--format=%ad%x00%cd",
        "--date=raw",
        "HEAD",
    ).splitlines()
    output_dates = _git(
        repo,
        "log",
        "--reverse",
        "--topo-order",
        "--format=%ad%x00%cd",
        "--date=raw",
        "refs/heads/mi-export",
    ).splitlines()
    assert output_dates == source_dates

    source_messages = _git(
        repo,
        "log",
        "--reverse",
        "--topo-order",
        "--format=%B%x00",
        "HEAD",
    ).split("\0")
    output_messages = _git(
        repo,
        "log",
        "--reverse",
        "--topo-order",
        "--format=%B%x00",
        "refs/heads/mi-export",
    ).split("\0")
    assert output_messages == source_messages


def test_convert_commit_identity_rejects_current_branch_ref(tmp_path: Path) -> None:
    repo = _make_repo_with_merge(tmp_path)

    result = subprocess.run(
        [
            "bash",
            str(SCRIPT),
            "--source",
            "HEAD",
            "--output-ref",
            "refs/heads/main",
        ],
        cwd=repo,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 2
    assert "currently checked-out branch" in result.stderr
