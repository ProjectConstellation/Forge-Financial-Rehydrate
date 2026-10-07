"""Compute Governor + Modal client (DOSSIER §4, §24–25; DIRECTIVE §4, §22; OP-009 §1).

Decides LOCAL_NORMAL vs LOCAL_SURGE vs MODAL_BURST by expected value of information and budget state:
GREEN <60% of the monthly Modal budget · YELLOW 60–85% · ORANGE 85–95% · RED >95% (only critical work).
Every job: parent id, timeout, cost estimate (core-seconds × list price + memory), ledger entry (true net P&L).
Market history is synced to the `forge-market` Volume so bursts read data locally inside Modal.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from forge.core.ids import new_id
from forge.persistence.db import dumps

log = logging.getLogger("forge.compute")


def _now() -> str:
    return datetime.now(UTC).isoformat()


class ComputeGovernor:
    def __init__(self, forge: Any) -> None:
        self.f = forge
        cfg = forge.s.compute.modal
        self.cfg = cfg
        self.budget = float(cfg.monthly_budget_usd)
        os.environ.setdefault("MODAL_ENVIRONMENT", cfg.environment)
        self.synced_at = 0.0
        self.cycles = 0
        self.burst_containers = 8
        self.burst_budget_s = 300.0
        self.available = True

    # ------------------------------------------------------------------ budget state
    def month_spend(self) -> float:
        return float(self.f.db.scalar("SELECT COALESCE(SUM(CAST(est_cost_usd AS REAL)),0) FROM compute_jobs "
                                      "WHERE location = 'MODAL_BURST' AND ts_start >= ?",
                                      (datetime.now(UTC).strftime("%Y-%m-01"),)) or 0.0)

    def budget_state(self) -> str:
        u = self.month_spend() / self.budget if self.budget else 1.0
        return "GREEN" if u < 0.60 else "YELLOW" if u < 0.85 else "ORANGE" if u < 0.95 else "RED"

    def estimate_cost(self, containers: int, seconds: float, cpu: float = 2.0, mem_gib: float = 3.0) -> float:
        return containers * seconds * (cpu * float(self.cfg.cpu_core_second_usd) + mem_gib * float(self.cfg.memory_gib_second_usd))

    async def should_burst(self, forge: Any, interval: int) -> bool:
        """EVI-driven: burst when research value is high (no proven edge yet, demotions, brain escalation) and budget allows."""
        if not self.available:
            return False
        self.cycles += 1
        state = self.budget_state()
        if state == "RED":
            return False
        counts = forge.reg.counts()
        no_edge = not (counts.get("PRODUCTION") or counts.get("CHALLENGER"))
        survival = (forge.treasury.get("regime") or {}).get("name") == "SURVIVAL"
        llm_waiting = bool(forge.db.kv_get("brain.candidate_queue", []))
        racing = bool(forge.db.kv_get("evolution.near_miss", []))
        self.burst_containers = 16 if (racing and state == "GREEN") else 8      # concentrate compute near the gate (OP-010)
        if racing and state in ("GREEN", "YELLOW"):
            return True
        cadence = {"GREEN": 2, "YELLOW": 4, "ORANGE": 8}[state]
        # value of information is highest while FORGE has no validated edge (SURVIVAL escalates research — OP-008)
        if (no_edge or survival) and state == "GREEN":
            cadence = 1
        return llm_waiting or self.cycles % cadence == 0

    # ------------------------------------------------------------------ data sync
    async def sync_volume(self) -> None:
        if time.time() - self.synced_at < 3 * 3600:
            return
        import modal

        def _upload() -> None:
            vol = modal.Volume.from_name("forge-market", environment_name=self.cfg.environment, create_if_missing=True)
            root = self.f.store.root
            with vol.batch_upload(force=True) as b:
                b.put_directory(str(root), "/candles")

        await asyncio.to_thread(_upload)
        self.synced_at = time.time()
        await self.f.say("Modal Lab", "Market history synced to Modal volume forge-market")

    # ------------------------------------------------------------------ bursts
    async def burst_search(self, forge: Any, interval: int, parents: list[Any], llm: list[dict[str, Any]] | None = None) -> dict[str, Any]:
        import modal
        await self.sync_volume()
        fn = modal.Function.from_name("forge-research", "search", environment_name=self.cfg.environment)
        n = self.burst_containers if self.budget_state() == "GREEN" else max(2, self.burst_containers // 2)
        pj = [g.model_dump(mode="json") for g in parents]
        fees = {"maker": float(forge.fees.maker), "taker": float(forge.fees.taker)}
        jid = new_id("job")
        t0 = time.time()
        forge.db.insert("compute_jobs", {"id": jid, "ts_start": _now(), "kind": f"evolution_{interval}", "location": "MODAL_BURST",
                                         "cpu": 2.0 * n, "memory_mb": 3072 * n, "status": "RUNNING",
                                         "strategy_ids": dumps([g.id for g in parents][:50])})
        forge.status("Modal Lab", f"{n} workers · evolutionary tournament ({interval // 60}m)")
        await forge.say("Modal Lab", f"Modal burst launched: {n} parallel workers × {self.burst_budget_s:.0f}s evolutionary "
                                     f"tournament on {interval // 60}m data (budget {self.budget_state()}, month ${self.month_spend():.2f}/${self.budget:.0f})")
        # different seeds and parent subsets per container (diversity); LLM genomes go to every container
        args = []
        for i in range(n):
            sub = pj[i::n] + pj[: max(0, 6 - len(pj[i::n]))]
            args.append((interval, sub, fees, self.burst_budget_s, int(t0) + i * 7919, llm or []))
        results: list[dict[str, Any]] = []
        try:
            async for r in fn.starmap.aio(args, return_exceptions=True):
                if isinstance(r, dict):
                    results.append(r)
                else:
                    log.warning("modal worker failed: %s", r)
        except Exception as e:
            forge.db.execute("UPDATE compute_jobs SET status='FAILED', ts_end=?, error=? WHERE id=?", (_now(), str(e)[:300], jid))
            self.available = False
            await forge.say("Modal Lab", f"Modal burst failed ({e}); falling back to local research", level="warn")
            raise
        secs = sum(float(r.get("container_seconds", r.get("seconds", 0))) for r in results)
        cost = self.estimate_cost(1, secs)
        forge.db.execute("UPDATE compute_jobs SET status='DONE', ts_end=?, duration_s=?, est_cost_usd=? WHERE id=?",
                         (_now(), time.time() - t0, f"{cost:.8f}", jid))
        if cost > 0:
            forge.ledger.record_opex(forge.book if forge.book in ("live", "paper") else "paper", "COMPUTE",
                                     Decimal(f"{cost:.8f}"), jid, memo=f"modal burst {n}x evolution_{interval}")
        merged: dict[str, Any] = {"candidates": [], "evaluated": 0, "seconds": time.time() - t0, "where": f"modal×{len(results)}",
                                  "best_fitness": max((r.get("best_fitness", 0) for r in results), default=0.0)}
        seen: set[str] = set()
        for r in results:
            merged["evaluated"] += r.get("evaluated", 0)
            for c in r.get("candidates", []):
                gid = c["genome"]["id"]
                if gid not in seen:
                    seen.add(gid)
                    merged["candidates"].append(c)
        await forge.say("Modal Lab", f"Burst complete: {merged['evaluated']} genomes across {len(results)} containers, "
                                     f"{secs:.0f} container-s, est cost ${cost:.4f}")
        return merged

    async def run(self, forge: Any) -> None:
        while not forge.stop_event.is_set():
            forge.status("Compute Governor", f"Modal {self.budget_state()} · month ${self.month_spend():.2f}/${self.budget:.0f} "
                                             f"· {'available' if self.available else 'unavailable (local fallback)'}")
            await asyncio.sleep(120)

    def summary(self) -> dict[str, Any]:
        return {"available": self.available, "state": self.budget_state(), "month_usd": self.month_spend(),
                "budget_usd": self.budget}


def attach_compute(forge: Any) -> None:
    if not forge.s.compute.modal.enabled:
        raise RuntimeError("Modal disabled in config")
    if not (forge.s.secrets.modal_token_id and forge.s.secrets.modal_token_secret):
        raise RuntimeError("MODAL_TOKEN_ID/SECRET not configured (CONFIG_REQUIRED)")
    forge.compute = ComputeGovernor(forge)
