#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from scripts.molmo_cleanup.planner_manipulation_probe_checker import assert_probe_result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate MolmoSpaces planner-backed manipulation probe artifacts."
    )
    parser.add_argument("path", type=Path, help="run_result.json or probe output directory")
    parser.add_argument("--accept-blocked-capability", action="store_true")
    parser.add_argument("--require-planner-backed", action="store_true")
    parser.add_argument("--accept-rby1m-curobo-blocked", action="store_true")
    parser.add_argument("--require-rby1m-curobo-ready", action="store_true")
    parser.add_argument("--require-curobo-extension-cache", action="store_true")
    parser.add_argument("--require-warp-compatibility", action="store_true")
    parser.add_argument("--require-cuda-memory", action="store_true")
    parser.add_argument("--require-curobo-memory-profile", action="store_true")
    parser.add_argument("--require-cleanup-scene-bound", action="store_true")
    parser.add_argument("--require-policy-exception-context", action="store_true")
    parser.add_argument("--require-proof-quality", action="store_true")
    parser.add_argument("--require-proof-min-steps", type=int, default=None)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    path = args.path / "run_result.json" if args.path.is_dir() else args.path
    data = json.loads(path.read_text(encoding="utf-8"))
    _assert_probe_result(
        data,
        path.parent,
        accept_blocked_capability=args.accept_blocked_capability,
        require_planner_backed=args.require_planner_backed,
        accept_rby1m_curobo_blocked=args.accept_rby1m_curobo_blocked,
        require_rby1m_curobo_ready=args.require_rby1m_curobo_ready,
        require_curobo_extension_cache=args.require_curobo_extension_cache,
        require_warp_compatibility=args.require_warp_compatibility,
        require_cuda_memory=args.require_cuda_memory,
        require_curobo_memory_profile=args.require_curobo_memory_profile,
        require_cleanup_scene_bound=args.require_cleanup_scene_bound,
        require_policy_exception_context=args.require_policy_exception_context,
        require_proof_quality=args.require_proof_quality,
        require_proof_min_steps=args.require_proof_min_steps,
    )
    print(f"molmo-planner-manipulation-probe ok: {path}")


def _assert_probe_result(
    data: dict[str, Any],
    base: Path,
    *,
    accept_blocked_capability: bool = False,
    require_planner_backed: bool = False,
    accept_rby1m_curobo_blocked: bool = False,
    require_rby1m_curobo_ready: bool = False,
    require_curobo_extension_cache: bool = False,
    require_warp_compatibility: bool = False,
    require_cuda_memory: bool = False,
    require_curobo_memory_profile: bool = False,
    require_cleanup_scene_bound: bool = False,
    require_policy_exception_context: bool = False,
    require_proof_quality: bool = False,
    require_proof_min_steps: int | None = None,
) -> None:
    assert_probe_result(
        data,
        base,
        accept_blocked_capability=accept_blocked_capability,
        require_planner_backed=require_planner_backed,
        accept_rby1m_curobo_blocked=accept_rby1m_curobo_blocked,
        require_rby1m_curobo_ready=require_rby1m_curobo_ready,
        require_curobo_extension_cache=require_curobo_extension_cache,
        require_warp_compatibility=require_warp_compatibility,
        require_cuda_memory=require_cuda_memory,
        require_curobo_memory_profile=require_curobo_memory_profile,
        require_cleanup_scene_bound=require_cleanup_scene_bound,
        require_policy_exception_context=require_policy_exception_context,
        require_proof_quality=require_proof_quality,
        require_proof_min_steps=require_proof_min_steps,
    )


if __name__ == "__main__":
    main()
