"""FORGE Agent API — the ONLY door between Hermes (or any external agent) and FORGE (Hermes dossier §4, OP-015/OP-017).

Auth: a dedicated agent token (`run/agent_token`, separate from the operator token). It is accepted ONLY on /api/agent/*,
never on operator controls (STOP ALL, cash-out, live mode). No exchange keys, no orders, no DB writes outside research
artifacts. Every call is attributed (intel_artifacts) and every Hermes token is costed into the same ledger as FORGE's
own brain (inference_calls + OPEX:INFERENCE) so Hermes must earn its keep under the same value-per-$ law.

Endpoints
  GET  /api/agent/tools          tool schemas (FORGE ToolRouter — identical tools to FORGE's own brain)
  POST /api/agent/tool           {name, args, role, session_id} → result (artifacts attributed to hermes_<role>)
  POST /api/agent/usage          {api_request_id, role, model, usage, session_id} → cost recorded (idempotent)
  GET  /api/agent/allow          ?role=&est_usd= → {"wake": bool, ...}  budget gate used by Hermes pre-run scripts
  GET  /api/agent/digest         ?since=<ts> → what changed (listing/rail/strategy/evidence/incidents) since a timestamp
"""

from __future__ import annotations

import hmac
import json
import secrets
import time
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request

HERMES_ROLES = ("governor", "scout", "scientist", "critic", "doctor")
HERMES_SHARE_PRIOR = 0.40          # share of the Intelligence Treasury pace Hermes may use before its value is measured


def agent_token(home: Path) -> str:
    p = home / "run" / "agent_token"
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(secrets.token_urlsafe(32))
        p.chmod(0o600)
    return p.read_text().strip()


def is_agent_request(req: Request, token: str) -> bool:
    a = req.headers.get("authorization", "")
    return a.startswith("Bearer ") and hmac.compare_digest(a[7:].strip(), token)


# External (non-DeepSeek) model list prices, USD per 1M tokens — used to MEASURE value-per-$ even when compute is free.
EXTERNAL_PRICES = {"claude-opus-5-5": {"in": 5.0, "out": 25.0, "cache": 0.5}}


def hermes_spent_24h(db: Any, external: bool = False) -> float:
    from datetime import UTC, datetime, timedelta
    cut = (datetime.now(UTC) - timedelta(hours=24)).isoformat()
    cond = "model LIKE 'claude%'" if external else "model NOT LIKE 'claude%'"
    return float(db.scalar("SELECT COALESCE(SUM(CAST(cost_usd AS REAL)),0) FROM inference_calls "
                           f"WHERE agent LIKE 'hermes%' AND {cond} AND ts >= ?", (cut,)) or 0.0)


def credit_allowance(forge: Any, mode: dict[str, Any]) -> dict[str, Any]:
    """Free operator credit (e.g. Opus 5.5 for 72 h): not a FORGE expense, but paced so it lasts the whole window."""
    from datetime import UTC, datetime
    start, hours, credit = float(mode["start"]), float(mode.get("hours", 72)), float(mode.get("credit_usd", 180))
    used = float(forge.db.scalar("SELECT COALESCE(SUM(CAST(cost_usd AS REAL)),0) FROM inference_calls WHERE agent LIKE "
                                 "'hermes%' AND model LIKE 'claude%' AND ts >= ?",
                                 (datetime.fromtimestamp(start, UTC).isoformat(),)) or 0.0)
    elapsed_h = max((time.time() - start) / 3600, 0.0)
    left_h = max(hours - elapsed_h, 0.0)
    # pace: credit spread evenly over the window, with catch-up allowed (unused earlier budget is spendable later)
    allowed_so_far = credit * min(1.0, (elapsed_h + 2.0) / hours)
    return {"mode": "credit", "credit_usd": credit, "used_usd": used, "hours_left": left_h, "budget_24h": credit / hours * 24,
            "spent_24h": hermes_spent_24h(forge.db, external=True), "headroom": allowed_so_far - used,
            "expired": left_h <= 0, "pace": f"free credit ${credit:.0f}/{hours:.0f}h, used ${used:.2f}"}


