from __future__ import annotations

import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

ACTIVE_SEARCH_ROOTS = (
    ".github",
    "README.md",
    "docs/ai/openclaw",
    "docs/human",
    "docs/troubleshooting",
    "examples",
    "just",
    "roboclaws",
    "scripts",
    "skills",
    "tests",
)
ALLOWED_HISTORICAL_PATHS = {
    "docs/human/model-matrix.md",
    "docs/human/molmospaces-visual-grounding-results.md",
}
FORBIDDEN_ACTIVE_PATTERNS = (
    "mimo-v2-" + "omni",
    "xiaomi/mimo-v2-" + "omni",
    "mimo-" + "omni",
    "MiMo v2 " + "Omni",
    "MiMo V2 " + "Omni",
    "claude-mimo-" + "omni",
    "mify-" + "omni",
    "probe_mify_" + "omni",
    "mimo_" + "omni",
    "mimo_v2_" + "omni",
)


def test_active_mimo_references_do_not_use_deprecated_omni_ids() -> None:
    result = subprocess.run(
        [
            "rg",
            "-n",
            "|".join(FORBIDDEN_ACTIVE_PATTERNS),
            *ACTIVE_SEARCH_ROOTS,
            "--glob",
            "!docs/retrospectives/**",
            "--glob",
            "!docs/plans/**",
            "--glob",
            "!docs/status/**",
            "--glob",
            "!output/**",
            "--glob",
            "!vendors/**",
            "--glob",
            "!**/__pycache__/**",
        ],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode in {0, 1}, result.stderr
    offenders = [
        line
        for line in result.stdout.splitlines()
        if line.split(":", 1)[0] not in ALLOWED_HISTORICAL_PATHS
    ]
    assert offenders == []
