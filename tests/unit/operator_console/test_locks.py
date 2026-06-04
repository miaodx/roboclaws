from __future__ import annotations

import os
from pathlib import Path

import pytest

from roboclaws.operator_console.locks import ResourceLock, ResourceLockError


def test_lock_prevents_conflicting_starts(tmp_path: Path) -> None:
    lock = ResourceLock(tmp_path, "molmospaces_mujoco")
    owner = lock.acquire(run_id="run-1", pid=os.getpid())
    assert owner.owner_run_id == "run-1"
    assert lock.read().held

    with pytest.raises(ResourceLockError, match="Backend lock"):
        lock.acquire(run_id="run-2", pid=999999998)

    lock.release(run_id="run-1", force=True)
    assert not lock.read().held


def test_lock_recovers_stale_owner(tmp_path: Path) -> None:
    lock = ResourceLock(tmp_path, "molmospaces_mujoco")
    lock.acquire(run_id="stale", pid=999999999)
    owner = lock.acquire(run_id="run-2", pid=os.getpid())
    assert owner.owner_run_id == "run-2"
