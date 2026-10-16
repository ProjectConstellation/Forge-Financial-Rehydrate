"""Shared client for the FORGE workforce power switch and on-demand wake.

WHY THIS EXISTS. forge.service is hardened: NoNewPrivileges=yes, ProtectSystem=strict,
ReadWritePaths=/srv/forge/var. It therefore can NEVER sudo — correct, and not to be weakened. Two
call sites nonetheless used `sudo -u forge-hermes ... hermes cron run <id>`:

    agents/employment_accountability.py:_hermes_wake   (the PRIMARY wake path)
    lab/officer_dispatch.py:_hermes_wake               (the dispatch wake path)
    agents/results_enforcer.py:_wake                   (its "direct fallback")

`subprocess.Popen` with stdout/stderr=DEVNULL returns immediately and does NOT raise when sudo
refuses, so all three returned True — recorded as `woke=True` — while nothing happened. Every one of
the 8 FORCE_WAKE records in agents.heartbeat was therefore false, and on-demand waking of officers has
silently never worked; officers only ever ran on their natural cron schedule. That is why stale
officers were reported as force-woken and stayed stale.

The fix uses the same privilege boundary the power switch already proved out: drop a nonce-keyed
request into /srv/forge/var/run (writable from the sandbox); a root systemd PATH unit executes it by
dropping to forge-hermes; results come back in a nonce-keyed file. Wakes are queued non-blocking by
default and reconciled later, so the enforcer loop never stalls, and honesty is preserved: a queued
wake reports QUEUED, not success.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

RUN = Path("/srv/forge/var/run")
# Requests are per-nonce, NOT a single shared file. A single request path meant two wakes queued in
# quick succession overwrote each other, so one of them was silently dropped and its nonce never got a
# result (observed: 7 wakes left pending). The root path unit watches with PathExistsGlob and drains
# every pending request, so nothing is lost.
REQUEST_TMPL = "team_power.request.%s.json"
RESULT_TMPL = "team_power.result.%s.json"

# How long a caller may block for a result. Power-switch actions (pause/resume/status) are
# founder-facing and worth waiting for; wakes are queued and reconciled instead.
WAIT_SWITCH_S = 90.0
WAIT_WAKE_S = 0.0


def _nonce() -> str:
    import secrets
    return secrets.token_hex(8)


def request(verb: str, actor: str, arg: str | None = None, *, wait_s: float | None = None) -> dict[str, Any]:
    """Queue a request to the root executor. Returns a result dict, or {"queued": True} if not waiting.

    `verb` must be one of pause/resume/status/wake. `arg` is only honoured for `wake` and must be a
    ROLE NAME (never a job id): the root-side wrapper resolves role -> job id from live jobs.json and
    refuses unknown roles, so a caller cannot make it execute an arbitrary id.
    """
    if verb not in ("pause", "resume", "status", "wake"):
        return {"ok": False, "error": f"verb {verb!r} not permitted"}
    wait = WAIT_SWITCH_S if wait_s is None else wait_s
    nonce = _nonce()
    res_path = RUN / (RESULT_TMPL % nonce)
    req_path = RUN / (REQUEST_TMPL % nonce)
    payload = {"verb": verb, "actor": actor, "nonce": nonce, "ts": time.time()}
    if arg is not None:
        payload["arg"] = str(arg)[:64]
    try:
        RUN.mkdir(parents=True, exist_ok=True)
        tmp = req_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload))
        os.replace(tmp, req_path)
    except Exception as e:
        return {"ok": False, "error": f"could not queue request: {type(e).__name__}: {e}"}

    if wait <= 0:
        return {"ok": True, "queued": True, "nonce": nonce,
                "note": "request queued for the root executor; not yet confirmed"}

    deadline = time.time() + wait
    while time.time() < deadline:
        if res_path.exists():
            try:
                out = json.loads(res_path.read_text())
            except Exception as e:
                out = {"ok": False, "error": f"unreadable result: {e}"}
            try:
                res_path.unlink(missing_ok=True)
            except Exception:
                pass
            out["nonce"] = nonce
            return out
        time.sleep(0.4)
    return {"ok": False, "queued": True, "nonce": nonce,
            "error": "root executor did not answer within %.0fs" % wait,
            "hint": "check: systemctl is-active forge-team-power.path"}


def collect_result(nonce: str) -> dict[str, Any] | None:
    """Non-blocking pickup of a previously queued result, if it has arrived."""
    res_path = RUN / (RESULT_TMPL % nonce)
    if not res_path.exists():
        return None
    try:
        out = json.loads(res_path.read_text())
    except Exception:
        out = {"ok": False, "error": "unreadable result"}
    try:
        res_path.unlink(missing_ok=True)
    except Exception:
        pass
    return out


def queue_wake(db: Any, role: str, actor: str = "results_enforcer") -> str:
    """Queue an on-demand wake. Returns the admission state recorded: QUEUED, THROTTLED or ERROR.

    Honest by construction: we record QUEUED, never "woke". reconcile_wakes() upgrades it to CONFIRMED
    or FAILED once the root executor answers, so no caller can mistake an attempt for a success.
    """
    now = time.time()
    key = f"agents.wake_admission.{role}"
    with db.transaction():
        last = db.kv_get(key) or {}
        # `ATTEMPTED` is LEGACY vocabulary written by the old `sudo -u forge-hermes` path, which could
        # never run under the service's NoNewPrivileges hardening. Those entries record a wake that did
        # not happen, so they must not throttle the honest path; treat them as absent and overwrite.
        if str(last.get("state") or "").upper() == "ATTEMPTED":
            last = {}
        if now - float(last.get("ts") or 0) < 600:
            return "THROTTLED"
        res = request("wake", actor, role, wait_s=WAIT_WAKE_S)
        if not res.get("queued") and not res.get("ok"):
            db.kv_set(key, {"ts": now, "state": "ERROR", "error": res.get("error"), "by": actor})
            return "ERROR"
        db.kv_set(key, {"ts": now, "state": "QUEUED", "nonce": res.get("nonce"), "by": actor})
    return "QUEUED"


def reconcile_wakes(db: Any, *, max_age_s: float = 1800.0) -> dict[str, Any]:
    """Upgrade QUEUED wakes to CONFIRMED/FAILED using the root executor's answers.

    A wake whose answer never arrives inside max_age_s is marked UNCONFIRMED rather than left looking
    successful — an unverified wake must not be reported as a wake.
    """
    now = time.time()
    out: dict[str, Any] = {"confirmed": 0, "failed": 0, "unconfirmed": 0, "pending": 0}
    try:
        rows = db.query("SELECT key, value FROM kv_state WHERE key LIKE 'agents.wake_admission.%'") or []
    except Exception:
        return out
    for r in rows:
        try:
            st = json.loads(r["value"]) if isinstance(r["value"], str) else r["value"]
        except Exception:
            continue
        if not isinstance(st, dict) or st.get("state") != "QUEUED":
            continue
        role = str(r["key"]).rsplit(".", 1)[-1]
        res = collect_result(str(st.get("nonce") or ""))
        if res is None:
            if now - float(st.get("ts") or 0) > max_age_s:
                st.update(state="UNCONFIRMED",
                          note="root executor never answered; the wake is NOT confirmed")
                db.kv_set(r["key"], st)
                out["unconfirmed"] += 1
            else:
                out["pending"] += 1
            continue
        if res.get("ok"):
            st.update(state="CONFIRMED", result_states=res.get("states"), confirmed_ts=now)
            out["confirmed"] += 1
        else:
            st.update(state="FAILED", error=str(res.get("error") or res.get("detail"))[:300],
                      confirmed_ts=now)
            out["failed"] += 1
        db.kv_set(r["key"], st)
    return out
