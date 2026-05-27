from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

REPO_ROOT = Path(__file__).resolve().parents[3]
CHECKER = REPO_ROOT / "scripts" / "isaac_lab_cleanup" / "check_isaac_lab_runtime_smoke_result.py"


def write_smoke_image(path: Path) -> None:
    image = Image.new("RGB", (64, 48), color=(20, 40, 60))
    draw = ImageDraw.Draw(image)
    draw.rectangle((8, 8, 56, 40), outline=(220, 180, 40), width=3)
    image.save(path)


def run_checker(
    tmp_path: Path,
    result: dict[str, object],
    *args: str,
    prefix_logs: bool = False,
) -> subprocess.CompletedProcess[str]:
    result_path = tmp_path / "init_result.json"
    text = json.dumps(result)
    if prefix_logs:
        text = f"Isaac startup log line\n{text}\n"
    result_path.write_text(text, encoding="utf-8")
    return subprocess.run(
        [
            sys.executable,
            str(CHECKER),
            "--init-result",
            str(result_path),
            *args,
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_isaac_runtime_smoke_checker_rejects_placeholder_real_mode(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "smoke.png"
    write_smoke_image(image_path)
    result = {
        "ok": True,
        "backend": "isaaclab_subprocess",
        "runtime": {
            "runtime_mode": "real",
            "rendering": {
                "real_rendering_proven": False,
                "placeholder_visuals": True,
            },
        },
        "scene_load": {
            "status": "blocked_capability",
            "usd_stage_loaded": False,
        },
        "artifacts": {"runtime_smoke_image": str(image_path)},
    }

    completed = run_checker(
        tmp_path,
        result,
        "--require-real-rendering",
        "--require-usd-stage-loaded",
        "--require-nonblank-image",
    )

    assert completed.returncode == 1
    summary = json.loads(completed.stdout)
    assert summary["status"] == "failed"
    assert "real Isaac rendering is not proven" in summary["errors"]
    assert "USD stage loading is not proven" in summary["errors"]
    assert "smoke image appears blank" not in summary["errors"]


def test_isaac_runtime_smoke_checker_accepts_real_rendering_evidence(
    tmp_path: Path,
) -> None:
    image_path = tmp_path / "smoke.png"
    state_path = tmp_path / "state.json"
    write_smoke_image(image_path)
    result = {
        "ok": True,
        "backend": "isaaclab_subprocess",
        "runtime": {
            "runtime_mode": "real",
            "rendering": {
                "real_rendering_proven": True,
                "placeholder_visuals": False,
            },
        },
        "scene_load": {
            "status": "loaded",
            "usd_stage_loaded": True,
        },
        "scene_usd": "/tmp/example.usd",
        "artifacts": {"runtime_smoke_image": str(image_path)},
    }
    state_path.write_text(
        json.dumps(
            {
                "backend": "isaaclab_subprocess",
                "runtime": {"runtime_mode": "real"},
            }
        ),
        encoding="utf-8",
    )

    completed = run_checker(
        tmp_path,
        result,
        "--state-path",
        str(state_path),
        "--require-real-rendering",
        "--require-usd-stage-loaded",
        "--require-nonblank-image",
        prefix_logs=True,
    )

    assert completed.returncode == 0
    summary = json.loads(completed.stdout)
    assert summary["status"] == "passed"
    assert summary["errors"] == []
