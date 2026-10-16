"""Staged Alpaca PAPER training bankroll — grows with real treasury earnings."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _f(name: str, default: float) -> float:
    try:
        return float(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def read_runtime_state(key: str) -> dict[str, Any] | None:
    """Read only canonical runtime state; never open a writable connection for training."""
    import sqlite3
    db_path = Path(os.environ.get("FORGE_HOME", "/srv/forge/var")) / "state" / "forge.sqlite"
    try:
        with sqlite3.connect(f"file:{db_path}?mode=ro", uri=True, timeout=2) as conn:
            row = conn.execute("SELECT value FROM kv_state WHERE key=?", (key,)).fetchone()
            return json.loads(row[0]) if row else None
    except (sqlite3.Error, ValueError, OSError):
        return None


def _read_treasury_nav() -> float:
    import time
    truth = read_runtime_state("treasury.truth") or {}
    if not truth.get("fresh") or not 0 <= time.time() - float(truth.get("ts") or 0) <= 300:
        return 0.
    return float(truth.get("treasury_nav") or 0)


@dataclass(frozen=True)
class PaperBankrollPolicy:
    stage: str
    bankroll_usd: float
    max_open_usd: float
    max_per_order_usd: float
    max_positions: int
    ignore_broker_equity: bool
    treasury_nav_usd: float
    stage_reason: str

    @classmethod
    def from_env(cls, treasury_nav: float | None = None) -> "PaperBankrollPolicy":
        treas = float(treasury_nav) if treasury_nav is not None else _read_treasury_nav()
        seed = _f("ALPACA_TRAIN_SEED_USD", 25.0)
        boot = _f("ALPACA_TRAIN_BOOTSTRAP_USD", 50.0)
        regular = _f("ALPACA_TRAIN_REGULAR_USD", 200.0)
        scale = _f("ALPACA_TRAIN_SCALE_USD", 2000.0)
        import math
        if not math.isfinite(treas) or treas < 0:
            treas = 0.
        if not all(math.isfinite(v) and v > 0 for v in (seed, boot, regular, scale)):
            raise ValueError("training bankroll tiers must be finite and positive")
        t2 = _f("ALPACA_TRAIN_TIER2_TREASURY", 50.0)
        t3 = _f("ALPACA_TRAIN_TIER3_TREASURY", 200.0)
        t4 = _f("ALPACA_TRAIN_TIER4_TREASURY", 1000.0)

        forced = (os.environ.get("ALPACA_TRAIN_STAGE") or "auto").strip().lower()
        if forced in ("seed", "bootstrap", "regular", "scale"):
            stage, reason = forced, f"forced stage={forced}"
        elif treas <= 0:
            stage, reason = "seed", "treasury unknown/zero → conservative SEED; no economic growth inferred"
        elif treas < 25:
            stage, reason = "seed", f"treasury ${treas:.2f} < $25 → SEED"
        elif treas < t2:
            stage, reason = "bootstrap", f"treasury ${treas:.2f} < ${t2:.0f} → BOOTSTRAP"
        elif treas < t4:
            stage, reason = "regular", f"treasury ${treas:.2f} in [${t2:.0f},${t4:.0f}) → REGULAR"
        else:
            stage, reason = "scale", f"treasury ${treas:.2f} ≥ ${t4:.0f} → SCALE"

        bankroll = {"seed": seed, "bootstrap": boot, "regular": regular, "scale": scale}[stage]
        if stage == "regular" and treas >= t3 and treas < t4 and t4 > t3:
            frac = (treas - t3) / (t4 - t3)
            bankroll = regular + frac * (scale - regular)
            reason += f"; ramp→${bankroll:.0f}"

        fracs = {
            "seed": (0.60, 0.40, 3),
            "bootstrap": (0.50, 0.30, 4),
            "regular": (0.40, 0.20, 5),
            "scale": (0.35, 0.15, 8),
        }
        open_frac, order_frac, max_pos = fracs[stage]
        return cls(
            stage=stage,
            bankroll_usd=round(bankroll, 2),
            max_open_usd=round(bankroll * open_frac, 2),
            max_per_order_usd=round(bankroll * order_frac, 2),
            max_positions=max_pos,
            ignore_broker_equity=os.environ.get("ALPACA_IGNORE_BROKER_EQUITY", "true").lower()
            in ("1", "true", "yes", "on"),
            treasury_nav_usd=round(treas, 2),
            stage_reason=reason,
        )

    def effective_nav(self, broker_equity: float | None = None) -> float:
        if self.ignore_broker_equity or broker_equity is None:
            return self.bankroll_usd
        return min(float(broker_equity), self.bankroll_usd)

    def allow_order(self, *, notional_usd: float, open_usd: float, n_positions: int) -> tuple[bool, str]:
        import math
        if not all(math.isfinite(x) for x in (notional_usd, open_usd)) or notional_usd <= 0 or open_usd < 0 or n_positions < 0:
            return False, "invalid exposure or notional"
        if n_positions >= self.max_positions and notional_usd > 0:
            return False, f"max positions {self.max_positions}"
        if notional_usd > self.max_per_order_usd + 1e-9:
            return False, f"order ${notional_usd:.2f} > max_per_order ${self.max_per_order_usd:.2f}"
        if open_usd + notional_usd > self.max_open_usd + 1e-9:
            return False, f"open ${open_usd + notional_usd:.2f} > max_open ${self.max_open_usd:.2f}"
        if notional_usd > self.bankroll_usd + 1e-9:
            return False, f"order exceeds bankroll ${self.bankroll_usd:.2f}"
        return True, "ok"

    def as_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "bankroll_usd": self.bankroll_usd,
            "max_open_usd": self.max_open_usd,
            "max_per_order_usd": self.max_per_order_usd,
            "max_positions": self.max_positions,
            "ignore_broker_equity": self.ignore_broker_equity,
            "treasury_nav_usd": self.treasury_nav_usd,
            "stage_reason": self.stage_reason,
            "ladder": {
                "seed": _f("ALPACA_TRAIN_SEED_USD", 25),
                "bootstrap": _f("ALPACA_TRAIN_BOOTSTRAP_USD", 50),
                "regular": _f("ALPACA_TRAIN_REGULAR_USD", 200),
                "scale": _f("ALPACA_TRAIN_SCALE_USD", 2000),
                "unlock_regular_at_treasury": _f("ALPACA_TRAIN_TIER2_TREASURY", 50),
                "ramp_starts_at_treasury": _f("ALPACA_TRAIN_TIER3_TREASURY", 200),
                "unlock_scale_at_treasury": _f("ALPACA_TRAIN_TIER4_TREASURY", 1000),
            },
            "doctrine": "Training NAV tracks earned treasury growth; never Alpaca $100k paper toy money",
        }