def hermes_allowance(forge: Any) -> dict[str, Any]:
    """Hermes' slice of the live intelligence pace: prior 40%, then proportional to measured value-per-$ vs FORGE's brain.
    In operator-credit mode (OP-018) the free credit pool is used instead."""
    mode = forge.db.kv_get("hermes.mode") or {}
    if mode.get("mode") == "credit":
        a = credit_allowance(forge, mode)
        if not a["expired"]:
            return a
    b = getattr(forge, "brain", None)
    if b is None:
        return {"wake": False, "reason": "no brain/DeepSeek configured"}
    p = b.pace()
    h_roi = max(b.roi(f"hermes_{r}") for r in HERMES_ROLES)
    f_roi = max(b.roi(r) for r in ("perception", "scientist"))
    share = min(0.7, max(0.1, HERMES_SHARE_PRIOR * h_roi / max(f_roi, 1e-6)))
    spent = hermes_spent_24h(forge.db, external=False)
    allow = p.budget_24h * share
    return {"budget_24h": allow, "spent_24h": spent, "headroom": allow - spent, "share": share,
            "hermes_value_per_usd": h_roi, "forge_value_per_usd": f_roi, "balance": b.balance, "pace": p.reason}


def digest(forge: Any, since: float) -> dict[str, Any]:
    """Compact change feed so Hermes pre-run scripts wake the LLM only when something economically meaningful happened."""
    from datetime import UTC, datetime
    iso = datetime.fromtimestamp(since, UTC).isoformat()
    db = forge.db
    ev = db.query("SELECT ts, product_id, event FROM listing_events WHERE ts >= ? ORDER BY id DESC LIMIT 50", (iso,))
    tr = db.query("SELECT ts, agent, message FROM timeline WHERE ts >= ? AND level IN ('warn','error') ORDER BY id DESC LIMIT 20",
                  (iso,))
    st = db.query("SELECT ts, strategy_id, from_population, to_population, reason FROM strategy_events WHERE ts >= ? ORDER BY ts DESC "
                  "LIMIT 20", (iso,)) if db.scalar("SELECT 1 FROM sqlite_master WHERE name='strategy_events'") else []
    settled = db.scalar("SELECT COUNT(*) FROM crossrail_signals WHERE status='SETTLED' AND settled_ts >= ?", (since,)) or 0
    sc = db.kv_get("crossrail.scorecard") or {}
    return {"since": since, "now": time.time(), "listing_events": ev, "warnings": tr, "strategy_events": st,
            "crossrail_settled_since": settled,
            "crossrail": {k: sc.get(k) for k in ("calibration_n", "brier_model", "brier_market", "brier_stacked",
                                                 "model_weight_share", "signals")},
            "treasury": {k: forge.treasury.get(k) for k in ("equity_usd", "true_net_usd", "daily_pnl_usd")},
            "meaningful": bool(ev or tr or st or settled >= 10)}


