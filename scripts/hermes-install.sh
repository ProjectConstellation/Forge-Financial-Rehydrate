#!/usr/bin/env bash
# Install/refresh FORGE's Hermes integration (idempotent). Hermes runs as `forge-hermes`, HERMES_HOME under /srv/forge.
set -euo pipefail
H=/srv/forge/runtime/hermes
HH=$H/home
hc() { sudo -u forge-hermes env HOME=$HH HERMES_HOME=$HH $H/app/venv/bin/hermes "$@"; }
# 1) plugin + gate scripts + agent token (token copied 0600; Hermes never sees exchange keys)
sudo rsync -a --delete /srv/forge/hermes/plugin/hermes-forge/ $HH/plugins/hermes-forge/
sudo rsync -a /srv/forge/hermes/scripts/ $HH/scripts/
gate() { # file role est quiet_h key
  printf 'import runpy, sys\nsys.path.insert(0, __file__.rsplit("/", 1)[0])\nsys.argv = ["forge_gate.py", "%s", "%s", "%s", "%s"]\nrunpy.run_path(__file__.rsplit("/", 1)[0] + "/forge_gate.py", run_name="__main__")\n' \
    "$2" "$3" "$4" "$5" | sudo tee $HH/scripts/$1 >/dev/null
}
gate gate_governor.py       governor       0.05 6    governor
gate gate_alpha_inventor.py alpha_inventor 0.05 8    alpha_inventor
gate gate_adversary.py      adversary      0.05 8    adversary
gate gate_critic.py         critic         0.05 24   critic
gate gate_doctor.py         doctor         0.02 9999 doctor
gate gate_rail_hunter.py    rail_hunter    0.05 12   rail_hunter
gate gate_architect.py      architect      0.05 12   architect
gate gate_report.py         governor       0.05 20   report
sudo install -m 600 -o forge-hermes -g forge-hermes /srv/forge/var/run/agent_token $HH/forge/agent_token
sudo chown -R forge-hermes:forge-hermes $HH
hc plugins enable hermes-forge >/dev/null 2>&1 || true
# 2) cron jobs + model: managed by scripts/hermes-mode.sh (opus | deepseek)
# 3) cron platform: FORGE tools + skills/memory/todo/session_search/delegation only (no browser/shell/files/desktop)
hc tools disable web browser terminal file code_execution vision image_gen tts computer_use connections clarify --platform cron >/dev/null 2>&1 || true
hc tools enable forge --platform cron >/dev/null 2>&1 || true
