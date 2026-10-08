"""Cognitive Spend Governor (lite) — refuse/record low-ROI discretionary DeepSeek calls.

Deterministic monitors never call this. Hermes/brain discretionary sessions should.
"""
from __future__ import annotations

import time
from typing import Any


ALLOWED_TRIGGERS = {
    "opportunity", "anomaly", "decision", "research", "scheduled_review",
    "incident", "optimization", "founder", "profit_recovery", "trial",
}


def gate(db: Any, *, agent: str, trigger: str, effort: str, est_cost_usd: float,
         decision_changes: bool = True) -> dict[str, Any]:
    trigger = (trigger or "unknown").lower()
    effort = (effort or "medium").lower()
    st = db.kv_get("cognitive_governor") or {"invocations": 0, "blocked": 0, "spend_usd": 0.0}
    # Paper-stage: allow research but block max-effort without decision value
    allow = True
    reason = "ok"
    if trigger not in ALLOWED_TRIGGERS and trigger != "unknown":
        allow = False
        reason = f"unknown_trigger:{trigger}"
    if effort in ("max", "xhigh") and not decision_changes and est_cost_usd > 0.05:
        allow = False
        reason = "max_effort_without_decision_value"
    # Soft daily cap from sentinel if present
    sent = db.kv_get("deepseek.sentinel") or {}
    bal = sent.get("balance")
    if allow and isinstance(bal, (int, float)) and bal < 0.25 and effort == "max":
        allow = False
        reason = "balance_too_low_for_max"
    st["invocations"] = int(st.get("invocations") or 0) + 1
    if not allow:
        st["blocked"] = int(st.get("blocked") or 0) + 1
    st["last"] = {"ts": time.time(), "agent": agent, "trigger": trigger, "effort": effort,
                  "est_cost_usd": est_cost_usd, "allow": allow, "reason": reason}
    db.kv_set("cognitive_governor", st)
    return {"allow": allow, "reason": reason, "effort": effort if allow else "medium"}
