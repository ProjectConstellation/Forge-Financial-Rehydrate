"""System One decision layer (optional, vendor-neutral) — TypeSafe Jev adapter (researched 2026-10-07).

Role in FORGE (deliberately narrow — see docs/DECISIONS.md D-015): a sub-second, near-free SEMANTIC TRIAGE ROUTER that
decides whether a situation deserves DeepSeek Flash / Pro / Modal, and (later) parses event/contract text for the Kalshi
rail. It is NOT placed in the numeric trade path: Jev documents weakness on numeric precision, and FORGE's numeric
fast path is deterministic (ms) with a second-opinion model trained on FORGE's own outcomes.

Starts in SHADOW: every decision is recorded (latency, cost, prediction) and scored against what the expensive path
actually concluded/produced. It may GATE Flash calls only after it demonstrates agreement/value; usage then scales with
measured value. Never touches the Risk Governor, wallet security or execution.
"""

from __future__ import annotations

import json
import logging
import os
import time
from datetime import UTC, datetime
from typing import Any, Protocol

import httpx

from forge.core.healing import Circuit

log = logging.getLogger("forge.systemone")
PRICE_PER_INPUT_TOKEN = 0.042 / 1_000_000          # USD, jev-1.13 (output tokens free) — docs.typesafe.ai/models


class SystemOneProvider(Protocol):
    name: str

    async def decide(self, state: Any, questions: dict[str, dict[str, Any]]) -> dict[str, Any]: ...


class TypeSafeJev:
    name = "typesafe-jev"

    def __init__(self, api_key: str, model: str = "jev-latest", timeout_s: float = 8.0,
                 transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.model = model
        self.circuit = Circuit("jev", threshold=3, base_cooldown_s=300)
        self._c = httpx.AsyncClient(base_url="https://api.typesafe.ai", timeout=timeout_s, transport=transport,
                                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})

    async def decide(self, state: Any, questions: dict[str, dict[str, Any]]) -> dict[str, Any]:
        if not self.circuit.allow():
            raise RuntimeError("System One circuit OPEN")
        t0 = time.perf_counter()
        try:
            r = await self._c.post("/v1/systemone", content=json.dumps({"state": state, "model": self.model, "questions": questions}))
            r.raise_for_status()
            d = r.json()
        except Exception as e:
            self.circuit.failure(str(e))
            raise
        self.circuit.success()
        usage = d.get("usage", {})
        return {"answers": d.get("answers", {}), "model": d.get("model"), "latency_ms": (time.perf_counter() - t0) * 1000,
                "input_tokens": usage.get("input_tokens", 0),
                "cost_usd": usage.get("input_tokens", 0) * PRICE_PER_INPUT_TOKEN}


TRIAGE_QUESTIONS = {
    "escalate": {"type": "noul", "instructions": "Does this market situation contain something that could change how the trading "
                 "system should allocate capital right now (worth a deeper reasoning model's time)?",
                 "criteria": {"true": "A material new development, regime change, anomaly, failure or high-value opportunity",
                              "false": "Routine, quiet, or already-handled conditions"}},
    "regime_shift": {"type": "noul", "instructions": "Does the `regimes` breadth together with `top_movers` indicate the market regime is changing?"},
    "anomaly": {"type": "noul", "instructions": "Is there a data anomaly or suspicious market behavior mentioned in `alerts` or `top_movers`?"},
    "value": {"type": "score", "instructions": "How valuable would deeper analysis be for earning money right now?",
              "criteria": ["Low: nothing actionable", "Medium: worth a cheap check", "High: worth deep reasoning and simulation"]},
}


