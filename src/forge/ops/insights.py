"""EXECUTIVE OPS insight tools: leaderboard, trades, changes, chart series, rule alerts, credential requests (OP-026)."""

from __future__ import annotations

import json
import re
import secrets
import time
from datetime import UTC, datetime
from typing import Any

from forge.ops.econ import parse_window


def _iso(t: float) -> str:
    return datetime.fromtimestamp(t, UTC).isoformat()


# ------------------------------------------------------------------------------------------------ leaderboard
def leaderboard(forge: Any, window: str = "7d", limit: int = 10) -> dict[str, Any]:
    """Every money-making unit ranked by money AND evidence: evolved strategies (paper/forward) + income streams."""
    db = forge.db
    since, label = parse_window(window)
    strat = db.query("SELECT p.strategy_id AS id, s.family, s.population, COUNT(*) AS trades, ROUND(SUM(p.realized_pnl_usd - "
                     "p.fees_usd), 4) AS net_usd, ROUND(SUM(p.cost_usd), 2) AS deployed_usd, "
                     "SUM(CASE WHEN p.realized_pnl_usd - p.fees_usd > 0 THEN 1 ELSE 0 END) AS wins FROM positions p "
                     "LEFT JOIN strategies s ON s.id = p.strategy_id WHERE p.status = 'CLOSED' AND p.cost_usd > 0 AND "
                     "p.closed_at >= ? GROUP BY p.strategy_id ORDER BY net_usd DESC", (_iso(since),))
    fwd = {}
    for r in db.query("SELECT m.strategy_id, m.metrics FROM strategy_metrics m JOIN strategies s ON s.id = m.strategy_id WHERE "
                      "m.scope = 'forward' AND s.population IN ('PRODUCTION','CHALLENGER','SHADOW') AND m.id IN (SELECT "
                      "MAX(id) FROM strategy_metrics WHERE scope = 'forward' GROUP BY strategy_id)"):
        mm = json.loads(r["metrics"] or "{}")
        fwd[r["strategy_id"]] = {"forward_n": mm.get("n"), "forward_mean": mm.get("mean"), "forward_lb90": mm.get("lb90")}
    for s in strat:
        s.update(fwd.get(s["id"], {}))
    v = db.kv_get("velocity") or {}
    streams = sorted(({"id": s["id"], "live": s.get("live"), "tier": s.get("tier"), "n": s.get("n"),
                       "mean_per_unit": s.get("mu"), "p_positive": s.get("p_pos"), "rel_edge": s.get("rel_edge"),
                       "clusters_per_h": s.get("lam")} for s in v.get("streams", []) if s.get("n")),
                     key=lambda x: (x["mean_per_unit"] or 0) * (x["clusters_per_h"] or 0), reverse=True)
    frontier = {x["stream"]: x["usd_per_h"] for x in ((v.get("frontier") or {}).get("potential") or {}).get("streams", [])}
    for s in streams:
        s["potential_usd_per_h"] = frontier.get(s["id"], 0.0)
    return {"window": label, "strategies_best": strat[:limit], "strategies_worst": list(reversed(strat[-limit:])) if strat else [],
            "streams_ranked": streams, "note": "strategies = paper book (realized − fees); streams = shadow/live evidence "
                                               "per independent cluster; potential $/h from the profit-velocity frontier"}


# ------------------------------------------------------------------------------------------------ trades
def trades(forge: Any, window: str = "24h", book: str = "all", limit: int = 25) -> dict[str, Any]:
    db = forge.db
    since, label = parse_window(window)
    limit = max(1, min(int(limit), 100))
    out: dict[str, Any] = {"window": label}
    if book in ("all", "paper", "live"):
        cond = "" if book == "all" else " AND p.book = ?"
        args: tuple = (_iso(since),) + (() if book == "all" else (book,))
        out["positions"] = db.query(
            "SELECT p.book, p.symbol, p.strategy_id, p.status, ROUND(p.cost_usd, 2) cost_usd, p.entry_price, p.exit_price, "
            "ROUND(p.realized_pnl_usd - p.fees_usd, 4) net_usd, p.exit_reason, p.opened_at, p.closed_at FROM positions p "
            f"WHERE (p.opened_at >= ? OR p.status != 'CLOSED'){cond} AND p.cost_usd > 0 ORDER BY p.opened_at DESC LIMIT {limit}",  # noqa: S608
            args)
        out["open_now"] = sum(1 for p in out["positions"] if p["status"] != "CLOSED")
    if book in ("all", "shadow", "kalshi"):
        out["kalshi_signals"] = db.query(
            "SELECT kind, ticker, side, price, ROUND(edge, 3) edge, status, ROUND(pnl, 3) pnl, "
            "strftime('%H:%M', ts, 'unixepoch') at_utc FROM crossrail_signals WHERE ts >= ? AND kind NOT IN ('MAKE') "
            f"ORDER BY ts DESC LIMIT {limit}", (since,))  # noqa: S608
        out["kalshi_live_orders"] = db.query("SELECT ticker, side, count, avg_price, status, ROUND(pnl, 3) pnl FROM "
                                             "kalshi_live_orders WHERE ts >= ? ORDER BY ts DESC LIMIT 20", (since,))
    return out


