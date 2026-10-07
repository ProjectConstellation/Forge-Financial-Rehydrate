"""Circuit breakers (DOSSIER §22.2). PROTECTED CORE.

Breakers trip on counted anomalies inside a sliding window and stay tripped for a cooldown.
Actions are escalating: WARN → REDUCE_SIZE → DISABLE_STRATEGY / DISABLE_VENUE_NEW_ORDERS →
CANCEL_OPEN_ORDERS → ENTER_OBSERVE_ONLY. Tripped breakers block new entries (RiskContext.breakers).
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from dataclasses import dataclass

DEFAULTS: dict[str, tuple[int, float, float, str]] = {
    # code: (count threshold, window_s, cooldown_s, action)
    "exchange_reject": (5, 600, 1800, "DISABLE_VENUE_NEW_ORDERS"),
    "ws_integrity": (6, 600, 300, "DISABLE_VENUE_NEW_ORDERS"),
    "balance_mismatch": (1, 60, 3600, "ENTER_OBSERVE_ONLY"),
    "slippage_anomaly": (3, 3600, 3600, "REDUCE_SIZE"),
    "auth_error": (2, 300, 3600, "ENTER_OBSERVE_ONLY"),
    "duplicate_order": (1, 60, 3600, "ENTER_OBSERVE_ONLY"),
    "order_frequency": (1, 60, 600, "DISABLE_VENUE_NEW_ORDERS"),
    "pnl_recon_mismatch": (2, 3600, 3600, "ENTER_OBSERVE_ONLY"),
    "inference_cost_runaway": (1, 3600, 3600, "WARN"),
    "modal_spend_anomaly": (1, 3600, 3600, "WARN"),
    "rapid_drawdown": (1, 60, 7200, "ENTER_OBSERVE_ONLY"),
    "clock_drift": (1, 60, 600, "DISABLE_VENUE_NEW_ORDERS"),
}
BLOCKING = {"DISABLE_VENUE_NEW_ORDERS", "ENTER_OBSERVE_ONLY", "CANCEL_OPEN_ORDERS"}


@dataclass
class Trip:
    code: str
    action: str
    until: float
    detail: str


class BreakerBoard:
    def __init__(self) -> None:
        self.events: dict[str, deque[float]] = defaultdict(deque)
        self.tripped: dict[str, Trip] = {}

    def record(self, code: str, detail: str = "") -> Trip | None:
        thr, window, cooldown, action = DEFAULTS.get(code, (3, 600, 600, "WARN"))
        now = time.monotonic()
        q = self.events[code]
        q.append(now)
        while q and now - q[0] > window:
            q.popleft()
        if len(q) >= thr:
            t = Trip(code, action, now + cooldown, detail)
            self.tripped[code] = t
            q.clear()
            return t
        return None

    def active(self) -> dict[str, Trip]:
        now = time.monotonic()
        for k in [k for k, t in self.tripped.items() if t.until <= now]:
            del self.tripped[k]
        return dict(self.tripped)

    def blocking(self) -> set[str]:
        return {k for k, t in self.active().items() if t.action in BLOCKING}

    def size_multiplier(self) -> float:
        return 0.5 if any(t.action == "REDUCE_SIZE" for t in self.active().values()) else 1.0

    def reset(self, code: str | None = None) -> None:
        if code:
            self.tripped.pop(code, None)
        else:
            self.tripped.clear()

    def snapshot(self) -> list[dict[str, object]]:
        now = time.monotonic()
        return [{"code": t.code, "action": t.action, "remaining_s": round(t.until - now), "detail": t.detail}
                for t in self.active().values()]
