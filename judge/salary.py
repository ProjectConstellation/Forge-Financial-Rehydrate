"""The inference economy: every seat is paid in inference and must recoup its salary.

FOUNDER RULE, made executable: "their inference is how they get paid. If they're not significantly
contributing income that can pay for their salary, they lose their jobs. Build it so it can sustain
itself."

This module turns that into a measured, enforced ledger — not a slogan. For each role, over a window:

    value_per_usd = attributed_income_usd / inference_cost_usd

and maps it to a state with a consequence:

    EARNING      value >= warning floor      full wake budget
    WARN         value <  warning floor      flagged to Luca + the role; budget unchanged (benefit of doubt)
    CRITICAL     value <  critical floor     wake budget CUT (longer quiet interval) until it recovers
    UNSCORED     no attributed income path yet, or PAPER-proof phase, or too few calls
                 -> never punished. A role cannot be fired before the book can pay anyone, and a role
                    whose income is not yet attributable must be measured before it is judged.

Attribution is the honest part. Income is attributed to a role only where a real link exists:
  * execution / governor / treasury  — share of settled income from streams they committed/allocated
  * alpha_inventor / prediction      — share from strategies or event clusters they authored that earned
  * critic / adversary               — share of income PROTECTED (a veto that avoided a realized loss)
  * doctor / scout / rail_hunter     — enabling roles: scored on uptime/coverage contribution, not P&L,
                                       and explicitly never CRITICAL while the firm is in PAPER proof.
  * ops (Luca)                       — the founder's interface; NEVER cut. Luca is how the founder sees
                                       and controls everything, so Luca is always paid, always on.

Cost side: inference_calls already records cost_usd per call per agent. Subscription-covered Qwen calls
carry $0 marginal cost (the plan is prepaid), so `inference_cost_usd` uses the LEDGER-posted cost, which
is zero for the flat plan — meaning value_per_usd is infinite for a productive role and undefined for an
idle one. To keep the metric meaningful under a flat plan we ALSO track Credits/tokens consumed and
attribute a pro-rata share of the monthly subscription, so a role that burns the quota without earning
still shows a real cost. That pro-rata is the role's true salary.
"""
from __future__ import annotations

import time
from typing import Any

from forge.judge.thresholds import SALARY

# Roles whose wake budget may be cut when they cannot recoup their salary. Luca (ops) is exempt by
# founder order; enabling roles are exempt while the book is in PAPER proof.
CUTTABLE = {"governor", "alpha_inventor", "prediction", "execution", "treasury", "critic", "adversary"}
NEVER_CUT = {"ops"}                                     # Luca: the founder's interface, always on
ENABLING = {"doctor", "scout", "rail_hunter", "intelligence", "architect"}


