#!/usr/bin/env bash
# Hermes model mode: DeepSeek V4.1 Flash only (Opus/Azure retired).
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
if [ "$MODE" = "opus" ]; then echo "REFUSED: Opus/Azure retired. Use: forge-hermes-mode deepseek|status"; exit 2; fi
# ---- generic provider swap (zero recode: endpoint + model + key) ------------------------------------------------------
#   forge-hermes-mode add-provider <name> <base_url> <chat_completions|anthropic_messages> <model> <in_$/M> <out_$/M>
#        (API key read from STDIN, stored only in Hermes' 0600 .env as HERMES_KEY_<NAME>)
#   forge-hermes-mode use <name> <model> [credit_usd hours]      (credit_* = free/prepaid pool; omit for DeepSeek-style ROI)
if [ "$MODE" = "add-provider" ]; then
  name=$2; url=$3; transport=$4; model=$5; pin=${6:-0}; pout=${7:-0}
  envvar="HERMES_KEY_$(echo "$name" | tr 'a-z-' 'A-Z_')"
  key=$(cat)
  sudo python3 - "$HH/.env" "$envvar" "$key" <<'PY'
import os, sys
p, var, key = sys.argv[1:4]
lines = [l for l in open(p).read().splitlines() if not l.startswith(var + "=")] + [f"{var}={key}"]
open(p, "w").write("\n".join(lines) + "\n"); os.chmod(p, 0o600)
PY
  sudo chown forge-hermes:forge-hermes $HH/.env
  sudo -u forge-hermes python3 - "$HH/config.yaml" "$name" "$url" "$transport" "$model" "$envvar" <<'PY'
import sys, yaml
p, name, url, transport, model, envvar = sys.argv[1:7]
c = yaml.safe_load(open(p)); c.setdefault("providers", {})[name] = {"name": name, "api": url, "key_env": envvar,
    "transport": transport, "default_model": model, "models": {model: {}}, "discover_models": False}
yaml.safe_dump(c, open(p, "w"), sort_keys=False); print("provider", name, "->", url, transport, model)
PY
  sudo -u forge env PYTHONPATH=/srv/forge/src /srv/forge/.venv/bin/python -c "
import sys; from forge.persistence.db import Database
db=Database('/srv/forge/var/state/forge.sqlite'); p=db.kv_get('hermes.prices') or {}
p[sys.argv[1]]={'in': float(sys.argv[2]), 'out': float(sys.argv[3]), 'cache': float(sys.argv[2])*0.1}; db.kv_set('hermes.prices', p); print('prices', p)" "$model" "$pin" "$pout"
  exit 0
fi
if [ "$MODE" = "use" ]; then
  prov=$2; model=$3
  hc config set model.provider "$prov" >/dev/null; hc config set model.default "$model" >/dev/null
  hc config set cron.model "$model" >/dev/null; hc config set cron.model_provider "$prov" >/dev/null
  if [ -n "${4:-}" ]; then kv "{\"mode\": \"credit\", \"model\": \"$model\", \"credit_usd\": $4, \"hours\": ${5:-72}, \"start\": $(date +%s)}"
  else kv "{\"mode\": \"deepseek\", \"model\": \"$model\"}"; fi
  sudo systemctl restart forge-hermes; hc config show 2>/dev/null | grep -E "Model:" | head -1; exit 0
fi
case "$MODE" in
  opus)
# RETIRED: hc config set model.provider azure-opus >/dev/null; hc config set model.default claude-opus-5-5 >/dev/null
# RETIRED: hc config set cron.model claude-opus-5-5 >/dev/null; hc config set cron.model_provider azure-opus >/dev/null
    EFF=high
    # name | schedule | gate script | bootstrap
    JOBS="forge-governor|every 1h|gate_governor.py|boot_governor.md
forge-alpha-inventor|0,30 * * * *|gate_alpha_inventor.py|boot_alpha_inventor.md
forge-adversary|15,45 * * * *|gate_adversary.py|boot_adversary.md
forge-critic|every 2h|gate_critic.py|boot_critic.md
forge-doctor|every 30m|gate_doctor.py|boot_doctor.md
forge-rail-hunter|every 2h|gate_rail_hunter.py|boot_rail_hunter.md
forge-scout|every 1h|forge_scout.py|boot_scout.md
forge-architect|every 3h|gate_architect.py|boot_architect.md
forge-daily-report|0 12 * * *|gate_report.py|boot_report.md"
# RETIRED: kv "{\"mode\": \"credit\", \"model\": \"claude-opus-5-5\", \"credit_usd\": ${2:-180}, \"hours\": ${3:-72}}" ;;
  deepseek)
    # Ensure provider block exists (Hermes built-in deepseek profile + DEEPSEEK_API_KEY)
    hc config set model.provider deepseek >/dev/null; hc config set model.default deepseek-flash >/dev/null
    hc config set cron.model deepseek-flash >/dev/null; hc config set cron.model_provider deepseek >/dev/null
    hc config set agent.reasoning_effort medium >/dev/null || true
    EFF=medium
    JOBS="forge-governor|every 3h|gate_governor.py|boot_governor.md
forge-alpha-inventor|0 */6 * * *|gate_alpha_inventor.py|boot_alpha_inventor.md
forge-adversary|0 3,9,15,21 * * *|gate_adversary.py|boot_adversary.md
forge-critic|0 7 * * *|gate_critic.py|boot_critic.md
forge-doctor|every 30m|gate_doctor.py|boot_doctor.md
forge-rail-hunter|every 12h|gate_rail_hunter.py|boot_rail_hunter.md
forge-scout|every 2h|forge_scout.py|boot_scout.md
forge-architect|0 5 * * *|gate_architect.py|boot_architect.md
forge-daily-report|0 12 * * *|gate_report.py|boot_report.md"
    kv '{"mode": "deepseek", "model": "deepseek-flash", "effort_policy": "medium_everyday_high_hard_extra_high_rare"}' ;;
  status) hc config show 2>/dev/null | grep -E "Model:" | head -1; hc cron list 2>/dev/null | grep -E "Name:|Schedule:|\[(active|paused)\]" | paste - - - | sed -E 's/\s+/ /g'; exit 0 ;;
  *) echo "usage: $0 opus [credit_usd] [hours] | deepseek | status"; exit 1 ;;
esac
for id in $(ids_named); do hc cron remove "$id" >/dev/null 2>&1 || true; done
while IFS='|' read -r name sched gate boot; do
  e=$EFF; case "$name" in
    # HIGH: invention, falsification, prompt evolution, governor, rail, critic
    # EXTRA HIGH (max): never default on cron — only event/LIVE-gate style wakes
    forge-alpha-inventor|forge-adversary|forge-architect|forge-governor|forge-rail-hunter|forge-critic) e=high ;;
    *) e=medium ;;  # normal minimum
  esac
  hc cron create "$sched" "$(cat $P/$boot)" --name "$name" --script "$gate" --reasoning-effort "$e" \
     --deliver local --failure-deliver local >/dev/null && echo "  job $name [$sched, $e]"
done <<< "$JOBS"
sudo systemctl restart forge-hermes
hc config show 2>/dev/null | grep -E "Model:" | head -1
