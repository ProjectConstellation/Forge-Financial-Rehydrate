"""Second-opinion model (meta-labeling) — calibrated evidence, never an automatic veto (OP-012).

Trains an L2-regularized logistic regression per strategy family on scored opportunities (acted, rejected and observed —
counterfactual outcomes included), using the feature snapshot captured at signal time. Its influence is EARNED:
the blend weight comes from a chronological out-of-sample test — weight > 0 only if it lowers log-loss versus the
strategy's own probability; otherwise it is ignored. Its effect on realized outcomes keeps being measured.
"""

from __future__ import annotations

import json
import math
import time
from typing import Any

import numpy as np

from forge.persistence.db import Database

FEATS = ("ret_12", "ret_48", "vol_48", "vol_pct", "rvol_12", "er_24", "z_50", "rs_btc_48", "dd_288", "atr_14",
         "regime_conf", "breadth", "spread_bps")


def _logit(p: float) -> float:
    p = min(max(p, 1e-4), 1 - 1e-4)
    return math.log(p / (1 - p))


def _sig(z: np.ndarray | float) -> Any:
    return 1 / (1 + np.exp(-z))


def fit_logistic(X: np.ndarray, y: np.ndarray, l2: float = 1.0, iters: int = 25) -> np.ndarray:
    X1 = np.hstack([X, np.ones((len(X), 1))])
    w = np.zeros(X1.shape[1])
    for _ in range(iters):                                   # Newton-Raphson (IRLS)
        p = _sig(X1 @ w)
        g = X1.T @ (p - y) + l2 * np.r_[w[:-1], 0]
        H = (X1 * (p * (1 - p))[:, None]).T @ X1 + l2 * np.diag(np.r_[np.ones(len(w) - 1), 0])
        try:
            w -= np.linalg.solve(H, g)
        except np.linalg.LinAlgError:
            break
    return w


def logloss(p: np.ndarray, y: np.ndarray) -> float:
    p = np.clip(p, 1e-4, 1 - 1e-4)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


class SecondOpinion:
    KEY = "metalabel.models"

    def __init__(self, db: Database) -> None:
        self.db = db
        self.models: dict[str, Any] = db.kv_get(self.KEY, {}) or {}
        self.trained_at = 0.0

    def train(self, min_samples: int = 60) -> dict[str, Any]:
        rows = self.db.query("SELECT family, probability, components, outcome FROM opportunities WHERE outcome IS NOT NULL "
                             "ORDER BY ts_ns")
        by: dict[str, list[tuple[list[float], float, int]]] = {}
        for r in rows:
            c = json.loads(r["components"] or "{}")
            f = c.get("feat")
            if not f:
                continue
            x = [float(f.get(k, 0.0) or 0.0) for k in FEATS]
            if not all(math.isfinite(v) for v in x):
                continue
            by.setdefault(r["family"] or "?", []).append((x, float(r["probability"] or 0.5), int(json.loads(r["outcome"])["win"])))
        out = {}
        for fam, data in by.items():
            if len(data) < min_samples:
                continue
            X = np.array([d[0] for d in data])
            pb = np.array([d[1] for d in data])
            y = np.array([d[2] for d in data], dtype=float)
            mu, sd = X.mean(axis=0), X.std(axis=0) + 1e-9
            Z = (X - mu) / sd
            cut = int(len(Z) * 0.7)
            w = fit_logistic(Z[:cut], y[:cut])
            pm = _sig(np.hstack([Z[cut:], np.ones((len(Z) - cut, 1))]) @ w)
            ll_base, ll_meta = logloss(pb[cut:], y[cut:]), logloss(pm, y[cut:])
            gain = (ll_base - ll_meta) / max(ll_base, 1e-9)
            weight = float(np.clip(gain * 5, 0.0, 0.6))          # influence only if it measurably helps out-of-sample
            w_full = fit_logistic(Z, y)
            out[fam] = {"w": w_full.tolist(), "mu": mu.tolist(), "sd": sd.tolist(), "weight": weight, "n": len(data),
                        "oos_logloss_base": ll_base, "oos_logloss_meta": ll_meta, "trained": time.time()}
        if out:
            self.models.update(out)
            self.db.kv_set(self.KEY, self.models)
        self.trained_at = time.time()
        return out

    def opinion(self, family: str, feat: dict[str, float], p_strategy: float) -> tuple[float, float | None, float]:
        """Returns (p_final, p_meta, weight). weight=0 → model has not earned influence (or no model yet)."""
        m = self.models.get(family)
        if not m:
            return p_strategy, None, 0.0
        x = np.array([float(feat.get(k, 0.0) or 0.0) for k in FEATS])
        if not np.all(np.isfinite(x)):
            return p_strategy, None, 0.0
        z = (x - np.array(m["mu"])) / np.array(m["sd"])
        pm = float(_sig(np.r_[z, 1.0] @ np.array(m["w"])))
        w = float(m["weight"])
        pf = float(_sig((1 - w) * _logit(p_strategy) + w * _logit(pm)))
        return pf, pm, w
