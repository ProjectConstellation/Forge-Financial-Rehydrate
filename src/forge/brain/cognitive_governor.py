"""Inference ROI Governor — 24/7 ops without wasting DeepSeek.

Deterministic code owns continuous scanning/P&L/risk/feeds/health/telemetry.
DeepSeek wakes when intelligence is economically useful.
Normal minimum effort: MEDIUM. HIGH for hard institutional work.
"""
from __future__ import annotations

import time
from typing import Any

from forge.config_policies import INFERENCE_DEFAULT_EFFORT, INFERENCE_HIGH_ROLES

ALLOWED_TRIGGERS = {
    "opportunity", "anomaly", "decision", "research", "scheduled_review",
    "incident", "optimization", "founder", "profit_recovery", "trial",
    "edge_decay", "strategy_decay", "capital_reallocation", "new_rail",
    "engineering", "risk_investigation", "alpha_invention", "stat_diagnosis",
}


def recommend_effort(agent: str, trigger: str, complex: bool = False) -> str:
    a = (agent or "").lower()
    if complex or a in INFERENCE_HIGH_ROLES or (trigger or "").lower() in {
        "alpha_invention", "strategy_decay", "edge_decay", "capital_reallocation",
        "new_rail", "engineering", "risk_investigation", "stat_diagnosis", "founder",
    }:
        return "high"
    return INFERENCE_DEFAULT_EFFORT  # medium


def gate(db: Any, *, agent: str, trigger: str, effort: str, est_cost_usd: float,
         decision_changes: bool = True) -> dict[str, Any]:
    trigger = (trigger or "unknown").lower()
    effort = (effort or INFERENCE_DEFAULT_EFFORT).lower()
    # Enforce medium minimum (never none/low for discretionary agent cognition)
    if effort in ("none", "low", ""):
        effort = INFERENCE_DEFAULT_EFFORT
    recommended = recommend_effort(agent, trigger, complex=effort in ("high", "max"))
    if effort == "medium" and recommended == "high":
        effort = "high"
    st = db.kv_get("cognitive_governor") or {"invocations": 0, "blocked": 0, "spend_usd": 0.0}
    allow = True
    reason = "ok"
    if trigger not in ALLOWED_TRIGGERS and trigger != "unknown":
        allow = False
        reason = f"unknown_trigger:{trigger}"
    if effort in ("max", "xhigh") and not decision_changes and est_cost_usd > 0.05:
        allow = False
        reason = "max_effort_without_decision_value"
    sent = db.kv_get("deepseek.sentinel") or {}
    bal = sent.get("balance")
    if allow and isinstance(bal, (int, float)) and bal < 0.25 and effort == "max":
        allow = False
        reason = "balance_too_low_for_max"
    st["invocations"] = int(st.get("invocations") or 0) + 1
    if not allow:
        st["blocked"] = int(st.get("blocked") or 0) + 1
    st["last"] = {"ts": time.time(), "agent": agent, "trigger": trigger, "effort": effort,
                  "recommended": recommended, "est_cost_usd": est_cost_usd, "allow": allow, "reason": reason}
    db.kv_set("cognitive_governor", st)
    return {"allow": allow, "reason": reason, "effort": effort if allow else INFERENCE_DEFAULT_EFFORT}
