#!/usr/bin/env bash
# Online backup of FORGE state (no secrets). Keeps 14 daily copies.
set -euo pipefail
sudo -u forge bash -c 'set -e; D=/srv/forge/var/backups/$(date -u +%F); mkdir -p "$D"
  /srv/forge/.venv/bin/python -c "import sqlite3; s=sqlite3.connect(\"/srv/forge/var/state/forge.sqlite\"); d=sqlite3.connect(\"$D/forge-state.sqlite\"); s.backup(d); d.close()"
  tar -C /srv/forge/var -czf "$D/audit.tgz" audit
  ls -1dt /srv/forge/var/backups/*/ | tail -n +15 | xargs -r rm -rf
  echo "backup -> $D"'
