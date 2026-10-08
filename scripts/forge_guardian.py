#!/usr/bin/env python3
"""FORGE GUARDIAN — intelligent root watchdog (every 60s).

Self-heal layers (inner → outer):
  1. Engine Supervisor restarts stalled loops.
  2. systemd Restart=always on units.
  3. GUARDIAN verifies units are *working*, repairs crashes, alerts once per incident.
  4. Host watchdog (Lassie) if the VM dies.

Intelligence rules:
  - Do NOT race intentional restarts/deploys (activating/deactivating/reloading → wait).
  - Require sustained downtime (DOWN_TICKS) before repair+alert — suppresses "down 1 min" deploy noise.
  - Suppress recovery chatter for brief incidents (< MIN_INCIDENT_ALERT_S).
  - Honor /var/lib/forge-guardian/snooze_until (unix ts) during maintenance/deploys.
  - Never resume trading: process restart is fine; STOPPED trading state lives in DB and must stay STOPPED
    until founder CONFIRM resume_trading. If trading is STOPPED, say so in repair notes; do not call resume.
  - Prefer diagnose+repair over blind thrash; audit every repair.
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
SNOOZE = Path("/var/lib/forge-guardian/snooze_until")
UNITS = ["forge", "forge-hermes", "forge-tunnel", "forge-ops", "forge-eng"]
AUX = ["forge-deployer.timer", "forge-ops-provision.path", "forge-cred-provision.path"]
CRITICAL_LOOPS = {"api", "market_stream", "feed_watch", "bars_300", "bars_3600", "execution", "treasury", "healing",
                  "crossrail", "crossrail_fast", "settlement_window", "sw_sampler", "kalshi_live", "velocity", "econ"}
ALERT_COOLDOWN_S = 1800
DOWN_TICKS = 3          # ~3 min sustained down before repair (timer ~60s)
MIN_INCIDENT_ALERT_S = 120  # don't Telegram-spam sub-2min blips
TRANSIENT = {"activating", "deactivating", "reloading", "maintenance"}


def sh(*cmd: str, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(list(cmd), capture_output=True, text=True, timeout=timeout)


def load() -> dict:
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {"incidents": {}, "health_miss": 0, "loop_stale_since": {}, "down_ticks": {}, "repairs": []}


def save(st: dict) -> None:
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st))


def snoozed() -> bool:
    try:
        until = float(SNOOZE.read_text().strip())
        return time.time() < until
    except Exception:
        return False


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


def trading_stopped_note() -> str:
    """If trading intentionally STOPPED, never imply we resumed it."""
    try:
        st = api("GET", "/api/ops/status", timeout=8)
        ts = st.get("trading_state") or {}
        state = ts.get("state") if isinstance(ts, dict) else ts
        if state == "STOPPED":
            reason = (ts.get("reason") if isinstance(ts, dict) else "") or "intentional stop"
            return f" (trading remains STOPPED — {reason[:120]}; will NOT auto-resume)"
    except Exception:
        pass
    return ""


def incident(st: dict, key: str, text: str, repaired: bool, *, notify_owner: bool = True) -> None:
    now = time.time()
    inc = st["incidents"].get(key)
    if notify_owner and (inc is None or now - inc.get("alerted", 0) > ALERT_COOLDOWN_S):
        notify(f"🛡️ FORGE Guardian: {text}" + (" — auto-repaired, verifying." if repaired else "") + trading_stopped_note())
        st["incidents"][key] = {"since": inc["since"] if inc else now, "alerted": now, "text": text, "notified": True}
    else:
        st["incidents"][key] = {
            "since": inc["since"] if inc else now,
            "alerted": (inc or {}).get("alerted", 0),
            "text": text,
            "notified": bool((inc or {}).get("notified")),
        }
    st["repairs"] = (st.get("repairs", []) + [{"ts": now, "key": key, "text": text}])[-50:]
    audit(f"guardian:{key}", "REPAIRED" if repaired else "ALERT", {"text": text})


def resolve(st: dict, key: str) -> None:
    inc = st["incidents"].pop(key, None)
    if not inc:
        return
    dur = int(time.time() - inc.get("since", time.time()))
    # Only ping recovery if we alerted the owner and it wasn't a brief blip
    if inc.get("notified") and inc.get("alerted") and dur >= MIN_INCIDENT_ALERT_S:
        notify(f"✅ FORGE Guardian: recovered — {inc['text']} (down {max(1, dur // 60)} min){trading_stopped_note()}")
    st.setdefault("down_ticks", {}).pop(key, None)


def unit_props(unit: str) -> dict:
    out = sh("systemctl", "show", unit, "-p", "ActiveState", "-p", "SubState", "-p", "Result",
             "-p", "NRestarts", "-p", "ActiveEnterTimestampMonotonic").stdout
    props = {}
    for line in out.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            props[k] = v
    return props


def active(unit: str) -> bool:
    return sh("systemctl", "is-active", "--quiet", unit).returncode == 0


def restart(unit: str) -> None:
    sh("systemctl", "restart", unit, timeout=180)


def check_units(st: dict) -> None:
    if snoozed():
        return
    ticks = st.setdefault("down_ticks", {})
    for u in UNITS + AUX:
        key = f"unit:{u}"
        props = unit_props(u)
        sub = props.get("SubState", "")
        astate = props.get("ActiveState", "")
        # Mid-transition (deploy/restart) — wait, do not fight systemd
        if sub in TRANSIENT or astate in ("activating", "deactivating", "reloading"):
            continue
        if active(u):
            ticks.pop(key, None)
            resolve(st, key)
            continue
        ticks[key] = int(ticks.get(key, 0)) + 1
        if ticks[key] < DOWN_TICKS:
            # Sustained-down debounce: no restart yet (avoids deploy race + "1 min" spam)
            continue
        sh("systemctl", "enable", u)
        if u.endswith((".timer", ".path")):
            sh("systemctl", "start", u)
        else:
            restart(u)
        ok = active(u) or unit_props(u).get("ActiveState") == "activating"
        incident(st, key, f"{u} was down (sustained ≥{DOWN_TICKS} min)", repaired=ok)
        ticks[key] = 0


def check_api(st: dict) -> dict | None:
    if snoozed():
        return None
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
    # 3 misses ≈ 3 min — but skip if unit is mid-restart
    props = unit_props("forge")
    if props.get("SubState") in TRANSIENT:
        return None
    if st["health_miss"] >= 3:
        restart("forge")
        st["health_miss"] = 0
        incident(st, "api", "FORGE API unresponsive ≥3 min — engine restarted", repaired=True)
    return None


def check_loops(st: dict, status: dict | None) -> None:
    if not status or snoozed():
        return
    stale = set((status.get("health") or {}).get("stale_loops") or [])
    now = time.time()
    since = {k: v for k, v in st.get("loop_stale_since", {}).items() if k in stale}
    for loop in stale:
        since.setdefault(loop, now)
    st["loop_stale_since"] = since
    long_stale = [k for k, t in since.items() if now - t >= 600 and (k in CRITICAL_LOOPS or len(since) >= 4)]
    if long_stale:
        # If trading STOPPED intentionally, still restart process (API/health) but note we won't resume trading
        restart("forge")
        st["loop_stale_since"] = {}
        incident(st, "loops", f"engine loops stalled ≥10 min ({', '.join(sorted(long_stale)[:6])}) — engine restarted",
                 repaired=True)
    elif not stale:
        resolve(st, "loops")


def check_telegram(st: dict) -> None:
    if snoozed():
        return
    env = ops_env()
    if not env.get("TELEGRAM_BOT_TOKEN") or not active("forge-ops"):
        return
    props = unit_props("forge-ops")
    if props.get("SubState") in TRANSIENT:
        return
    started = props.get("ActiveEnterTimestampMonotonic", "").strip()
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
    st["snoozed"] = snoozed()
    save(st)
    try:
        api("POST", "/api/ops/guardian", {"last_run": st["last_run"], "open_incidents": st["incidents"],
                                          "recent_repairs": st.get("repairs", [])[-10:],
                                          "snoozed": st["snoozed"], "down_ticks": st.get("down_ticks", {})})
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
