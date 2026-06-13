"""Retry wrapper with exponential backoff + jitter.

Heavy multi-turn reasoning calls (especially reasoning models) can time out or
hit transient rate limits. We retry a few times; if it still fails the caller
degrades that single turn rather than killing the whole debate.
"""
from __future__ import annotations

import random
import time
from typing import Callable, TypeVar

T = TypeVar("T")


def call_with_retry(
    fn: Callable[[], T],
    *,
    attempts: int = 3,
    base_delay: float = 2.0,
    max_delay: float = 20.0,
) -> T:
    last: Exception | None = None
    for i in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - intentional broad retry
            last = exc
            if i == attempts:
                break
            delay = min(max_delay, base_delay * (2 ** (i - 1))) + random.uniform(0, 1.0)
            time.sleep(delay)
    assert last is not None
    raise last