# ------------------------------------------------------------------------------------------------ changes
def changes(forge: Any, since_window: str = "today") -> dict[str, Any]:
    db = forge.db
    since, label = parse_window(since_window)
    iso = _iso(since)
    g = db.kv_get("guardian.state") or {}
    return {
        "since": label,
        "deployments": db.query("SELECT id, title, deploy_status, substr(commit_sha, 1, 10) sha FROM eng_tickets WHERE ts >= ? "
                                "OR done_ts >= ? ORDER BY id DESC LIMIT 15", (since, since)),
        "strategy_promotions": db.query("SELECT strategy_id, from_population, to_population, substr(reason, 1, 120) reason, ts "
                                        "FROM strategy_events WHERE ts >= ? AND to_population IN ('PRODUCTION','CHALLENGER',"
                                        "'SHADOW') ORDER BY ts DESC LIMIT 15", (iso,)),
        "strategy_kills": db.scalar("SELECT COUNT(*) FROM strategy_events WHERE ts >= ? AND to_population = 'RETIRED'", (iso,)),
        "directives_completed": db.query("SELECT id, role, substr(result, 1, 300) result FROM ops_directives WHERE status = 'DONE' "
                                         "AND done_ts >= ? ORDER BY id DESC LIMIT 15", (since,)),
        "objectives": db.query("SELECT id, kind, substr(objective, 1, 120) objective, status FROM ops_objectives WHERE ts >= ? "
                               "OR done_ts >= ?", (since, since)),
        "owner_and_agent_actions": db.query("SELECT strftime('%H:%M', ts, 'unixepoch') at_utc, actor, action, outcome FROM "
                                            "ops_audit WHERE ts >= ? AND action NOT IN ('status','tool','econ','debrief',"
                                            "'capabilities','eng_next','eng_ticket','eng_queue','guardian','audit_read') "
                                            "ORDER BY id DESC LIMIT 25", (since,)),
        "incidents_repaired": [r for r in (g.get("recent_repairs") or []) if r.get("ts", 0) >= since],
        "new_listings": db.scalar("SELECT COUNT(*) FROM listing_events WHERE ts >= ?", (iso,)),
        "warnings": db.query("SELECT ts, agent, substr(message, 1, 160) message FROM timeline WHERE level IN ('warn','error') "
                             "AND ts >= ? ORDER BY id DESC LIMIT 8", (iso,)),
    }


# ------------------------------------------------------------------------------------------------ chart series
SERIES = ("treasury", "paper_equity", "usd_per_hour", "stream_pnl")


