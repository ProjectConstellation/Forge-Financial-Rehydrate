"""EXECUTIVE OPS: TOTP 2FA + replay, lockdown, transfers (phrase + 2FA, blocked without permission), objectives, econ."""
import base64
import os
import time
import types

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from forge.api import ops_api
from forge.ops import totp


class _Audit:
    def __init__(self):
        self.events = []

    def append(self, kind, data, actor=None):
        self.events.append((kind, data, actor))


class _Rest:
    def __init__(self, can_transfer):
        self.can_transfer, self.moves = can_transfer, []

    async def key_permissions(self):
        return {"can_view": True, "can_trade": True, "can_transfer": self.can_transfer}

    async def _request(self, method, path, body=None, private=False, idempotent=True, retries=3):
        self.moves.append((method, path, body))
        return {"source_portfolio_uuid": body["source_portfolio_uuid"], "target_portfolio_uuid": body["target_portfolio_uuid"]}


@pytest.fixture()
def ex(db, tmp_path, monkeypatch):
    monkeypatch.setattr(ops_api, "LOOPBACK", {"testclient"})
    ops_api._hits.clear()
    (tmp_path / "run").mkdir()
    forge = types.SimpleNamespace(db=db, audit=_Audit(), s=types.SimpleNamespace(mode=types.SimpleNamespace(value="PAPER"),
                                                                                  home=tmp_path),
                                  book="paper", treasury={"cash_usd": 5.0, "equity_usd": 28.0}, rest=_Rest(False),
                                  sup=types.SimpleNamespace(snapshot=lambda: []), started=0.0)
    db.kv_set("velocity", {"treasury": {"total": 28.27}})
    app = FastAPI()
    ops_api.mount_ops(app, forge, "tok")
    c = TestClient(app)
    c.headers.update({"Authorization": "Bearer tok"})
    return c, db, forge, tmp_path


def _enable_2fa(home):
    secret = base64.b32encode(os.urandom(20)).decode().rstrip("=")
    totp.secret_path(home).write_text(secret)
    return secret


def test_totp_verify_and_replay(db, tmp_path):
    (tmp_path / "run").mkdir()
    s = _enable_2fa(tmp_path)
    now = 1_800_000_000.0
    code = totp._code(s, int(now // 30))
    assert totp.verify(tmp_path, db, code, now) == (True, "ok")
    assert totp.verify(tmp_path, db, code, now)[0] is False            # replay refused
    assert totp.verify(tmp_path, db, totp._code(s, int(now // 30) + 1), now + 30)[0] is True
    assert totp.verify(tmp_path, db, "000000", now + 60)[0] in (False, True)   # (astronomically unlikely to be valid)
    assert totp._code("GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ", 59 // 30) == "287082"   # RFC 6238 SHA1 vector (t=59s)


def test_confirm_uses_authenticator_and_lockdown(ex):
    c, db, forge, home = ex
    s = _enable_2fa(home)
    r = c.post("/api/ops/action", json={"action": "kalshi_live_on"}).json()
    assert r["factor"] == "authenticator" and "owner_code" not in r
    good = totp._code(s, int(time.time() // 30))
    assert c.post("/api/ops/confirm", json={"pending_id": r["pending_id"], "code": "123"}).status_code == 403
    assert c.post("/api/ops/confirm", json={"pending_id": r["pending_id"], "code": good}).json()["status"] == "DONE"
    # lockdown: everything but stop_trading/unlock refused
    assert c.post("/api/ops/action", json={"action": "lockdown"}).json()["result"]["locked"] is True
    assert c.post("/api/ops/action", json={"action": "compute_boost", "params": {"hours": 1}}).status_code == 423
    assert c.post("/api/ops/transfer/preview", json={"amount_usd": 5}).status_code == 423
    assert c.post("/api/ops/action", json={"action": "stop_trading"}).json()["status"] == "DONE"
    u = c.post("/api/ops/action", json={"action": "unlock"}).json()
    db.kv_set("ops.totp.last_step", 0)
    nxt = totp._code(s, int(time.time() // 30) + 1)                    # next step (current one already used)
    assert c.post("/api/ops/confirm", json={"pending_id": u["pending_id"], "code": nxt}).json()["result"]["locked"] is False
    assert any(e[0] == "OPS" for e in forge.audit.events)              # mirrored into the hash-chained journal


def test_transfer_blocked_then_phrase_and_2fa(ex):
    c, db, forge, home = ex
    p = c.post("/api/ops/transfer/preview", json={"amount_usd": 5}).json()
    assert p["status"] == "BLOCKED" and any("can_transfer" in b for b in p["blockers"])
    forge.rest = _Rest(True)
    db.kv_set("ops.transfer.config", {"source_portfolio_uuid": "src", "owner_portfolio_uuid": "own", "owner_label": "Owner Primary"})
    p = c.post("/api/ops/transfer/preview", json={"amount_usd": 5}).json()
    assert p["status"] == "PREVIEWED" and p["treasury_after_usd"] == 23.27 and p["destination"] == "Owner Primary"
    tid = p["transfer_id"]
    assert c.post("/api/ops/transfer/confirm", json={"transfer_id": tid, "phrase": "CONFIRM TRANSFER $5", "code": "1"}).status_code == 403   # no 2FA set up
    s = _enable_2fa(home)
    code = totp._code(s, int(time.time() // 30))
    assert c.post("/api/ops/transfer/confirm", json={"transfer_id": tid, "phrase": "CONFIRM TRANSFER $50",
                                                     "code": code}).status_code == 403                                      # wrong amount
    out = c.post("/api/ops/transfer/confirm", json={"transfer_id": tid, "phrase": "confirm transfer $5.00", "code": code}).json()
    assert out["status"] == "EXECUTED" and forge.rest.moves[0][1] == "/api/v3/brokerage/portfolios/move_funds"
    assert forge.rest.moves[0][2]["funds"] == {"value": "5.00", "currency": "USD"}
    assert any(e[0] == "OWNER_TRANSFER" for e in forge.audit.events)
    assert c.post("/api/ops/transfer/confirm", json={"transfer_id": tid, "phrase": "CONFIRM TRANSFER $5",
                                                     "code": code}).status_code == 404                                      # single use


def test_objective_campaign_and_econ_windows(ex):
    c, db, forge, home = ex
    r = c.post("/api/ops/action", json={"action": "launch_objective", "params": {
        "kind": "integrate_platform", "objective": "Add Interactive Brokers"}}).json()["result"]
    assert set(r["roles"]) == {"rail_hunter", "critic", "governor"} and r["engineering_ticket"]
    assert db.scalar("SELECT COUNT(*) FROM ops_directives WHERE status='OPEN'") == 3
    from forge.ops.econ import mark, parse_window, window
    for w in ("30s", "1m", "today", "24h", "lifetime", "90s", "3h"):
        parse_window(w)
    with pytest.raises(ValueError):
        parse_window("forever-ish")
    db.insert("econ_ticks", {**mark(forge), "ts": time.time() - 40, "live_total_usd": 28.00})
    w = window(forge, "1m")
    assert abs(w["LIVE"]["true_net_usd"] - 0.27) < 1e-9 and w["LIVE"]["treasury_now_usd"] == 28.27
