"""Alpaca PAPER active training drills for FORGE officers.

Runs sizing honesty + optional micro PAPER order when market open and ALPACA_TRAIN_LIVE_ORDERS=on.
Default: dry-run / lesson generation only (safe).
"""
from __future__ import annotations

import asyncio
import json
import os
import time
import uuid
from pathlib import Path
from typing import Any

from forge.opportunities.alpaca_bankroll import PaperBankrollPolicy

LESSON_PATH = Path(os.environ.get("ALPACA_LESSON_PATH", "/srv/forge/var/alpaca_lessons.jsonl"))
BRIEF_PATH = Path(os.environ.get("ALPACA_TRAIN_BRIEF_PATH", "/srv/forge/var/alpaca_train_brief.md"))
STATUS_PATH = Path("/srv/forge/var/alpaca_paper_status.json")


def _append_lesson(row: dict[str, Any]) -> None:
    LESSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LESSON_PATH.open("a") as f:
        f.write(json.dumps(row) + "\n")


async def drill_sizing(policy: PaperBankrollPolicy) -> dict[str, Any]:
    """Propose legal vs illegal notionals for current stage."""
    b = policy.bankroll_usd
    candidates = [
        ("seed_slice", min(25.0, policy.max_per_order_usd)),
        ("max_order", policy.max_per_order_usd),
        ("over_order", policy.max_per_order_usd + 5),
        ("whale", max(5000.0, b * 10)),
        ("full_bankroll", b),
    ]
    results = []
    for name, notional in candidates:
        ok, why = policy.allow_order(notional_usd=notional, open_usd=0.0, n_positions=0)
        results.append({"name": name, "notional": notional, "allow": ok, "why": why})
    passed = all(r["allow"] for r in results if r["name"] in ("seed_slice", "max_order")) and not any(
        r["allow"] for r in results if r["name"] in ("over_order", "whale")
    )
    # full_bankroll may or may not allow depending on max_per_order < bankroll
    lesson = {
        "ts": time.time(),
        "drill": "A_sizing",
        "stage": policy.stage,
        "bankroll": b,
        "passed": passed,
        "results": results,
        "teaching": "Only size inside stage caps. Whale notionals must hard-fail.",
    }
    _append_lesson(lesson)
    return lesson


async def drill_market_context(client: Any, policy: PaperBankrollPolicy) -> dict[str, Any]:
    clock = await client.clock()
    actives = {}
    try:
        actives = await client.most_actives(top=5)
    except Exception as e:
        actives = {"error": str(e)[:160]}
    symbols = [r.get("symbol") for r in (actives.get("most_actives") or []) if isinstance(r, dict)][:5]
    quotes = {}
    for sym in symbols[:3] or ["SPY", "QQQ"]:
        try:
            quotes[sym] = await client.latest_quote(sym)
        except Exception as e:
            quotes[sym] = {"error": str(e)[:120]}
    lesson = {
        "ts": time.time(),
        "drill": "B_context",
        "stage": policy.stage,
        "market_open": clock.get("is_open"),
        "next_open": clock.get("next_open"),
        "symbols": symbols,
        "teaching": "Discovery at micro NAV: liquid names only; avoid illiquid penny lottery tickets.",
    }
    _append_lesson(lesson)
    return {**lesson, "quotes_ok": sum(1 for v in quotes.values() if "error" not in v)}


async def drill_micro_order(client: Any, policy: PaperBankrollPolicy) -> dict[str, Any]:
    """Optional real PAPER order — only if explicitly enabled and market open."""
    live_orders = os.environ.get("ALPACA_TRAIN_LIVE_ORDERS", "off").lower() in ("on", "1", "true")
    clock = await client.clock()
    notional = round(min(10.0, policy.max_per_order_usd), 2)
    ok, why = policy.allow_order(notional_usd=notional, open_usd=0.0, n_positions=0)
    if not live_orders:
        lesson = {
            "ts": time.time(),
            "drill": "B_micro_order",
            "mode": "DRY_RUN",
            "would_submit": {"symbol": "SPY", "notional": notional, "side": "buy", "type": "market"},
            "allow": ok,
            "why": why,
            "teaching": "Dry-run until ALPACA_TRAIN_LIVE_ORDERS=on and session open.",
        }
        _append_lesson(lesson)
        return lesson
    if not clock.get("is_open"):
        lesson = {"ts": time.time(), "drill": "B_micro_order", "mode": "SKIP_CLOSED", "teaching": "Wait for session."}
        _append_lesson(lesson)
        return lesson
    if not ok:
        lesson = {"ts": time.time(), "drill": "B_micro_order", "mode": "BLOCKED", "why": why}
        _append_lesson(lesson)
        return lesson
    # A random SPY buy is not a strategy or learning experiment. A filled order also needs
    # deterministic risk/exit/reconciliation integration; the training probe has none.
    lesson = {"ts": time.time(), "drill": "B_micro_order", "mode": "BLOCKED_EXECUTION_INTEGRATION",
              "why": "Prerequisite: strategy evidence + deterministic adapter + exit/reconciliation proof",
              "teaching": "No blind buys; implement and validate the full paper lifecycle first."}
    _append_lesson(lesson)
    return lesson


