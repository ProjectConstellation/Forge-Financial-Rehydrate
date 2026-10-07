"""One-tap Telegram pairing: binds only the private-chat sender of the exact nonce; token never exposed; 0600 provision."""
import asyncio
import json
import os
import stat
import types

import httpx

from forge.ops import telegram_setup as ts

TOKEN = "8123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsawZ"


def test_pairing_binds_only_exact_private_nonce(db, tmp_path, monkeypatch):
    (tmp_path / "run").mkdir()
    sent = []
    state = {"nonce": None, "served": False}

    def handler(req: httpx.Request) -> httpx.Response:
        path = req.url.path
        if path.endswith("/getMe"):
            return httpx.Response(200, json={"ok": True, "result": {"username": "forge_exec_test_bot"}})
        if path.endswith("/getUpdates"):
            if state["served"] or state["nonce"] is None:
                return httpx.Response(200, json={"ok": True, "result": []})
            state["served"] = True
            n = state["nonce"]
            return httpx.Response(200, json={"ok": True, "result": [
                {"update_id": 1, "message": {"chat": {"type": "group"}, "from": {"id": 666}, "text": f"/start {n}"}},
                {"update_id": 2, "message": {"chat": {"type": "private"}, "from": {"id": 777}, "text": "/start wrong"}},
                {"update_id": 3, "message": {"chat": {"type": "private"}, "from": {"id": 888}, "text": "/start"}},
                {"update_id": 4, "message": {"chat": {"type": "private"}, "from": {"id": 424242, "first_name": "Owner"},
                                             "text": f"/start {n}"}}]})
        if path.endswith("/sendMessage"):
            sent.append(req.content)
        return httpx.Response(200, json={"ok": True, "result": True})

    real = httpx.AsyncClient
    monkeypatch.setattr(ts.httpx, "AsyncClient", lambda **kw: real(transport=httpx.MockTransport(handler)))
    audit = types.SimpleNamespace(events=[], append=lambda k, d, actor=None: audit.events.append((k, d)))
    forge = types.SimpleNamespace(db=db, s=types.SimpleNamespace(home=tmp_path), audit=audit)
    p = ts.TelegramPairer(forge)

    async def run():
        st = await p.start(TOKEN)
        state["nonce"] = p._nonce
        assert TOKEN not in json.dumps(st) and st["deep_link"].startswith("https://t.me/forge_exec_test_bot?start=")
        await asyncio.wait_for(p._task, 10)
    asyncio.run(run())
    assert p.state["state"] == "connected" and TOKEN not in json.dumps(p.state)
    prov = tmp_path / "run" / "ops_provision.json"
    d = json.loads(prov.read_text())
    assert d == {"platform": "telegram", "token": TOKEN, "user_id": 424242}
    assert stat.S_IMODE(os.stat(prov).st_mode) == 0o600
    assert db.kv_get("ops.telegram")["owner_user_id"] == 424242 and TOKEN not in json.dumps(db.kv_get("ops.telegram"))
    assert all(TOKEN not in json.dumps(e) for e in audit.events) and len(sent) == 1


def test_rejects_malformed_token(db, tmp_path):
    p = ts.TelegramPairer(types.SimpleNamespace(db=db, s=types.SimpleNamespace(home=tmp_path), audit=None))
    try:
        asyncio.run(p.start("not-a-token"))
        raise AssertionError("should reject")
    except ValueError:
        pass
