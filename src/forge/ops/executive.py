"""Executive layer: debrief, executive objectives (multi-role campaigns), engineering tickets, owner transfers."""

from __future__ import annotations

import json
import secrets
import time
from typing import Any

# objective kind → which specialists get what (the delegation playbook)
PLAYBOOKS: dict[str, list[tuple[str, str]]] = {
    "grow_profit": [
        ("governor", "EXECUTIVE OBJECTIVE: {o}. Diagnose why true-net $/h is below target using get_profit_velocity "
                     "(binding constraint, stream tiers, levers). Propose the capital reallocation + which streams to push, "
                     "prove or kill. Report: bottleneck, decision, expected $/h impact."),
        ("alpha_inventor", "EXECUTIVE OBJECTIVE: {o}. Invent and submit strategy candidates aimed at the top profit-velocity "
                           "levers (fast-recycling, independent, fee-aware). Prefer families not yet explored."),
        ("adversary", "EXECUTIVE OBJECTIVE: {o}. Falsify the newest candidates and current shadow streams hard; kill weak "
                      "ones fast so capital and compute move to what survives."),
        ("rail_hunter", "EXECUTIVE OBJECTIVE: {o}. Find the next legitimate, API-automatable earning rail or market with "
                        "faster settlement or higher independent flow; quantify fees, capacity and expected $/h."),
        ("critic", "EXECUTIVE OBJECTIVE: {o}. Red-team the plan: where could the extra $/h be an illusion (correlation, "
                   "fill realism, overfitting, fees)? Name the single most likely failure."),
    ],
    "integrate_platform": [
        ("rail_hunter", "PLATFORM INTEGRATION REQUEST: {o}. Research the OFFICIAL API (docs URLs), whether automated "
                        "trading is permitted by its terms, account/jurisdiction eligibility, fees, settlement speed, "
                        "capacity, what FORGE could earn (vs current streams), and EXACTLY which credential is required "
                        "(type, scopes/permissions: trade + read, NO withdrawal). Report a go/no-go with evidence."),
        ("critic", "PLATFORM INTEGRATION REQUEST: {o}. Review legality/ToS, counterparty and custody risk, and whether "
                   "it duplicates an existing rail. Veto with reasons if unsafe."),
        ("governor", "PLATFORM INTEGRATION REQUEST: {o}. Decide economic priority vs current levers once rail_hunter and "
                     "critic report."),
    ],
    "fix": [
        ("doctor", "EXECUTIVE OBJECTIVE (FIX): {o}. Diagnose root cause with get_system_health and recent failures; state "
                   "the fix, whether FORGE self-heals it, or what engineering must change."),
    ],
    "custom": [("governor", "EXECUTIVE OBJECTIVE: {o}. Plan it within your decision rights, delegate via your report, and "
                            "report the outcome.")],
}


def launch_objective(db: Any, kind: str, objective: str, actor: str) -> dict[str, Any]:
    if kind not in PLAYBOOKS:
        raise ValueError(f"kind must be one of {sorted(PLAYBOOKS)}")
    objective = objective.strip()[:1500]
    if not objective:
        raise ValueError("objective text required")
    ids = []
    for role, tmpl in PLAYBOOKS[kind]:
        ids.append(db.insert_id("ops_directives", {"ts": time.time(), "role": role, "instruction": tmpl.format(o=objective),
                                                   "priority": "high", "status": "OPEN", "requested_by": actor}))
    ticket = None
    if kind == "integrate_platform":
        ticket = db.insert_id("eng_tickets", {"ts": time.time(), "title": f"Integrate platform: {objective[:120]}",
                                              "spec": "Build adapter (read + trade, no withdrawal) after rail_hunter go; "
                                                      "shadow first; allocator only after evidence.",
                                              "status": "OPEN", "requested_by": actor})
    oid = db.insert_id("ops_objectives", {"ts": time.time(), "kind": kind, "objective": objective, "status": "ACTIVE",
                                          "directive_ids": json.dumps(ids), "ticket_id": ticket})
    return {"objective_id": oid, "kind": kind, "directives": ids, "engineering_ticket": ticket,
            "roles": [r for r, _ in PLAYBOOKS[kind]]}


