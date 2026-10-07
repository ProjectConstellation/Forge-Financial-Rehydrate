"""Strategy registry: population states, lineage, mutation rationale, metrics (DOSSIER §13–14; OP-007).

States: PRODUCTION · CHALLENGER · EXPERIMENTAL · SHADOW · HIBERNATING · RETIRED · QUARANTINED.
Nothing is ever deleted — retired/hibernating genomes remain queryable and resurrectable.
"""

from __future__ import annotations

import contextlib
import json
import logging
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from forge.persistence.db import Database, dumps
from forge.strategies.genome import Genome

log = logging.getLogger("forge.registry")

class State(StrEnum):
    PRODUCTION = "PRODUCTION"      # live capital (Earning Loop)
    CHALLENGER = "CHALLENGER"      # passed validation; small live allocation competing with incumbents
    SHADOW = "SHADOW"              # live data, would-be trades only
    EXPERIMENTAL = "EXPERIMENTAL"  # in research/backtest pipeline
    HIBERNATING = "HIBERNATING"    # sleeping until its regime returns
    RETIRED = "RETIRED"            # permanent institutional memory
    QUARANTINED = "QUARANTINED"    # suspicious/invalid/bug-related


ACTIVE_LIVE = (State.PRODUCTION, State.CHALLENGER)
ACTIVE_OBSERVING = (State.PRODUCTION, State.CHALLENGER, State.SHADOW)


def _now() -> str:
    return datetime.now(UTC).isoformat()


