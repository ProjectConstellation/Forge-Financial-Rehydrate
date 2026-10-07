"""Empirical confidence calibration (DOSSIER §2.4, DIRECTIVE §35, OP-009 §5).

Every prediction (strategy P(win), regime calls, LLM probability claims) is stored with its later outcome.
Per prediction class, a monotone (isotonic / PAV) reliability map is fit on Bayesian-smoothed bins, so an
"80%" class that historically wins 60% is automatically mapped to ~60% — and sizing follows the mapped value.
Classes with little evidence are shrunk toward their observed base rate (or 0.5 with no history).
"""

from __future__ import annotations

import time
from datetime import UTC, datetime

import numpy as np

from forge.persistence.db import Database

BINS = np.linspace(0.0, 1.0, 11)


def pav(y: np.ndarray, w: np.ndarray) -> np.ndarray:
    """Pool-adjacent-violators isotonic regression (non-decreasing)."""
    y, w = y.astype(float).copy(), w.astype(float).copy()
    blocks = [[y[i], w[i], 1] for i in range(len(y))]
    i = 0
    while i < len(blocks) - 1:
        if blocks[i][0] > blocks[i + 1][0]:
            a, b = blocks[i], blocks[i + 1]
            tw = a[1] + b[1]
            blocks[i] = [(a[0] * a[1] + b[0] * b[1]) / tw if tw else (a[0] + b[0]) / 2, tw, a[2] + b[2]]
            del blocks[i + 1]
            i = max(i - 1, 0)
        else:
            i += 1
    return np.concatenate([[v] * n for v, _, n in blocks])


class CalibrationEngine:
    def __init__(self, db: Database, prior_strength: float = 8.0, refresh_s: float = 300.0) -> None:
        self.db = db
        self.k = prior_strength
        self.refresh_s = refresh_s
        self._maps: dict[str, tuple[float, np.ndarray, int]] = {}

    def record(self, cls: str, predicted: float, outcome: bool, source: str, strategy_id: str | None = None,
               regime: str | None = None) -> None:
        self.db.insert("calibration_points", {"strategy_id": strategy_id, "family": cls, "regime": regime,
                                              "predicted": float(min(max(predicted, 0.0), 1.0)),
                                              "outcome": int(bool(outcome)), "source": source,
                                              "ts": datetime.now(UTC).isoformat()})
        self._maps.pop(cls, None)

    def _fit(self, cls: str) -> tuple[np.ndarray, int]:
        rows = self.db.query("SELECT predicted, outcome, source FROM calibration_points WHERE family = ? "
                             "ORDER BY id DESC LIMIT 5000", (cls,))
        if not rows:
            return np.full(10, np.nan), 0
        p = np.array([r["predicted"] for r in rows])
        o = np.array([r["outcome"] for r in rows], dtype=float)
        # live/paper outcomes weigh more than counterfactual/backtest ones
        w = np.array([{"live": 3.0, "paper": 2.0, "shadow": 1.5}.get(r["source"], 1.0) for r in rows])
        base = float((o * w).sum() / w.sum())
        idx = np.clip(np.digitize(p, BINS) - 1, 0, 9)
        succ = np.bincount(idx, weights=o * w, minlength=10)
        tot = np.bincount(idx, weights=w, minlength=10)
        mids = (BINS[:-1] + BINS[1:]) / 2
        prior = 0.5 * mids + 0.5 * base                    # skeptical prior: halfway between claim and base rate
        smoothed = (succ + self.k * prior) / (tot + self.k)
        return pav(smoothed, tot + self.k), len(rows)

    def calibrate(self, cls: str, p: float) -> tuple[float, int]:
        """Returns (calibrated probability, evidence count)."""
        cached = self._maps.get(cls)
        if cached is None or time.time() - cached[0] > self.refresh_s:
            m, n = self._fit(cls)
            self._maps[cls] = (time.time(), m, n)
            cached = self._maps[cls]
        _, m, n = cached
        if n == 0 or np.isnan(m).all():
            return 0.5 + (p - 0.5) * 0.5, 0               # no evidence: halve the claimed edge
        i = int(np.clip(np.digitize([p], BINS)[0] - 1, 0, 9))
        return float(m[i]), n

    def reliability(self, cls: str) -> dict[str, object]:
        rows = self.db.query("SELECT predicted, outcome FROM calibration_points WHERE family = ?", (cls,))
        if not rows:
            return {"class": cls, "n": 0}
        p = np.array([r["predicted"] for r in rows])
        o = np.array([r["outcome"] for r in rows], dtype=float)
        brier = float(np.mean((p - o) ** 2))
        idx = np.clip(np.digitize(p, BINS) - 1, 0, 9)
        table = [{"bin": f"{BINS[i]:.1f}-{BINS[i + 1]:.1f}", "n": int((idx == i).sum()),
                  "observed": float(o[idx == i].mean()) if (idx == i).any() else None} for i in range(10)]
        return {"class": cls, "n": len(rows), "brier": brier, "mean_pred": float(p.mean()), "hit_rate": float(o.mean()),
                "table": table}

    def classes(self) -> list[str]:
        return [r["family"] for r in self.db.query("SELECT DISTINCT family FROM calibration_points")]
