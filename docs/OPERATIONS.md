# Operations
## Service
- `sudo systemctl status|restart|stop forge` · logs: `journalctl -u forge -f` and `/srv/forge/var/logs/forge.jsonl`
- Dashboard (private): `http://127.0.0.1:8470` (SSH tunnel: `ssh -L 8470:127.0.0.1:8470 <server>`). Operator token: `sudo cat /srv/forge/var/run/operator_token`
- Health: `/health` · readiness: `/ready` · Prometheus text: `/metrics`
## Emergency
- **STOP ALL TRADING**: dashboard button, or `sudo -u forge FORGE_HOME=/srv/forge/var /srv/forge/.venv/bin/forge stop-all [--flatten]` (or `scripts/stop-all.sh`)
- Resume (deliberate): `... forge resume` and type `RESUME TRADING`
- Cash-out Stage 1: `... forge cashout all [--now]` → liquidates to USD, pauses entries; then Coinbase app → Cash out.
## Status / audit / readiness
- `... forge status` · `... forge verify-audit` (hash chain) · `... forge readiness` (live gate)
## Going LIVE (only after `forge readiness` is green except the flag)
1. `sudo nano /etc/forge/forge.env` → `FORGE_LIVE_TRADING=true`
2. `sudo systemctl edit forge` → `[Service]\nEnvironment=FORGE_MODE=LIVE` → `sudo systemctl restart forge`
## Modal
- `scripts/deploy-modal.sh` (stop + deploy + verify source hash). Budget state shown on dashboard (GREEN/YELLOW/ORANGE/RED).
## Backups
- `scripts/backup.sh` → `/srv/forge/var/backups/YYYY-MM-DD/` (SQLite online backup + audit, no secrets).
