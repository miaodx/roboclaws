"""Empty-MCP binding smoke for `just code::cc` / `just code::codex`.

Spins up a tools-less FastMCP server on a free localhost port (no AI2-THOR,
no Engine), exercises the same recipe wiring `just code::cc` would, and
verifies Docker-backed `claude mcp` and `codex mcp` register the URL cleanly.
For claude (which health-probes every entry on `mcp list`), we additionally
assert the entry comes back as `Connected` — proof that the streamable-HTTP
handshake completed end-to-end.

Skipped on hosts without `just`, Docker, or the `mcp` package.
"""

from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
import threading
import time
from contextlib import closing
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
SERVER_DIR = REPO_ROOT / ".tmp" / "roboclaws-mcp"
PID_FILE = SERVER_DIR / "server.pid"
DOCKER_AGENT = REPO_ROOT / "scripts" / "dev" / "coding_agent_docker.sh"

# Unique per process so concurrent runs (and the user's real `roboclaws`
# registration) never collide.
TEST_NAME = f"roboclaws-bind-test-{os.getpid()}"


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_for_port(host: str, port: int, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.1)
    raise TimeoutError(f"port {host}:{port} never opened within {timeout}s")


def _have(cmd: str) -> bool:
    return shutil.which(cmd) is not None


def _agent_cmd(binary: str) -> list[str]:
    return [str(DOCKER_AGENT), "run", binary]


@pytest.fixture(scope="module")
def empty_mcp_url() -> str:
    """Bring up a tools-less FastMCP streamable-HTTP server; yield its URL."""
    if not _have("just"):
        pytest.skip("just CLI required")
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        pytest.skip("mcp.server.fastmcp not available")

    port = _free_port()
    mcp = FastMCP("roboclaws-bind-test", host="127.0.0.1", port=port)
    threading.Thread(
        target=mcp.run,
        kwargs={"transport": "streamable-http"},
        name=f"empty-mcp-{port}",
        daemon=True,
    ).start()
    _wait_for_port("127.0.0.1", port)
    return f"http://127.0.0.1:{port}/mcp"


@pytest.fixture
def warm_path_pid():
    """Inject a live PID so `just mcp::up` takes the warm path.

    The warm path returns the URL immediately without trying to start a real
    AI2-THOR-backed server. Backs up and restores any pre-existing PID file
    so we never clobber the user's real running server.
    """
    backup = PID_FILE.read_text(encoding="utf-8") if PID_FILE.exists() else None
    SERVER_DIR.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(f"{os.getpid()}\n", encoding="utf-8")
    try:
        yield
    finally:
        if backup is not None:
            PID_FILE.write_text(backup, encoding="utf-8")
        else:
            PID_FILE.unlink(missing_ok=True)


@pytest.mark.usefixtures("warm_path_pid")
def test_just_mcp_up_emits_clean_url(empty_mcp_url: str) -> None:
    """`just mcp::up FloorPlan H P` returns http://H:P/mcp — no `name=` leak."""
    port = empty_mcp_url.rsplit(":", 1)[1].split("/", 1)[0]
    # The recipe uses bare `python`; ensure the venv's bin dir is on PATH so
    # subprocess inherits it even when pytest was launched via .venv/bin/python
    # without the venv being activated in the parent shell.
    env = os.environ.copy()
    venv_bin = str(Path(sys.executable).parent)
    env["PATH"] = venv_bin + os.pathsep + env.get("PATH", "")
    result = subprocess.run(
        ["just", "mcp::up", "FloorPlan201", "127.0.0.1", port],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=15,
        env=env,
    )
    assert result.returncode == 0, f"just failed: {result.stderr}"
    last_line = result.stdout.strip().splitlines()[-1]
    assert last_line == empty_mcp_url, f"recipe emitted {last_line!r}, want {empty_mcp_url!r}"


@pytest.mark.skipif(not _have("docker"), reason="Docker required")
def test_claude_binds_and_connects(empty_mcp_url: str) -> None:
    """Docker-backed `claude mcp add <name> <url>` registers and probes successfully."""
    # Pre-cleanup in case a prior run left this name behind.
    subprocess.run(
        [*_agent_cmd("claude"), "mcp", "remove", TEST_NAME],
        cwd=REPO_ROOT,
        capture_output=True,
    )
    try:
        add = subprocess.run(
            [
                *_agent_cmd("claude"),
                "mcp",
                "add",
                "--transport",
                "http",
                TEST_NAME,
                empty_mcp_url,
            ],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=180,
        )
        assert add.returncode == 0, f"claude mcp add failed: {add.stderr}"

        lst = subprocess.run(
            [*_agent_cmd("claude"), "mcp", "list"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=180,
        )
        assert lst.returncode == 0, f"claude mcp list failed: {lst.stderr}"

        # Find the line for our entry; it must show our URL and ✓ Connected.
        match = next(
            (ln for ln in lst.stdout.splitlines() if ln.startswith(f"{TEST_NAME}:")),
            None,
        )
        assert match is not None, f"binding missing in `claude mcp list`:\n{lst.stdout}"
        assert empty_mcp_url in match, f"URL absent: {match!r}"
        assert "Connected" in match, (
            f"empty MCP failed claude's probe — registration is reachable but "
            f"the streamable-HTTP handshake did not complete. Line: {match!r}"
        )
    finally:
        subprocess.run(
            [*_agent_cmd("claude"), "mcp", "remove", TEST_NAME],
            cwd=REPO_ROOT,
            capture_output=True,
        )


@pytest.mark.skipif(not _have("docker"), reason="Docker required")
def test_codex_binds_url(empty_mcp_url: str) -> None:
    """Docker-backed `codex mcp add <name> --url <url>` stores the registration."""
    subprocess.run(
        [*_agent_cmd("codex"), "mcp", "remove", TEST_NAME],
        cwd=REPO_ROOT,
        capture_output=True,
    )
    try:
        add = subprocess.run(
            [*_agent_cmd("codex"), "mcp", "add", TEST_NAME, "--url", empty_mcp_url],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=180,
        )
        assert add.returncode == 0, f"codex mcp add failed: {add.stderr}"

        lst = subprocess.run(
            [*_agent_cmd("codex"), "mcp", "list"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=180,
        )
        assert lst.returncode == 0, f"codex mcp list failed: {lst.stderr}"
        assert TEST_NAME in lst.stdout, f"binding missing in `codex mcp list`:\n{lst.stdout}"
        assert empty_mcp_url in lst.stdout, f"URL missing in codex listing:\n{lst.stdout}"
    finally:
        subprocess.run(
            [*_agent_cmd("codex"), "mcp", "remove", TEST_NAME],
            cwd=REPO_ROOT,
            capture_output=True,
        )
