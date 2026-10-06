"""Per-symbol data-quality state (DOSSIER §9.2). No live strategy may trade on data failing these checks."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class SymbolQuality:
    symbol: str
    last_tick_ns: int = 0
    last_trade_ns: int = 0
    last_book_ns: int = 0
    exchange_lag_ms: float = 0.0       # recv - exchange timestamp (EWMA)
    outliers: int = 0
    crossed: int = 0

    def fresh(self, now_ns: int, stale_ms: int) -> bool:
        last = max(self.last_tick_ns, self.last_book_ns)
        return last > 0 and (now_ns - last) / 1e6 <= stale_ms


@dataclass
class FeedQuality:
    connected: bool = False
    last_message_ns: int = 0
    last_heartbeat_ns: int = 0
    reconnects: int = 0
    sequence_gaps: int = 0
    messages: int = 0
    parse_errors: int = 0
    connected_since_ns: int = 0
    symbols: dict[str, SymbolQuality] = field(default_factory=dict)

    def sym(self, s: str) -> SymbolQuality:
        q = self.symbols.get(s)
        if q is None:
            q = self.symbols[s] = SymbolQuality(s)
        return q

    def healthy(self, now_ns: int, stale_ms: int = 10_000) -> bool:
        return self.connected and (now_ns - self.last_message_ns) / 1e6 <= stale_ms

    def snapshot(self, now_ns: int) -> dict[str, object]:
        return {
            "connected": self.connected,
            "seconds_since_message": round((now_ns - self.last_message_ns) / 1e9, 2) if self.last_message_ns else None,
            "reconnects": self.reconnects,
            "sequence_gaps": self.sequence_gaps,
            "messages": self.messages,
            "parse_errors": self.parse_errors,
            "uptime_s": round((now_ns - self.connected_since_ns) / 1e9) if self.connected else 0,
            "symbols": len(self.symbols),
        }
