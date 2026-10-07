#!/usr/bin/env bash
# Install/refresh FORGE's Hermes integration (idempotent). Hermes runs as `forge-hermes`, HERMES_HOME under /srv/forge.
set -euo pipefail
H=/srv/forge/runtime/hermes
HH=$H/home
hc() { sudo -u forge-hermes env HOME=$HH HERMES_HOME=$HH $H/app/venv/bin/hermes "$@"; }
# 1) plugin + gate scripts + agent token (token copied 0600; Hermes never sees exchange keys)
sudo rsync -a --delete /srv/forge/hermes/plugin/hermes-forge/ $HH/plugins/hermes-forge/
sudo rsync -a /srv/forge/hermes/scripts/ $HH/scripts/
for r in governor scientist critic doctor; do
  printf 'import runpy, sys\nsys.argv = ["forge_gate.py", "%s", "%s", "%s"]\nrunpy.run_path(__file__.rsplit("/", 1)[0] + "/forge_gate.py", run_name="__main__")\n' \
    "$r" "$( [ $r = scientist ] && echo 0.03 || echo 0.01 )" "$( case $r in governor) echo 6;; scientist) echo 8;; critic) echo 24;; doctor) echo 9999;; esac )" \
    | sudo tee $HH/scripts/gate_$r.py >/dev/null
done
sudo install -m 600 -o forge-hermes -g forge-hermes /srv/forge/var/run/agent_token $HH/forge/agent_token
sudo chown -R forge-hermes:forge-hermes $HH
hc plugins enable hermes-forge >/dev/null 2>&1 || true
# 2) cron jobs (Flash; low effort except scientist; local delivery; budget/change-gated pre-run scripts)
existing=$(hc cron list 2>/dev/null || true)
mk() { # name schedule script effort prompt
  if ! grep -q "$1" <<<"$existing"; then
    hc cron create "$2" "$5" --name "$1" --script "$3" --reasoning-effort "$4" --deliver local --failure-deliver local >/dev/null
    echo "created $1"
  fi
}
P=/srv/forge/hermes/prompts
mk forge-scout       "every 2h"  forge_scout.py  low  "$(cat $P/scout.md)"
mk forge-governor    "every 3h"  gate_governor.py low  "$(cat $P/governor.md)"
mk forge-scientist   "every 6h"  gate_scientist.py high "$(cat $P/scientist.md)"
mk forge-critic      "0 7 * * *" gate_critic.py  low  "$(cat $P/critic.md)"
mk forge-doctor      "every 30m" gate_doctor.py  low  "$(cat $P/doctor.md)"
mk forge-daily-report "0 12 * * *" gate_governor.py low "$(cat $P/report.md)"
hc cron list 2>/dev/null | head -40
# 3) cron platform: FORGE tools + skills/memory/todo/session_search/delegation only (no browser/shell/files/desktop)
hc tools disable web browser terminal file code_execution vision image_gen tts computer_use connections clarify --platform cron >/dev/null 2>&1 || true
hc tools enable forge --platform cron >/dev/null 2>&1 || true