def objectives(db: Any, status: str = "ACTIVE") -> list[dict[str, Any]]:
    rows = db.query("SELECT * FROM ops_objectives" + ("" if status == "ALL" else " WHERE status = ?") + " ORDER BY id DESC LIMIT 20",
                    () if status == "ALL" else (status,))
    for r in rows:
        ids = json.loads(r.get("directive_ids") or "[]")
        ds = db.query(f"SELECT id, role, status, substr(result, 1, 600) result FROM ops_directives WHERE id IN "  # noqa: S608
                      f"({','.join('?' * len(ids))})", ids) if ids else []
        r["progress"] = {"done": sum(d["status"] == "DONE" for d in ds), "total": len(ds)}
        r["directives"] = ds
        if ds and all(d["status"] in ("DONE", "CANCELLED") for d in ds) and r["status"] == "ACTIVE":
            db.execute("UPDATE ops_objectives SET status = 'COMPLETE', done_ts = ? WHERE id = ?", (time.time(), r["id"]))
            r["status"] = "COMPLETE"
    return rows


def file_ticket(db: Any, title: str, spec: str, credential: str | None, actor: str) -> dict[str, Any]:
    tid = db.insert_id("eng_tickets", {"ts": time.time(), "title": title[:200], "spec": spec[:4000],
                                       "credential_needed": (credential or None) and credential[:300], "status": "OPEN",
                                       "requested_by": actor})
    return {"ticket_id": tid, "status": "OPEN",
            "note": "queued for the engineering channel (code changes/deploys are done there, tested, then deployed)"}


# ------------------------------------------------------------------------------------------------ debrief
def debrief(forge: Any) -> dict[str, Any]:
    from forge.ops.econ import window
    db = forge.db
    v = db.kv_get("velocity") or {}
    today, hour = window(forge, "today"), window(forge, "1h")
    streams = [s for s in v.get("streams", []) if s.get("n")]
    by_mean = sorted(streams, key=lambda s: s.get("mu") or 0.0, reverse=True)
    pop = forge.reg.counts() if hasattr(forge, "reg") else {}
    trials24 = db.scalar("SELECT COUNT(*) FROM research_trials WHERE ts >= ?",
                         (time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(time.time() - 86400)),)) or 0
    opp24 = db.scalar("SELECT COUNT(*) FROM crossrail_signals WHERE ts >= ?", (time.time() - 86400,)) or 0
    h = getattr(forge, "health", None)
    comp = getattr(forge, "compute", None)
    worked = [f"{s['id']}: {s['n']} independent outcomes, mean {s['mu']:+.4f}/unit, tier {s['tier']}"
              for s in by_mean if (s.get("mu") or 0) > 0][:3]
    didnt = [f"{s['id']}: {s['n']} outcomes, mean {s['mu']:+.4f}/unit (P>0 = {s.get('p_pos', 0):.2f})"
             for s in reversed(by_mean) if (s.get("mu") or 0) < 0][:3]
    return {
        "FORGE_TODAY": {
            "treasury_usd": (v.get("treasury") or {}).get("total"), "regime": (v.get("regime") or {}).get("regime"),
            "live_true_net_today_usd": today["LIVE"]["true_net_usd"], "live_last_hour_usd": hour["LIVE"]["true_net_usd"],
            "paper_realized_today_usd": today["PAPER"]["realized_usd"],
            "profit_velocity_usd_per_h": {"realized_live_24h": ((v.get("realized") or {}).get("24h") or {}).get("usd_per_h"),
                                          **(v.get("expected_usd_per_h") or {}), "target": v.get("target_usd_per_h")},
            "capital_deployed_pct": today["deployed_pct"],
            "best_stream": by_mean[0]["id"] if by_mean else None, "weakest_stream": by_mean[-1]["id"] if by_mean else None,
            "opportunities_evaluated_24h": opp24, "strategies": pop, "research_trials_24h": trials24,
            "health_score": (h.score() if h else {}), "spend_today": today["COSTS"],
            "modal_month": comp.summary() if comp else None},
        "WHAT_WORKED": worked, "WHAT_DIDNT": didnt,
        "WHAT_FORGE_IS_DOING": {"diagnosis": v.get("diagnosis"),
                                "objectives": [{"id": o["id"], "objective": o["objective"][:120], "progress": o["progress"]}
                                               for o in objectives(db)],
                                "research_focus": db.kv_get("brain.research_focus")},
        "NEXT_BEST": [p["action"] + f" (+${p['delta_usd_per_h']:.4f}/h)" for p in (v.get("priorities") or [])[:4]],
    }


