from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_run_next_treats_zero_padded_run_ids_as_decimal(tmp_path: Path) -> None:
    harness_dir = tmp_path / "harness"
    (harness_dir / "tasks").mkdir(parents=True)
    (harness_dir / "runs").mkdir()
    (harness_dir / "runs" / "008").mkdir()
    (harness_dir / "runs-log").mkdir()
    (harness_dir / "tasks" / "photo-living-room.txt").write_text("task\n", encoding="utf-8")
    shutil.copy(ROOT / "harness" / "run-next.sh", harness_dir / "run-next.sh")
    (harness_dir / "run.sh").write_text(
        '#!/usr/bin/env bash\nprintf \'run_id=%s task=%s cap=%s\\n\' "$1" "$2" "$3"\n',
        encoding="utf-8",
    )

    result = subprocess.run(
        ["bash", "harness/run-next.sh", "photo-living-room", "7"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "next run_id: 009" in result.stdout
    assert "run_id=009 task=harness/tasks/photo-living-room.txt cap=7" in result.stdout
