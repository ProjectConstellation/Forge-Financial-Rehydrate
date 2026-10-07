#!/usr/bin/env bash
# FORGE Engineering Cell setup (OP-025). Run on the FORGE host as root:  sudo bash scripts/eng-setup.sh   (idempotent)
# forge-eng user + sandboxed Hermes Engineer (Opus 5.5 xhigh, terminal/file tools inside its own repo only) + root
# deployer timer (the ONLY path from AI-written code to production).
set -euo pipefail
F=/srv/forge; H=$F/runtime/hermes; E=$F/runtime/eng; EH=$E/home; R=$E/repo
id forge-eng >/dev/null 2>&1 || useradd --system -U -d $EH -s /usr/sbin/nologin -c "FORGE Engineer (sandboxed)" forge-eng
mkdir -p $EH/forge $EH/plugins $F/runtime/deploy; chown -R forge-eng:forge-eng $EH
setfacl -m u:forge-eng:--x $F $F/runtime
chmod 755 $E 2>/dev/null || true

# git: allow the three repos explicitly (different owners) — nothing else
for d in $F $F/.git $R $R/.git $F/runtime/deploy/stage $F/runtime/deploy/stage/.git; do git config --system --get-all safe.directory | grep -qx "$d" || git config --system --add safe.directory "$d"; done

# engineer repo (own clone; remote prod = production, read-only to forge-eng)
install -d -o forge-eng -g forge-eng -m 755 $R
if [ ! -d $R/.git ]; then sudo -u forge-eng git clone -q $F $R; fi
sudo -u forge-eng git -C $R remote remove origin 2>/dev/null || true
sudo -u forge-eng git -C $R remote get-url prod >/dev/null 2>&1 || sudo -u forge-eng git -C $R remote add prod $F
sudo -u forge-eng git -C $R config user.name "FORGE Engineer"; sudo -u forge-eng git -C $R config user.email "engineer@forge.local"
sudo -u forge-eng git -C $R fetch -q prod
chmod 755 $R
# venv for the engineer + the deployer's sandboxed test runs (Python 3.14, uv.lock --frozen)
sudo -u forge-eng env UV_NO_CONFIG=1 UV_CACHE_DIR=$EH/.cache/uv UV_PYTHON=/usr/bin/python3.14 UV_PYTHON_DOWNLOADS=never \
  bash -c "cd $R && $F/.tools/uv sync --frozen --quiet"

# Hermes profile
install -o forge-eng -g forge-eng -m 600 $F/hermes/eng/SOUL.md $EH/SOUL.md
[ -f $EH/config.yaml ] || install -o forge-eng -g forge-eng -m 600 $F/hermes/eng/config.yaml $EH/config.yaml
rm -rf $EH/plugins/hermes-forge-eng; cp -r $F/hermes/plugin/hermes-forge-eng $EH/plugins/
mkdir -p $EH/scripts; install -m 644 $F/hermes/eng/gate_engineer.py $EH/scripts/gate_engineer.py
touch $EH/.env; chmod 600 $EH/.env
python3 - $H/home/.env $EH/.env <<'PY'
import sys
src, dst = sys.argv[1:3]
keep = {l.split("=", 1)[0]: l for l in open(dst).read().splitlines() if "=" in l}
for l in open(src).read().splitlines():
    if l.split("=", 1)[0] in ("AZURE_ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY"):
        keep[l.split("=", 1)[0]] = l
keep["FORGE_API"] = "FORGE_API=http://127.0.0.1:8470"
open(dst, "w").write("\n".join(keep.values()) + "\n")
PY
install -m 600 $F/var/run/eng_token $EH/forge/eng_token
chown -R forge-eng:forge-eng $EH

cat > /etc/systemd/system/forge-eng.service <<'X'
[Unit]
Description=FORGE Engineer (Hermes v0.21.5; sandboxed coding agent; never deploys — the root deployer does)
After=network-online.target forge.service
Wants=network-online.target

[Service]
Type=simple
User=forge-eng
Group=forge-eng
Slice=forge.slice
Environment=HOME=/srv/forge/runtime/eng/home
Environment=HERMES_HOME=/srv/forge/runtime/eng/home
WorkingDirectory=/srv/forge/runtime/eng/repo
ExecStart=/srv/forge/runtime/hermes/app/venv/bin/hermes gateway
Restart=always
RestartSec=15
Nice=10
CPUQuota=150%
MemoryMax=2500M
TasksMax=512
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictSUIDSGID=true
LockPersonality=true
ReadWritePaths=/srv/forge/runtime/eng/home /srv/forge/runtime/eng/repo
ReadOnlyPaths=/srv/forge/runtime/hermes/app
InaccessiblePaths=/etc/forge /srv/forge/var /srv/forge/runtime/hermes/home /srv/forge/runtime/ops -/srv/forge/runtime/signal -/srv/forge-archive -/srv/forge/runtime/deploy -/srv/northstar -/opt/northstar

[Install]
WantedBy=multi-user.target
X

# root deployer + 2-minute timer
install -m 700 $F/scripts/forge_deployer.py /usr/local/sbin/forge-deployer
cat > /etc/systemd/system/forge-deployer.service <<'X'
[Unit]
Description=FORGE root deployer (policy scan → sandboxed tests → deploy → 10-min health watch → auto-rollback)
After=forge.service
[Service]
Type=oneshot
ExecStart=/usr/local/sbin/forge-deployer
TimeoutStartSec=3600
X
cat > /etc/systemd/system/forge-deployer.timer <<'X'
[Unit]
Description=FORGE deployer queue check (every 2 min)
[Timer]
OnBootSec=3min
OnUnitInactiveSec=2min
[Install]
WantedBy=timers.target
X
systemctl daemon-reload
systemctl enable --now forge-eng >/dev/null 2>&1
systemctl enable --now forge-deployer.timer >/dev/null 2>&1
sleep 10

# the Engineer's wake-up job (gate = free when no ticket is waiting)
HC="sudo -u forge-eng env HOME=$EH HERMES_HOME=$EH $H/app/venv/bin/hermes"
for id in $($HC cron list 2>/dev/null | awk '/^  [0-9a-f]{12} \[/{id=$1} $1=="Name:" && $2=="forge-engineer" {print id}'); do $HC cron remove "$id" >/dev/null 2>&1 || true; done
$HC cron create "every 10m" "$(cat $F/hermes/eng/boot_engineer.md)" --name forge-engineer --script "$EH/scripts/gate_engineer.py" \
  --reasoning-effort xhigh --deliver local --failure-deliver local >/dev/null
systemctl restart forge-eng
echo "forge-eng: $(systemctl is-active forge-eng) · deployer timer: $(systemctl is-active forge-deployer.timer)"
