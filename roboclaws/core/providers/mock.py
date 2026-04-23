from __future__ import annotations

import random
import time
from typing import Any

from roboclaws.core.engine import NAVIGATION_ACTIONS
from roboclaws.core.vlm import ProviderStatus, _record_call_success


class MockProvider:
    """Returns random valid actions — no API key required, suitable for CI."""

    def __init__(self, seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self._cost = 0.0
        self.model = "mock"
        self._status = ProviderStatus(provider_name="mock", model=self.model)

    @property
    def cumulative_cost(self) -> float:
        return self._cost

    def reset_cost(self) -> None:
        self._cost = 0.0

    def get_status(self) -> dict[str, Any]:
        return self._status.to_dict()

    def get_action(
        self,
        images: list[str],
        state: dict[str, Any],
    ) -> dict[str, Any]:
        started = time.monotonic()
        action = self._rng.choice(NAVIGATION_ACTIONS)
        _record_call_success(
            self._status,
            duration_seconds=time.monotonic() - started,
        )
        return {"reasoning": f"MockProvider chose {action}", "action": action}
