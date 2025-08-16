"""
Application-level caching utilities for database entities.

Provides an asyncio-safe LRU cache with TTL and basic metrics, plus
helpers specialized for caching `ChatDocument` by ID.
"""

import asyncio
import time
from typing import Any, Dict, Optional, Tuple
from dataclasses import dataclass
from collections import OrderedDict


@dataclass
class CacheStats:
    hits: int
    misses: int
    size: int
    capacity: int
    evictions: int


class LRUCache:
    """
    Simple asyncio-safe LRU cache with TTL per entry.

    - Uses OrderedDict for O(1) LRU ops
    - TTL eviction on get/set
    - Tracks hits/misses/evictions
    """

    def __init__(self, capacity: int = 1024, ttl_seconds: int = 3600) -> None:
        self._capacity = capacity
        self._ttl = ttl_seconds
        self._lock = asyncio.Lock()
        self._store: "OrderedDict[str, Tuple[float, Any]]" = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    async def get(self, key: str) -> Optional[Any]:
        now = time.time()
        async with self._lock:
            item = self._store.get(key)
            if not item:
                self._misses += 1
                return None
            expires_at, value = item
            if expires_at < now:
                # expired
                del self._store[key]
                self._misses += 1
                return None
            # move to end (most recently used)
            self._store.move_to_end(key, last=True)
            self._hits += 1
            return value

    async def set(self, key: str, value: Any) -> None:
        now = time.time()
        expires_at = now + self._ttl
        async with self._lock:
            if key in self._store:
                # update existing
                self._store[key] = (expires_at, value)
                self._store.move_to_end(key, last=True)
            else:
                if len(self._store) >= self._capacity:
                    # evict LRU
                    self._store.popitem(last=False)
                    self._evictions += 1
                self._store[key] = (expires_at, value)

    async def delete(self, key: str) -> None:
        async with self._lock:
            if key in self._store:
                del self._store[key]

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()

    async def stats(self) -> CacheStats:
        async with self._lock:
            return CacheStats(
                hits=self._hits,
                misses=self._misses,
                size=len(self._store),
                capacity=self._capacity,
                evictions=self._evictions,
            )


class DocumentCache:
    """
    Specialization for caching ChatDocument by doc_id.

    The value is the ORM object as returned by SQLAlchemy session. Consumers
    should be careful to only cache by-id objects that can be safely reused
    within the same process. We invalidate aggressively on write operations.
    """

    def __init__(self, capacity: int = 5000, ttl_seconds: int = 3600) -> None:
        self._cache = LRUCache(capacity=capacity, ttl_seconds=ttl_seconds)

    @staticmethod
    def _key_doc(doc_id: str) -> str:
        return f"doc:{doc_id}"

    async def get_document(self, doc_id: str) -> Optional[Any]:
        return await self._cache.get(self._key_doc(doc_id))

    async def set_document(self, doc_id: str, document: Any) -> None:
        await self._cache.set(self._key_doc(doc_id), document)

    async def invalidate_document(self, doc_id: str) -> None:
        await self._cache.delete(self._key_doc(doc_id))

    async def clear_all(self) -> None:
        await self._cache.clear()

    async def get_stats(self) -> CacheStats:
        return await self._cache.stats()


