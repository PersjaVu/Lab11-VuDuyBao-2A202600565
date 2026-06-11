"""
Lab 11 / Assignment 11 — Layer 0: Rate Limiter

What it does:
    Per-user sliding-window rate limiting. Each user may send at most
    `max_requests` messages within any `window_seconds` window; extra
    requests are blocked with a message telling them how long to wait.

Why it is needed (what it catches that other layers don't):
    Every other layer inspects message CONTENT. None of them stops a user
    (or a script) from hammering the agent with hundreds of requests —
    brute-forcing guardrails, running up LLM costs, or denying service to
    others. The rate limiter is the cheapest layer, so it runs FIRST:
    a blocked request costs zero LLM calls.
"""
import time
from collections import defaultdict, deque

# ADK is optional so the module stays importable (and testable) without
# google-adk installed — same pattern as session_anomaly.py.
try:
    from google.genai import types
    from google.adk.plugins import base_plugin
    _BasePlugin = base_plugin.BasePlugin
    ADK_AVAILABLE = True
except ImportError:
    types = None
    ADK_AVAILABLE = False

    class _BasePlugin:
        """Minimal stand-in so the plugin class can exist without google-adk."""
        def __init__(self, name=""):
            self.name = name


class RateLimitPlugin(_BasePlugin):
    """Plugin that blocks users who send too many requests in a time window.

    Sliding-window algorithm: keep a deque of request timestamps per user;
    on each request drop the timestamps older than `window_seconds`, then
    block if the deque is already at `max_requests`.
    """

    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        super().__init__(name="rate_limiter")
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.user_windows = defaultdict(deque)  # user_id -> deque of timestamps
        self.blocked_count = 0
        self.total_count = 0

    def check(self, user_id: str, now: float = None) -> dict:
        """Core sliding-window check (pure logic, testable without ADK).

        Returns:
            dict with 'blocked' (bool) and 'wait_seconds' (float, 0 if allowed)
        """
        self.total_count += 1
        if now is None:
            now = time.time()
        window = self.user_windows[user_id]

        # 1. Remove expired timestamps from the front of the deque
        while window and window[0] <= now - self.window_seconds:
            window.popleft()

        # 2. Window full -> block and tell the user how long to wait
        if len(window) >= self.max_requests:
            self.blocked_count += 1
            wait = window[0] + self.window_seconds - now
            return {"blocked": True, "wait_seconds": max(wait, 0.0)}

        # 3. Allowed -> record this request
        window.append(now)
        return {"blocked": False, "wait_seconds": 0.0}

    async def on_user_message_callback(self, *, invocation_context, user_message):
        """Block the message before it reaches the LLM if the user is over quota."""
        user_id = getattr(invocation_context, "user_id", "anonymous") or "anonymous"
        verdict = self.check(user_id)

        if verdict["blocked"]:
            return types.Content(
                role="model",
                parts=[types.Part.from_text(text=(
                    f"You are sending requests too quickly. Please wait "
                    f"{verdict['wait_seconds']:.0f} seconds and try again."
                ))],
            )
        return None  # under the limit -> let the message through


# ============================================================
# Quick tests — Test 3 from the assignment:
# 15 rapid requests; expected: first 10 pass, last 5 blocked.
# ============================================================

def test_rate_limiter():
    """Send 15 rapid requests from the same user; first 10 pass, last 5 blocked."""
    limiter = RateLimitPlugin(max_requests=10, window_seconds=60)

    print("Testing RateLimitPlugin (15 rapid requests, limit 10/60s):")
    for i in range(1, 16):
        verdict = limiter.check("student")
        if verdict["blocked"]:
            print(f"  Request {i:2}: BLOCKED (wait {verdict['wait_seconds']:.0f}s)")
        else:
            print(f"  Request {i:2}: PASSED")

    print(f"\nStats: {limiter.blocked_count} blocked / {limiter.total_count} total")

    # A different user must NOT be affected by the first user's quota
    verdict = limiter.check("another_user")
    print(f"Different user: {'BLOCKED' if verdict['blocked'] else 'PASSED'} "
          f"(per-user isolation works)")


if __name__ == "__main__":
    test_rate_limiter()
