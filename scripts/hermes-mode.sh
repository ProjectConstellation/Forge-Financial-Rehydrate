#!/usr/bin/env bash
# Swap Hermes between Opus 5.5 (operator credit, high reasoning, fast cadence) and DeepSeek V4.1 Flash (measured-ROI budget).
#   scripts/hermes-mode.sh opus [credit_usd] [hours]     |     scripts/hermes-mode.sh deepseek     |     scripts/hermes-mode.sh status
set -euo pipefail
H=/srv/forge/runtime/hermes; HH=$H/home
hc() { sudo -u forge-hermes env HOME=$HH HERMES_HOME=$HH $H/app/venv/bin/hermes "$@"; }
kv() { sudo -u forge env PYTHONPATH=/srv/forge/src /srv/forge/.venv/bin/python -c "
import json,sys,time; from forge.persistence.db import Database
db=Database('/srv/forge/var/state/forge.sqlite'); v=json.loads(sys.argv[1]); v.setdefault('start', time.time()) if v.get('mode')=='credit' else None
db.kv_set('hermes.mode', v); print('FORGE hermes.mode =', v)" "$1"; }
id_of() { hc cron list 2>/dev/null | awk -v n="$1" '/^  [0-9a-f]{12} \[/{id=$1} $1=="Name:" && $2==n {print id}'; }
ensure() { # name schedule script effort promptfile
  local id; id=$(id_of "$1")
  if [ -z "$id" ]; then hc cron create "$2" "$(cat /srv/forge/hermes/prompts/$5)" --name "$1" --script "$3" --reasoning-effort "$4" \
       --deliver local --failure-deliver local >/dev/null; else hc cron edit "$id" --schedule "$2" --reasoning-effort "$4" >/dev/null; fi
}
pause() { local id; id=$(id_of "$1"); [ -n "$id" ] && hc cron pause "$id" >/dev/null 2>&1 || true; }
resume() { local id; id=$(id_of "$1"); [ -n "$id" ] && hc cron resume "$id" >/dev/null 2>&1 || true; }
case "${1:-status}" in
  opus)
    hc config set model.provider azure-opus >/dev/null; hc config set model.default claude-opus-5-5 >/dev/null
    hc config set cron.model claude-opus-5-5 >/dev/null; hc config set cron.model_provider azure-opus >/dev/null
    ensure forge-scout       "every 1h"  forge_scout.py   high scout.md
    ensure forge-governor    "every 1h"  gate_governor.py high governor.md
    ensure forge-scientist   "every 1h"  gate_scientist.py high scientist.md
    ensure forge-scientist-b "every 90m" gate_scientist_b.py high scientist_b.md
    ensure forge-rail-hunter "every 3h"  gate_rail_hunter.py high rail_hunter.md
    ensure forge-critic      "every 4h"  gate_critic.py   high critic.md
    ensure forge-doctor      "every 30m" gate_doctor.py   high doctor.md
    for j in forge-scientist-b forge-rail-hunter; do resume $j; done
    kv "{\"mode\": \"credit\", \"model\": \"claude-opus-5-5\", \"credit_usd\": ${2:-180}, \"hours\": ${3:-72}}"
    ;;
  deepseek)
    hc config set model.provider deepseek >/dev/null; hc config set model.default deepseek-flash >/dev/null
    hc config set cron.model deepseek-flash >/dev/null; hc config set cron.model_provider deepseek >/dev/null
    ensure forge-scout       "every 2h"  forge_scout.py   low  scout.md
    ensure forge-governor    "every 3h"  gate_governor.py low  governor.md
    ensure forge-scientist   "every 6h"  gate_scientist.py high scientist.md
    ensure forge-critic      "0 7 * * *" gate_critic.py   low  critic.md
    ensure forge-doctor      "every 30m" gate_doctor.py   low  doctor.md
    for j in forge-scientist-b forge-rail-hunter; do pause $j; done
    kv '{"mode": "deepseek", "model": "deepseek-flash"}'
    ;;
  status) ;;
  *) echo "usage: $0 opus [credit_usd] [hours] | deepseek | status"; exit 1;;
esac
sudo systemctl restart forge-hermes
hc config show 2>/dev/null | grep -E "Model:" ; hc cron list 2>/dev/null | grep -E "^\s+Name:|Schedule:|\[(active|paused)\]" | paste - - - | sed -E 's/\s+/ /g'