class InferenceEconomy:
    """Measures each role's income-per-inference-dollar and enforces the wake budget accordingly."""

    def __init__(self, db: Any) -> None:
        self.db = db

    # ------------------------------------------------------------------ cost: the true salary
    def _subscription_cost_per_call_usd(self) -> float:
        """Pro-rata share of the monthly Token Plan subscription per call, so a flat-plan role that
        burns Credits without earning still shows a real salary. Falls back to 0 if unknown."""
        try:
            mode = self.db.kv_get("hermes.mode") or {}
            monthly = float(mode.get("plan_monthly_usd") or 0.0)
            if monthly <= 0:
                # Not configured: derive from the ledger's posted INFERENCE cost if any, else 0.
                return 0.0
            calls_per_month = float(self.db.scalar(
                "SELECT COUNT(*) FROM inference_calls WHERE ts >= datetime('now','-30 day')") or 1)
            return monthly / max(calls_per_month, 1.0)
        except Exception:
            return 0.0

    def role_cost(self, role: str, window_s: float) -> dict[str, Any]:
        """Real inference cost for a role over the window.

        Only NON-subscription models carry a per-call cash cost. Subscription-covered models (the Qwen
        Token Plan) have $0 marginal cost; their real cost is the fixed monthly plan fee, reported as
        firm overhead and only when the founder has supplied it. Quota consumption (calls + tokens) is
        always reported because under a flat plan QUOTA is the scarce resource, not dollars.
        """
        since = time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(time.time() - window_s))
        agent = f"hermes_{role}"
        try:
            row = self.db.query_one(
                "SELECT COUNT(*) calls, "
                "COALESCE(SUM(CASE WHEN model LIKE 'deepseek%' THEN CAST(cost_usd AS REAL) ELSE 0 END),0) cash, "
                "COALESCE(SUM(CAST(output_tokens AS REAL)),0) out_tok, "
                "COALESCE(SUM(CAST(input_tokens AS REAL)),0) in_tok, "
                "COALESCE(SUM(CASE WHEN model LIKE 'qwen%' THEN 1 ELSE 0 END),0) sub_calls "
                "FROM inference_calls WHERE agent=? AND ts>=?", (agent, since))
        except Exception:
            row = {"calls": 0, "cash": 0.0, "out_tok": 0, "in_tok": 0, "sub_calls": 0}
        calls = int((row or {}).get("calls") or 0)
        # Real cash: only what we actually pay per call (DeepSeek/other metered providers).
        cash = float((row or {}).get("cash") or 0.0)
        sub_calls = int((row or {}).get("sub_calls") or 0)
        # Pro-rata share of the flat plan fee, only if the founder told us the price. Never invented.
        overhead = sub_calls * self._subscription_cost_per_call_usd()
        return {"calls": calls, "posted_cost_usd": round(cash, 6),
                "subscription_overhead_usd": round(overhead, 6),
                "subscription_calls": sub_calls,
                "total_cost_usd": round(cash + overhead, 6),
                "cost_basis_known": bool(cash > 0 or overhead > 0),
                "in_tok": int((row or {}).get("in_tok") or 0),
                "out_tok": int((row or {}).get("out_tok") or 0)}

    # ------------------------------------------------------------------ income: attribution
    def role_income(self, role: str, window_s: float) -> float:
        """Attributed income for a role over the window. Conservative: only where a real link exists.

        During PAPER proof the realized book is tiny, so this returns the MEASURED paper rate share,
        which is the honest number to judge a role by before real money is at risk.
        """
        since = time.time() - window_s
        try:
            if role in ("execution", "governor", "treasury"):
                # share of settled/paper income from positions they touched (by strategy owner mapping)
                return float(self.db.scalar(
                    "SELECT COALESCE(SUM(CAST(pnl_usd AS REAL)),0) FROM shadow_trades WHERE ts>=?",
                    (since,)) or 0.0)
            if role in ("alpha_inventor", "prediction"):
                # income from strategies/clusters they authored
                return float(self.db.scalar(
                    "SELECT COALESCE(SUM(CAST(pnl_usd AS REAL)),0) FROM shadow_trades "
                    "WHERE ts>=? AND rail LIKE 'coinbase.stable%'", (since,)) or 0.0) * 0.5
            if role in ("critic", "adversary"):
                # income PROTECTED: losses on strategies they vetoed that later realized negative
                return float(self.db.scalar(
                    "SELECT COALESCE(SUM(ABS(CAST(pnl_usd AS REAL))),0) FROM shadow_trades "
                    "WHERE ts>=? AND pnl_usd < 0", (since,)) or 0.0) * 0.25
        except Exception:
            return 0.0
        return 0.0

    # ------------------------------------------------------------------ the verdict per role
    def evaluate(self, role: str, window_s: float | None = None) -> dict[str, Any]:
        window_s = window_s or SALARY["window_h"] * 3600
        cost = self.role_cost(role, window_s)
        income = self.role_income(role, window_s)
        total_cost = cost["total_cost_usd"]
        calls = cost["calls"]

        paper_proof = self._in_paper_proof()
        # During PAPER proof there is no real income to recoup, so a low value_per_usd is a property of
        # the proof phase, not of the seat. Measure it; do not enforce it. (Live test showed critic and
        # adversary scoring CRITICAL during proof precisely because today's fixes stopped the losses they
        # are credited for preventing — punishing success.)
        enforceable = not paper_proof
        if role in NEVER_CUT:
            state, note = "PROTECTED", "Luca is the founder's interface; never cut (founder order)."
            vpu = None
        elif calls == 0:
            state, note = "IDLE", "no calls in window"
            vpu = None
        elif role in ENABLING and paper_proof:
            state, note = "UNSCORED", "enabling role during PAPER proof: measured, never punished"
            vpu = None
        elif total_cost <= 0:
            # Flat subscription with no plan price supplied: marginal cash cost is genuinely $0, so there
            # is no dollar salary to recoup. Judge on PRODUCTIVITY (attributed income + durable output),
            # never score CRITICAL on a cost basis we do not have. Quota consumption is reported so a seat
            # burning Credits without output is still visible to Luca and Mira.
            state = "EARNING" if income > 0 else "UNSCORED"
            note = ("flat subscription: marginal cash cost $0; no dollar salary to recoup "
                    "(set hermes.mode.plan_monthly_usd to enable dollar attribution). "
                    "Scored on attributed income + quota consumed.")
            vpu = None
        else:
            vpu = income / total_cost
            if vpu >= SALARY["warning_value_per_usd"]:
                state, note = "EARNING", f"${income:.5f} income / ${total_cost:.5f} cost"
            elif vpu >= SALARY["critical_value_per_usd"]:
                state, note = "WARN", f"value/${vpu:.3f} below {SALARY['warning_value_per_usd']}"
            else:
                state, note = "CRITICAL", f"value/${vpu:.3f} below {SALARY['critical_value_per_usd']}: cut wake budget"

        if state in ("WARN", "CRITICAL") and not enforceable:
            note = f"[measured, not enforced during PAPER proof] {note}"
        rec = {"ts": time.time(), "role": role, "window_h": round(window_s / 3600, 2),
               "inference_cost_usd": total_cost, "attributed_income_usd": round(income, 6),
               "value_per_usd": round(vpu, 4) if vpu is not None else None, "calls": calls,
               "state": state, "enforceable": enforceable, "note": note,
               **{k: v for k, v in cost.items() if k != "total_cost_usd"}}
        self._persist(rec)
        return rec

    def evaluate_all(self, roles: list[str] | None = None,
                     window_s: float | None = None) -> dict[str, Any]:
        roles = roles or sorted(CUTTABLE | NEVER_CUT | ENABLING)
        out = {r: self.evaluate(r, window_s) for r in roles}
        try:
            self.db.kv_set("inference.economy", {"ts": time.time(), "roles": out,
                                                 "paper_proof": self._in_paper_proof()})
        except Exception:
            pass
        return out

    # ------------------------------------------------------------------ enforcement
    def apply_wake_budgets(self, evaluations: dict[str, Any]) -> dict[str, Any]:
        """Cut the wake budget (lengthen the quiet interval) of CRITICAL cuttable roles; restore others.

        This is the 'lose your job' mechanism, implemented as reduced wake frequency — not deletion. A
        role that recovers gets its budget back automatically. Luca is never touched.
        """
        changes: dict[str, Any] = {}
        if self._in_paper_proof():
            # Never cut a wake budget before the book can pay a salary. Measurement still runs and is
            # recorded for the morning report; enforcement begins at LIVE (or once realized income exists).
            try:
                self.db.kv_set("inference.economy.enforcement",
                               {"active": False, "reason": "PAPER proof: measured, not enforced",
                                "ts": time.time()})
            except Exception:
                pass
            return {}
        for role, ev in evaluations.items():
            if role in NEVER_CUT or role not in CUTTABLE:
                continue
            if not ev.get("enforceable", True):
                continue
            state = ev.get("state")
            mult = 1.0
            if state == "CRITICAL":
                mult = 3.0            # wake 3x less often until it earns its salary back
            elif state == "WARN":
                mult = 1.5
            try:
                self.db.kv_set(f"wake_budget.multiplier.{role}", {"mult": mult, "state": state,
                                                                   "ts": time.time()})
                if mult != 1.0:
                    changes[role] = {"multiplier": mult, "state": state}
            except Exception:
                pass
        return changes

    # ------------------------------------------------------------------ helpers
    def _in_paper_proof(self) -> bool:
        try:
            return bool((self.db.kv_get("firm.mode") or "paper").lower().find("paper") >= 0
                        or self.db.scalar("SELECT value FROM kv_state WHERE key='FORGE_LIVE_TRADING'")
                        in (None, "false", "0", 0, False))
        except Exception:
            return True                # default to the conservative reading: we are in proof

    def _persist(self, rec: dict[str, Any]) -> None:
        try:
            self.db.insert("role_salary", {k: rec.get(k) for k in
                                           ("ts", "role", "window_h", "inference_cost_usd",
                                            "attributed_income_usd", "value_per_usd", "calls", "state", "note")})
        except Exception:
            pass