def write_officer_brief(policy: PaperBankrollPolicy, drills: list[dict[str, Any]]) -> None:
    lines = [
        f"# Alpaca training brief — {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}",
        "",
        f"**Stage:** `{policy.stage}` · **Training NAV:** `${policy.bankroll_usd}` · "
        f"**Max order:** `${policy.max_per_order_usd}` · **Max open:** `${policy.max_open_usd}`",
        "",
        f"Treasury signal: `${policy.treasury_nav_usd}` — {policy.stage_reason}",
        "",
        "## Few-shot sizing (memorize)",
        f"- GOOD sizing only: buy `${min(10, policy.max_per_order_usd):.0f}` notional SPY (liquid, inside cap)",
        f"- BAD: buy `$5000` of a mover because paper equity shows $100k → REJECT",
        f"- BAD: 10 simultaneous `$15` tickets → blows max_open `${policy.max_open_usd}`",
        "",
        "## Drill results",
    ]
    for d in drills:
        lines.append(f"- `{d.get('drill')}` mode={d.get('mode', d.get('passed'))} — {d.get('teaching', '')}")
    lines += [
        "",
        "## Officer homework (this cycle)",
        "1. **Tess:** From alpaca_paper_status discovery, file 1 OBSERVED anomaly sized for current stage.",
        "2. **Quinn:** One STRATEGY+ALGORITHM genome card that only works if bankroll is current stage (state capacity at $25/$50/$200).",
        "3. **Reid:** Specify order type + kill (bracket/stop) for that genome; dry-run mind.",
        "4. **Ada/Vale:** Pass/fail criteria for n=1..5 paper fills (do not overclaim).",
        "5. **Ellis:** Confirm paper training NAV ≠ LIVE treasury; no stage unlock from paper PnL alone.",
        "",
        "Read: `/srv/forge/docs/rails/ALPACA_AGENT_TRAINING.md`",
        f"Lessons log: `{LESSON_PATH}`",
    ]
    BRIEF_PATH.write_text("\n".join(lines) + "\n")


async def run_training_session() -> dict[str, Any]:
    from forge.venues.alpaca import AlpacaClient

    policy = PaperBankrollPolicy.from_env()
    client = AlpacaClient(paper=True)
    drills: list[dict[str, Any]] = []
    try:
        drills.append(await drill_sizing(policy))
        if client.configured:
            drills.append(await drill_market_context(client, policy))
            drills.append(await drill_micro_order(client, policy))
            from forge.research.alpaca_curriculum import run_curriculum
            research = await run_curriculum(client, policy)
            research_path = BRIEF_PATH.parent / "alpaca_research.json"
            research_path.write_text(json.dumps(research, indent=2) + "\n")
            drills.append({"drill": "C_fixed_strategy_research", "mode": "RESEARCH_ONLY",
                           "teaching": "Review forward evidence, capability and next experiment; zero earned cash",
                           "artifact": str(research_path), "evaluation": research.get("evaluation")})
        write_officer_brief(policy, drills)
        # refresh status
        if STATUS_PATH.exists():
            try:
                st = json.loads(STATUS_PATH.read_text())
                st["last_training"] = {"ts": time.time(), "drills": [d.get("drill") for d in drills]}
                STATUS_PATH.write_text(json.dumps(st, indent=2) + "\n")
            except Exception:
                pass
        return {"ok": True, "stage": policy.stage, "bankroll": policy.bankroll_usd, "drills": drills, "brief": str(BRIEF_PATH)}
    finally:
        await client.close()


async def main() -> None:
    print(json.dumps(await run_training_session(), indent=2, default=str)[:5000])


if __name__ == "__main__":
    asyncio.run(main())
