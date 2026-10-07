import asyncio
import json

import httpx

from forge.brain.systemone import JevRouterFailover


def test_jev_failover_parses_and_trips_circuit():
    ok = {"n": 0}
    def handler(req):
        ok["n"] += 1
        if ok["n"] == 1:
            return httpx.Response(200, json={"model": "deepseek/deepseek-v4.1-flash", "usage": {"cost": 0.001},
                                             "choices": [{"message": {"content": json.dumps({"market_view": "quiet", "escalate": False})}}]})
        return httpx.Response(502, json={"error": "upstream"})
    fo = JevRouterFailover("k", transport=httpx.MockTransport(handler))
    async def run():
        r = await fo.chat_json("s", "u")
        assert r["json"]["market_view"] == "quiet" and r["cost_usd"] == 0.001
        for _ in range(3):
            try:
                await fo.chat_json("s", "u")
            except Exception:
                pass
        assert fo.circuit.state == "OPEN"
    asyncio.run(run())
