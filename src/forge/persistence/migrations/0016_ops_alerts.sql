-- EXECUTIVE OPS rule alerts (edge-triggered, no LLM cost; delivered to the owner by the guardian).
CREATE TABLE ops_alerts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  metric TEXT NOT NULL,
  arg TEXT,
  op TEXT NOT NULL,
  threshold TEXT NOT NULL,
  note TEXT,
  once INTEGER NOT NULL DEFAULT 0,
  active INTEGER NOT NULL DEFAULT 1,
  armed_true INTEGER NOT NULL DEFAULT 0,
  last_fired REAL,
  fire_count INTEGER NOT NULL DEFAULT 0
);
