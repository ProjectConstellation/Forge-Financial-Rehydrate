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
    assert db.scalar("SELECT role FROM intel_artifacts WHERE kind='lead'") == "hermes_rail_hunter"   # scout → canonical role
    u = c.post("/api/agent/usage", headers=h, json={"api_request_id": "r1", "role": "scout", "model": "deepseek-flash",
                                                    "usage": {"prompt_tokens": 100000, "completion_tokens": 10000}}).json()
    assert abs(u["cost_usd"] - 0.042) < 1e-9
    assert c.post("/api/agent/usage", headers=h, json={"api_request_id": "r1", "usage": {}}).json()["duplicate"]
    a = c.get("/api/agent/allow", headers=h, params={"role": "scout", "est_usd": 0.01}).json()
    assert a["wake"] and abs(a["spent_24h"] - 0.042) < 1e-9 and a["budget_24h"] > 0
    big = c.get("/api/agent/allow", headers=h, params={"est_usd": 5.0}).json()
    assert not big["wake"]                                                   # cannot exceed its slice of the pace


def test_credit_mode_free_and_paced(db):
    import time as _t
    c = _app(db)
    h = {"Authorization": "Bearer tok"}
    db.kv_set("hermes.mode", {"mode": "credit", "credit_usd": 180, "hours": 72, "start": _t.time() - 3600})
    u = c.post("/api/agent/usage", headers=h, json={"api_request_id": "o1", "role": "scientist", "model": "claude-opus-5-5",
                                                    "usage": {"input_tokens": 10000, "output_tokens": 2000,
                                                              "cache_read_input_tokens": 50000}}).json()
    assert abs(u["cost_usd"] - (10000 * 5 + 50000 * 0.5 + 2000 * 25) / 1e6) < 1e-9     # list price, measured
    a = c.get("/api/agent/allow", headers=h, params={"role": "scientist", "est_usd": 0.5}).json()
    assert a["mode"] == "credit" and a["wake"] and a["hours_left"] > 70
    assert not c.get("/api/agent/allow", headers=h, params={"est_usd": 50}).json()["wake"]   # paced over the window


def test_tool_output_truncation_stays_valid_json():
    import json as _j

    from forge.brain.tools import _fit_json
    big = [{"id": i, "blob": "x" * 500} for i in range(500)]
    out = _j.loads(_fit_json(big, 30000))
    assert out["truncated"] and 0 < len(out["items"]) < 500 and out["total"] == 500
    assert _j.loads(_fit_json({"a": "y" * 50000}, 30000))["truncated"]
