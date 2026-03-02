from __future__ import annotations

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from time import monotonic


@dataclass(slots=True)
class InMemoryRateLimiter:
    limit: int = 5
    window_seconds: float = 60.0
    clock: Callable[[], float] = monotonic
    _hits: dict[int, deque[float]] = field(default_factory=dict)

    def allow_request(self, user_id: int) -> bool:
        now = self.clock()
        hits = self._hits.setdefault(user_id, deque())
        threshold = now - self.window_seconds

        while hits and hits[0] <= threshold:
            hits.popleft()

        if len(hits) >= self.limit:
            return False

        hits.append(now)
        return True
