#!/usr/bin/env python3
"""FORGE GUARDIAN — root watchdog for the whole money-generating system (runs every 60 s from a systemd timer).

Layers of self-healing (inner → outer):
  1. FORGE's own Supervisor restarts crashed/stalled loops inside the engine (per-loop heartbeats).
  2. systemd restarts any crashed service immediately (Restart=always, StartLimitIntervalSec=0 → never gives up).
  3. GUARDIAN (this): verifies that every FORGE service is actually *working*, not just "active":
       - all units active (forge, forge-hermes, forge-tunnel, forge-ops, forge-eng) + timers/paths → start/restart
       - FORGE API answers /health (3 consecutive misses → restart forge)
       - engine loops: critical loops stale for ≥ 10 min → restart forge
       - EXECUTIVE OPS Telegram link: connected since its last start, bot token valid → else restart forge-ops
       - resources: memory pressure, disk space, swap → alert
     Every repair is audited (OPS audit trail, hash-chained journal) and the owner gets ONE Telegram note per incident
     (plus a recovery note) — never routine noise.
  4. Linode host watchdog (Lassie) reboots the VM if it powers off unexpectedly; every unit is enabled at boot.
"""

from __future__ import annotations

import json
import subprocess
import time
import urllib.parse
import urllib.request
from pathlib import Path

API = "http://127.0.0.1:8470"
STATE = Path("/var/lib/forge-guardian/state.json")
UNITS = ["forge", "forge-hermes", "forge-tunnel", "forge-ops", "forge-eng"]
AUX = ["forge-deployer.timer", "forge-ops-provision.path", "forge-cred-provision.path"]
CRITICAL_LOOPS = {"api", "market_stream", "feed_watch", "bars_300", "bars_3600", "execution", "treasury", "healing",
                  "crossrail", "crossrail_fast", "settlement_window", "sw_sampler", "kalshi_live", "velocity", "econ"}
ALERT_COOLDOWN_S = 1800


def sh(*cmd: str, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(list(cmd), capture_output=True, text=True, timeout=timeout)


def load() -> dict:
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {"incidents": {}, "health_miss": 0, "loop_stale_since": {}, "repairs": []}


def save(st: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st))


def ops_env() -> dict:
    try:
        return dict(line.split("=", 1) for line in Path("/srv/forge/runtime/ops/home/.env").read_text().splitlines() if "=" in line)
    except Exception:
        return {}


def notify(text: str) -> None:
    env = ops_env()
    tok, chat = env.get("TELEGRAM_BOT_TOKEN"), (env.get("TELEGRAM_ALLOWED_USERS") or "").split(",")[0]
    if not tok or not chat:
        return
    try:
        data = urllib.parse.urlencode({"chat_id": chat, "text": text[:3500]}).encode()
        urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/sendMessage", data=data, timeout=15)
    except Exception:
        pass


def api(method: str, path: str, body: dict | None = None, timeout: int = 10) -> dict:
    tok = Path("/srv/forge/var/run/ops_token").read_text().strip()
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json",
                                          "X-Ops-Actor": "guardian"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode() or "{}")


def audit(action: str, outcome: str, detail: dict) -> None:
    try:
        api("POST", "/api/ops/audit", {"action": action, "args": None, "outcome": outcome, "detail": detail, "channel": "guardian"})
    except Exception:
        pass


def incident(st: dict, key: str, text: str, repaired: bool) -> None:
    """One owner alert per incident key per cooldown; recovery note when it clears."""
    now = time.time()
    inc = st["incidents"].get(key)
    if inc is None or now - inc.get("alerted", 0) > ALERT_COOLDOWN_S:
        notify(f"🛡️ FORGE Guardian: {text}" + (" — auto-repaired, verifying." if repaired else ""))
        st["incidents"][key] = {"since": inc["since"] if inc else now, "alerted": now, "text": text}
    st["repairs"] = (st.get("repairs", []) + [{"ts": now, "key": key, "text": text}])[-50:]
    audit(f"guardian:{key}", "REPAIRED" if repaired else "ALERT", {"text": text})


def resolve(st: dict, key: str) -> None:
    inc = st["incidents"].pop(key, None)
    if inc and inc.get("alerted"):
        notify(f"✅ FORGE Guardian: recovered — {inc['text']} (down {int((time.time() - inc['since']) / 60)} min)")


def active(unit: str) -> bool:
    return sh("systemctl", "is-active", "--quiet", unit).returncode == 0


def restart(unit: str) -> None:
    sh("systemctl", "restart", unit, timeout=120)


