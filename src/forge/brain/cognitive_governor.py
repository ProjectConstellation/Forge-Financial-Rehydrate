"""Inference ROI Governor — 24/7 ops without wasting DeepSeek.

Spend wisely (not a hard spend cap):
  MEDIUM      — everyday cognition (status, debriefs, simple NL, doctor/scout)
  HIGH        — hard institutional work (invention, CIO, decay, rails, eng debug)
  EXTRA_HIGH  — rare existential / LIVE-gate / major capital decisions
                (alias: xhigh → DeepSeek thinking `max`; highest spend we use)

Deterministic code owns continuous scanning/P&L/risk/feeds/health/telemetry.
DeepSeek wakes when intelligence is economically useful.
"""
from __future__ import annotations

import time
from typing import Any

from forge.config_policies import (
    INFERENCE_CHAT_ROLES,
    INFERENCE_DEFAULT_EFFORT,
    INFERENCE_HIGH_ROLES,
)

ALLOWED_TRIGGERS = {
    "opportunity", "anomaly", "decision", "research", "scheduled_review",
    "incident", "optimization", "founder", "profit_recovery", "trial",
    "edge_decay", "strategy_decay", "capital_reallocation", "new_rail",
    "engineering", "risk_investigation", "alpha_invention", "stat_diagnosis",
    "max", "extra_high", "xhigh", "existential", "major_reallocation",
    "live_gate", "root_cause_cascade", "executive_complex", "cio_decision",
    "prompt_evolution", "debrief", "status",
}

# Triggers that justify EXTRA HIGH (DeepSeek max) — keep this set small
EXTRA_HIGH_TRIGGERS = frozenset({
    "max", "extra_high", "xhigh", "existential", "live_gate",
    "root_cause_cascade", "major_reallocation",
})

HIGH_TRIGGERS = frozenset({
    "alpha_invention", "strategy_decay", "edge_decay", "capital_reallocation",
    "new_rail", "engineering", "risk_investigation", "stat_diagnosis",
    "cio_decision", "executive_complex", "prompt_evolution", "profit_recovery",
    "founder", "incident", "optimization", "decision",
})


def normalize_effort(effort: str) -> str:
    """Map aliases → medium | high | max (DeepSeek wire value for extra-high)."""
    e = (effort or INFERENCE_DEFAULT_EFFORT).lower().strip()
    if e in ("none", "low", ""):
        return INFERENCE_DEFAULT_EFFORT
    if e in ("extra_high", "xhigh", "max"):
        return "max"  # DeepSeek Thinking Mode max = our EXTRA HIGH
    if e == "high":
        return "high"
    return "medium"


def recommend_effort(agent: str, trigger: str, complex: bool = False) -> str:
    """Wise default MEDIUM; HIGH for hard work; EXTRA HIGH (max) only when truly warranted."""
    a = (agent or "").lower().strip()
    trig = (trigger or "").lower().strip()

    if trig in EXTRA_HIGH_TRIGGERS:
        return "max"

    # Complex founder/ops campaigns → HIGH (not auto EXTRA HIGH)
    if complex or trig in HIGH_TRIGGERS:
        return "high"

    # Scheduled specialist hard-roles → HIGH when woken for their craft
    if a in INFERENCE_HIGH_ROLES and trig not in ("scheduled_review", "debrief", "status", "opportunity"):
        return "high"

    # Luke / ops everyday chat stays MEDIUM unless trigger escalated above
    if a in INFERENCE_CHAT_ROLES:
        return INFERENCE_DEFAULT_EFFORT

    return INFERENCE_DEFAULT_EFFORT


def gate(db: Any, *, agent: str, trigger: str, effort: str, est_cost_usd: float,
         decision_changes: bool = True) -> dict[str, Any]:
    trigger = (trigger or "unknown").lower()
    effort = normalize_effort(effort)
    recommended = recommend_effort(agent, trigger, complex=effort in ("high", "max"))
    # Promote upward to recommended when caller under-asked; never silently jump medium→max
    rank = {"medium": 0, "high": 1, "max": 2}
    if rank.get(effort, 0) < rank.get(recommended, 0):
        # only auto-promote one step unless trigger is explicitly extra-high
        if recommended == "max" and trigger not in EXTRA_HIGH_TRIGGERS:
            effort = "high"
        else:
            effort = recommended

    st = db.kv_get("cognitive_governor") or {"invocations": 0, "blocked": 0, "spend_usd": 0.0}
    allow = True
    reason = "ok"
    if trigger not in ALLOWED_TRIGGERS and trigger != "unknown":
        allow = False
        reason = f"unknown_trigger:{trigger}"
    # EXTRA HIGH requires a decision that can change capital/risk/infra — wise gate, not a spend cap
    if effort == "max" and not decision_changes and est_cost_usd > 0.05:
        allow = False
        reason = "extra_high_without_decision_value"
        effort = "high"  # fall back to HIGH rather than block entirely when possible
        allow = True
        reason = "downgraded_extra_high_to_high"
    sent = db.kv_get("deepseek.sentinel") or {}
    bal = sent.get("balance")
    if allow and isinstance(bal, (int, float)) and bal < 0.15 and effort == "max":
        effort = "high"
        reason = "balance_low_extra_high_to_high"
    st["invocations"] = int(st.get("invocations") or 0) + 1
    if not allow:
        st["blocked"] = int(st.get("blocked") or 0) + 1
    st["last"] = {"ts": time.time(), "agent": agent, "trigger": trigger, "effort": effort,
                  "recommended": recommended, "est_cost_usd": est_cost_usd, "allow": allow, "reason": reason,
                  "policy": "medium_everyday_high_hard_extra_high_rare"}
    st["policy"] = "medium_everyday_high_hard_extra_high_rare"
    db.kv_set("cognitive_governor", st)
    return {"allow": allow, "reason": reason, "effort": effort if allow else INFERENCE_DEFAULT_EFFORT}
