#!/usr/bin/env bash
# STOP ALL TRADING (DIRECTIVE §29). Usage: scripts/stop-all.sh [--flatten] [--reason "text"]
set -euo pipefail
sudo -u forge env FORGE_HOME=/srv/forge/var FORGE_ENV=production /srv/forge/.venv/bin/python -m forge.cli stop-all "$@"
