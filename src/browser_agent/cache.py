"""
Page State Cache

Simple TTL cache for page state queries to reduce redundant calls
within the agent loop.

Usage:
    from browser_agent.cache import page_state_cache

    # Get or compute accessibility tree
    tree = await page_state_cache.get_or_set(
        key="accessibility_tree",
        compute_fn=lambda: get_accessibility_tree(page),
        ttl_seconds=2.0  # Short TTL for dynamic content
    )

    # Invalidate on action
    page_state_cache.invalidate()
"""

import asyncio
import time
from typing import Any, Callable, Awaitable, Optional


class PageStateCache:
    """
    Simple TTL cache for page state queries.

    Features:
    - Time-based expiration (configurable TTL)
    - Manual invalidation (for after actions)
    - Automatic cleanup of expired entries
    - Async-safe operations
    """

    def __init__(self, default_ttl: float = 2.0):
        """
        Initialize cache with default TTL.

        Args:
            default_ttl: Default time-to-live in seconds (default: 2.0)
        """
        self._cache: dict[str, tuple[Any, float]] = {}
        self._default_ttl = default_ttl
        self._lock = asyncio.Lock()

    def _is_expired(self, expiry_time: float) -> bool:
        """Check if a cached entry has expired."""
        return time.time() > expiry_time

    def _cleanup_expired(self) -> None:
        """Remove expired entries from cache."""
        current_time = time.time()
        expired_keys = [
            key for key, (_, expiry) in self._cache.items()
            if current_time > expiry
        ]
        for key in expired_keys:
            del self._cache[key]

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache if not expired.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        if key not in self._cache:
            return None

        value, expiry_time = self._cache[key]
        if self._is_expired(expiry_time):
            del self._cache[key]
            return None

        return value

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """
        Set value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if not specified)
        """
        ttl = ttl if ttl is not None else self._default_ttl
        expiry_time = time.time() + ttl
        self._cache[key] = (value, expiry_time)

    async def get_or_set(
        self,
        key: str,
        compute_fn: Callable[[], Awaitable[Any]],
        ttl: Optional[float] = None,
    ) -> Any:
        """
        Get value from cache or compute and cache it.

        Thread-safe operation using async lock.

        Args:
            key: Cache key
            compute_fn: Async function to compute value if not cached
            ttl: Time-to-live in seconds (uses default if not specified)

        Returns:
            Cached or computed value
        """
        async with self._lock:
            # Check cache first
            value = self.get(key)
            if value is not None:
                return value

            # Compute and cache
            value = await compute_fn()
            self.set(key, value, ttl)
            return value

    def invalidate(self, key: Optional[str] = None) -> None:
        """
        Invalidate cache entries.

        Args:
            key: Specific key to invalidate (invalidates all if None)
        """
        if key is None:
            self._cache.clear()
        elif key in self._cache:
            del self._cache[key]

    def stats(self) -> dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache stats (size, keys)
        """
        self._cleanup_expired()
        return {
            "size": len(self._cache),
            "keys": list(self._cache.keys()),
        }


# Global instance for page state caching
page_state_cache = PageStateCache(default_ttl=2.0)
