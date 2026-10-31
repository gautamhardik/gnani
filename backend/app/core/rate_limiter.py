"""
DukaanSaathi — API Rate Limiter & Abuse Prevention (Phase 9)
Provides sliding-window in-memory request rate limiting for sensitive endpoints
(merchant login, customer voice turns, session creation).

NOTE ON MULTI-INSTANCE ARCHITECTURE:
This in-memory rate limiter protects a single FastAPI instance. In multi-instance
production deployments behind a reverse proxy or load balancer, distributed rate
limiting must be enforced via edge controls (Cloudflare WAF / NGINX limit_req)
or a shared Redis-backed token bucket to prevent fragmented quota guarantees.
"""

import time
from collections import defaultdict
from typing import Dict, List, Tuple
from fastapi import HTTPException, Request, status


class SlidingWindowRateLimiter:
    """
    Sliding window rate limiter tracking request timestamps per client IP key.
    """

    def __init__(self):
        # Maps (key, action) -> list of timestamp floats
        self._requests: Dict[Tuple[str, str], List[float]] = defaultdict(list)

    def check_rate_limit(
        self,
        key: str,
        action: str,
        max_requests: int,
        window_seconds: int = 60
    ) -> Tuple[bool, int, int]:
        """
        Records an attempt and checks if the key has exceeded max_requests within window_seconds.
        Returns:
            (is_allowed, remaining_requests, retry_after_seconds)
        """
        now = time.time()
        window_start = now - window_seconds
        cache_key = (key, action)

        # Filter out timestamps outside the active sliding window
        valid_timestamps = [t for t in self._requests[cache_key] if t > window_start]
        self._requests[cache_key] = valid_timestamps

        if len(valid_timestamps) >= max_requests:
            oldest = valid_timestamps[0]
            retry_after = max(1, int(oldest + window_seconds - now))
            return False, 0, retry_after

        # Record this request
        self._requests[cache_key].append(now)
        remaining = max_requests - len(self._requests[cache_key])
        return True, remaining, 0

    def reset(self):
        """Clears all tracked rate-limiting state (useful for tests)."""
        self._requests.clear()


limiter = SlidingWindowRateLimiter()


def get_client_ip(request: Request) -> str:
    """
    Extracts the client IP from X-Forwarded-For (if behind trusted proxy) or client.host.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # Take the first (client) IP in the chain
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


def enforce_rate_limit(
    action: str,
    max_requests: int,
    window_seconds: int = 60
):
    """
    FastAPI dependency factory enforcing rate limits on endpoints.
    """
    def dependency(request: Request):
        client_ip = get_client_ip(request)
        allowed, remaining, retry_after = limiter.check_rate_limit(
            key=client_ip,
            action=action,
            max_requests=max_requests,
            window_seconds=window_seconds
        )
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for {action}. Please try again in {retry_after} seconds.",
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": "0",
                }
            )
        return True

    return dependency

