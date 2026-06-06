from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field


@dataclass
class MetricsRecorder:
    """Small in-process metrics hook that can be replaced by Prometheus clients later."""

    counters: Counter[str] = field(default_factory=Counter)

    def increment(self, name: str, amount: int = 1) -> None:
        self.counters[name] += amount
