"""SQLite (WAL) persistence with ordered SQL migrations.

Design: a single connection guarded by a re-entrant lock. FORGE's write rate is low (decisions,
fills, metrics) — market ticks go to Parquet, not SQLite — so one serialized connection is both
simplest and fastest at this footprint. All SQL is kept portable so a PostgreSQL backend can be
added behind the same interface (RESOLUTIONS #3).
"""

from __future__ import annotations

import json
import sqlite3
import threading
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from decimal import Decimal
from importlib import resources
from pathlib import Path
from typing import Any


def _adapt_decimal(d: Decimal) -> str:
    return format(d, "f")


sqlite3.register_adapter(Decimal, _adapt_decimal)


def dumps(obj: Any) -> str:
    return json.dumps(obj, default=_json_default, separators=(",", ":"), sort_keys=True)


def _json_default(o: Any) -> Any:
    if isinstance(o, Decimal):
        return format(o, "f")
    if isinstance(o, datetime):
        return o.astimezone(UTC).isoformat()
    if isinstance(o, set | frozenset | tuple):
        return list(o)
    if hasattr(o, "model_dump"):
        return o.model_dump(mode="json")
    if isinstance(o, Path):
        return str(o)
    raise TypeError(f"not JSON serializable: {type(o)}")


class Database:
    def __init__(self, path: Path | str) -> None:
        self.path = str(path)
        if self.path != ":memory:":
            Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None,
                                     timeout=10.0)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.RLock()
        self._tx_depth = 0
        with self._lock:
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA synchronous=NORMAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._conn.execute("PRAGMA busy_timeout=10000")
            self._conn.execute("PRAGMA temp_store=MEMORY")

    # ---- core API --------------------------------------------------------------------------
    def execute(self, sql: str, params: Sequence[Any] | dict[str, Any] = ()) -> sqlite3.Cursor:
        with self._lock:
            return self._conn.execute(sql, params)

    def executemany(self, sql: str, rows: Sequence[Sequence[Any]]) -> None:
        with self.transaction():
            self._conn.executemany(sql, rows)

    def query(self, sql: str, params: Sequence[Any] | dict[str, Any] = ()) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(r) for r in self._conn.execute(sql, params).fetchall()]

    def query_one(self, sql: str, params: Sequence[Any] | dict[str, Any] = ()) -> dict[str, Any] | None:
        with self._lock:
            r = self._conn.execute(sql, params).fetchone()
            return dict(r) if r else None

    def scalar(self, sql: str, params: Sequence[Any] | dict[str, Any] = ()) -> Any:
        with self._lock:
            r = self._conn.execute(sql, params).fetchone()
            return r[0] if r else None

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Nested-safe transaction (outermost BEGIN IMMEDIATE / COMMIT)."""
        with self._lock:
            outer = self._tx_depth == 0
            if outer:
                self._conn.execute("BEGIN IMMEDIATE")
            self._tx_depth += 1
            try:
                yield self._conn
            except BaseException:
                self._tx_depth -= 1
                if outer:
                    self._conn.execute("ROLLBACK")
                raise
            else:
                self._tx_depth -= 1
                if outer:
                    self._conn.execute("COMMIT")

    def insert(self, table: str, row: dict[str, Any], *, or_ignore: bool = False) -> int:
        cols = ", ".join(row)
        qs = ", ".join("?" for _ in row)
        verb = "INSERT OR IGNORE" if or_ignore else "INSERT"
        vals = [dumps(v) if isinstance(v, dict | list) else v for v in row.values()]
        with self._lock:
            cur = self._conn.execute(f"{verb} INTO {table} ({cols}) VALUES ({qs})", vals)
            return cur.rowcount

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    # ---- KV state --------------------------------------------------------------------------
    def kv_get(self, key: str, default: Any = None) -> Any:
        r = self.query_one("SELECT value FROM kv_state WHERE key = ?", (key,))
        return json.loads(r["value"]) if r else default

    def kv_set(self, key: str, value: Any) -> None:
        self.execute(
            "INSERT INTO kv_state(key, value, updated_at) VALUES(?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at",
            (key, dumps(value), datetime.now(UTC).isoformat()),
        )

    # ---- migrations ------------------------------------------------------------------------
    def migrate(self) -> list[str]:
        self.execute("CREATE TABLE IF NOT EXISTS schema_migrations ("
                     "version INTEGER PRIMARY KEY, name TEXT NOT NULL, applied_at TEXT NOT NULL)")
        applied = {r["version"] for r in self.query("SELECT version FROM schema_migrations")}
        done: list[str] = []
        files = sorted(
            (f for f in resources.files("forge.persistence.migrations").iterdir()
             if f.name.endswith(".sql")),
            key=lambda f: f.name,
        )
        for f in files:
            version = int(f.name.split("_", 1)[0])
            if version in applied:
                continue
            sql = f.read_text()
            with self._lock:
                self._conn.execute("BEGIN IMMEDIATE")
                try:
                    for stmt in _split_sql(sql):
                        self._conn.execute(stmt)
                    self._conn.execute("INSERT INTO schema_migrations VALUES (?, ?, ?)",
                                       (version, f.name, datetime.now(UTC).isoformat()))
                    self._conn.execute("COMMIT")
                except BaseException:
                    self._conn.execute("ROLLBACK")
                    raise
            done.append(f.name)
        return done

    def schema_version(self) -> int:
        return int(self.scalar("SELECT COALESCE(MAX(version), 0) FROM schema_migrations") or 0)


def _split_sql(sql: str) -> list[str]:
    out, buf = [], []
    for line in sql.splitlines():
        if line.strip().startswith("--"):
            continue
        buf.append(line)
        if line.rstrip().endswith(";"):
            stmt = "\n".join(buf).strip()
            if stmt:
                out.append(stmt)
            buf = []
    tail = "\n".join(buf).strip()
    if tail:
        out.append(tail)
    return out