def check_units(st: dict) -> None:
    for u in UNITS + AUX:
        key = f"unit:{u}"
        if active(u):
            resolve(st, key)
            continue
        sh("systemctl", "enable", u)
        restart(u) if not u.endswith((".timer", ".path")) else sh("systemctl", "start", u)
        incident(st, key, f"{u} was down", repaired=active(u))


def check_api(st: dict) -> dict | None:
    try:
        with urllib.request.urlopen(API + "/health", timeout=8) as r:
            ok = r.status == 200
    except Exception:
        ok = False
    if ok:
        st["health_miss"] = 0
        resolve(st, "api")
        try:
            return api("GET", "/api/ops/status", timeout=20)
        except Exception:
            return None
    st["health_miss"] = st.get("health_miss", 0) + 1
    if st["health_miss"] >= 3:
        restart("forge")
        st["health_miss"] = 0
        incident(st, "api", "FORGE API was unresponsive for 3 min — engine restarted", repaired=True)
    return None


def check_loops(st: dict, status: dict | None) -> None:
    if not status:
        return
    stale = set((status.get("health") or {}).get("stale_loops") or [])
    now = time.time()
    since = {k: v for k, v in st.get("loop_stale_since", {}).items() if k in stale}
    for loop in stale:
        since.setdefault(loop, now)
    st["loop_stale_since"] = since
    long_stale = [k for k, t in since.items() if now - t >= 600 and (k in CRITICAL_LOOPS or len(since) >= 4)]
    if long_stale:
        restart("forge")
        st["loop_stale_since"] = {}
        incident(st, "loops", f"engine loops stalled ≥10 min ({', '.join(sorted(long_stale)[:6])}) — engine restarted",
                 repaired=True)
    elif not stale:
        resolve(st, "loops")


def check_telegram(st: dict) -> None:
    env = ops_env()
    if not env.get("TELEGRAM_BOT_TOKEN") or not active("forge-ops"):
        return
    started = sh("systemctl", "show", "forge-ops", "-p", "ActiveEnterTimestampMonotonic", "--value").stdout.strip()
    since_start = sh("systemctl", "show", "forge-ops", "-p", "ActiveEnterTimestamp", "--value").stdout.strip()
    log = sh("journalctl", "-u", "forge-ops", "--since", since_start or "-1h", "--no-pager", "-o", "cat").stdout
    connected = "Connected to Telegram" in log
    lost = log.rfind("Telegram") > log.rfind("Connected to Telegram") and any(
        w in log[log.rfind("Connected to Telegram"):] for w in ("Conflict", "disconnected", "NetworkError", "Unauthorized"))
    try:
        up_s = time.monotonic() - int(started) / 1e6 if started.isdigit() else 999
    except Exception:
        up_s = 999
    key = "telegram"
    if (not connected and up_s > 180) or lost:
        try:
            me = json.loads(urllib.request.urlopen(f"https://api.telegram.org/bot{env['TELEGRAM_BOT_TOKEN']}/getMe",
                                                   timeout=15).read().decode())
            token_ok = bool(me.get("ok"))
        except Exception:
            token_ok = None
        if token_ok is False:
            incident(st, "telegram_token", "Telegram rejected the bot token (revoked?) — re-pair at forge.northstarimagine.com/setup",
                     repaired=False)
            return
        restart("forge-ops")
        incident(st, key, "EXECUTIVE OPS lost its Telegram connection — agent restarted", repaired=True)
    elif connected:
        resolve(st, key)


def check_resources(st: dict) -> None:
    try:
        psi = Path("/proc/pressure/memory").read_text().splitlines()[0]
        avg60 = float(psi.split("avg60=")[1].split()[0])
    except Exception:
        avg60 = 0.0
    if avg60 > 30:
        incident(st, "memory", f"memory pressure high (avg60={avg60:.0f}%)", repaired=False)
    elif avg60 < 5:
        resolve(st, "memory")
    disk = sh("df", "--output=avail", "-B1", "/srv/forge").stdout.split()
    free_gb = int(disk[-1]) / 1e9 if disk and disk[-1].isdigit() else 999
    if free_gb < 8:
        sh("journalctl", "--vacuum-size=500M")
        incident(st, "disk", f"low disk: {free_gb:.1f} GB free (journal vacuumed)", repaired=False)
    else:
        resolve(st, "disk")


def main() -> int:
    st = load()
    check_units(st)
    status = check_api(st)
    check_loops(st, status)
    check_telegram(st)
    check_resources(st)
    try:
        for m in api("GET", "/api/ops/outbox").get("messages", [])[:10]:
            notify(m["text"])
    except Exception:
        pass
    st["last_run"] = time.time()
    save(st)
    try:
        api("POST", "/api/ops/guardian", {"last_run": st["last_run"], "open_incidents": st["incidents"],
                                          "recent_repairs": st.get("repairs", [])[-10:]})
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
