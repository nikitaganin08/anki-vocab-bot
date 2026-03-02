from dataclasses import dataclass

from app.bot.rate_limiter import InMemoryRateLimiter


@dataclass
class ManualClock:
    now: float = 0.0

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_rate_limiter_blocks_after_five_requests_in_window() -> None:
    clock = ManualClock(now=100.0)
    limiter = InMemoryRateLimiter(limit=5, window_seconds=60.0, clock=clock)

    for _ in range(5):
        assert limiter.allow_request(user_id=1) is True

    assert limiter.allow_request(user_id=1) is False


def test_rate_limiter_allows_requests_after_window_expires() -> None:
    clock = ManualClock(now=100.0)
    limiter = InMemoryRateLimiter(limit=5, window_seconds=60.0, clock=clock)

    for _ in range(5):
        assert limiter.allow_request(user_id=1) is True

    assert limiter.allow_request(user_id=1) is False
    clock.advance(61.0)
    assert limiter.allow_request(user_id=1) is True
