"""Agent API: token scope, loopback-only, tool proxy attribution, usage costing, budget gate."""
import types

from fastapi import FastAPI
from fastapi.testclient import TestClient

from forge.api.agent_api import mount


class FakeBrain:
    balance, tier = 2.0, "NORMAL"
    c = types.SimpleNamespace(cost=lambda model, u: (u["prompt_tokens"] * 0.3 + u["completion_tokens"] * 1.2) / 1e6)

    def pace(self):
        return types.SimpleNamespace(budget_24h=0.60, reason="test")

    def roi(self, role):
        return 2.0


def _app(db):
    from decimal import Decimal  # noqa: F401
    led = types.SimpleNamespace(record_opex=lambda *a, **k: True)
    f = types.SimpleNamespace(db=db, brain=FakeBrain(), ledger=led, book="paper", treasury={"equity_usd": 28.0},
                              s=types.SimpleNamespace(deepseek=types.SimpleNamespace(prices={"deepseek-flash": 1})),
                              reg=types.SimpleNamespace(counts=lambda: {}))
    app = FastAPI()
    mount(app, f, "tok")
    return TestClient(app)


def test_agent_api_scope_and_accounting(db):
    c = _app(db)
    assert c.get("/api/agent/tools").status_code == 401                      # token required
    h = {"Authorization": "Bearer tok"}
    assert any(t["function"]["name"] == "get_opportunity_surface" for t in c.get("/api/agent/tools", headers=h).json()["tools"])
    r = c.post("/api/agent/tool", headers=h, json={"name": "submit_research_lead", "role": "scout", "session_id": "s1",
                                                   "args": {"title": "t", "body": "b", "category": "rail"}}).json()
    assert r["lead_id"].startswith("lead")
    assert db.scalar("SELECT role FROM intel_artifacts WHERE kind='lead'") == "hermes_scout"
    u = c.post("/api/agent/usage", headers=h, json={"api_request_id": "r1", "role": "scout", "model": "deepseek-flash",
                                                    "usage": {"prompt_tokens": 100000, "completion_tokens": 10000}}).json()
    assert abs(u["cost_usd"] - 0.042) < 1e-9
    assert c.post("/api/agent/usage", headers=h, json={"api_request_id": "r1", "usage": {}}).json()["duplicate"]
    a = c.get("/api/agent/allow", headers=h, params={"role": "scout", "est_usd": 0.01}).json()
    assert a["wake"] and abs(a["spent_24h"] - 0.042) < 1e-9 and a["budget_24h"] > 0
    big = c.get("/api/agent/allow", headers=h, params={"est_usd": 5.0}).json()
    assert not big["wake"]                                                   # cannot exceed its slice of the pace
