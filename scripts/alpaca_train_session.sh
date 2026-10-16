#!/usr/bin/env bash
set -euo pipefail
set -a; source /etc/forge/forge.env; set +a
cd /srv/forge
exec /srv/forge/.venv/bin/python -m forge.opportunities.alpaca_train
