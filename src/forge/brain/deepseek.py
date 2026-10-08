"""DeepSeek client (OP-004/OP-006): two brains, exact cost accounting, every call ledgered.

Verified API (2026-10-06): POST /chat/completions; model ∈ {deepseek-flash, deepseek-v4-pro};
`thinking: {type: enabled|disabled}`; `reasoning_effort: none|low|high|max`; tools; response_format json_object.
Usage: prompt_cache_hit_tokens / prompt_cache_miss_tokens / completion_tokens. Peak = Mon–Fri 01–04 & 06–10 UTC.
The model never receives secrets; it only sees curated, typed tool results.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import httpx

from forge.config import DeepSeekConfig
from forge.core.ids import new_id
from forge.ledger.ledger import Ledger
from forge.persistence.db import Database, dumps

log = logging.getLogger("forge.deepseek")


@dataclass
class LLMResult:
    call_id: str
    content: str
    tool_calls: list[dict[str, Any]]
    reasoning: str
    usage: dict[str, int]
    cost_usd: float
    latency_ms: int
    model: str
    raw_message: dict[str, Any] = field(default_factory=dict)

    def json(self) -> Any:
        txt = self.content.strip()
        if txt.startswith("```"):
            txt = txt.strip("`")
            txt = txt[txt.find("{"):] if "{" in txt else txt
        start, end = txt.find("{"), txt.rfind("}")
        return json.loads(txt[start:end + 1]) if start >= 0 and end > start else json.loads(txt)


def is_peak(cfg: DeepSeekConfig, now: datetime | None = None) -> bool:
    now = now or datetime.now(UTC)
    if now.weekday() >= 5:
        return False
    return any(a <= now.hour < b for a, b in cfg.peak_windows_utc)


class DeepSeekClient:
    def __init__(self, cfg: DeepSeekConfig, api_key: str, db: Database, ledger: Ledger, book: str,
                 transport: httpx.AsyncBaseTransport | None = None) -> None:
        self.cfg, self.db, self.ledger, self.book = cfg, db, ledger, book
        self._client = httpx.AsyncClient(base_url=cfg.base_url, timeout=cfg.timeout_s, transport=transport,
                                         headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
        self.spent_session = 0.0
        self.calls = 0
        self.errors = 0

    def cost(self, model: str, usage: dict[str, int]) -> float:
        p = self.cfg.prices.get(model) or self.cfg.prices["deepseek-flash"]
        mult = Decimal(1) if is_peak(self.cfg) else Decimal("0.5")
        hit = Decimal(usage.get("prompt_cache_hit_tokens", 0))
        miss = Decimal(usage.get("prompt_cache_miss_tokens", max(usage.get("prompt_tokens", 0) - int(hit), 0)))
        out = Decimal(usage.get("completion_tokens", 0))
        return float((hit * p.input_cache_hit + miss * p.input_cache_miss + out * p.output) * mult / Decimal(1_000_000))

    async def balance(self) -> float | None:
        try:
            r = await self._client.get("/user/balance")
            r.raise_for_status()
            infos = r.json().get("balance_infos", [])
            return float(sum(float(i.get("total_balance", 0)) for i in infos if i.get("currency") == "USD"))
        except Exception as e:
            log.warning("balance check failed: %s", e)
            return None

    async def chat(self, messages: list[dict[str, Any]], *, agent: str, purpose: str, deep: bool = False,
                   effort: str = "high", tools: list[dict[str, Any]] | None = None, json_mode: bool = False,
                   max_tokens: int = 4000, strategy_id: str | None = None, opportunity_id: str | None = None,
                   prompt_version: str = "v1") -> LLMResult:
        model = self.cfg.deep_model if deep else self.cfg.model
        body: dict[str, Any] = {"model": model, "messages": messages, "max_tokens": max_tokens,
                                "reasoning_effort": effort}
        body["thinking"] = {"type": "disabled" if effort == "none" else "enabled"}
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        if json_mode and not tools:
            body["response_format"] = {"type": "json_object"}
        cid = new_id("llm")
        t0 = time.time()
        err = None
        data: dict[str, Any] = {}
        for attempt in range(3):
            try:
                r = await self._client.post("/chat/completions", content=json.dumps(body))
                if r.status_code in (429, 500, 502, 503) and attempt < 2:
                    await _sleep(2 ** attempt * 2)
                    continue
                r.raise_for_status()
                data = r.json()
                err = None
                break
            except (httpx.HTTPError, ValueError) as e:
                err = f"{type(e).__name__}: {str(e)[:200]}"
                if attempt < 2:
                    await _sleep(2 ** attempt * 2)
        lat = int((time.time() - t0) * 1000)
        self.calls += 1
        if err or not data:
            self.errors += 1
            self._record(cid, agent, purpose, model, effort, prompt_version, {}, 0.0, lat, None, "error",
                         strategy_id, opportunity_id, err)
            raise RuntimeError(f"DeepSeek call failed: {err}")
        msg = (data.get("choices") or [{}])[0].get("message", {}) or {}
        usage = data.get("usage", {}) or {}
        cost = self.cost(model, usage)
        self.spent_session += cost
        tcs = msg.get("tool_calls") or []
        self._record(cid, agent, purpose, model, effort, prompt_version, usage, cost, lat,
                     [t.get("function", {}).get("name") for t in tcs], "ok", strategy_id, opportunity_id, None)
        return LLMResult(cid, msg.get("content") or "", tcs, msg.get("reasoning_content") or "", usage, cost, lat, model, msg)

    def _record(self, cid: str, agent: str, purpose: str, model: str, effort: str, pv: str, usage: dict[str, int],
                cost: float, lat: int, tools: list[str] | None, result: str, sid: str | None, oid: str | None,
                err: str | None) -> None:
        self.db.insert("inference_calls", {
            "id": cid, "ts": datetime.now(UTC).isoformat(), "agent": agent, "purpose": purpose, "model": model,
            "effort": effort, "prompt_version": pv, "input_tokens": int(usage.get("prompt_tokens", 0)),
            "cached_tokens": int(usage.get("prompt_cache_hit_tokens", 0)),
            "output_tokens": int(usage.get("completion_tokens", 0)), "cost_usd": f"{cost:.8f}", "latency_ms": lat,
            "tool_calls": dumps(tools or []), "result_class": result, "strategy_id": sid, "opportunity_id": oid,
            "error": err})
        if cost > 0:   # real operating expense → true net P&L (OP-006 attribution starts here)
            self.ledger.record_opex(self.book, "INFERENCE", Decimal(f"{cost:.8f}"), cid, strategy_id=sid,
                                    memo=f"{agent}:{purpose}:{model}")

    async def close(self) -> None:
        await self._client.aclose()


async def _sleep(s: float) -> None:
    import asyncio
    await asyncio.sleep(s)