def mount(app: FastAPI, forge: Any, token: str) -> None:
    from forge.brain.tools import TOOLS, ToolRouter

    def check(req: Request) -> None:
        if not is_agent_request(req, token):
            raise HTTPException(401, "agent token required")

    @app.get("/api/agent/tools")
    async def tools(request: Request) -> Any:
        check(request)
        return {"tools": TOOLS}

    @app.post("/api/agent/tool")
    async def tool(request: Request) -> Any:
        check(request)
        body = await request.json()
        role = str(body.get("role") or "governor")
        role = role if role in HERMES_ROLES else "governor"
        call_id = f"hermes:{str(body.get('session_id') or 'na')[:60]}"
        router = ToolRouter(forge, call_id, f"hermes_{role}")
        out = await router.dispatch(str(body.get("name", "")), json.dumps(body.get("args") or {}))
        for a in router.artifacts:
            forge.db.insert("intel_artifacts", {"ts": _now(), "call_id": call_id, "role": f"hermes_{role}",
                                                "model": str(body.get("model") or "deepseek-flash"), "kind": a["kind"],
                                                "ref_id": a.get("ref_id"), "prediction": None, "detail": None})
        return json.loads(out)

    @app.post("/api/agent/usage")
    async def usage(request: Request) -> Any:
        check(request)
        b = await request.json()
        rid = f"hermes_{str(b.get('api_request_id') or secrets.token_hex(8))[:60]}"
        if forge.db.scalar("SELECT 1 FROM inference_calls WHERE id = ?", (rid,)):
            return {"ok": True, "duplicate": True}
        u = b.get("usage") or {}
        cache = int(u.get("prompt_cache_hit_tokens") or u.get("cache_read_input_tokens") or u.get("cache_read_tokens")
                    or u.get("cached_tokens") or 0)
        if u.get("prompt_tokens") is not None:                 # OpenAI/DeepSeek shape: prompt includes cached
            prompt = int(u["prompt_tokens"])
        else:                                                  # Anthropic shape: input excludes cache reads
            prompt = int(u.get("input_tokens") or 0) + (cache if "cache_read_input_tokens" in u else 0)
        usage_n = {"prompt_tokens": prompt, "completion_tokens": int(u.get("completion_tokens") or u.get("output_tokens") or 0),
                   "prompt_cache_hit_tokens": cache}
        model = str(b.get("model") or "deepseek-flash")
        role = str(b.get("role") or "governor")
        brain = getattr(forge, "brain", None)
        ext = EXTERNAL_PRICES.get(model)
        if ext:      # list-price cost for value measurement; free operator credit → NOT a treasury expense
            cost = ((usage_n["prompt_tokens"] - usage_n["prompt_cache_hit_tokens"]) * ext["in"]
                    + usage_n["prompt_cache_hit_tokens"] * ext["cache"] + usage_n["completion_tokens"] * ext["out"]) / 1e6
        else:
            cost = brain.c.cost(model if model in forge.s.deepseek.prices else "deepseek-flash", usage_n) if brain else 0.0
        forge.db.insert("inference_calls", {
            "id": rid, "ts": _now(), "agent": f"hermes_{role}", "purpose": str(b.get("purpose") or "hermes")[:80],
            "model": model, "effort": b.get("effort"), "prompt_version": "hermes",
            "input_tokens": usage_n["prompt_tokens"], "cached_tokens": usage_n["prompt_cache_hit_tokens"],
            "output_tokens": usage_n["completion_tokens"], "cost_usd": f"{cost:.8f}", "latency_ms": int(b.get("latency_ms") or 0),
            "tool_calls": None, "result_class": "hermes", "strategy_id": None, "opportunity_id": None, "error": None})
        if cost > 0 and not ext:
            forge.ledger.record_opex(forge.book if forge.book in ("live", "paper") else "paper", "INFERENCE",
                                     Decimal(f"{cost:.8f}"), rid, memo=f"hermes {role}")
        return {"ok": True, "cost_usd": cost}

    @app.get("/api/agent/allow")
    async def allow(request: Request, role: str = "governor", est_usd: float = 0.01) -> Any:
        check(request)
        a = hermes_allowance(forge)
        credit = a.get("mode") == "credit"
        a["wake"] = bool(a.get("headroom", 0) >= est_usd) and (credit or getattr(forge.brain, "tier", "") != "CRITICAL")
        a["role"] = role
        return a

    @app.get("/api/agent/digest")
    async def dig(request: Request, since: float = 0.0) -> Any:
        check(request)
        return digest(forge, since or time.time() - 3600)


def _now() -> str:
    from datetime import UTC, datetime
    return datetime.now(UTC).isoformat()