class SystemOneTriage:
    """SHADOW → GATE lifecycle with attribution. Mode persisted in kv 'systemone.mode'."""

    def __init__(self, forge: Any, provider: SystemOneProvider) -> None:
        self.f, self.p = forge, provider

    @property
    def mode(self) -> str:
        return self.f.db.kv_get("systemone.mode") or "SHADOW"

    async def triage(self, situation: dict[str, Any]) -> dict[str, Any] | None:
        try:
            res = await self.p.decide(situation, TRIAGE_QUESTIONS)
        except Exception as e:
            log.warning("system one triage failed: %s", e)
            return None
        a = res["answers"]
        out = {"escalate": a.get("escalate", {}).get("noul"), "regime_shift": a.get("regime_shift", {}).get("noul"),
               "anomaly": a.get("anomaly", {}).get("noul"), "value": a.get("value", {}).get("score"),
               "value_conf": a.get("value", {}).get("confidence"), "latency_ms": round(res["latency_ms"], 1),
               "cost_usd": res["cost_usd"], "model": res["model"], "mode": self.mode}
        self.f.db.insert("intel_artifacts", {"ts": datetime.now(UTC).isoformat(), "call_id": f"s1_{int(time.time() * 1000)}",
                                             "role": "systemone", "model": str(res["model"]), "kind": "triage", "ref_id": None,
                                             "prediction": out["escalate"], "detail": json.dumps(out)})
        if res["cost_usd"] > 0:
            from decimal import Decimal
            self.f.ledger.record_opex(self.f.book if self.f.book in ("live", "paper") else "paper", "INFERENCE",
                                      Decimal(f"{res['cost_usd']:.10f}"), f"s1-{time.time_ns()}", memo="systemone triage")
        return out

    def record_reference(self, flash_escalated: bool) -> None:
        """Score the latest shadow triage against the expensive path's conclusion (agreement → calibration)."""
        r = self.f.db.query_one("SELECT id, prediction FROM intel_artifacts WHERE role='systemone' AND kind='triage' "
                                "ORDER BY id DESC LIMIT 1")
        if r and r["prediction"] is not None:
            self.f.calib.record("systemone:escalate", float(r["prediction"]), flash_escalated, "shadow")
            self._maybe_promote()

    def _maybe_promote(self) -> None:
        rel = self.f.calib.reliability("systemone:escalate")
        if self.mode == "SHADOW" and rel.get("n", 0) >= 60 and rel.get("brier", 1) <= 0.15:
            self.f.db.kv_set("systemone.mode", "GATE")
        elif self.mode == "GATE" and rel.get("brier", 0) > 0.22:
            self.f.db.kv_set("systemone.mode", "SHADOW")      # lost its edge → demoted back to shadow


def make_provider() -> SystemOneProvider | None:
    key = os.environ.get("TYPESAFE_API_KEY", "").strip()
    return TypeSafeJev(key) if key else None


class JevRouterFailover:
    """OpenRouter `typesafe/jev-router` — used ONLY as an independent failover path when the direct DeepSeek circuit is open
    (measured 2026-10-07: routes to deepseek-v4.1-flash via Together, 3–8 s, $0.001–0.003/call → no triage advantage, but
    genuine provider diversity). Key: OPENROUTER_API_KEY_JEV (operator-scoped to Jev usage only)."""

    name = "openrouter-jev-router"

    def __init__(self, api_key: str, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.circuit = Circuit("jev-router", threshold=3, base_cooldown_s=600)
        self._c = httpx.AsyncClient(base_url="https://openrouter.ai/api/v1", timeout=60, transport=transport,
                                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json",
                                             "HTTP-Referer": "https://forge.northstarimagine.com", "X-Title": "FORGE"})

    async def chat_json(self, system: str, user: str, max_tokens: int = 3000) -> dict[str, Any]:
        if not self.circuit.allow():
            raise RuntimeError("Jev Router circuit OPEN")
        t0 = time.perf_counter()
        try:
            r = await self._c.post("/chat/completions", content=json.dumps({
                "model": "typesafe/jev-router", "usage": {"include": True}, "max_tokens": max_tokens,
                "response_format": {"type": "json_object"},
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}))
            r.raise_for_status()
            d = r.json()
        except Exception as e:
            self.circuit.failure(str(e))
            raise
        self.circuit.success()
        txt = (d["choices"][0]["message"].get("content") or "").strip()
        s, e = txt.find("{"), txt.rfind("}")
        return {"json": json.loads(txt[s:e + 1]) if s >= 0 and e > s else {}, "routed_model": d.get("model"),
                "cost_usd": float((d.get("usage") or {}).get("cost") or 0.0), "latency_ms": (time.perf_counter() - t0) * 1000}


def make_failover() -> JevRouterFailover | None:
    key = os.environ.get("OPENROUTER_API_KEY_JEV", "").strip()
    return JevRouterFailover(key) if key else None
