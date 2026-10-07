from datetime import UTC, datetime, timedelta

from forge.persistence.db import Database


def test_iso_window_comparison_is_correct():
    """Regression: ISO 'T' timestamps must be compared against ISO-formatted bounds (not datetime() with a space)."""
    db = Database(":memory:")
    db.execute("CREATE TABLE t (ts TEXT)")
    old = (datetime.now(UTC) - timedelta(hours=3)).isoformat()
    new = (datetime.now(UTC) - timedelta(minutes=5)).isoformat()
    db.execute("INSERT INTO t VALUES (?), (?)", (old, new))
    n = db.scalar("SELECT COUNT(*) FROM t WHERE ts > strftime('%Y-%m-%dT%H:%M:%S','now','-60 minutes')")
    assert n == 1
