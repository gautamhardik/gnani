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
import threading
from collections import defaultdict
from typing import Dict, List, Tuple
from fastapi import HTTPException, Request, status


class SlidingWindowRateLimiter:
    """
    Thread-safe sliding window rate limiter tracking request timestamps per client IP key.
    """

    def __init__(self):
        # Maps (key, action) -> list of timestamp floats
        self._requests: Dict[Tuple[str, str], List[float]] = defaultdict(list)
        self._lock = threading.Lock()

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

        with self._lock:
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
        with self._lock:
            self._requests.clear()


limiter = SlidingWindowRateLimiter()


def get_client_ip(request: Request) -> str:
    """
    Extracts the verified client IP.
    Only inspects X-Forwarded-For if the direct peer is a trusted reverse proxy
    (localhost, Docker bridge network, or testclient). Otherwise, strictly returns direct peer IP
    to prevent unverified IP spoofing and rate limit evasion.
    """
    peer_ip = request.client.host if request.client else "127.0.0.1"
    trusted_proxies = {"127.0.0.1", "::1", "localhost", "testclient"}

    if peer_ip in trusted_proxies or peer_ip.startswith("172.") or peer_ip.startswith("10."):
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            client_ip = forwarded.split(",")[0].strip()
            if client_ip:
                return client_ip

    return peer_ip


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

