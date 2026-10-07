"""Liveness supervisor (24/7 requirement): heartbeats, automatic restart of crashed/stalled loops, systemd watchdog.

- Every loop is a *factory* run under supervision; if it raises or exits it is restarted with backoff.
- Every loop beats; a loop silent beyond its limit is cancelled and restarted.
- The systemd watchdog (WatchdogSec) is fed only while all CRITICAL loops are healthy, so a frozen event loop or a stuck
  critical loop makes systemd kill and restart the whole service (Restart=always).
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import socket
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

log = logging.getLogger("forge.supervisor")


def sd_notify(msg: str) -> None:
    addr = os.environ.get("NOTIFY_SOCKET")
    if not addr:
        return
    if addr.startswith("@"):
        addr = "\0" + addr[1:]
    with contextlib.suppress(OSError), socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as s:
        s.connect(addr)
        s.sendall(msg.encode())


@dataclass
class Supervised:
    name: str
    factory: Callable[[], Awaitable[None]]
    max_silence_s: float
    critical: bool = False
    task: asyncio.Task[None] | None = None
    last_beat: float = field(default_factory=time.time)
    restarts: int = 0
    last_error: str = ""


class Supervisor:
    def __init__(self) -> None:
        self.loops: dict[str, Supervised] = {}
        self.on_restart: Callable[[str, str], Awaitable[None]] | None = None

    def beat(self, name: str) -> None:
        s = self.loops.get(name)
        if s:
            s.last_beat = time.time()

    def add(self, name: str, factory: Callable[[], Awaitable[None]], max_silence_s: float, critical: bool = False) -> None:
        self.loops[name] = Supervised(name, factory, max_silence_s, critical)

    def _spawn(self, s: Supervised) -> None:
        async def runner() -> None:
            try:
                await s.factory()
            except asyncio.CancelledError:
                raise
            except Exception as e:
                s.last_error = f"{type(e).__name__}: {str(e)[:200]}"
                log.exception("loop %s crashed", s.name)
        s.last_beat = time.time()
        s.task = asyncio.create_task(runner(), name=f"loop:{s.name}")

    def start(self) -> list[asyncio.Task[None]]:
        for s in self.loops.values():
            self._spawn(s)
        return [s.task for s in self.loops.values() if s.task]

    async def _restart(self, s: Supervised, why: str) -> None:
        if s.task and not s.task.done():
            s.task.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await asyncio.wait_for(s.task, timeout=10)
        s.restarts += 1
        await asyncio.sleep(min(30, 2 ** min(s.restarts, 5)))
        self._spawn(s)
        if self.on_restart:
            with contextlib.suppress(Exception):
                await self.on_restart(s.name, why)

    async def watch(self, stop: asyncio.Event) -> None:
        sd_notify("READY=1")
        while not stop.is_set():
            now = time.time()
            healthy = True
            for s in list(self.loops.values()):
                if s.task is None:
                    continue
                if s.task.done():
                    healthy = healthy and not s.critical
                    await self._restart(s, f"exited ({s.last_error or 'no error'})")
                elif now - s.last_beat > s.max_silence_s:
                    healthy = healthy and not s.critical
                    await self._restart(s, f"stalled {now - s.last_beat:.0f}s > {s.max_silence_s:.0f}s")
            if healthy:
                sd_notify("WATCHDOG=1")
            await asyncio.sleep(15)

    def snapshot(self) -> list[dict[str, object]]:
        now = time.time()
        return [{"loop": s.name, "alive": bool(s.task and not s.task.done()), "silent_s": round(now - s.last_beat),
                 "limit_s": s.max_silence_s, "restarts": s.restarts, "critical": s.critical, "last_error": s.last_error}
                for s in self.loops.values()]
