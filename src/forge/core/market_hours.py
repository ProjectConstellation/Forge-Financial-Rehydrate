"""US equity market-hours awareness for the Alpaca/Twelve equities rail.

Founder order 2026-10-10: "we shouldn't unnecessarily be wasting API inference compute on stock
trades... the stock market is only open during certain hours." Equities are a 24/5 rail, so
research and signal generation for them must be gated to sessions when prices actually move.
Crypto (Coinbase) and event contracts (Kalshi) are 24/7 and are NOT gated here.

Regular session:  09:30-16:00 US Eastern, Mon-Fri.
Extended session: 04:00-09:30 and 16:00-20:00 US Eastern (Alpaca 24/5 coverage; thin overnight).
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

_EST_OFFSET = 5      # US Eastern = UTC-5 (EST)
_EDT_OFFSET = 4      # US Eastern = UTC-4 (EDT)


def _dst_start(year: int) -> datetime:
    """2nd Sunday of March, 02:00 local (07:00 UTC)."""
    mar1 = datetime(year, 3, 1, tzinfo=UTC)
    day = ((6 - mar1.weekday()) % 7) + 8          # first Sunday is +((6-wd)%7); second is +7 more
    return datetime(year, 3, day, 7, 0, tzinfo=UTC)


def _dst_end(year: int) -> datetime:
    """1st Sunday of November, 02:00 local (06:00 UTC)."""
    nov1 = datetime(year, 11, 1, tzinfo=UTC)
    day = ((6 - nov1.weekday()) % 7) + 1
    return datetime(year, 11, day, 6, 0, tzinfo=UTC)


def _eastern_offset(dt: datetime) -> int:
    """Hours to subtract from UTC to get US Eastern (4 during DST, else 5)."""
    return _EDT_OFFSET if _dst_start(dt.year) <= dt < _dst_end(dt.year) else _EST_OFFSET


def eastern_now(dt: datetime | None = None) -> datetime:
    """US Eastern wall-clock (naive) derived from UTC without a tzdata dependency."""
    dt = dt or datetime.now(UTC)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return (dt - timedelta(hours=_eastern_offset(dt))).replace(tzinfo=None)


def is_equity_regular_session(dt: datetime | None = None) -> bool:
    """True during 09:30-16:00 US Eastern on a weekday (Mon-Fri)."""
    e = eastern_now(dt)
    if e.weekday() >= 5:
        return False
    return 9.5 <= (e.hour + e.minute / 60.0) < 16.0


def is_equity_extended_session(dt: datetime | None = None) -> bool:
    """True during any tradeable equity session: 04:00-20:00 US Eastern on a weekday."""
    e = eastern_now(dt)
    if e.weekday() >= 5:
        return False
    return 4.0 <= (e.hour + e.minute / 60.0) < 20.0


def equity_session(dt: datetime | None = None) -> str:
    """Machine-readable session label for logs, KVs and agent briefs."""
    if is_equity_regular_session(dt):
        return "REGULAR"
    if is_equity_extended_session(dt):
        return "EXTENDED"
    return "WEEKEND" if eastern_now(dt).weekday() >= 5 else "CLOSED"


def next_regular_open(dt: datetime | None = None) -> datetime | None:
    """Next 09:30 US Eastern regular open (Eastern-naive; advisory messages only)."""
    e = eastern_now(dt)
    for add in range(0, 9):
        day = e + timedelta(days=add)
        if day.weekday() < 5:
            cand = day.replace(hour=9, minute=30, second=0, microsecond=0)
            if add > 0 or cand > e:
                return cand
    return None
