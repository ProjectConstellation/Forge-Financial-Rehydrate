#!/usr/bin/env bash
# Swap Hermes between Opus 5.5 (operator credit, high reasoning, fast cadence) and DeepSeek V4.1 Flash (measured-ROI budget).
#   forge-hermes-mode opus [credit_usd] [hours]   |   forge-hermes-mode deepseek   |   forge-hermes-mode status
# Prompts are thin bootstraps; the real role genomes live in FORGE (prompt_genomes) and evolve there.
set -euo pipefail
H=/srv/forge/runtime/hermes; HH=$H/home; P=/srv/forge/hermes/prompts
hc() { sudo -u forge-hermes env HOME=$HH HERMES_HOME=$HH $H/app/venv/bin/hermes "$@"; }
kv() { sudo -u forge env PYTHONPATH=/srv/forge/src /srv/forge/.venv/bin/python -c "
import json,sys,time; from forge.persistence.db import Database
db=Database('/srv/forge/var/state/forge.sqlite'); v=json.loads(sys.argv[1])
if v.get('mode')=='credit': v.setdefault('start', (db.kv_get('hermes.mode') or {}).get('start') or time.time())
db.kv_set('hermes.mode', v); print('FORGE hermes.mode =', v)" "$1"; }
ids_named() { hc cron list 2>/dev/null | awk '/^  [0-9a-f]{12} \[/{id=$1} $1=="Name:" && $2 ~ /^forge-/ {print id}'; }
MODE="${1:-status}"
case "$MODE" in
  opus)
    hc config set model.provider azure-opus >/dev/null; hc config set model.default claude-opus-5-5 >/dev/null
    hc config set cron.model claude-opus-5-5 >/dev/null; hc config set cron.model_provider azure-opus >/dev/null
    EFF=high
    # name | schedule | gate script | bootstrap
    JOBS="forge-governor|every 1h|gate_governor.py|boot_governor.md
forge-alpha-inventor|0 * * * *|gate_alpha_inventor.py|boot_alpha_inventor.md
forge-adversary|30 * * * *|gate_adversary.py|boot_adversary.md
forge-critic|every 3h|gate_critic.py|boot_critic.md
forge-doctor|every 30m|gate_doctor.py|boot_doctor.md
forge-rail-hunter|every 3h|gate_rail_hunter.py|boot_rail_hunter.md
forge-scout|every 1h|forge_scout.py|boot_scout.md
forge-architect|every 6h|gate_architect.py|boot_architect.md
forge-daily-report|0 12 * * *|gate_report.py|boot_report.md"
    kv "{\"mode\": \"credit\", \"model\": \"claude-opus-5-5\", \"credit_usd\": ${2:-180}, \"hours\": ${3:-72}}" ;;
  deepseek)
    hc config set model.provider deepseek >/dev/null; hc config set model.default deepseek-flash >/dev/null
    hc config set cron.model deepseek-flash >/dev/null; hc config set cron.model_provider deepseek >/dev/null
    EFF=low
    JOBS="forge-governor|every 3h|gate_governor.py|boot_governor.md
forge-alpha-inventor|0 */6 * * *|gate_alpha_inventor.py|boot_alpha_inventor.md
forge-adversary|0 3,9,15,21 * * *|gate_adversary.py|boot_adversary.md
forge-critic|0 7 * * *|gate_critic.py|boot_critic.md
forge-doctor|every 30m|gate_doctor.py|boot_doctor.md
forge-rail-hunter|every 12h|gate_rail_hunter.py|boot_rail_hunter.md
forge-scout|every 2h|forge_scout.py|boot_scout.md
forge-architect|0 5 * * *|gate_architect.py|boot_architect.md
forge-daily-report|0 12 * * *|gate_report.py|boot_report.md"
    kv '{"mode": "deepseek", "model": "deepseek-flash"}' ;;
  status) hc config show 2>/dev/null | grep -E "Model:" | head -1; hc cron list 2>/dev/null | grep -E "Name:|Schedule:|\[(active|paused)\]" | paste - - - | sed -E 's/\s+/ /g'; exit 0 ;;
  *) echo "usage: $0 opus [credit_usd] [hours] | deepseek | status"; exit 1 ;;
esac
for id in $(ids_named); do hc cron remove "$id" >/dev/null 2>&1 || true; done
while IFS='|' read -r name sched gate boot; do
  e=$EFF; case "$name" in forge-alpha-inventor|forge-adversary|forge-architect) e=high ;; esac
  hc cron create "$sched" "$(cat $P/$boot)" --name "$name" --script "$gate" --reasoning-effort "$e" \
     --deliver local --failure-deliver local >/dev/null && echo "  job $name [$sched, $e]"
done <<< "$JOBS"
sudo systemctl restart forge-hermes
hc config show 2>/dev/null | grep -E "Model:" | head -1
