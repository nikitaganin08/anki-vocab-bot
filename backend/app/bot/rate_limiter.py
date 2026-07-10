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
    _hits: deque[float] = field(default_factory=deque)

    def allow_request(self) -> bool:
        now = self.clock()
        threshold = now - self.window_seconds

        while self._hits and self._hits[0] <= threshold:
            self._hits.popleft()

        if len(self._hits) >= self.limit:
            return False

        self._hits.append(now)
        return True
