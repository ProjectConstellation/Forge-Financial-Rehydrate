"""Normalized firm API surface (blueprint §87) — wraps existing KV/state, no duplicates."""
from __future__ import annotations

import time
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


def _j(data: Any) -> JSONResponse:
    return JSONResponse(data)


def mount_firm_v1(app: FastAPI, forge: Any) -> None:
    @app.get("/api/v1/treasury")
    async def v1_treasury() -> Any:
        return _j(forge.db.kv_get("treasury.truth") or {"error": "not_ready"})

    @app.get("/api/v1/treasury/reconcile")
    async def v1_reconcile() -> Any:
        t = forge.db.kv_get("treasury.truth") or {}
        return _j(t.get("reconciliation") or t)

    @app.get("/api/v1/performance")
    async def v1_perf(window: str = "1h") -> Any:
        from forge.ops.econ import window as econ_window
        try:
            return _j(econ_window(forge, window))
        except Exception as e:
            return _j({"error": str(e)[:200]})

    @app.get("/api/v1/strategies")
    async def v1_strategies() -> Any:
        return _j({
            "tcs": forge.db.kv_get("treasury.tcs"),
            "edge_decay": forge.db.kv_get("edge_decay"),
            "reallocation": forge.db.kv_get("capital.reallocation"),
        })

    @app.get("/api/v1/opportunities")
    async def v1_opps() -> Any:
        return _j({
            "allocation": forge.db.kv_get("surface.allocation"),
            "half_life": forge.db.kv_get("opportunity.half_life"),
            "algo_factory": forge.db.kv_get("research.algo_factory"),
            "velocity_priorities": (forge.db.kv_get("velocity") or {}).get("priorities"),
        })

    @app.get("/api/v1/agents")
    async def v1_agents() -> Any:
        return _j(forge.db.kv_get("agents.heartbeat") or {})

    @app.get("/api/v1/research")
    async def v1_research() -> Any:
        return _j({
            "algo_factory": forge.db.kv_get("research.algo_factory"),
            "equity": forge.db.kv_get("equity.paper_research"),
            "modal": forge.compute.summary() if getattr(forge, "compute", None) else None,
        })

    @app.get("/api/v1/risk")
    async def v1_risk() -> Any:
        from forge.core import state as tstate
        return _j({
            "trading_state": tstate.trading_state(forge.db),
            "breakers": forge.breakers.blocking() if hasattr(forge, "breakers") else None,
            "red_zone": forge.db.kv_get("treasury.red_zone"),
        })

    @app.get("/api/v1/systems")
    async def v1_systems() -> Any:
        loops = forge.sup.snapshot() if hasattr(forge.sup, "snapshot") else []
        return _j({
            "mode_label": (forge.db.kv_get("treasury.truth") or {}).get("mode_label"),
            "forge_live_trading": (forge.db.kv_get("treasury.truth") or {}).get("forge_live_trading"),
            "loops": loops,
            "guardian": forge.db.kv_get("guardian.state"),
            "hermes_mode": forge.db.kv_get("hermes.mode"),
            "ready": True,
            "ts": time.time(),
        })

    @app.get("/api/v1/timeline")
    async def v1_timeline(limit: int = 50) -> Any:
        rows = forge.db.query(
            "SELECT ts, kind, summary FROM timeline ORDER BY ts DESC LIMIT ?", (min(limit, 200),)
        ) if hasattr(forge.db, "query") else []
        return _j({"events": rows})

    @app.get("/api/v1/trial/current")
    async def v1_trial() -> Any:
        return _j({
            "paper_trial": forge.db.kv_get("paper_trial"),
            "trial_8h": forge.db.kv_get("trial.8h"),
            "report": forge.db.kv_get("trial.8h.report"),
        })