class StrategyRegistry:
    def __init__(self, db: Database) -> None:
        self.db = db

    def upsert(self, g: Genome, state: State, reason: str = "", fitness: float | None = None) -> None:
        now = _now()
        existing = self.db.query_one("SELECT population FROM strategies WHERE id = ?", (g.id,))
        if existing is None:
            self.db.insert("strategies", {
                "id": g.id, "family": g.family, "generation": g.generation, "population": state.value,
                "genome": dumps(g.model_dump(mode="json")), "genome_hash": g.dna_hash(),
                "parent_ids": dumps(g.parents), "hypothesis": g.hypothesis, "fitness": fitness,
                "created_at": now, "updated_at": now, "status_reason": reason})
            self.db.insert("strategy_events", {"strategy_id": g.id, "ts": now, "from_population": None,
                                               "to_population": state.value, "reason": reason or "created"})
        else:
            self.transition(g.id, state, reason, fitness=fitness)

    def transition(self, sid: str, to: State, reason: str, evidence: dict[str, Any] | None = None,
                   fitness: float | None = None) -> None:
        cur = self.db.query_one("SELECT population FROM strategies WHERE id = ?", (sid,))
        if cur is None:
            raise KeyError(sid)
        if cur["population"] == to.value and fitness is None:
            return
        now = _now()
        with self.db.transaction():
            self.db.execute("UPDATE strategies SET population = ?, updated_at = ?, status_reason = ?, "
                            "fitness = COALESCE(?, fitness) WHERE id = ?", (to.value, now, reason, fitness, sid))
            if cur["population"] != to.value:
                self.db.insert("strategy_events", {"strategy_id": sid, "ts": now, "from_population": cur["population"],
                                                   "to_population": to.value, "reason": reason,
                                                   "evidence": dumps(evidence or {})})

    def get(self, sid: str) -> Genome | None:
        r = self.db.query_one("SELECT genome FROM strategies WHERE id = ?", (sid,))
        return self._load(r["genome"], sid) if r else None

    def _load(self, raw: str, sid: str) -> Genome | None:
        """Schema-drift self-healing: a stored genome that violates a (since tightened) bound is repaired by clamping to the
        bound and re-saved; an unrepairable genome is quarantined (RETIRED) — one bad row can never stop evolution."""
        g, repaired = repair_genome(json.loads(raw))
        if g is None:
            log.warning("genome %s unrepairable — quarantined (RETIRED)", sid)
            with contextlib.suppress(Exception):
                self.db.execute("UPDATE strategies SET population = 'RETIRED' WHERE id = ?", (sid,))
            return None
        if repaired:
            log.warning("genome %s repaired after schema drift: %s", sid, repaired)
            with contextlib.suppress(Exception):
                self.db.execute("UPDATE strategies SET genome = ? WHERE id = ?", (g.model_dump_json(), sid))
        return g

    def state(self, sid: str) -> State | None:
        r = self.db.query_one("SELECT population FROM strategies WHERE id = ?", (sid,))
        return State(r["population"]) if r else None

    def list(self, states: tuple[State, ...] | None = None) -> list[tuple[Genome, State, dict[str, Any]]]:
        if states:
            q = f"SELECT * FROM strategies WHERE population IN ({','.join('?' * len(states))})"
            rows = self.db.query(q, tuple(s.value for s in states))
        else:
            rows = self.db.query("SELECT * FROM strategies")
        out = []
        for r in rows:
            g = self._load(r["genome"], r["id"])
            if g is not None:
                out.append((g, State(r["population"]), r))
        return out

    def exists_dna(self, dna_hash: str) -> str | None:
        r = self.db.query_one("SELECT id FROM strategies WHERE genome_hash = ?", (dna_hash,))
        return r["id"] if r else None

    def set_allocation(self, sid: str, usd: float) -> None:
        self.db.execute("UPDATE strategies SET virtual_allocation_usd = ?, updated_at = ? WHERE id = ?",
                        (f"{usd:.8f}", _now(), sid))

    # ---- lineage & mutations -----------------------------------------------------------------
    def add_lineage(self, parent: str, child: str, edge: str, data: dict[str, Any] | None = None) -> None:
        self.db.insert("lineage_edges", {"parent_id": parent, "child_id": child, "edge_type": edge,
                                         "created_at": _now(), "data": dumps(data or {})})

    def record_mutation(self, mid: str, parent: str, child: str, operator: str, source: str,
                        rationale: dict[str, Any]) -> None:
        self.db.insert("mutations", {"id": mid, "parent_id": parent, "child_id": child, "operator": operator,
                                     "source": source, "rationale": dumps(rationale), "created_at": _now()}, or_ignore=True)

    def resolve_mutation(self, child: str, result: dict[str, Any], promoted: bool) -> None:
        self.db.execute("UPDATE mutations SET result = ?, promoted = ?, evaluated_at = ? WHERE child_id = ?",
                        (dumps(result), int(promoted), _now(), child))

    def lineage(self, sid: str, depth: int = 6) -> dict[str, Any]:
        def up(x: str, d: int) -> list[dict[str, Any]]:
            if d == 0:
                return []
            rows = self.db.query("SELECT parent_id, edge_type, data FROM lineage_edges WHERE child_id = ?", (x,))
            return [{"id": r["parent_id"], "edge": r["edge_type"], "parents": up(r["parent_id"], d - 1)} for r in rows]

        kids = self.db.query("SELECT child_id, edge_type FROM lineage_edges WHERE parent_id = ?", (sid,))
        return {"id": sid, "ancestors": up(sid, depth), "children": [{"id": k["child_id"], "edge": k["edge_type"]} for k in kids]}

    # ---- metrics -----------------------------------------------------------------------------
    def record_metrics(self, sid: str, scope: str, metrics: dict[str, Any], regime: str = "ALL",
                       window: tuple[str, str] | None = None) -> None:
        self.db.insert("strategy_metrics", {"strategy_id": sid, "scope": scope, "regime": regime,
                                            "window_start": window[0] if window else None,
                                            "window_end": window[1] if window else None,
                                            "metrics": dumps(metrics), "created_at": _now()})

    def latest_metrics(self, sid: str, scope: str) -> dict[str, Any] | None:
        r = self.db.query_one("SELECT metrics FROM strategy_metrics WHERE strategy_id = ? AND scope = ? "
                              "ORDER BY id DESC LIMIT 1", (sid, scope))
        return json.loads(r["metrics"]) if r else None

    def counts(self) -> dict[str, int]:
        return {r["population"]: r["n"] for r in self.db.query(
            "SELECT population, COUNT(*) AS n FROM strategies GROUP BY population")}


def repair_genome(d: dict[str, Any], max_passes: int = 8) -> tuple[Genome | None, list[str]]:
    """Validate; on bound violations clamp the offending numeric field to the bound named in the error (ge/le/gt/lt)."""
    from pydantic import ValidationError
    fixes: list[str] = []
    for _ in range(max_passes):
        try:
            return Genome.model_validate(d), fixes
        except ValidationError as e:
            changed = False
            for err in e.errors():
                ctx, loc = err.get("ctx") or {}, err.get("loc") or ()
                bound = next((ctx[k] for k in ("ge", "le", "gt", "lt") if k in ctx), None)
                if bound is None or not loc:
                    continue
                node: Any = d
                for k in loc[:-1]:
                    node = node[k] if isinstance(node, dict | list) else None
                    if node is None:
                        break
                if isinstance(node, dict) and loc[-1] in node:
                    nb = float(bound) + (1e-9 if "gt" in ctx else -1e-9 if "lt" in ctx else 0.0)
                    if isinstance(node[loc[-1]], int) and not isinstance(node[loc[-1]], bool):
                        nb = int(round(nb))
                    fixes.append(f"{'.'.join(map(str, loc))}: {node[loc[-1]]} → {nb}")
                    node[loc[-1]] = nb
                    changed = True
            if not changed:
                return None, fixes
    return None, fixes
