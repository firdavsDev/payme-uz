"""Retry policy for transport failures.

Retries are opt-in per call, never global: replaying a request that may have
already moved money is worse than surfacing the error. Only calls the API
layer marks as safe are retried, and only for connection failures - a timeout
can mean the server processed the request and the answer was lost.
"""

from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field

from aiohttp import ClientConnectionError


@dataclass(frozen=True)
class RetryPolicy:
    """Exponential backoff with jitter, bounded by ``attempts``."""

    attempts: int = 3
    base_delay: float = 0.5
    max_delay: float = 8.0
    jitter: float = 0.25
    retry_on: tuple[type[BaseException], ...] = field(default=(ClientConnectionError,))

    def should_retry(self, exc: BaseException, attempt: int) -> bool:
        """True when ``exc`` is retryable and attempts remain."""
        return attempt < self.attempts and isinstance(exc, self.retry_on)

    def delay_for(self, attempt: int) -> float:
        """Backoff before retry number ``attempt`` (1-based), with jitter.

        Jitter spreads retries out so a fleet of workers recovering from the
        same blip does not hit Payme in lockstep.
        """
        delay = min(self.base_delay * (2 ** (attempt - 1)), self.max_delay)
        spread = delay * self.jitter
        return max(0.0, delay + random.uniform(-spread, spread))

    async def sleep(self, attempt: int) -> None:
        await asyncio.sleep(self.delay_for(attempt))


#: Default for calls that move money; a failure is reported, never replayed.
NO_RETRY = RetryPolicy(attempts=1)
