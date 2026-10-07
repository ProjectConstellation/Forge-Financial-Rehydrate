#!/usr/bin/env bash
# FORGE OPS COMMANDER host setup (OP-023). Run on the FORGE host as root:  sudo bash scripts/ops-setup.sh
# Idempotent. Creates the forge-ops user + sandboxed unit, installs the ops profile (SOUL, config, plugin, keys copied
# server-side from the research Hermes .env — never printed), the polkit rule (restart/start of forge*.service only),
# and /usr/local/sbin/forge-ops-telegram (hidden-input Telegram activation). The service starts without messaging until
# Telegram is activated.
set -euo pipefail
F=/srv/forge; H=$F/runtime/hermes; O=$F/runtime/ops; OH=$O/home
id forge-ops >/dev/null 2>&1 || useradd --system -U -d $OH -s /usr/sbin/nologin -c "FORGE OPS Commander" forge-ops
usermod -aG systemd-journal forge-ops
mkdir -p $OH/plugins $OH/forge $O/work
setfacl -m u:forge-ops:--x $F $F/runtime

# profile: identity + config (config only seeded once; SOUL refreshed) + plugin
install -m 600 $F/hermes/ops/SOUL.md $OH/SOUL.md
[ -f $OH/config.yaml ] || install -m 600 $F/hermes/ops/config.yaml $OH/config.yaml
rm -rf $OH/plugins/hermes-forge-ops; cp -r $F/hermes/plugin/hermes-forge-ops $OH/plugins/
# keys: model credentials copied server-side from the research profile (no display); FORGE ops token
touch $OH/.env; chmod 600 $OH/.env
python3 - $H/home/.env $OH/.env <<'PY'
import sys
src, dst = sys.argv[1:3]
want = ("AZURE_ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY")
keep = {l.split("=", 1)[0]: l for l in open(dst).read().splitlines() if "=" in l}
for l in open(src).read().splitlines():
    if l.split("=", 1)[0] in want:
        keep[l.split("=", 1)[0]] = l
keep["FORGE_API"] = "FORGE_API=http://127.0.0.1:8470"
open(dst, "w").write("\n".join(keep.values()) + "\n")
PY
install -m 600 $F/var/run/ops_token $OH/forge/ops_token
chown -R forge-ops:forge-ops $O

# Telegram adapter dependency (pinned to Hermes v0.21.5's own extra); shared read-only app venv
if ! $H/app/venv/bin/python -c "import telegram" 2>/dev/null; then
  sudo -u forge-hermes env UV_NO_CONFIG=1 UV_CACHE_DIR=$H/app/uvcache HOME=$H/home bash -c \
    "cd $H/work && $F/.tools/uv pip install --python $H/app/venv/bin/python --quiet 'python-telegram-bot[webhooks]==22.8'"
fi

# polkit: forge-ops may ONLY restart/start the three FORGE units (no stop, no other unit, no other verb)
install -d -m 755 /etc/polkit-1/rules.d
cat > /etc/polkit-1/rules.d/60-forge-ops.rules <<'X'
polkit.addRule(function(action, subject) {
  if (action.id == "org.freedesktop.systemd1.manage-units" && subject.user == "forge-ops") {
    var unit = action.lookup("unit"), verb = action.lookup("verb");
    var units = ["forge.service", "forge-hermes.service", "forge-tunnel.service"];
    if (units.indexOf(unit) >= 0 && (verb == "restart" || verb == "start")) { return polkit.Result.YES; }
    return polkit.Result.NO;
  }
});
X
systemctl try-reload-or-restart polkit 2>/dev/null || true

cat > /etc/systemd/system/forge-ops.service <<'X'
[Unit]
Description=FORGE OPS COMMANDER (Hermes v0.21.5, owner-only remote operations; FORGE scope only)
After=network-online.target forge.service
Wants=network-online.target

[Service]
Type=simple
User=forge-ops
Group=forge-ops
SupplementaryGroups=systemd-journal
Slice=forge.slice
Environment=HOME=/srv/forge/runtime/ops/home
Environment=HERMES_HOME=/srv/forge/runtime/ops/home
WorkingDirectory=/srv/forge/runtime/ops/work
ExecStart=/srv/forge/runtime/hermes/app/venv/bin/hermes gateway
Restart=always
RestartSec=15
Nice=5
CPUQuota=50%
MemoryMax=700M
TasksMax=128
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictSUIDSGID=true
LockPersonality=true
ReadWritePaths=/srv/forge/runtime/ops/home /srv/forge/runtime/ops/work
ReadOnlyPaths=/srv/forge/runtime/hermes/app
InaccessiblePaths=/etc/forge /srv/forge/var /srv/forge/runtime/hermes/home -/srv/forge/.devvar -/srv/northstar -/opt/northstar

[Install]
WantedBy=multi-user.target
X

cat > /usr/local/sbin/forge-ops-telegram <<'X'
#!/usr/bin/env bash
# Activate Telegram for the FORGE OPS COMMANDER. Run as root (Linode LISH console or SSH). Inputs are never echoed.
set -euo pipefail
E=/srv/forge/runtime/ops/home/.env
read -rsp "Telegram bot token from @BotFather (hidden): " TOK; echo
read -rp  "Your numeric Telegram user ID (from @userinfobot): " UID_
[[ "$UID_" =~ ^[0-9]{5,15}$ ]] || { echo "user ID must be numeric"; exit 1; }
ME=$(curl -s -4 -m 15 "https://api.telegram.org/bot${TOK}/getMe")
echo "$ME" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('ok'), d; print('bot OK: @'+d['result']['username'])" \
  || { echo "token rejected by Telegram"; exit 1; }
python3 - "$E" "$TOK" "$UID_" <<'PY'
import os, sys
p, tok, uid = sys.argv[1:4]
kv = {l.split("=", 1)[0]: l for l in open(p).read().splitlines() if "=" in l}
for k in ("GATEWAY_ALLOW_ALL_USERS", "TELEGRAM_WEBHOOK_URL"):
    kv.pop(k, None)
kv["TELEGRAM_BOT_TOKEN"] = f"TELEGRAM_BOT_TOKEN={tok}"
kv["TELEGRAM_ALLOWED_USERS"] = f"TELEGRAM_ALLOWED_USERS={uid}"
kv["TELEGRAM_HOME_CHANNEL"] = f"TELEGRAM_HOME_CHANNEL={uid}"
open(p, "w").write("\n".join(kv.values()) + "\n"); os.chmod(p, 0o600)
PY
chown forge-ops:forge-ops "$E"
systemctl restart forge-ops
sleep 8; systemctl is-active forge-ops && echo "FORGE OPS online — open your bot in Telegram and say: Hey FORGE, what's happening?"
X
chmod 700 /usr/local/sbin/forge-ops-telegram

systemctl daemon-reload
systemctl enable forge-ops >/dev/null 2>&1
systemctl restart forge-ops
sleep 6; echo "forge-ops: $(systemctl is-active forge-ops)"
