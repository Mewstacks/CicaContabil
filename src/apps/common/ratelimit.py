from __future__ import annotations

import time

from django.core.cache import cache


def rate_limited(key: str, *, limit: int, window_seconds: int) -> bool:
    """Count one hit against a fixed window and report whether the caller is over it.

    DRF's throttles only cover DRF views, so plain Django views that reach a database,
    an ODBC link or an outbound API need their own counter.
    """

    if limit <= 0:
        return False
    bucket = f"ratelimit:{key}:{int(time.monotonic()) // window_seconds}"
    try:
        hits = cache.incr(bucket)
    except ValueError:
        # A fresh window. add() loses a concurrent race harmlessly: the loser's hit is
        # counted by the incr below rather than dropped.
        cache.add(bucket, 0, window_seconds)
        hits = cache.incr(bucket)
    return bool(hits > limit)
