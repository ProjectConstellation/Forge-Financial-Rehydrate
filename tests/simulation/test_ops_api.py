"""OPS COMMANDER API: auth (token + loopback), audit, rate limits, out-of-band confirmation, directives round trip."""
import types

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from forge.api import ops_api


class _Audit:
    def __init__(self):
        self.events = []

    def append(self, kind, data, actor=None):
        self.events.append((kind, data, actor))


@pytest.fixture()
def ops(db, monkeypatch):
    monkeypatch.setattr(ops_api, "LOOPBACK", {"127.0.0.1", "::1", "localhost", "testclient"})
    ops_api._hits.clear()
    forge = types.SimpleNamespace(db=db, audit=_Audit(), s=types.SimpleNamespace(mode=types.SimpleNamespace(value="PAPER")),
                                  book="paper", treasury={}, sup=types.SimpleNamespace(snapshot=lambda: []), started=0.0)
    app = FastAPI()
    ops_api.mount_ops(app, forge, "secret-ops-token")
    c = TestClient(app)
    c.headers.update({"Authorization": "Bearer secret-ops-token", "X-Ops-Actor": "test-owner"})
    return c, db, forge


def test_auth_required_and_loopback_only(ops, monkeypatch):
    c, db, _ = ops
    assert TestClient(c.app).get("/api/ops/status").status_code == 401
    bad = TestClient(c.app)
    bad.headers.update({"Authorization": "Bearer wrong"})
    assert bad.get("/api/ops/status").status_code == 401
    monkeypatch.setattr(ops_api, "LOOPBACK", {"127.0.0.1"})               # a non-loopback client is refused
    assert c.get("/api/ops/status").status_code == 401


def test_safe_action_executes_and_is_audited(ops):
    c, db, forge = ops
    r = c.post("/api/ops/action", json={"action": "stop_trading", "params": {"reason": "test"}}).json()
    assert r["status"] == "DONE" and db.kv_get("trading.state")["state"] == "STOPPED"
    assert forge.audit.events[-1][0] == "EMERGENCY_STOP"
    a = db.query("SELECT actor, action, outcome FROM ops_audit ORDER BY id DESC LIMIT 1")[0]
    assert a == {"actor": "test-owner", "action": "stop_trading", "outcome": "OK"}
    assert c.post("/api/ops/action", json={"action": "rm_rf", "params": {}}).status_code == 403


def test_confirm_flow_out_of_band_code(ops):
    c, db, _ = ops
    c.post("/api/ops/action", json={"action": "stop_trading"})
    r = c.post("/api/ops/action", json={"action": "resume_trading"}).json()
    assert r["status"] == "CONFIRMATION_REQUIRED" and len(r["owner_code"]) == 6
    pid, code = r["pending_id"], r["owner_code"]
    assert db.kv_get("trading.state")["state"] == "STOPPED"               # nothing happens before confirmation
    wrong = f"{(int(code) + 1) % 10**6:06d}"
    assert c.post("/api/ops/confirm", json={"pending_id": pid, "code": wrong}).status_code == 403
    ok = c.post("/api/ops/confirm", json={"pending_id": pid, "code": code}).json()
    assert ok["status"] == "DONE" and db.kv_get("trading.state")["state"] == "RUNNING"
    assert c.post("/api/ops/confirm", json={"pending_id": pid, "code": code}).status_code == 404   # single use
    # three wrong attempts lock the pending action
    r = c.post("/api/ops/action", json={"action": "kalshi_live_on"}).json()
    for _ in range(3):
        c.post("/api/ops/confirm", json={"pending_id": r["pending_id"], "code": "000000" if r["owner_code"] != "000000" else "1"})
    assert c.post("/api/ops/confirm", json={"pending_id": r["pending_id"], "code": r["owner_code"]}).status_code == 410


def test_rate_limit(ops, monkeypatch):
    c, _, _ = ops
    monkeypatch.setitem(ops_api.RATE, "write", (2, 600.0))
    codes = [c.post("/api/ops/action", json={"action": "kalshi_live_off"}).status_code for _ in range(3)]
    assert codes == [200, 200, 429]


def test_directive_reaches_brief_and_report_closes_it(ops):
    c, db, forge = ops
    d = c.post("/api/ops/directive", json={"role": "alpha_inventor", "instruction": "Investigate KXBTC15M final-minute edge",
                                           "priority": "high"}).json()
    assert d["status"] == "OPEN"
    assert c.post("/api/ops/directive", json={"role": "ceo", "instruction": "x"}).status_code == 400
    from forge.agents.genome import PromptGenomes
    pg = PromptGenomes(types.SimpleNamespace(db=db, treasury={}, s=forge.s, book="paper"))
    assert [x["id"] for x in pg.directives_for("alpha_inventor")] == [d["id"]]
    assert pg.directives_for("critic") == []
    pg.submit_report("alpha_inventor", "sess-1", {"status": "ACTED", "directives": [
        {"id": d["id"], "status": "DONE", "result": "edge exists in final 90 s; candidate submitted"}]})
    row = db.query_one("SELECT status, result FROM ops_directives WHERE id = ?", (d["id"],))
    assert row["status"] == "DONE" and "final 90 s" in row["result"]
    # a different role cannot close someone else's directive
    d2 = c.post("/api/ops/directive", json={"role": "doctor", "instruction": "check feed"}).json()
    pg.submit_report("critic", "sess-2", {"directives": [{"id": d2["id"], "status": "DONE"}]})
    assert db.scalar("SELECT status FROM ops_directives WHERE id = ?", (d2["id"],)) == "OPEN"


def test_read_tool_whitelist(ops):
    c, _, _ = ops
    assert c.post("/api/ops/tool", json={"name": "submit_strategy_candidates", "args": {}}).status_code == 403
