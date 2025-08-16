"""
Lightweight in-process metrics registry for application monitoring.

Provides simple counters and histograms with optional label support.
Designed to be JSON-serializable for quick export via API.
"""

import asyncio
from typing import Dict, Any, Tuple


class MetricsRegistry:
    _instance = None

    def __init__(self):
        self._counters: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], float] = {}
        self._histograms: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], Dict[str, float]] = {}
        self._lock = asyncio.Lock()

    @classmethod
    def instance(cls) -> "MetricsRegistry":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @staticmethod
    def _key(name: str, labels: Dict[str, Any]) -> Tuple[str, Tuple[Tuple[str, str], ...]]:
        items = tuple(sorted((str(k), str(v)) for k, v in (labels or {}).items()))
        return name, items

    async def inc(self, name: str, value: float = 1.0, labels: Dict[str, Any] = None) -> None:
        key = self._key(name, labels or {})
        async with self._lock:
            self._counters[key] = self._counters.get(key, 0.0) + value

    async def observe(self, name: str, observation: float, labels: Dict[str, Any] = None) -> None:
        key = self._key(name, labels or {})
        async with self._lock:
            hist = self._histograms.get(key)
            if hist is None:
                hist = {"count": 0.0, "sum": 0.0, "min": observation, "max": observation}
                self._histograms[key] = hist
            hist["count"] += 1
            hist["sum"] += observation
            hist["min"] = observation if observation < hist["min"] else hist["min"]
            hist["max"] = observation if observation > hist["max"] else hist["max"]

    async def export(self) -> Dict[str, Any]:
        # Build serializable snapshot
        async with self._lock:
            counters = []
            for (name, labels), value in self._counters.items():
                counters.append({"name": name, "labels": dict(labels), "value": value})
            histograms = []
            for (name, labels), hist in self._histograms.items():
                avg = hist["sum"] / hist["count"] if hist["count"] else 0.0
                histograms.append({
                    "name": name,
                    "labels": dict(labels),
                    "count": hist["count"],
                    "sum": hist["sum"],
                    "min": hist["min"],
                    "max": hist["max"],
                    "avg": avg,
                })
            return {"counters": counters, "histograms": histograms}


async def inc(name: str, value: float = 1.0, labels: Dict[str, Any] = None) -> None:
    await MetricsRegistry.instance().inc(name, value, labels)


async def observe(name: str, observation: float, labels: Dict[str, Any] = None) -> None:
    await MetricsRegistry.instance().observe(name, observation, labels)


async def get_metrics() -> Dict[str, Any]:
    return await MetricsRegistry.instance().export()


