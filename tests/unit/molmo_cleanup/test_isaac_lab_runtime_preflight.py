from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / "scripts" / "isaac_lab_cleanup" / "check_isaac_lab_runtime.py"


def run_preflight(tmp_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--output-dir",
            str(tmp_path / "preflight"),
            "--stamp",
            "unit",
            "--runtime-dir",
            str(tmp_path / ".venv-isaaclab"),
            "--python-executable",
            sys.executable,
            "--skip-gpu-probe",
            "--min-free-gb",
            "0",
            *args,
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def load_report(result: subprocess.CompletedProcess[str]) -> dict[str, object]:
    summary = json.loads(result.stdout)
    return json.loads(Path(summary["report_path"]).read_text(encoding="utf-8"))


def test_isaac_lab_runtime_preflight_writes_blocked_report_without_install(
    tmp_path: Path,
) -> None:
    runtime_dir = tmp_path / ".venv-isaaclab"

    result = run_preflight(tmp_path)

    assert result.returncode == 0
    report = load_report(result)
    assert report["schema"] == "roboclaws_isaac_lab_runtime_preflight_v1"
    assert report["status"] == "blocked"
    assert report["runtime_dir"] == str(runtime_dir)
    assert runtime_dir.exists() is False
    assert report["install_attempt"] == {
        "requested": False,
        "status": "not_requested",
        "steps": [],
    }

    checks = {item["name"]: item for item in report["checks"]}  # type: ignore[index]
    assert checks["nvidia_gpu"]["status"] == "skipped"
    assert checks["runtime_python_exists"]["status"] == "blocked"
    assert checks["runtime_import_isaacsim"]["status"] == "blocked"

    install_plan = report["install_plan"]  # type: ignore[index]
    step_names = [item["name"] for item in install_plan["steps"]]
    assert step_names == [
        "create_runtime_env",
        "upgrade_pip",
        "install_isaacsim",
        "install_cuda_torch",
        "clone_isaac_lab_source",
        "install_isaac_lab_source",
    ]
    install_script = Path(install_plan["script_path"])
    assert install_script.is_file()
    assert "--accept-nvidia-eula" in json.dumps(install_plan)
    assert "isaacsim[all,extscache]==6.0.0" in install_script.read_text(encoding="utf-8")


def test_isaac_lab_runtime_install_requires_eula_acknowledgement(tmp_path: Path) -> None:
    runtime_dir = tmp_path / ".venv-isaaclab"

    result = run_preflight(tmp_path, "--install")

    assert result.returncode == 2
    report = load_report(result)
    assert report["install_attempt"]["status"] == "blocked"  # type: ignore[index]
    assert "accept-nvidia-eula" in report["install_attempt"]["reason"]  # type: ignore[index]
    assert runtime_dir.exists() is False


def test_isaac_lab_runtime_default_runtime_path_is_gitignored(tmp_path: Path) -> None:
    result = run_preflight(tmp_path, "--runtime-dir", ".venv-isaaclab")

    assert result.returncode == 0
    report = load_report(result)
    checks = {item["name"]: item for item in report["checks"]}  # type: ignore[index]
    assert checks["runtime_gitignore"]["status"] == "pass"


def test_isaac_lab_runtime_missing_python_executable_is_reported(tmp_path: Path) -> None:
    result = run_preflight(tmp_path, "--python-executable", str(tmp_path / "missing-python"))

    assert result.returncode == 0
    report = load_report(result)
    checks = {item["name"]: item for item in report["checks"]}  # type: ignore[index]
    assert checks["python_312_available"]["status"] == "blocked"
    assert "Could not execute requested Python runtime" in checks["python_312_available"]["detail"]
