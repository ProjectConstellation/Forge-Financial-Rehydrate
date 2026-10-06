"""In-process async event bus with bounded queues (no unbounded memory, DOSSIER §53).

- Every subscriber gets its own bounded queue.
- `lossy` subscribers (e.g. dashboard, feature recomputation on BBO) drop the oldest event when full
  and count drops; non-lossy subscribers apply backpressure (publisher awaits).
- Critical topics are never published lossy-only.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from collections import defaultdict
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from forge.core.clock import SYSTEM_CLOCK, Clock

log = logging.getLogger("forge.bus")


class Topic(StrEnum):
    MARKET_TICK = "MARKET_TICK"
    ORDER_BOOK_UPDATE = "ORDER_BOOK_UPDATE"
    CANDLE_CLOSED = "CANDLE_CLOSED"
    FEATURE_UPDATE = "FEATURE_UPDATE"
    REGIME_CHANGED = "REGIME_CHANGED"
    DATA_QUALITY = "DATA_QUALITY"
    OPPORTUNITY_FOUND = "OPPORTUNITY_FOUND"
    OPPORTUNITY_EXPIRED = "OPPORTUNITY_EXPIRED"
    STRATEGY_SIGNAL = "STRATEGY_SIGNAL"
    RISK_APPROVED = "RISK_APPROVED"
    RISK_REJECTED = "RISK_REJECTED"
    ORDER_SUBMITTED = "ORDER_SUBMITTED"
    ORDER_FILLED = "ORDER_FILLED"
    ORDER_CANCELLED = "ORDER_CANCELLED"
    POSITION_OPENED = "POSITION_OPENED"
    POSITION_CLOSED = "POSITION_CLOSED"
    STRATEGY_UNDERPERFORMING = "STRATEGY_UNDERPERFORMING"
    STRATEGY_RETIRED = "STRATEGY_RETIRED"
    CHALLENGER_CREATED = "CHALLENGER_CREATED"
    CHALLENGER_PROMOTED = "CHALLENGER_PROMOTED"
    MODAL_JOB_STARTED = "MODAL_JOB_STARTED"
    MODAL_JOB_COMPLETED = "MODAL_JOB_COMPLETED"
    DEEPSEEK_CALL = "DEEPSEEK_CALL"
    COMPUTE_BUDGET_WARNING = "COMPUTE_BUDGET_WARNING"
    EMERGENCY_STOP = "EMERGENCY_STOP"
    TIMELINE = "TIMELINE"            # plain-English narrative events for the dashboard
    AGENT_STATUS = "AGENT_STATUS"
    ALERT = "ALERT"


@dataclass(slots=True)
class Event:
    topic: Topic
    data: dict[str, Any]
    ts_ns: int = 0
    source: str = ""


Handler = Callable[[Event], Awaitable[None]]


@dataclass
class _Sub:
    name: str
    queue: asyncio.Queue[Event]
    lossy: bool
    dropped: int = 0
    task: asyncio.Task[None] | None = None
    errors: int = 0


@dataclass
class BusStats:
    published: dict[str, int] = field(default_factory=lambda: defaultdict(int))


class EventBus:
    def __init__(self, clock: Clock = SYSTEM_CLOCK) -> None:
        self._clock = clock
        self._subs: dict[Topic, list[_Sub]] = defaultdict(list)
        self._all: list[_Sub] = []
        self.stats = BusStats()
        self._closed = False

    def subscribe(self, topics: list[Topic] | None, handler: Handler, *, name: str,
                  maxsize: int = 1000, lossy: bool = False) -> None:
        """Subscribe `handler` to topics (None = all topics). Starts a consumer task."""
        sub = _Sub(name=name, queue=asyncio.Queue(maxsize=maxsize), lossy=lossy)
        sub.task = asyncio.get_event_loop().create_task(self._consume(sub, handler), name=f"bus:{name}")
        if topics is None:
            self._all.append(sub)
        else:
            for t in topics:
                self._subs[t].append(sub)

    async def _consume(self, sub: _Sub, handler: Handler) -> None:
        while True:
            ev = await sub.queue.get()
            try:
                await handler(ev)
            except asyncio.CancelledError:
                raise
            except Exception:  # a broken subscriber must never kill the bus
                sub.errors += 1
                log.exception("bus subscriber %s failed on %s", sub.name, ev.topic)
            finally:
                sub.queue.task_done()

    async def publish(self, topic: Topic, data: dict[str, Any], source: str = "") -> None:
        if self._closed:
            return
        ev = Event(topic=topic, data=data, ts_ns=self._clock.now_ns(), source=source)
        self.stats.published[topic] += 1
        for sub in (*self._subs.get(topic, ()), *self._all):
            if sub.lossy:
                if sub.queue.full():
                    with contextlib.suppress(asyncio.QueueEmpty):
                        sub.queue.get_nowait()
                        sub.queue.task_done()
                    sub.dropped += 1
                sub.queue.put_nowait(ev)
            else:
                await sub.queue.put(ev)

    async def drain(self) -> None:
        """Wait until every queue is empty (used by tests/simulation)."""
        subs = {id(s): s for lst in self._subs.values() for s in lst} | {id(s): s for s in self._all}
        for s in subs.values():
            await s.queue.join()

    def subscriber_stats(self) -> list[dict[str, Any]]:
        subs = {id(s): s for lst in self._subs.values() for s in lst} | {id(s): s for s in self._all}
        return [{"name": s.name, "depth": s.queue.qsize(), "dropped": s.dropped, "errors": s.errors}
                for s in subs.values()]

    async def close(self) -> None:
        self._closed = True
        subs = {id(s): s for lst in self._subs.values() for s in lst} | {id(s): s for s in self._all}
        for s in subs.values():
            if s.task:
                s.task.cancel()
        for s in subs.values():
            if s.task:
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await s.task
