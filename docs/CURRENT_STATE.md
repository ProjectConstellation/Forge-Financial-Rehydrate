# CURRENT STATE — 2026-10-07 (read AGENTS.md → OPERATOR_POLICY → this → BUILD_STATUS)
- Founder portal LIVE: https://forge.northstarimagine.com (tunnel service `forge-tunnel`, config /etc/forge/tunnel/). Real-time SSE /api/live (1 s snapshots).
- `forge.service` (systemd, user forge) RUNNING in **PAPER** mode on live Coinbase data; FORGE_HOME=/srv/forge/var; API 127.0.0.1:8470.
- Paper treasury $28.27 mirrors the live USD balance. LIVE disabled until `forge readiness` green (needs ≥1 CHALLENGER).
- Improvement Loop: alternating 5m/1h evolution; Modal bursts (8×2 CPU) while budget GREEN and no validated edge.
- Supervision: 15 loops with heartbeats + auto-restart; systemd Type=notify WatchdogSec=180.
- Brain: Flash perception every 10–15 min; budget scales with measured ROI and earnings (OP-010); Pro (high) research every 3h or on escalation; Pro (max) on critical events.
- Key research lessons: docs/RESEARCH_LOG.md. Decisions: docs/DECISIONS.md. Incidents: docs/INCIDENTS.md.
- Dev: tests `.venv/bin/pytest`; dev home `.devvar/`; deploy Modal `scripts/deploy-modal.sh`; restart `sudo systemctl restart forge`.
- Open operator actions: rotate keys; top up DeepSeek (~$1.88 left); optional FORGE portfolio; domain for public dashboard.
