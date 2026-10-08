# FORGE Firm Capability Matrix — 2026-10-08 (Phase 0/1)
Mode: **PAPER_REAL_MARKET_SIM_MONEY** · LIVE algorithmic trading OFF until founder auth.

| Requirement | Component | Status | Gap | Action |
|---|---|---|---|---|
| Dedicated runtime | forge/hermes/ops/eng/tunnel/guardian | WORKING | — | PRESERVE |
| DeepSeek Flash intelligence | hermes profiles + brain | WORKING | Opus retired | PRESERVE |
| Paper spot evolution | PaperVenue + genomes | WORKING | Fee-blind breakouts weak | UPGRADE exits/fees |
| Stable peg/triangle | pegmaker shadow | WORKING (+EV) | Under-allocated vs spot | UPGRADE paper priority |
| Kalshi shadow/SAGE-1 | crossrail + settlement_window | WORKING | No API key → no auth PAPER | GATE on founder key |
| USDC idle yield | idle_yield LIVE convert | WORKING | Rewards $0 so far | PRESERVE |
| Profit velocity | profit_velocity | WORKING | Dual floor missing | UPGRADE $0.50/$1 |
| Profit Recovery playbook | — | MISSING | No auto objective open | BUILD |
| Mara firm identity | ops SOUL | PARTIAL | Not named firm chart | UPGRADE |
| Role → employee map | roles.py | PARTIAL | Old names only | UPGRADE aliases |
| Cognitive spend governor | inference_calls | PARTIAL | No gate/ROI loop | BUILD lite |
| PAPER/LIVE labels | metrics/ops | PARTIAL | Ambiguous wording | UPGRADE |
| SEC / equities PAPER | — | MISSING | No ingest | BUILD Stage-1 |
| Twelve Data / Odds | — | MISSING | Need keys | PREPARE adapters |
| 24h paper trial pack | — | MISSING | Instrumentation | BUILD |
