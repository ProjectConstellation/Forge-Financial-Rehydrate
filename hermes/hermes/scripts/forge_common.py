"""Shared helpers for Hermes pre-run gate scripts (no LLM, no secrets in env: token read from HERMES_HOME/forge)."""
import json
import os
import time
import urllib.request
from pathlib import Path

HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
API = "http://127.0.0.1:8470"
STATE = HOME / "forge" / "gate_state.json"


def call(path: str) -> dict:
    tok = (HOME / "forge" / "agent_token").read_text().strip()
    req = urllib.request.Request(API + path, headers={"Authorization": f"Bearer {tok}"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def state() -> dict:
    try:
        return json.loads(STATE.read_text())
    except Exception:
        return {}


def save(st: dict) -> None:
    STATE.write_text(json.dumps(st))


def gate(role: str, est_usd: float) -> dict | None:
    """Budget gate: None → skip (no LLM). FORGE decides Hermes' slice of the live intelligence pace."""
    try:
        a = call(f"/api/agent/allow?role={role}&est_usd={est_usd}")
    except Exception as e:
        print(json.dumps({"wakeAgent": False, "note": f"FORGE unreachable {e}"}))
        return None
    if not a.get("wake"):
        return None
    return a


def skip() -> None:
    print(json.dumps({"wakeAgent": False}))


def wake(context: dict) -> None:
    print(json.dumps({"wakeAgent": True, "context": context}, default=str)[:60000])


def now() -> float:
    return time.time()
