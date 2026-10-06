"""UTC-only time. A replaceable clock lets replay/backtests run deterministically."""

from __future__ import annotations

import time
from datetime import UTC, datetime


class Clock:
    def now_ns(self) -> int:
        return time.time_ns()

    def now(self) -> datetime:
        return datetime.fromtimestamp(self.now_ns() / 1e9, tz=UTC)

    def monotonic(self) -> float:
        return time.monotonic()


class ManualClock(Clock):
    """Deterministic clock for tests and replay."""

    def __init__(self, start_ns: int = 1_791_300_000_000_000_000) -> None:
        self._ns = start_ns
        self._mono = 0.0

    def now_ns(self) -> int:
        return self._ns

    def monotonic(self) -> float:
        return self._mono

    def set_ns(self, ns: int) -> None:
        if ns < self._ns:
            raise ValueError("ManualClock cannot go backwards")
        self._mono += (ns - self._ns) / 1e9
        self._ns = ns

    def advance(self, seconds: float) -> None:
        self.set_ns(self._ns + int(seconds * 1e9))


SYSTEM_CLOCK = Clock()


def utcnow() -> datetime:
    return datetime.now(UTC)


def iso(ts_ns: int | None = None) -> str:
    ns = ts_ns if ts_ns is not None else time.time_ns()
    return datetime.fromtimestamp(ns / 1e9, tz=UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
