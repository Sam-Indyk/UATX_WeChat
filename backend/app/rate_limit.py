"""In-memory sliding-window rate limiter, keyed by user id.

Used by send_message to stop a single user from flooding messages —
button-mashing, accidental double-submits, or a malicious script. The
limiter lives in-process so it's per-Railway-container; on container
restart the counts reset, which is acceptable (the goal is UX, not
security).

We deliberately do NOT use IP keying because UATX students share dorm
networks; one bad actor would punish everyone else on the same NAT.
User-id keying is per-account and survives proxy hops.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock


# 30 messages per 60 seconds per user. One every two seconds sustained —
# generous for any real conversation, tight enough to choke a bot.
MESSAGE_RATE_LIMIT = 30
MESSAGE_RATE_WINDOW_SECONDS = 60


_history: dict[str, deque[float]] = defaultdict(deque)
_lock = Lock()


def check_message_rate(user_id: str) -> tuple[bool, int]:
    """Returns (allowed, retry_after_seconds). Records the attempt on
    success. retry_after is 0 when allowed.
    """
    now = time.monotonic()
    cutoff = now - MESSAGE_RATE_WINDOW_SECONDS
    with _lock:
        history = _history[user_id]
        # Trim entries that have fallen out of the window.
        while history and history[0] < cutoff:
            history.popleft()
        if len(history) >= MESSAGE_RATE_LIMIT:
            oldest = history[0]
            retry_after = max(1, int(MESSAGE_RATE_WINDOW_SECONDS - (now - oldest)) + 1)
            return False, retry_after
        history.append(now)
        return True, 0


def reset_for_tests() -> None:
    """Clear the in-memory state. Call from the per-test fixture so the
    rate-limit counter doesn't leak between tests."""
    with _lock:
        _history.clear()
