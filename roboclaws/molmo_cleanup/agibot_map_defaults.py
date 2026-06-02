from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_AGIBOT_MAP_ALIAS = "robot_map_12"
DEFAULT_AGIBOT_ENVIRONMENT_ID = "agibot-robot-map-12"
DEFAULT_AGIBOT_MAP_VERSION = "agibot-sdk-fetch-2026-06-01"
DEFAULT_AGIBOT_CONFIDENCE_LAYER = "Agibot Robot Map 12 Semantic Actions Rehearsal"

DEFAULT_AGIBOT_CONTEXT_JSON = (
    REPO_ROOT / "tests" / "fixtures" / "agibot_robot_map_12_context.completed.json"
)
DEFAULT_AGIBOT_MAP_ARTIFACT_DIR = (
    REPO_ROOT / "vendors" / "agibot_sdk" / "artifacts" / "maps" / DEFAULT_AGIBOT_MAP_ALIAS
)