# ------------------------------------------------------------------------------------------------ transfers
def transfer_config(db: Any) -> dict[str, Any]:
    return db.kv_get("ops.transfer.config") or {}


async def transfer_preview(forge: Any, amount: float) -> dict[str, Any]:
    """Destination = the owner's own Coinbase portfolio (pre-registered on the server, never via chat). Coinbase moves
    between portfolios of the same account are free; the owner withdraws to bank from the Coinbase app."""
    db = forge.db
    cfg = transfer_config(db)
    v = db.kv_get("velocity") or {}
    total = float((v.get("treasury") or {}).get("total") or 0)
    blockers = []
    if not cfg.get("source_portfolio_uuid") or not cfg.get("owner_portfolio_uuid"):
        blockers.append("transfer destination not registered (server command: forge-exec-transfer-setup)")
    perms = {}
    rest = getattr(forge, "rest", None)
    if rest is not None:
        try:
            perms = await rest.key_permissions()
        except Exception as e:
            blockers.append(f"cannot read Coinbase key permissions: {str(e)[:80]}")
    if not perms.get("can_transfer"):
        blockers.append("FORGE's Coinbase key has can_transfer=false (by design). Enabling requires the owner to issue a "
                        "key with Transfer permission scoped to FORGE's portfolio (moves between own portfolios only, "
                        "no external withdrawals)")
    cash = float((getattr(forge, "treasury", {}) or {}).get("cash_usd") or 0)
    if amount <= 0:
        blockers.append("amount must be positive")
    if amount > total:
        blockers.append(f"amount exceeds treasury ${total:.2f}")
    tid = secrets.token_hex(4)
    status = "BLOCKED" if blockers else "PREVIEWED"
    db.insert("ops_transfers", {"id": tid, "ts": time.time(), "amount_usd": amount, "currency": "USD",
                                "destination": cfg.get("owner_label", "owner's Coinbase portfolio"), "status": status,
                                "fee_usd": 0.0, "treasury_before": total, "treasury_after": total - amount,
                                "detail": json.dumps({"blockers": blockers})})
    return {"transfer_id": tid, "status": status, "amount_usd": amount,
            "destination": cfg.get("owner_label", "owner's Coinbase portfolio (not yet registered)"), "fee_usd": 0.0,
            "treasury_before_usd": round(total, 2), "treasury_after_usd": round(total - amount, 2),
            "cash_available_usd": round(cash, 2), "blockers": blockers,
            "confirm_with": f"CONFIRM TRANSFER ${amount:.2f} <6-digit authenticator code>" if not blockers else None}


async def transfer_execute(forge: Any, tid: str) -> dict[str, Any]:
    db = forge.db
    t = db.query_one("SELECT * FROM ops_transfers WHERE id = ?", (tid,))
    if not t or t["status"] != "PREVIEWED" or time.time() - float(t["ts"]) > 600:
        raise ValueError("no fresh previewed transfer with that id (previews expire after 10 min)")
    cfg = transfer_config(db)
    body = {"funds": {"value": f"{float(t['amount_usd']):.2f}", "currency": t["currency"]},
            "source_portfolio_uuid": cfg["source_portfolio_uuid"], "target_portfolio_uuid": cfg["owner_portfolio_uuid"]}
    try:
        r = await forge.rest._request("POST", "/api/v3/brokerage/portfolios/move_funds", body=body, private=True,
                                      idempotent=False, retries=1)
    except Exception as e:
        db.execute("UPDATE ops_transfers SET status='FAILED', detail=? WHERE id=?", (json.dumps({"error": str(e)[:300]}), tid))
        forge.audit.append("OWNER_TRANSFER_FAILED", {"id": tid, "amount": t["amount_usd"], "error": str(e)[:200]},
                           actor="exec-ops")
        raise
    db.execute("UPDATE ops_transfers SET status='EXECUTED', venue_ref=?, detail=? WHERE id=?",
               (json.dumps(r)[:300], json.dumps({"response": r}, default=str)[:2000], tid))
    forge.audit.append("OWNER_TRANSFER", {"id": tid, "amount": t["amount_usd"], "destination": t["destination"]},
                       actor="exec-ops")
    return {"transfer_id": tid, "status": "EXECUTED", "venue_response": r,
            "verify": "balances re-read on the next account refresh (≤ 60 s); ask 'what's our balance' to confirm"}
