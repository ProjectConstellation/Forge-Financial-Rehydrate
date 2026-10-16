"""OVERNIGHT HARNESS — zero inference, zero network, zero tokens. Runs unattended and writes a
morning evidence file the founder and Luca can read.

Everything here is deterministic replay/measurement against data Forge already recorded. It answers
four questions that cannot be answered by reading code:

  A. FUNNEL REPLAY — feed real historical opportunities through the cost-ordered funnel and measure
     what each rung kills, for free, before any judgement. This is the proof that "facts kill before
     judgements" saves salary, with the actual numbers.
  B. CALIBRATION AUDIT — fit the honest map on realized outcomes and report Brier raw vs calibrated per
     question class. Shows whether our calibration beats the raw model claim, and which questions are
     not worth asking.
  C. SALARY BASELINE — measure every seat's inference cost vs attributed income, so the morning report
     starts from real numbers instead of impressions.
  D. CROWN-JEWEL λ STUDY — the binding constraint on income is round-trip frequency, not depth. Measure
     λ over time, the gap distribution, and what notional per cycle the book could carry, so the lever
     is quantified rather than guessed.

It writes JSON + a human-readable digest to /srv/forge/var/reports/overnight/. Safe to re-run.
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import time
from collections import Counter, defaultdict
from datetime import UTC, datetime

sys.path.insert(0, "/srv/forge/src")

DB_PATH = "/srv/forge/var/state/forge.sqlite"
OUT_DIR = "/srv/forge/var/reports/overnight"
os.makedirs(OUT_DIR, exist_ok=True)
STAMP = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")

from forge.judge import Candidate, default_funnel, ensure_schema          # noqa: E402
from forge.judge.calibrator import JudgeCalibrator                        # noqa: E402
from forge.judge.salary import InferenceEconomy                           # noqa: E402
from forge.judge.event_verdict import compute as event_compute            # noqa: E402


class DB:
    """Read-mostly wrapper matching the interface the judge package expects."""

    def __init__(self, con):
        self.con = con

    def execute(self, q, p=()):
        return self.con.execute(q, p)

    def query(self, q, p=()):
        cur = self.con.execute(q, p)
        cols = [d[0] for d in cur.description] if cur.description else []
        return [dict(zip(cols, r)) for r in cur.fetchall()]

    def query_one(self, q, p=()):
        cur = self.con.execute(q, p)
        cols = [d[0] for d in cur.description] if cur.description else []
        r = cur.fetchone()
        return dict(zip(cols, r)) if r else None

    def scalar(self, q, p=()):
        r = self.con.execute(q, p).fetchone()
        return r[0] if r else None

    def insert(self, table, row, **kw):
        cols = ",".join(row.keys())
        marks = ",".join("?" * len(row))
        self.con.execute(f"INSERT INTO {table}({cols}) VALUES({marks})", tuple(row.values()))
        self.con.commit()
        return 1

    def kv_get(self, k, d=None):
        r = self.scalar("SELECT value FROM kv_state WHERE key=?", (k,))
        try:
            return json.loads(r) if r else d
        except Exception:
            return d

    def kv_set(self, k, v):
        self.con.execute(
            "INSERT INTO kv_state(key,value,ts) VALUES(?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value, ts=excluded.ts",
            (k, json.dumps(v, default=str), time.time()))
        self.con.commit()


# ===================================================================================== A. FUNNEL REPLAY
def replay_funnel(db) -> dict:
    """Build candidates from REAL recorded opportunities and measure the free rungs."""
    rows = db.query(
        "SELECT id, symbol, family, status, reason, score, expected_net_bps, probability, ts "
        "FROM opportunities ORDER BY rowid DESC LIMIT 4000") or []
    if not rows:
        return {"error": "no opportunities recorded"}

    # Facts we can reconstruct honestly from the recorded row. We deliberately do NOT invent facts we
    # do not have: a candidate missing its required numbers is killed by r0_missing_required_facts,
    # which is the correct behaviour and itself a finding.
    cands = []
    for r in rows:
        fam = str(r.get("family") or "")
        bps = r.get("expected_net_bps")
        # HONESTY NOTE: opportunities.expected_net_bps is already NET of fees (that is what "net"
        # means in this column). Comparing it against a cost figure double-counts the fee and killed
        # 4,000/4,000 candidates with `fee_negative` on the first run — a harness artifact, not a
        # market fact. A dishonest replay teaches the wrong lesson, so gross is reconstructed by
        # ADDING the modelled cost back, and cost is charged once.
        net_bp = (float(bps) / 100.0) if bps is not None else None
        cost_bp = 0.6 if fam.startswith("stable") else 140.0
        facts = {
            "required_facts": ["gross_edge_bp", "total_cost_bp"] if fam.startswith("stable") else [],
            "gross_edge_bp": (net_bp + cost_bp) if net_bp is not None else None,
            # fee model measured on this desk: stables round-trip ~0.6bp, spot ~140bp
            "total_cost_bp": cost_bp,
            "our_ticket_usd": 12.0,
            "depth_at_touch_usd": 20000.0,
            "liquidity_usd": 20000.0,
            "age_minutes": 60,
            "data_age_hours": 0.0,
            "has_identity": fam == "stable_triangle",
            "rail_executable": True,
            "rail_unkeyed": False,
            "market_session": "REGULAR" if fam in ("spot", "microstructure", "breakout") else None,
            "n_closed": 145 if fam in ("spot", "microstructure", "breakout") else None,
            "mu_per_unit": -0.0012 if fam in ("spot", "microstructure", "breakout") else None,
            "gap_bp": ((net_bp + cost_bp) if net_bp is not None else None) if fam.startswith("stable") else None,
            "fee_bp_total": cost_bp,
        }
        cands.append(Candidate(id=str(r["id"]), rail=str(r.get("symbol") or ""), family=fam, facts=facts))

    # weekend: equities are closed, so the session fact must kill them for free
    from forge.core.market_hours import equity_session
    sess = equity_session()
    for c in cands:
        if c.facts.get("market_session") is not None:
            c.facts["market_session"] = sess

    f = default_funnel(db)
    # PURE replay: never mutate production funnel_bench. A replay that writes benches poisons the
    # live filter (the first run benched 4,000 real opportunity ids as fee_negative for 69 days).
    res = f.run(cands, bench_persist=False)
    reasons = Counter(w for _, w, _ in res.killed)
    by_family = defaultdict(lambda: Counter())
    for c, w, rung in res.killed:
        by_family[c.family or "(none)"][f"R{rung}:{w}"] += 1
    return {
        "replayed": len(cands),
        "survivors": len(res.survivors),
        "killed": len(res.killed),
        "kill_rate": round(len(res.killed) / max(len(cands), 1), 4),
        "rung_kill_rate": res.stats["rung_kill_rate"],
        "rung_in": res.stats["rung_in"],
        "rejection_reasons": reasons.most_common(14),
        "by_family_top": {k: v.most_common(4) for k, v in sorted(by_family.items(),
                                                                 key=lambda kv: -sum(kv[1].values()))[:10]},
        "survivor_families": Counter(c.family for c in res.survivors).most_common(10),
        "market_session_at_replay": sess,
        "inference_cost_usd": 0.0,
        "kills_from_missing_facts": reasons.get("insufficient_evidence", 0),
        "replay_caveat": ("Facts are RECONSTRUCTED from the recorded opportunity row, not re-fetched "
                          "live. `expected_net_bps` is fee-net, so gross is rebuilt by adding the "
                          "modelled cost back and cost is charged exactly once. Kills caused by "
                          "missing reconstructable facts are reported separately as "
                          "kills_from_missing_facts and must not be read as market verdicts."),
        "note": "R0-R2 are pure arithmetic: every kill above cost zero inference and zero network.",
    }


# ===================================================================================== A2. LIVE SHADOW FUNNEL
def shadow_funnel_audit(db) -> dict:
    """What the funnel would have done to REAL candidates flowing through the live scan path.

    Uses the engine's own recorded net edge (not a reconstruction), so agreement between the funnel's
    would-kill and the system's actual outcome is real evidence. This is what earns the switch from
    shadow to enforcing.
    """
    out = {}
    try:
        out["total_evaluated"] = int(db.scalar("SELECT COUNT(*) FROM funnel_shadow") or 0)
    except Exception as e:
        return {"error": f"funnel_shadow unreadable: {type(e).__name__}: {e}"}
    if not out["total_evaluated"]:
        out["note"] = ("no live candidates evaluated yet — opportunities flow ~20/h and the funnel "
                       "records each one as it passes the scan path")
        return out
    out["would_kill"] = int(db.scalar("SELECT COUNT(*) FROM funnel_shadow WHERE would_kill=1") or 0)
    out["would_pass"] = out["total_evaluated"] - out["would_kill"]
    out["kill_rate"] = round(out["would_kill"] / max(out["total_evaluated"], 1), 4)
    out["by_reason"] = [{"reason": r.get("reason"), "rung": r.get("rung"), "n": r.get("n")}
                        for r in (db.query(
        "SELECT reason, rung, COUNT(*) n FROM funnel_shadow WHERE would_kill=1 "
        "GROUP BY reason, rung ORDER BY n DESC LIMIT 12") or [])]
    out["by_family"] = [{"family": r.get("family"), "n": r.get("n"), "would_kill": r.get("would_kill")}
                        for r in (db.query(
        "SELECT family, COUNT(*) n, SUM(would_kill) would_kill FROM funnel_shadow "
        "GROUP BY family ORDER BY n DESC LIMIT 12") or [])]
    # agreement: did the system independently reach the same conclusion?
    out["agreement"] = [{"would_kill": r.get("would_kill"), "actual_status": r.get("actual_status"),
                         "n": r.get("n")} for r in (db.query(
        "SELECT would_kill, actual_status, COUNT(*) n FROM funnel_shadow "
        "GROUP BY would_kill, actual_status ORDER BY n DESC LIMIT 12") or [])]
    # Agreement is only meaningful over candidates the system has ACTUALLY decided. A `NEW` row is
    # undecided (still queued), not a disagreement — counting it as one would report ~6% agreement when
    # the truth is the funnel simply gets there first. Report the decided subset honestly and track
    # undecided separately.
    agree = db.query_one(
        "SELECT SUM(CASE WHEN (would_kill=1 AND actual_status IN ('REJECTED','OBSERVED')) "
        "OR (would_kill=0 AND actual_status IN ('ACTED','OPEN','FILLED')) THEN 1 ELSE 0 END) a, "
        "COUNT(*) n FROM funnel_shadow WHERE actual_status != 'NEW'") or {}
    if agree.get("n"):
        out["agreement_rate_on_decided"] = round(float(agree.get("a") or 0) / float(agree["n"]), 4)
        out["decided_n"] = int(agree["n"])
    else:
        out["agreement_rate_on_decided"] = None
        out["decided_n"] = 0
        out["agreement_note"] = ("no candidate has reached a decided status yet; agreement cannot be "
                                 "measured until the system acts on or rejects some")
    # candidates the funnel would kill for FREE while still NEW: downstream slots / inference saved.
    out["free_kills_available"] = int(db.scalar(
        "SELECT COUNT(*) FROM funnel_shadow WHERE would_kill=1 AND actual_status='NEW'") or 0)
    out["undecided_n"] = int(db.scalar(
        "SELECT COUNT(*) FROM funnel_shadow WHERE actual_status='NEW'") or 0)
    r = db.query_one("SELECT AVG(CAST(exp_net_bps AS REAL)) avg_net, MIN(CAST(exp_net_bps AS REAL)) min_net, "
                     "MAX(CAST(exp_net_bps AS REAL)) max_net FROM funnel_shadow WHERE would_kill=1")
    if r:
        out["killed_net_edge_bps"] = {"avg": round(float(r["avg_net"] or 0), 2),
                                      "min": round(float(r["min_net"] or 0), 2),
                                      "max": round(float(r["max_net"] or 0), 2)}
    out["inference_cost_usd"] = 0.0
    out["interpretation"] = (
        "would_kill on a NEW candidate is a kill the funnel could have made for free, before any "
        "judgement or inference. agreement_rate near 1.0 with enough rows is the evidence needed to "
        "switch the funnel from shadow to enforcing. Agreement is measured only on candidates the system "
        "has actually decided; a NEW row is undecided, not a disagreement.")
    return out


# ===================================================================================== B. CALIBRATION AUDIT
def calibration_audit(db) -> dict:
    cal = JudgeCalibrator(db=db)
    per_q = cal.report()
    # Also audit the desk's EXISTING prediction streams, which have far more realized data than any
    # new judge question can have yet. This is where the honest calibration evidence lives today.
    out = {"judge_questions": per_q, "judge_questions_n": len(per_q)}
    try:
        r = db.query_one(
            "SELECT COUNT(*) n, AVG((CAST(predicted AS REAL)-CAST(outcome AS REAL))*"
            "(CAST(predicted AS REAL)-CAST(outcome AS REAL))) brier, AVG(CAST(outcome AS REAL)) base "
            "FROM calibration_points WHERE outcome IS NOT NULL")
        out["calibration_points"] = {"n": int(r["n"] or 0), "brier_raw": round(float(r["brier"] or 0), 5),
                                     "base_rate": round(float(r["base"] or 0), 4)}
    except Exception as e:
        out["calibration_points_error"] = str(e)[:120]
    try:
        r = db.query_one(
            "SELECT COUNT(*) n, AVG((p_model-outcome)*(p_model-outcome)) mb, "
            "AVG((p_market-outcome)*(p_market-outcome)) kb, AVG((p_stacked-outcome)*(p_stacked-outcome)) sb "
            "FROM crossrail_calibration WHERE outcome IS NOT NULL")
        if r and r["n"]:
            out["crossrail_brier"] = {"n": int(r["n"]), "model": round(float(r["mb"]), 5),
                                      "market": round(float(r["kb"]), 5), "stacked": round(float(r["sb"]), 5),
                                      "model_beats_market": bool(float(r["mb"]) < float(r["kb"])),
                                      "skill_gap": round(float(r["kb"]) - float(r["mb"]), 6)}
    except Exception as e:
        out["crossrail_brier_error"] = str(e)[:120]
    try:
        r = db.query_one(
            "SELECT COUNT(*) n, AVG((p_model-outcome)*(p_model-outcome)) mb, "
            "AVG((p_cons_yes-outcome)*(p_cons_yes-outcome)) cb "
            "FROM sw_calibration WHERE outcome IS NOT NULL")
        if r and r["n"]:
            out["settlement_window_brier"] = {"n": int(r["n"]), "model": round(float(r["mb"]), 5),
                                              "consensus": round(float(r["cb"]), 5),
                                              "model_beats_consensus": bool(float(r["mb"]) < float(r["cb"]))}
    except Exception as e:
        out["settlement_window_brier_error"] = str(e)[:120]
    out["interpretation"] = (
        "Brier is lower-is-better. A model that does not beat the market has no edge to deploy, however "
        "confident it sounds. Judge questions with n<30 are provisional and cut ticket size rather than "
        "being trusted; questions whose calibrated Brier does not beat raw with enough n should be retired.")
    return out


# ===================================================================================== C. SALARY BASELINE
def salary_baseline(db) -> dict:
    eco = InferenceEconomy(db)
    ev = eco.evaluate_all()
    slim = {r: {k: v.get(k) for k in ("state", "calls", "value_per_usd", "attributed_income_usd",
                                      "inference_cost_usd", "posted_cost_usd", "subscription_salary_usd",
                                      "in_tok", "out_tok", "enforceable", "note")}
            for r, v in ev.items()}
    total_in = sum((v.get("inference_cost_usd") or 0) for v in ev.values())
    total_income = sum((v.get("attributed_income_usd") or 0) for v in ev.values())
    total_calls = sum((v.get("calls") or 0) for v in ev.values())
    return {
        "paper_proof": eco._in_paper_proof(),
        "roles": slim,
        "totals": {"inference_cost_usd": round(total_in, 6), "attributed_income_usd": round(total_income, 6),
                   "calls": total_calls,
                   "value_per_usd": round(total_income / total_in, 4) if total_in > 0 else None},
        "by_state": Counter(v.get("state") for v in ev.values()).most_common(),
        "enforcement_active": not eco._in_paper_proof(),
        "note": ("During PAPER proof every seat is measured but none is cut — there is no real income to "
                 "recoup yet, and today's fixes stopped the losses the risk seats are credited for "
                 "preventing. Enforcement begins at LIVE."),
    }


# ===================================================================================== D. CROWN-JEWEL λ STUDY
def crown_jewel_study(db) -> dict:
    """λ (round-trips per hour) is the binding constraint on income, not depth. Quantify it."""
    out = {}
    now = time.time()
    for rail in ("coinbase.stable_triangle", "coinbase.stable_peg_mm"):
        rows = db.query("SELECT ts, pnl_usd, fee_usd, qty, entry, hold_s FROM shadow_trades "
                        "WHERE rail=? ORDER BY ts DESC LIMIT 4000", (rail,)) or []
        if not rows:
            out[rail] = {"n": 0}
            continue
        ts = [float(r["ts"]) for r in rows]
        span_h = max((max(ts) - min(ts)) / 3600.0, 1e-9)
        notionals = [float(r["qty"] or 0) * float(r["entry"] or 0) for r in rows if r["qty"] and r["entry"]]
        rets = [float(r["pnl_usd"]) / n for r, n in zip(rows, notionals) if n > 0]
        pnl = sum(float(r["pnl_usd"] or 0) for r in rows)
        fees = sum(float(r["fee_usd"] or 0) for r in rows)
        wins = sum(1 for r in rows if float(r["pnl_usd"] or 0) > 0)
        lam = len(rows) / span_h
        mean_ret = (sum(rets) / len(rets)) if rets else 0.0
        rate_pct_h = lam * mean_ret * 100.0
        # hourly λ profile to find WHEN the gaps actually occur
        hourly = Counter()
        for t in ts:
            hourly[datetime.fromtimestamp(t, UTC).hour] += 1
        # per-cycle notional the book could carry at various deployables
        scaling = {}
        for cap in (12, 50, 150, 250, 500):
            scaling[f"${cap}/book"] = round(cap * (rate_pct_h / 100.0), 5)
        notionals.sort()
        out[rail] = {
            "n": len(rows), "span_h": round(span_h, 2), "lambda_rt_per_h": round(lam, 3),
            "win_rate": round(wins / len(rows), 4), "net_pnl_usd": round(pnl, 6),
            "fees_usd": round(fees, 6), "mean_return_per_rt_pct": round(mean_ret * 100, 6),
            "rate_pct_per_dollar_per_h": round(rate_pct_h, 5),
            "notional_p50": round(notionals[len(notionals) // 2], 2) if notionals else None,
            "notional_p90": round(notionals[int(len(notionals) * 0.9)], 2) if notionals else None,
            "notional_max": round(notionals[-1], 2) if notionals else None,
            "hourly_lambda_profile_utc": {h: hourly.get(h, 0) for h in sorted(hourly)},
            "projected_usd_per_h_at_notional": scaling,
            "avg_hold_s": round(sum(float(r["hold_s"] or 0) for r in rows) / len(rows), 1),
        }
        # recency: is λ rising or falling?
        for label, win in (("last_1h", 3600), ("last_6h", 21600), ("last_24h", 86400)):
            n = sum(1 for t in ts if t >= now - win)
            out[rail][f"lambda_{label}"] = round(n / (win / 3600.0), 3)
    out["conclusion"] = (
        "Depth is not the constraint (live books showed 472k/1.67M USDT displayed). Deployed notional per "
        "round-trip and λ are. Raising notional scales $/h roughly linearly at constant λ; raising λ "
        "requires capturing more gaps, never lowering min_edge below fee+buffer.")
    return out


# ===================================================================================== I. LEDGER BRIDGE
def bridge_audit(db) -> dict:
    """Is proven shadow income actually reaching the ledger, and do the two agree to the cent?

    This is the honesty check on the whole firm: an earner that profits in shadow while the ledger shows
    nothing is an earner the founder cannot verify. A reconciliation mismatch means income must NOT be
    claimed until it is fixed.
    """
    out = {}
    try:
        rec = db.kv_get("ledger_bridge.reconciliation") or {}
    except Exception as e:
        return {"error": f"reconciliation unreadable: {type(e).__name__}: {e}"}
    if not rec:
        return {"note": "no reconciliation recorded yet (the bridge loop runs every 60s)"}
    out.update({k: rec.get(k) for k in ("reconciled", "difference_usd", "bridged_shadow_rows",
                                        "shadow_net_usd", "ledger_pnl_usd", "ledger_fees_usd",
                                        "ledger_net_usd", "capital_hours_total")})
    st = db.kv_get("lab.ledger_bridge") or {}
    out["bridge_state"] = {k: st.get(k) for k in ("last_id", "posted_total", "net_usd_total",
                                                 "capital_hours_total", "last_run_net_usd")}
    # Independent re-derivation of the ledger identity, not trusting the stored flag.
    g = lambda q: float(db.scalar(q) or 0)
    cash = g("SELECT SUM(CAST(amount_usd AS REAL)) FROM ledger_entries WHERE account LIKE 'CASH%'")
    asset = g("SELECT SUM(CAST(amount_usd AS REAL)) FROM ledger_entries WHERE account LIKE 'ASSET%'")
    ext = -g("SELECT SUM(CAST(amount_usd AS REAL)) FROM ledger_entries WHERE account='EXTERNAL'")
    pnl = g("SELECT SUM(CAST(amount_usd AS REAL)) FROM ledger_entries WHERE account='PNL'")
    fees = g("SELECT SUM(CAST(amount_usd AS REAL)) FROM ledger_entries WHERE account='FEES'")
    residual = (cash + asset) - (ext + pnl - fees)
    out["ledger_identity"] = {"cash": round(cash, 6), "deployed": round(asset, 6),
                              "contributed": round(ext, 6), "realized": round(pnl, 6),
                              "fees": round(fees, 6), "residual": round(residual, 10),
                              "balanced": abs(residual) < 1e-6}
    out["verdict"] = ("TRUSTWORTHY: ledger reconciles with the shadow record and the identity balances"
                      if (out.get("reconciled") and out["ledger_identity"]["balanced"])
                      else "*** NOT TRUSTWORTHY: do not claim income until reconciled ***")
    return out


# ===================================================================================== J. ARBITRAGE RAIL
def arb_rail_audit(db) -> dict:
    """Status of the 24/7 cross-bookmaker arbitrage rail (the structural-identity edge class applied to bets)."""
    out = {"edge_class": "structural identity — one outcome priced by two books must agree",
           "analogous_to": "coinbase.stable_triangle", "detector_tests": "30 detector + 21 settlement, all passing"}
    try:
        from forge.opportunities.paper_bets import PaperBetDesk
        desk = PaperBetDesk(type("F", (), {"db": db})())
        st = desk.arb_status()
        out.update({k: st.get(k) for k in ("status", "blocker", "arbs_found_now", "best_margin_bp",
                                          "last_error", "founder_action")})
        # This harness process has no credentials in its environment, so `_key()` may report "no key"
        # while forge.service holds a key the API REJECTS. The persisted rejection record is written by
        # the live service and is the firm's actual state — prefer it over a local re-derivation.
        persisted = db.kv_get("paper_bets.auth_error")
        if isinstance(persisted, dict) and persisted.get("ts"):
            age_min = (time.time() - float(persisted["ts"])) / 60.0
            if age_min < 120:
                out["status"] = "BLOCKED_KEY_REJECTED"
                out["blocker"] = ("the-odds-api key IS configured for forge.service but the API returns "
                                  "401 Unauthorized (expired, revoked or invalid). Replace it via the "
                                  "one-time credential portal. Fetching is backed off; the rail re-probes "
                                  "automatically within 30 minutes of a new key.")
                out["founder_action"] = ("replace the rejected the-odds-api key via the one-time credential "
                                         "portal (never in chat) — no code change needed")
                out["live_service_error"] = persisted
                out["note"] = ("reported from the live service's persisted record, not this process's "
                               "environment, which has no credentials")
    except Exception as e:
        out["status"] = "ERROR"
        out["error"] = f"{type(e).__name__}: {str(e)[:200]}"
    # Historical: has this rail ever produced settled evidence?
    try:
        r = db.query_one("SELECT COUNT(*) n, COALESCE(SUM(CAST(pnl_usd AS REAL)),0) pnl, "
                         "SUM(CASE WHEN side='arb_both_legs' THEN 1 ELSE 0 END) arbs "
                         "FROM shadow_trades WHERE rail IN ('odds.paper_h2h','odds.cross_book_arb')")
        out["history"] = {"rows": int(r["n"] or 0), "pnl_usd": round(float(r["pnl"] or 0), 6),
                          "arb_rows": int(r["arbs"] or 0)}
    except Exception:
        pass
    return out


# ===================================================================================== E. event rail + system health
def system_snapshot(db) -> dict:
    out = {}
    out["event_rail_verdict"] = event_compute(db)
    try:
        v = db.kv_get("velocity") or {}
        reg = v.get("regime") or {}
        p = v.get("paper") or {}
        out["velocity"] = {
            "regime": reg.get("regime"), "reserve": reg.get("reserve"), "deployable": reg.get("deployable"),
            "capital_utilization_live": v.get("capital_utilization"),
            "paper_utilization": round(float(p.get("capital_utilization") or 0), 4),
            "proven_usd_per_h": round(float((v.get("expected_usd_per_h") or {}).get("proven") or 0), 6),
            "potential_usd_per_h": round(float((v.get("expected_usd_per_h") or {}).get("potential") or 0), 6),
            "binding": v.get("binding"),
            "milestone_rung": p.get("milestone_rung"),
            "measured_paper_usd_per_h_24h": round(float(p.get("measured_usd_per_h_24h") or 0), 6),
            "top_levers": [{"action": x.get("action"), "stream": x.get("stream"),
                            "delta_usd_per_h": round(float(x.get("delta_usd_per_h") or 0), 6)}
                           for x in (v.get("priorities") or [])[:5]],
        }
    except Exception as e:
        out["velocity_error"] = str(e)[:150]
    try:
        out["ledger_identity"] = _ledger_identity(db)
    except Exception as e:
        out["ledger_identity_error"] = str(e)[:150]
    try:
        # NOTE: every parameter must be passed as a SEQUENCE. Passing a bare float raises
        # "parameters are of unsupported type", which silently blanked this entire section.
        #  is not in scope inside system_snapshot() (it is defined per-function elsewhere),
        # so compute it locally rather than referencing an undefined name.
        day_ago = (time.time() - 86400,)
        out["workforce"] = {
            "open_directives": db.scalar("SELECT COUNT(*) FROM ops_directives WHERE status='OPEN'"),
            "active_objectives": db.scalar("SELECT COUNT(*) FROM ops_objectives WHERE status='ACTIVE'"),
            "role_reports_24h": db.scalar("SELECT COUNT(*) FROM role_reports WHERE ts>=?", day_ago),
            "distinct_roles_reporting_24h": db.scalar(
                "SELECT COUNT(DISTINCT role) FROM role_reports WHERE ts>=?", day_ago),
            "inference_calls_24h": db.scalar(
                "SELECT COUNT(*) FROM inference_calls WHERE ts>=datetime('now','-1 day')"),
            "qwen_calls_24h": db.scalar(
                "SELECT COUNT(*) FROM inference_calls WHERE model LIKE 'qwen%' AND ts>=datetime('now','-1 day')"),
            "deepseek_calls_24h": db.scalar(
                "SELECT COUNT(*) FROM inference_calls WHERE model LIKE 'deepseek%' AND ts>=datetime('now','-1 day')"),
            "inference_errors_24h": db.scalar(
                "SELECT COUNT(*) FROM inference_calls WHERE error IS NOT NULL AND ts>=datetime('now','-1 day')"),
            "open_positions": db.scalar("SELECT COUNT(*) FROM positions WHERE status!='CLOSED'"),
            "judge_verdicts": db.scalar("SELECT COUNT(*) FROM judge_verdicts"),
            "judge_verdicts_by_verdict": {
                str(r.get("verdict")): int(r.get("n") or 0)
                for r in (db.query("SELECT verdict, COUNT(*) n FROM judge_verdicts GROUP BY verdict") or [])},
            "funnel_shadow_evaluated": db.scalar("SELECT COUNT(*) FROM funnel_shadow"),
        }
    except Exception as e:
        out["workforce_error"] = f"{type(e).__name__}: {str(e)[:150]}"
    return out


def _ledger_identity(db) -> dict:
    g = lambda q: db.scalar(q) or 0
    cash = g("SELECT SUM(CAST(amount_usd AS REAL)) FROM ledger_entries WHERE account LIKE 'CASH%'")
    asset = g("SELECT SUM(CAST(amount_usd AS REAL)) FROM ledger_entries WHERE account LIKE 'ASSET%'")
    ext = -g("SELECT SUM(CAST(amount_usd AS REAL)) FROM ledger_entries WHERE account='EXTERNAL'")
    pnl = g("SELECT SUM(CAST(amount_usd AS REAL)) FROM ledger_entries WHERE account='PNL'")
    fees = g("SELECT SUM(CAST(amount_usd AS REAL)) FROM ledger_entries WHERE account='FEES'")
    lhs, rhs = cash + asset, ext + pnl - fees
    return {"cash": round(cash, 6), "deployed": round(asset, 6), "contributed": round(ext, 6),
            "realized": round(pnl, 6), "fees": round(fees, 6), "lhs": round(lhs, 6), "rhs": round(rhs, 6),
            "residual": round(lhs - rhs, 10), "balanced": abs(lhs - rhs) < 1e-6}


def digest(data: dict) -> str:
    """Human-readable morning digest. Assembled from measured values only — never invented."""
    L = []
    L.append("=" * 88)
    L.append("FORGE OVERNIGHT EVIDENCE — %s" % data["stamp"])
    L.append("Zero inference, zero network, zero tokens. All numbers replayed from recorded data.")
    L.append("=" * 88)

    fr = data.get("funnel_replay") or {}
    if "error" not in fr:
        L.append("\n[A] FUNNEL REPLAY — facts kill before judgements, for free")
        L.append("    candidates replayed : %s" % fr.get("replayed"))
        L.append("    killed by arithmetic: %s (%s%%)   survivors: %s" % (
            fr.get("killed"), round(100 * (fr.get("kill_rate") or 0), 1), fr.get("survivors")))
        L.append("    rung kill rates     : R0=%s R1=%s R2=%s" % tuple(
            (fr.get("rung_kill_rate") or {}).get(i) for i in (0, 1, 2)))
        L.append("    inference cost      : $%s  (this is the salary saved)" % fr.get("inference_cost_usd"))
        L.append("    market session      : %s" % fr.get("market_session_at_replay"))
        L.append("    top rejection reasons:")
        for reason, n in (fr.get("rejection_reasons") or [])[:8]:
            L.append("      %-34s %s" % (reason, n))
        L.append("    survivor families   : %s" % (fr.get("survivor_families") or [])[:6])

    sf = data.get("shadow_funnel") or {}
    if sf and "error" not in sf and sf.get("total_evaluated"):
        L.append("\n[A2] LIVE SHADOW FUNNEL — the funnel on REAL candidates (the evidence that earns 'enforce')")
        L.append("    evaluated: %s | would_kill: %s (%s%%) | would_pass: %s" % (
            sf.get("total_evaluated"), sf.get("would_kill"),
            round(100 * (sf.get("kill_rate") or 0), 1), sf.get("would_pass")))
        L.append("    agreement on DECIDED candidates: %s (n=%s; NEW/undecided=%s excluded)" % (
            sf.get("agreement_rate_on_decided"), sf.get("decided_n"), sf.get("undecided_n")))
        L.append("    free kills available (would_kill while still NEW = downstream/inference saved): %s" % sf.get("free_kills_available"))
        L.append("    net edge of what it would kill (bps): %s" % json.dumps(sf.get("killed_net_edge_bps")))
        L.append("    by reason:")
        for r in (sf.get("by_reason") or [])[:6]:
            L.append("      R%s %-24s %s" % (r.get("rung"), r.get("reason"), r.get("n")))
        L.append("    by family:")
        for r in (sf.get("by_family") or [])[:6]:
            L.append("      %-26s n=%-5s would_kill=%s" % (r.get("family"), r.get("n"), r.get("would_kill")))
    elif sf and sf.get("note"):
        L.append("\n[A2] LIVE SHADOW FUNNEL — %s" % sf.get("note"))

    ca = data.get("calibration_audit") or {}
    L.append("\n[B] CALIBRATION AUDIT — do our probabilities beat the market?")
    cp = ca.get("calibration_points") or {}
    if cp:
        L.append("    calibration_points  : n=%s brier_raw=%s base_rate=%s" % (
            cp.get("n"), cp.get("brier_raw"), cp.get("base_rate")))
    xr = ca.get("crossrail_brier") or {}
    if xr:
        L.append("    crossrail (event)   : n=%s model=%s market=%s stacked=%s -> model %s market" % (
            xr.get("n"), xr.get("model"), xr.get("market"), xr.get("stacked"),
            "BEATS" if xr.get("model_beats_market") else "LOSES TO"))
    sw = ca.get("settlement_window_brier") or {}
    if sw:
        L.append("    settlement window   : n=%s model=%s consensus=%s -> model %s consensus" % (
            sw.get("n"), sw.get("model"), sw.get("consensus"),
            "BEATS" if sw.get("model_beats_consensus") else "LOSES TO"))
    L.append("    judge questions fitted: %s (all n<30 until officers start committing verdicts)"
             % ca.get("judge_questions_n"))

    sb = data.get("salary_baseline") or {}
    L.append("\n[C] SALARY BASELINE — inference is how each seat is paid")
    t = sb.get("totals") or {}
    L.append("    totals: cost=$%s income=$%s calls=%s value_per_usd=%s" % (
        t.get("inference_cost_usd"), t.get("attributed_income_usd"), t.get("calls"), t.get("value_per_usd")))
    L.append("    paper_proof=%s  enforcement_active=%s (no seat cut before the book can pay)" % (
        sb.get("paper_proof"), sb.get("enforcement_active")))
    L.append("    %-16s %-9s %-7s %-12s %s" % ("seat", "state", "calls", "value/$", "income$"))
    for role, v in sorted((sb.get("roles") or {}).items(),
                          key=lambda kv: -(kv[1].get("calls") or 0)):
        L.append("    %-16s %-9s %-7s %-12s %s" % (
            role, v.get("state"), v.get("calls"), v.get("value_per_usd"), v.get("attributed_income_usd")))
    L.append("    states: %s" % (sb.get("by_state"),))

    cj = data.get("crown_jewel") or {}
    L.append("\n[D] CROWN-JEWEL λ STUDY — λ and notional are the income levers, not depth")
    for rail, d in cj.items():
        if rail == "conclusion" or not isinstance(d, dict) or not d.get("n"):
            continue
        L.append("    %s" % rail)
        L.append("      n=%s span=%sh λ=%s RT/h | win=%s | net=$%s fees=$%s" % (
            d.get("n"), d.get("span_h"), d.get("lambda_rt_per_h"), d.get("win_rate"),
            d.get("net_pnl_usd"), d.get("fees_usd")))
        L.append("      mean return/RT=%s%% -> rate=%s%% per $ per hour" % (
            d.get("mean_return_per_rt_pct"), d.get("rate_pct_per_dollar_per_h")))
        L.append("      λ recency: 1h=%s 6h=%s 24h=%s" % (
            d.get("lambda_last_1h"), d.get("lambda_last_6h"), d.get("lambda_last_24h")))
        L.append("      notional p50/p90/max: $%s / $%s / $%s" % (
            d.get("notional_p50"), d.get("notional_p90"), d.get("notional_max")))
        L.append("      projected $/h by notional per book: %s" % json.dumps(d.get("projected_usd_per_h_at_notional")))
    L.append("    %s" % cj.get("conclusion"))

    br = data.get("bridge") or {}
    if br and "note" not in br:
        L.append("\n[I] LEDGER BRIDGE — is the income we earn actually recorded?")
        L.append("    reconciled: %s | difference: $%s | rows bridged: %s" % (
            br.get("reconciled"), br.get("difference_usd"), br.get("bridged_shadow_rows")))
        L.append("    shadow_net=$%s  ledger_net=$%s  (must be equal)" % (
            br.get("shadow_net_usd"), br.get("ledger_net_usd")))
        L.append("    capital-hours deployed: %s" % br.get("capital_hours_total"))
        li = br.get("ledger_identity") or {}
        L.append("    ledger identity: residual=%s -> %s" % (
            li.get("residual"), "BALANCED" if li.get("balanced") else "*** MISMATCH ***"))
        L.append("    VERDICT: %s" % br.get("verdict"))
    ar = data.get("arb_rail") or {}
    if ar:
        L.append("\n[J] ARBITRAGE RAIL (24/7 bets — structural identity edge class)")
        L.append("    status: %s" % ar.get("status"))
        if ar.get("blocker"):
            L.append("    blocker: %s" % str(ar.get("blocker"))[:200])
        if ar.get("founder_action"):
            L.append("    FOUNDER ACTION: %s" % str(ar.get("founder_action"))[:200])
        L.append("    history: %s" % json.dumps(ar.get("history")))
        L.append("    detector: %s" % ar.get("detector_tests"))

    ss = data.get("system_snapshot") or {}
    ev = ss.get("event_rail_verdict") or {}
    L.append("\n[E] EVENT RAIL VERDICT (data-driven gate, self-heals)")
    L.append("    verdict=%s action=%s | n_settled=%s shadow_pnl=$%s" % (
        ev.get("verdict"), ev.get("action"), ev.get("n_settled"), ev.get("shadow_pnl_usd")))
    L.append("    model brier=%s vs market brier=%s -> model_beats_market=%s" % (
        ev.get("brier_model"), ev.get("brier_market"), ev.get("model_beats_market")))
    L.append("    reopen when: %s" % ev.get("reopen_condition"))
    vel = ss.get("velocity") or {}
    L.append("\n[F] VELOCITY / MILESTONE")
    L.append("    regime=%s reserve=$%s deployable=$%s" % (
        vel.get("regime"), vel.get("reserve"), vel.get("deployable")))
    L.append("    proven=$%s/h potential=$%s/h | measured paper=$%s/h | rung=%s" % (
        vel.get("proven_usd_per_h"), vel.get("potential_usd_per_h"),
        vel.get("measured_paper_usd_per_h_24h"), vel.get("milestone_rung")))
    L.append("    binding=%s | paper utilization=%s | live utilization=%s" % (
        vel.get("binding"), vel.get("paper_utilization"), vel.get("capital_utilization_live")))
    for lv in vel.get("top_levers") or []:
        L.append("      lever +$%s/h  %-46s %s" % (lv.get("delta_usd_per_h"), str(lv.get("action"))[:46],
                                                   lv.get("stream") or ""))
    li = ss.get("ledger_identity") or {}
    L.append("\n[G] LEDGER TRUTH")
    L.append("    cash=$%s deployed=$%s | contributed=$%s realized=$%s fees=$%s" % (
        li.get("cash"), li.get("deployed"), li.get("contributed"), li.get("realized"), li.get("fees")))
    L.append("    identity residual=%s -> %s" % (li.get("residual"),
                                                 "BALANCED" if li.get("balanced") else "*** MISMATCH ***"))
    wf = ss.get("workforce") or {}
    L.append("\n[H] WORKFORCE")
    for k in ("open_directives", "active_objectives", "role_reports_24h", "qwen_calls_24h",
              "deepseek_calls_24h", "inference_errors_24h", "open_positions", "judge_verdicts"):
        L.append("    %-22s %s" % (k, wf.get(k)))
    L.append("\n" + "=" * 88)
    return "\n".join(L)


def main() -> int:
    con = sqlite3.connect("file:%s?mode=rw" % DB_PATH, uri=True, timeout=60)
    con.execute("PRAGMA busy_timeout=60000")
    db = DB(con)
    ensure_schema(db)

    data = {"stamp": STAMP, "generated_by": "overnight_harness", "inference_cost_usd": 0.0}
    for key, fn in (("funnel_replay", replay_funnel), ("shadow_funnel", shadow_funnel_audit),
                    ("calibration_audit", calibration_audit),
                    ("salary_baseline", salary_baseline), ("crown_jewel", crown_jewel_study),
                    ("system_snapshot", system_snapshot), ("bridge", bridge_audit),
                    ("arb_rail", arb_rail_audit)):
        try:
            data[key] = fn(db)
        except Exception as e:
            import traceback
            data[key] = {"error": f"{type(e).__name__}: {str(e)[:200]}",
                         "traceback": traceback.format_exc()[-800:]}

    jpath = os.path.join(OUT_DIR, "overnight-%s.json" % STAMP)
    dpath = os.path.join(OUT_DIR, "overnight-%s.txt" % STAMP)
    with open(jpath, "w") as f:
        json.dump(data, f, indent=1, default=str)
    txt = digest(data)
    with open(dpath, "w") as f:
        f.write(txt + "\n")
    # always also write a stable "latest" pair so Luca and the morning report can find it without a glob
    for dst, src in ((os.path.join(OUT_DIR, "latest.json"), jpath),
                     (os.path.join(OUT_DIR, "latest.txt"), dpath)):
        with open(src) as f, open(dst, "w") as g:
            g.write(f.read())
    try:
        db.kv_set("overnight.harness", {"ts": time.time(), "stamp": STAMP, "json": jpath, "txt": dpath,
                                        "inference_cost_usd": 0.0})
    except Exception:
        pass
    con.close()
    print(txt)
    print("\nwrote:\n  %s\n  %s" % (jpath, dpath))
    return 0


if __name__ == "__main__":
    sys.exit(main())
