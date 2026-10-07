"""One-tap Telegram pairing for FORGE EXECUTIVE OPS (first-party; no third-party bot broker).

Flow (owner on the logged-in FORGE portal): paste the BotFather token → FORGE validates it with Telegram (getMe) → shows a
deep link t.me/<bot>?start=<128-bit nonce> → owner taps it and presses Start in Telegram → FORGE (polling getUpdates)
binds the FIRST private-chat `/start <nonce>` sender's numeric user ID → writes a 0600 provision file that a root-only
systemd path unit installs into the agent's sandboxed profile (token + user-ID allowlist + private-chat-only) and restarts
the agent. The token is never logged, returned or stored in the DB.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import secrets
import time
from pathlib import Path
from typing import Any

import httpx

TOKEN_RE = re.compile(r"^\d{6,12}:[A-Za-z0-9_-]{30,64}$")
PAIR_TIMEOUT_S = 900


class TelegramPairer:
    def __init__(self, forge: Any) -> None:
        self.f = forge
        self._token: str | None = None
        self._nonce: str | None = None
        self._task: asyncio.Task | None = None
        self.state: dict[str, Any] = {"state": "idle"}

    def _provision_path(self) -> Path:
        return Path(self.f.s.home) / "run" / "ops_provision.json"

    def connected(self) -> dict[str, Any] | None:
        return self.f.db.kv_get("ops.telegram")

    async def start(self, token: str) -> dict[str, Any]:
        token = token.strip()
        if not TOKEN_RE.match(token):
            raise ValueError("that doesn't look like a BotFather token (format 123456789:ABC…)")
        async with httpx.AsyncClient(timeout=15) as h:
            me = (await h.get(f"https://api.telegram.org/bot{token}/getMe")).json()
            if not me.get("ok"):
                raise ValueError("Telegram rejected this token — copy it again from BotFather")
            await h.get(f"https://api.telegram.org/bot{token}/deleteWebhook")
        if self._task and not self._task.done():
            self._task.cancel()
        self._token, self._nonce = token, secrets.token_hex(16)
        user = me["result"]["username"]
        self.state = {"state": "waiting", "bot_username": user, "since": time.time(),
                      "deep_link": f"https://t.me/{user}?start={self._nonce}"}
        self.f.audit.append("OPS_TELEGRAM_PAIRING_STARTED", {"bot": user}, actor="portal")
        self._task = asyncio.get_running_loop().create_task(self._wait())
        return self.state

    async def _wait(self) -> None:
        offset, end = 0, time.time() + PAIR_TIMEOUT_S
        try:
            async with httpx.AsyncClient(timeout=40) as h:
                while time.time() < end:
                    r = (await h.get(f"https://api.telegram.org/bot{self._token}/getUpdates",
                                     params={"timeout": 25, "offset": offset, "allowed_updates": json.dumps(["message"])})).json()
                    for u in r.get("result", []):
                        offset = max(offset, int(u["update_id"]) + 1)
                        m = u.get("message") or {}
                        if (m.get("chat") or {}).get("type") != "private":
                            continue
                        if str(m.get("text", "")).strip() != f"/start {self._nonce}":
                            continue
                        uid = int(m["from"]["id"])
                        await h.get(f"https://api.telegram.org/bot{self._token}/getUpdates", params={"offset": offset, "timeout": 0})
                        await h.post(f"https://api.telegram.org/bot{self._token}/sendMessage", data={
                            "chat_id": uid, "text": "✅ FORGE EXECUTIVE OPS is bound to your Telegram account (private chat "
                                                    "only). It comes online in ~20 seconds. Try: Debrief me."})
                        self._provision(uid, m["from"].get("first_name", ""))
                        return
            self.state = {"state": "expired", "note": "no Start received within 15 min — paste the token again"}
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001
            self.state = {"state": "error", "note": str(e)[:200].replace(self._token or "~", "[token]")}
        finally:
            if self.state.get("state") != "connected":
                self._token = None

    def _provision(self, uid: int, first_name: str) -> None:
        p = self._provision_path()
        tmp = p.with_suffix(".tmp")
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as fh:
            json.dump({"platform": "telegram", "token": self._token, "user_id": uid}, fh)
        os.replace(tmp, p)                                   # root path unit consumes + deletes it
        user = self.state.get("bot_username")
        self.f.db.kv_set("ops.telegram", {"bot_username": user, "owner_user_id": uid, "owner_first_name": first_name[:40],
                                          "connected_ts": time.time()})
        self.f.audit.append("OPS_TELEGRAM_BOUND", {"bot": user, "owner_user_id": uid}, actor="portal")
        self.state = {"state": "connected", "bot_username": user, "owner_first_name": first_name[:40]}
        self._token = None
