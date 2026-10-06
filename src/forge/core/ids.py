"""Identifiers. Prefixed, sortable (time-ordered) IDs; deterministic idempotency keys."""

from __future__ import annotations

import hashlib
import os
import time


def new_id(prefix: str) -> str:
    """Time-ordered unique id like `opp_01HZX...` (ms timestamp + 64 random bits, base32)."""
    ms = int(time.time() * 1000)
    rnd = int.from_bytes(os.urandom(8), "big")
    return f"{prefix}_{_b32(ms, 9)}{_b32(rnd, 13)}"


_ALPH = "0123456789abcdefghjkmnpqrstvwxyz"


def _b32(n: int, width: int) -> str:
    out = []
    for _ in range(width):
        out.append(_ALPH[n & 31])
        n >>= 5
    return "".join(reversed(out))


def idempotency_key(*parts: object) -> str:
    """Deterministic key: the same logical action always maps to the same key (retry-safe)."""
    h = hashlib.sha256("|".join(str(p) for p in parts).encode()).hexdigest()
    return f"fg-{h[:32]}"
