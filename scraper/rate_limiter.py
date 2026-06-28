"""Rate limiting functionality using token bucket pattern."""

import asyncio
import time


class RateLimiter:
    """Token bucket rate limiter for async requests."""

    def __init__(self, rate: float):
        """
        Args:
            rate: Minimum seconds between requests
        """
        self.rate = rate
        self.last_request = 0
        self._lock = asyncio.Lock()

    async def acquire(self):
        """Wait until we can make another request."""
        async with self._lock:
            now = time.time()
            time_since_last = now - self.last_request

            if time_since_last < self.rate:
                sleep_time = self.rate - time_since_last
                await asyncio.sleep(sleep_time)

            self.last_request = time.time()