def series(forge: Any, metric: str, window: str = "24h") -> dict[str, Any]:
    db = forge.db
    since, label = parse_window(window)
    if metric == "treasury":
        pts = db.query("SELECT ts, live_total_usd v FROM econ_ticks WHERE ts >= ? ORDER BY ts", (since,))
        pts = pts[:: max(1, len(pts) // 400)]
        return {"metric": metric, "window": label, "kind": "line", "unit": "$", "points": [[p["ts"], p["v"]] for p in pts]}
    if metric == "paper_equity":
        pts = db.query("SELECT ts, equity_usd v FROM equity_series WHERE ts >= ? AND book = 'paper' ORDER BY ts", (_iso(since),))
        pts = pts[:: max(1, len(pts) // 400)]
        return {"metric": metric, "window": label, "kind": "line", "unit": "$",
                "points": [[datetime.fromisoformat(p["ts"]).timestamp(), p["v"]] for p in pts]}
    if metric == "usd_per_hour":
        pts = db.query("SELECT ts, realized_1h r, potential_usd_per_h e, target t FROM velocity_history WHERE ts >= ? ORDER BY ts",
                       (since,))
        return {"metric": metric, "window": label, "kind": "multiline", "unit": "$/h",
                "lines": {"realized (live, 1h)": [[p["ts"], p["r"]] for p in pts],
                          "potential": [[p["ts"], p["e"]] for p in pts], "target": [[p["ts"], p["t"]] for p in pts]}}
    if metric == "stream_pnl":
        rows = db.query("SELECT 'kalshi.' || kind k, ROUND(SUM(pnl), 3) v FROM crossrail_signals WHERE status='SETTLED' AND "
                        "settled_ts >= ? GROUP BY kind", (since,))
        rows += db.query("SELECT rail k, ROUND(SUM(pnl_usd), 4) v FROM shadow_trades WHERE ts >= ? GROUP BY rail", (since,))
        return {"metric": metric, "window": label, "kind": "bar", "unit": "$ (per-contract basis / shadow $)",
                "bars": [[r["k"], r["v"] or 0.0] for r in sorted(rows, key=lambda r: -(r["v"] or 0))]}
    raise ValueError(f"metric must be one of {SERIES}")


# ------------------------------------------------------------------------------------------------ rule alerts
METRICS = ("treasury_usd", "live_usd_per_h_1h", "live_net_today_usd", "paper_equity_usd", "health_score",
           "open_incidents", "potential_usd_per_h", "settled_signals_1h", "stream_tier")


def metric_value(forge: Any, metric: str, arg: str | None = None) -> Any:
    db = forge.db
    v = db.kv_get("velocity") or {}
    if metric == "treasury_usd":
        return (v.get("treasury") or {}).get("total")
    if metric == "live_usd_per_h_1h":
        return ((v.get("realized") or {}).get("1h") or {}).get("usd_per_h")
    if metric == "live_net_today_usd":
        from forge.ops.econ import window
        return window(forge, "today")["LIVE"]["true_net_usd"]
    if metric == "paper_equity_usd":
        return (getattr(forge, "treasury", {}) or {}).get("equity_usd")
    if metric == "health_score":
        h = getattr(forge, "health", None)
        sc = h.score() if h else {}
        return sc.get("overall") or sc.get("score") if isinstance(sc, dict) else sc
    if metric == "open_incidents":
        return len((db.kv_get("guardian.state") or {}).get("open_incidents") or {})
    if metric == "potential_usd_per_h":
        return (v.get("expected_usd_per_h") or {}).get("potential")
    if metric == "settled_signals_1h":
        return db.scalar("SELECT COUNT(*) FROM crossrail_signals WHERE status='SETTLED' AND settled_ts >= ?", (time.time() - 3600,))
    if metric == "stream_tier":
        return next((s.get("tier") for s in v.get("streams", []) if s.get("id") == arg), None)
    raise ValueError(f"metric must be one of {METRICS}")


def _hit(val: Any, op: str, thr: Any) -> bool:
    if val is None:
        return False
    if op in ("==", "!="):
        return (str(val) == str(thr)) == (op == "==")
    try:
        a, b = float(val), float(thr)
    except (TypeError, ValueError):
        return False
    return {"<": a < b, "<=": a <= b, ">": a > b, ">=": a >= b}.get(op, False)


def evaluate_alerts(forge: Any) -> int:
    """Edge-triggered: fires when a rule becomes true (re-arms when false again). Queues messages for the guardian."""
    db = forge.db
    fired = 0
    for r in db.query("SELECT * FROM ops_alerts WHERE active = 1"):
        try:
            val = metric_value(forge, r["metric"], r["arg"])
        except Exception:
            continue
        now_true = _hit(val, r["op"], r["threshold"])
        if now_true and not r["armed_true"]:
            fired += 1
            q = db.kv_get("ops.outbox") or []
            q.append({"ts": time.time(), "text": f"🔔 FORGE alert #{r['id']}: {r['note'] or r['metric']} — {r['metric']}"
                                                 f"{'(' + r['arg'] + ')' if r['arg'] else ''} {r['op']} {r['threshold']} "
                                                 f"(now {round(val, 4) if isinstance(val, float) else val})"})
            db.kv_set("ops.outbox", q[-50:])
            db.execute("UPDATE ops_alerts SET armed_true = 1, last_fired = ?, fire_count = fire_count + 1, active = "
                       "CASE WHEN once = 1 THEN 0 ELSE 1 END WHERE id = ?", (time.time(), r["id"]))
        elif not now_true and r["armed_true"]:
            db.execute("UPDATE ops_alerts SET armed_true = 0 WHERE id = ?", (r["id"],))
    return fired


# ------------------------------------------------------------------------------------------------ credential requests
CRED_NAME = re.compile(r"^[A-Z][A-Z0-9_]{2,63}$")
PEM_NAME = re.compile(r"^[a-z][a-z0-9_]{2,40}$")


def credential_request(db: Any, name: str, purpose: str, kind: str = "env") -> dict[str, Any]:
    if kind == "pem" and not PEM_NAME.match(name):
        raise ValueError("PEM credential name: lowercase letters/digits/_ (e.g. kalshi_private_key)")
    if kind == "env" and not CRED_NAME.match(name):
        raise ValueError("credential name: UPPER_SNAKE_CASE (e.g. KALSHI_API_KEY_ID)")
    nonce = secrets.token_urlsafe(18)
    reqs = db.kv_get("ops.cred_requests") or {}
    reqs = {k: r for k, r in reqs.items() if r["expires"] > time.time() and not r.get("used")}
    reqs[nonce] = {"name": name, "kind": kind, "purpose": purpose[:300], "expires": time.time() + 1800, "used": False}
    db.kv_set("ops.cred_requests", reqs)
    return {"link": f"https://forge.northstarimagine.com/setup/credential?r={nonce}", "name": name, "kind": kind,
            "expires_in_min": 30, "note": "one-time link for the owner (portal login required); the secret goes server-side "
                                          "only and FORGE restarts to load it"}
