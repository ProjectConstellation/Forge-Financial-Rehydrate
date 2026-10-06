"""Append-only, hash-chained JSONL audit journal (DOSSIER §26.1).

Each line: {"seq", "ts", "kind", "actor", "data", "prev", "hash"} where
hash = sha256(prev + canonical_json(body)). Tampering or truncation in the middle is detectable
with `verify()`. Secrets must never be passed in `data` (callers pass references only).
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from forge.persistence.db import dumps

GENESIS = "0" * 64
_SECRET_HINTS = ("secret", "private_key", "api_key", "token", "password")


class AuditJournal:
    def __init__(self, directory: Path) -> None:
        self.dir = directory
        self.dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._prev, self._seq = self._load_tail()

    def _files(self) -> list[Path]:
        return sorted(self.dir.glob("*.jsonl"))

    def _load_tail(self) -> tuple[str, int]:
        for f in reversed(self._files()):
            last = None
            with f.open("rb") as fh:
                for line in fh:
                    if line.strip():
                        last = line
            if last:
                rec = json.loads(last)
                return rec["hash"], rec["seq"]
        return GENESIS, 0

    @staticmethod
    def _scrub(data: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for k, v in data.items():
            if any(h in k.lower() for h in _SECRET_HINTS):
                out[k] = "[REDACTED]"
            elif isinstance(v, dict):
                out[k] = AuditJournal._scrub(v)
            else:
                out[k] = v
        return out

    def append(self, kind: str, data: dict[str, Any], actor: str = "forge") -> str:
        with self._lock:
            now = datetime.now(UTC)
            body = {"seq": self._seq + 1, "ts": now.isoformat(), "kind": kind, "actor": actor,
                    "data": self._scrub(data), "prev": self._prev}
            canon = dumps(body)
            h = hashlib.sha256((self._prev + canon).encode()).hexdigest()
            line = json.dumps({**json.loads(canon), "hash": h}, separators=(",", ":"), sort_keys=True)
            path = self.dir / f"{now:%Y-%m-%d}.jsonl"
            fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o640)
            try:
                os.write(fd, (line + "\n").encode())
                os.fsync(fd)
            finally:
                os.close(fd)
            self._prev, self._seq = h, body["seq"]
            return h

    def verify(self) -> tuple[bool, int, str]:
        """Return (ok, records_checked, message)."""
        prev, seq, n = GENESIS, 0, 0
        for f in self._files():
            with f.open() as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    rec = json.loads(line)
                    h = rec.pop("hash")
                    if rec["prev"] != prev or rec["seq"] != seq + 1:
                        return False, n, f"chain break at seq {rec['seq']} in {f.name}"
                    if hashlib.sha256((prev + dumps(rec)).encode()).hexdigest() != h:
                        return False, n, f"hash mismatch at seq {rec['seq']} in {f.name}"
                    prev, seq, n = h, rec["seq"], n + 1
        return True, n, "ok"

    def tail(self, n: int = 50) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for f in reversed(self._files()):
            lines = f.read_text().splitlines()
            for line in reversed(lines):
                if line.strip():
                    out.append(json.loads(line))
                    if len(out) >= n:
                        return out
        return out
