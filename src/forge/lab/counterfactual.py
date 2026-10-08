"""Counterfactual stubs — log alternate decisions for learning (blueprint §76)."""
from __future__ import annotations

import json
import logging
import time
from typing import Any

log = logging.getLogger("forge.counterfactual")


def record(db: Any, *, decision: str, chosen: str, alts: list[str], context: dict[str, Any]) -> None:
    try:
        db.execute(
            "INSERT INTO research_notes (id, ts, author, kind, title, body) VALUES (?,?,?,?,?,?)",
            (f"cf_{int(time.time()*1000)}", time.time(), "counterfactual", "counterfactual",
             f"{decision}:{chosen}", json.dumps({"alts": alts, "context": context}, default=str)[:1900]),
        )
    except Exception as e:
        log.debug("cf record: %s", e)
