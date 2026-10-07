import asyncio

from forge.core.supervisor import Supervisor


def test_restarts_crashed_and_stalled_loops(monkeypatch):
    async def run():
        sup = Supervisor()
        runs = {"crash": 0, "stall": 0}

        async def crashy():
            runs["crash"] += 1
            raise RuntimeError("boom")

        async def stally():
            runs["stall"] += 1
            await asyncio.sleep(3600)          # never beats

        sup.add("crash", crashy, 60)
        sup.add("stall", stally, 0.05)
        sup.start()
        stop = asyncio.Event()

        async def fast_sleep(t):                 # accelerate watch/backoff
            await asyncio.sleep(0)
        monkeypatch.setattr("forge.core.supervisor.asyncio.sleep", lambda t: fast_sleep(t) if t >= 1 else asyncio.tasks.sleep(t))
        await asyncio.tasks.sleep(0.1)
        w = asyncio.create_task(sup.watch(stop))
        await asyncio.tasks.sleep(0.5)
        stop.set()
        await asyncio.wait_for(w, timeout=5)
        snap = {s["loop"]: s for s in sup.snapshot()}
        assert runs["crash"] >= 2 and snap["crash"]["restarts"] >= 1
        assert runs["stall"] >= 2 and snap["stall"]["restarts"] >= 1
        for s in sup.loops.values():
            s.task.cancel()
    asyncio.run(run())
