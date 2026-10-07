"""Engineering Cell: engineer token scope, ticket lifecycle, owner approval for protected deploys, deployer policy."""
import importlib.util
import time
import types
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from forge.api import ops_api

DEPLOYER = Path(__file__).resolve().parents[2] / "scripts" / "forge_deployer.py"


@pytest.fixture()
def cell(db, tmp_path, monkeypatch):
    monkeypatch.setattr(ops_api, "LOOPBACK", {"testclient"})
    ops_api._hits.clear()
    audit = types.SimpleNamespace(append=lambda *a, **k: None)
    forge = types.SimpleNamespace(db=db, audit=audit, s=types.SimpleNamespace(mode=types.SimpleNamespace(value="PAPER"),
                                                                               home=tmp_path),
                                  book="paper", treasury={}, sup=types.SimpleNamespace(snapshot=lambda: []), started=0.0)
    app = FastAPI()
    ops_api.mount_ops(app, forge, "ops-tok", "eng-tok")
    ops, eng = TestClient(app), TestClient(app)
    ops.headers.update({"Authorization": "Bearer ops-tok"})
    eng.headers.update({"Authorization": "Bearer eng-tok"})
    return ops, eng, db


def test_engineer_scope_is_narrow(cell):
    ops, eng, db = cell
    for path in ("/api/ops/status", "/api/ops/audit", "/api/ops/capabilities", "/api/ops/econ"):
        assert eng.get(path).status_code == 403
    assert eng.post("/api/ops/action", json={"action": "stop_trading"}).status_code == 403
    assert eng.post("/api/ops/transfer/preview", json={"amount_usd": 1}).status_code == 403
    assert eng.get("/api/ops/eng/next").status_code == 200


def test_ticket_lifecycle_and_protected_approval(cell):
    ops, eng, db = cell
    t = ops.post("/api/ops/action", json={"action": "file_ticket", "params": {
        "title": "Upgrade SAGE-1 basis model", "spec": "…", "priority": "high"}}).json()["result"]
    assert t["status"] == "OPEN"
    nxt = eng.get("/api/ops/eng/next").json()["ticket"]
    assert nxt["id"] == t["ticket_id"]
    assert eng.post("/api/ops/eng/claim", json={"id": nxt["id"]}).json()["status"] == "IN_PROGRESS"
    assert eng.post("/api/ops/eng/update", json={"id": nxt["id"], "status": "SUBMITTED"}).status_code == 400   # needs sha
    sha = "a" * 40
    eng.post("/api/ops/eng/update", json={"id": nxt["id"], "status": "SUBMITTED", "commit_sha": sha, "note": "done"})
    q = ops.get("/api/ops/eng/queue").json()
    assert q[0]["commit_sha"] == sha and q[0]["deploy_status"] == "QUEUED"
    assert eng.get("/api/ops/eng/queue").status_code == 403                    # engineer can't see/drive the deployer
    ops.post("/api/ops/eng/deploy_result", json={"id": nxt["id"], "deploy_status": "AWAITING_OWNER", "deploy_class": "PROTECTED"})
    r = ops.post("/api/ops/action", json={"action": "approve_deploy", "params": {"ticket_id": nxt["id"]}}).json()
    assert r["status"] == "CONFIRMATION_REQUIRED"
    ok = ops.post("/api/ops/confirm", json={"pending_id": r["pending_id"], "code": r["owner_code"]}).json()
    assert ok["result"]["deploy_status"] == "APPROVED"
    ops.post("/api/ops/eng/deploy_result", json={"id": nxt["id"], "deploy_status": "DEPLOYED"})
    assert db.scalar("SELECT status FROM eng_tickets WHERE id = ?", (nxt["id"],)) == "DONE"
    assert eng.get("/api/ops/eng/next").json()["ticket"] is None


def test_platform_ticket_starts_on_hold(cell):
    ops, eng, db = cell
    r = ops.post("/api/ops/action", json={"action": "launch_objective", "params": {
        "kind": "integrate_platform", "objective": "Add Interactive Brokers"}}).json()["result"]
    assert eng.get("/api/ops/eng/next").json()["ticket"] is None                # held until research says go
    ops.post("/api/ops/action", json={"action": "release_ticket", "params": {"ticket_id": r["engineering_ticket"]}})
    t = eng.get("/api/ops/eng/next").json()["ticket"]
    assert t["id"] == r["engineering_ticket"]
    full = eng.get(f"/api/ops/eng/ticket?id={t['id']}").json()
    assert {d["role"] for d in full["objective"]["research"]} == {"rail_hunter", "critic", "governor"}


def test_deployer_policy():
    spec = importlib.util.spec_from_file_location("forge_deployer", DEPLOYER)
    d = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(d)
    assert d.classify(["src/forge/opportunities/settlement_window.py", "tests/x.py"], "x = 1") == ("STANDARD", [])
    cls, why = d.classify(["src/forge/risk/governor.py"], "x = 1")
    assert cls == "PROTECTED" and why == ["src/forge/risk/governor.py"]
    assert d.classify(["uv.lock"], "")[0] == "PROTECTED"
    assert d.classify(["src/forge/opportunities/kalshi_live.py"], "")[0] == "PROTECTED"
    for bad in ('open("/etc/forge/forge.env")', 'os.environ["COINBASE_CDP_API_KEY_SECRET"]', "os.system('ls')",
                "subprocess.run(cmd, shell=True)", "eval(code)", "await rest.move_funds()", "subprocess.run(['systemctl','stop'])"):
        assert d.classify(["src/forge/features/x.py"], bad)[0] == "REJECTED", bad
    _ = time.time()
