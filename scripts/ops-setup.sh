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
install -m 600 $F/hermes/ops/config.yaml $OH/config.yaml      # managed file: the repo is the source of truth
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

# voice notes: local speech-to-text (faster-whisper, CPU int8; no API key, audio never leaves the server)
if ! $H/app/venv/bin/python -c "import faster_whisper" 2>/dev/null; then
  sudo -u forge-hermes env UV_NO_CONFIG=1 UV_CACHE_DIR=$H/app/uvcache HOME=$H/home bash -c \
    "cd $H/work && $F/.tools/uv pip install --python $H/app/venv/bin/python --quiet faster-whisper" || echo "faster-whisper install failed (voice notes disabled)"
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
Description=FORGE EXECUTIVE OPS (Hermes v0.21.5, owner-only private control plane; FORGE scope only)
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
InaccessiblePaths=/etc/forge /srv/forge/var /srv/forge/runtime/hermes/home -/srv/forge/runtime/signal -/srv/forge/.devvar -/srv/northstar -/opt/northstar

[Install]
WantedBy=multi-user.target
X

apt-get -y -qq install qrencode openjdk-21-jre-headless >/dev/null 2>&1 || apt-get -y -qq install qrencode >/dev/null
rm -f /usr/local/sbin/forge-ops-telegram
install -d -m 750 -o root -g root /usr/local/sbin
OPS_ENV=/srv/forge/runtime/ops/home/.env

# ---------------------------------------------------------------- shared helper: set KEY=VALUE in the ops .env
cat > /usr/local/sbin/forge-exec-env-set <<'X'
#!/usr/bin/env python3
import os, sys
p = "/srv/forge/runtime/ops/home/.env"
kv = {l.split("=", 1)[0]: l for l in open(p).read().splitlines() if "=" in l}
for arg in sys.argv[1:]:
    k, _, v = arg.partition("=")
    if v == "__DELETE__":
        kv.pop(k, None)
    else:
        kv[k] = f"{k}={v}"
open(p, "w").write("\n".join(kv.values()) + "\n"); os.chmod(p, 0o600)
X
chmod 700 /usr/local/sbin/forge-exec-env-set

# ---------------------------------------------------------------- 2FA (authenticator) enrolment
cat > /usr/local/sbin/forge-exec-2fa <<'X'
#!/usr/bin/env bash
# Enrol the FORGE EXECUTIVE OPS authenticator (TOTP). Shows a QR once; the secret never leaves the server otherwise.
set -euo pipefail
P=/srv/forge/var/run/ops_totp
if [ -f "$P" ] && [ "${1:-}" != "--rotate" ]; then echo "2FA already enrolled (use --rotate to replace)"; exit 1; fi
S=$(python3 -c "import base64,os; print(base64.b32encode(os.urandom(20)).decode().rstrip('='))")
umask 077; printf "%s" "$S" > "$P"; chown forge:forge "$P"; chmod 600 "$P"
URI="otpauth://totp/FORGE:EXECUTIVE-OPS?secret=${S}&issuer=FORGE&digits=6&period=30"
echo "Scan with Google Authenticator / 1Password / Authy (entry: FORGE EXECUTIVE-OPS):"
qrencode -t ANSIUTF8 "$URI"
echo "Can't scan? Enter this setup key manually: $S"
read -rp "Type the 6-digit code now shown in your app to verify: " C
sudo -u forge env PYTHONPATH=/srv/forge/src /srv/forge/.venv/bin/python - "$C" <<'PY' && clear && echo "2FA enrolled and verified. (Screen cleared.)"
import sys, time
from pathlib import Path
from forge.ops import totp
s = Path("/srv/forge/var/run/ops_totp").read_text().strip(); c = sys.argv[1]
t = int(time.time() // 30)
assert any(totp._code(s, x) == c for x in (t - 1, t, t + 1)), "code mismatch — re-run with --rotate"
PY
X
chmod 700 /usr/local/sbin/forge-exec-2fa

# ---------------------------------------------------------------- Telegram (fallback channel)
cat > /usr/local/sbin/forge-exec-telegram <<'X'
#!/usr/bin/env bash
# Activate Telegram for FORGE EXECUTIVE OPS: private 1:1 chat with the owner's numeric user ID only.
set -euo pipefail
read -rsp "Telegram bot token from @BotFather (hidden): " TOK; echo
read -rp  "Your numeric Telegram user ID (from @userinfobot): " UID_
[[ "$UID_" =~ ^[0-9]{5,15}$ ]] || { echo "user ID must be numeric"; exit 1; }
curl -s -4 -m 15 "https://api.telegram.org/bot${TOK}/getMe" | python3 -c "import sys,json; d=json.load(sys.stdin); assert d.get('ok'), 'token rejected'; print('bot OK: @'+d['result']['username'])"
/usr/local/sbin/forge-exec-env-set "TELEGRAM_BOT_TOKEN=$TOK" "TELEGRAM_ALLOWED_USERS=$UID_" "TELEGRAM_ALLOWED_CHATS=$UID_" \
  "TELEGRAM_HOME_CHANNEL=$UID_" "GATEWAY_ALLOW_ALL_USERS=__DELETE__" "TELEGRAM_WEBHOOK_URL=__DELETE__" \
  "TELEGRAM_GROUP_ALLOWED_CHATS=__DELETE__" "TELEGRAM_GROUP_ALLOWED_USERS=__DELETE__"
chown forge-ops:forge-ops /srv/forge/runtime/ops/home/.env
systemctl restart forge-ops; sleep 8; systemctl is-active forge-ops
echo "In @BotFather also run: /setjoingroups → Disable (the bot can never be added to groups)."
echo "Now message your bot from your phone: 'Debrief me.'"
X
chmod 700 /usr/local/sbin/forge-exec-telegram

# ---------------------------------------------------------------- Signal (recommended: end-to-end encrypted)
cat > /usr/local/sbin/forge-exec-signal <<'X'
#!/usr/bin/env bash
# Activate Signal for FORGE EXECUTIVE OPS. Needs a phone number dedicated to the bot (can receive SMS or a voice call).
# Binds access to the owner's Signal account UUID (ACI) — not a phone number or username.
set -euo pipefail
V=0.14.9; D=/srv/forge/runtime/signal; OPS=/srv/forge/runtime/ops/home/.env
if [ ! -x /opt/signal-cli/bin/signal-cli ] && [ ! -x /opt/signal-cli/signal-cli ]; then
  T=$(mktemp -d); curl -fsSL -4 -o $T/sc.tgz "https://github.com/AsamK/signal-cli/releases/download/v$V/signal-cli-$V-Linux-native.tar.gz"
  mkdir -p /opt/signal-cli && tar -xzf $T/sc.tgz -C /opt/signal-cli && rm -rf $T
fi
SC=$(ls /opt/signal-cli/signal-cli /opt/signal-cli/bin/signal-cli 2>/dev/null | head -1)
install -d -m 700 -o forge-ops -g forge-ops $D
run() { sudo -u forge-ops "$SC" --config "$D" "$@"; }
read -rp "Bot phone number in E.164 (e.g. +15551234567): " NUM
echo "Open https://signalcaptchas.org/registration/generate.html on any browser, solve it, right-click 'Open Signal' → copy link."
read -rp "Paste the signalcaptcha:// link: " CAP
read -rp "Verify by (s)ms or (v)oice call? [s]: " MODE
if [ "${MODE:-s}" = "v" ]; then run -a "$NUM" register --voice --captcha "$CAP"; else run -a "$NUM" register --captcha "$CAP"; fi
read -rp "Verification code received: " CODE
run -a "$NUM" verify "$CODE"
run -a "$NUM" updateProfile --given-name "FORGE" --family-name "EXECUTIVE OPS"
echo "From YOUR phone, send any Signal message to $NUM now (waiting 120 s)…"
OWNER=$(run -a "$NUM" -o json receive -t 120 | python3 -c "
import sys, json
for l in sys.stdin:
    try: e = json.loads(l)['envelope']
    except Exception: continue
    if e.get('dataMessage') and e.get('sourceUuid'):
        print(e['sourceUuid']); break")
[ -n "$OWNER" ] || { echo "no message received — re-run"; exit 1; }
echo "Owner Signal account UUID: $OWNER"
cat > /etc/systemd/system/forge-signal.service <<U
[Unit]
Description=FORGE EXECUTIVE OPS Signal transport (signal-cli daemon, loopback only)
After=network-online.target
[Service]
User=forge-ops
Group=forge-ops
Slice=forge.slice
ExecStart=$SC --config $D -a $NUM daemon --http 127.0.0.1:8080 --receive-mode on-connection
Restart=always
RestartSec=10
MemoryMax=400M
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ReadWritePaths=$D
[Install]
WantedBy=multi-user.target
U
systemctl daemon-reload; systemctl enable --now forge-signal; sleep 6
/usr/local/sbin/forge-exec-env-set "SIGNAL_HTTP_URL=http://127.0.0.1:8080" "SIGNAL_ACCOUNT=$NUM" "SIGNAL_ALLOWED_USERS=$OWNER" \
  "SIGNAL_HOME_CHANNEL=$OWNER" "SIGNAL_GROUP_ALLOWED_USERS=__DELETE__" "GATEWAY_ALLOW_ALL_USERS=__DELETE__"
chown forge-ops:forge-ops "$OPS"
systemctl restart forge-ops; sleep 8; systemctl is-active forge-ops forge-signal
echo "Done. In Signal on your phone, message the bot: 'Debrief me.'  (Groups are ignored; only your UUID is accepted.)"
X
chmod 700 /usr/local/sbin/forge-exec-signal

# ---------------------------------------------------------------- credential intake for rails (never via chat)
cat > /usr/local/sbin/forge-exec-secret <<'X'
#!/usr/bin/env bash
# Install a FORGE credential:  forge-exec-secret NAME         (single-line value, hidden)
#                              forge-exec-secret --pem NAME   (multi-line PEM → /etc/forge/NAME.pem)
set -euo pipefail
E=/etc/forge/forge.env
if [ "${1:-}" = "--pem" ]; then
  N=${2:?name}; [[ "$N" =~ ^[a-z][a-z0-9_]{2,40}$ ]] || { echo "pem name: lowercase letters/digits/_"; exit 1; }
  echo "Paste the PEM (including BEGIN/END lines), then press Ctrl-D:"; umask 027
  cat > /etc/forge/$N.pem; chown root:forge /etc/forge/$N.pem; chmod 640 /etc/forge/$N.pem
  grep -q "BEGIN" /etc/forge/$N.pem && echo "stored /etc/forge/$N.pem" || { rm -f /etc/forge/$N.pem; echo "not a PEM"; exit 1; }
else
  N=${1:?NAME}; [[ "$N" =~ ^[A-Z][A-Z0-9_]{2,63}$ ]] || { echo "NAME: UPPER_SNAKE_CASE"; exit 1; }
  read -rsp "Value for $N (hidden): " VAL; echo
  cp -p $E /etc/forge/backup/forge.env.$(date -u +%Y%m%dT%H%M%SZ)
  python3 - "$E" "$N" "$VAL" <<'PY'
import sys
p, k, v = sys.argv[1:4]
lines = [l for l in open(p).read().splitlines() if not l.startswith(k + "=")] + [f"{k}={v}"]
open(p, "w").write("\n".join(lines) + "\n")
PY
  echo "stored $N in $E"
fi
systemctl restart forge; echo "FORGE restarting to load it (≈ 30 s). Tell EXECUTIVE OPS: 'test the new connection'."
X
chmod 700 /usr/local/sbin/forge-exec-secret

# ---------------------------------------------------------------- owner transfer destination
cat > /usr/local/sbin/forge-exec-transfer-setup <<'X'
#!/usr/bin/env bash
# Register where "transfer $X to me" sends money: FORGE's Coinbase portfolio → the owner's own Coinbase portfolio.
set -euo pipefail
cd /srv/forge
sudo -u forge bash -c 'set -a; . /etc/forge/forge.env; set +a; PYTHONPATH=src .venv/bin/python -' <<'PY'
import asyncio, json
from forge.config import load_settings
from forge.venues.coinbase.auth import CdpSigner
from forge.venues.coinbase.rest import CoinbaseRest
from forge.persistence.db import Database
async def main():
    s = load_settings()
    r = CoinbaseRest(signer=CdpSigner(s.secrets.coinbase_key_name, s.secrets.coinbase_key_secret))
    ps = (await r._request("GET", "/api/v3/brokerage/portfolios", private=True)).get("portfolios", [])
    await r.close()
    for i, p in enumerate(ps):
        print(f"[{i}] {p.get('name')}  type={p.get('type')}  uuid={p.get('uuid')}")
    src = int(input("Number of FORGE's portfolio (source): ")); dst = int(input("Number of YOUR portfolio (destination): "))
    assert src != dst
    db = Database("/srv/forge/var/state/forge.sqlite")
    db.kv_set("ops.transfer.config", {"source_portfolio_uuid": ps[src]["uuid"], "owner_portfolio_uuid": ps[dst]["uuid"],
                                      "owner_label": f"owner's Coinbase portfolio '{ps[dst].get('name')}'"})
    print("registered:", ps[src].get("name"), "→", ps[dst].get("name"))
asyncio.run(main())
PY
X
chmod 700 /usr/local/sbin/forge-exec-transfer-setup

# ---------------------------------------------------------------- portal one-tap pairing → root installs into the sandbox
cat > /usr/local/sbin/forge-exec-provision <<'X'
#!/usr/bin/env python3
"""Consume /srv/forge/var/run/ops_provision.json (written by FORGE after a verified portal pairing), install the
credentials into the EXECUTIVE OPS profile (private-chat + user-ID bound), delete the file, restart the agent."""
import json, os, re, subprocess, sys
P = "/srv/forge/var/run/ops_provision.json"
if not os.path.exists(P):
    sys.exit(0)
try:
    d = json.load(open(P))
finally:
    os.remove(P)
tok, uid = str(d.get("token", "")), str(d.get("user_id", ""))
if d.get("platform") != "telegram" or not re.fullmatch(r"\d{6,12}:[A-Za-z0-9_-]{30,64}", tok) or not re.fullmatch(r"\d{5,15}", uid):
    sys.exit("invalid provision payload")
subprocess.run(["/usr/local/sbin/forge-exec-env-set", f"TELEGRAM_BOT_TOKEN={tok}", f"TELEGRAM_ALLOWED_USERS={uid}",
                f"TELEGRAM_ALLOWED_CHATS={uid}", f"TELEGRAM_HOME_CHANNEL={uid}", "GATEWAY_ALLOW_ALL_USERS=__DELETE__",
                "TELEGRAM_WEBHOOK_URL=__DELETE__", "TELEGRAM_GROUP_ALLOWED_CHATS=__DELETE__",
                "TELEGRAM_GROUP_ALLOWED_USERS=__DELETE__"], check=True)
subprocess.run(["chown", "forge-ops:forge-ops", "/srv/forge/runtime/ops/home/.env"], check=True)
subprocess.run(["systemctl", "restart", "forge-ops"], check=True)
print("EXECUTIVE OPS Telegram provisioned for user", uid)
X
chmod 700 /usr/local/sbin/forge-exec-provision
cat > /etc/systemd/system/forge-ops-provision.path <<'X'
[Unit]
Description=Install EXECUTIVE OPS messaging credentials after a verified portal pairing
[Path]
PathExists=/srv/forge/var/run/ops_provision.json
[Install]
WantedBy=multi-user.target
X
cat > /etc/systemd/system/forge-ops-provision.service <<'X'
[Unit]
Description=Install EXECUTIVE OPS messaging credentials (root, one-shot)
[Service]
Type=oneshot
ExecStart=/usr/local/sbin/forge-exec-provision
X
systemctl daemon-reload; systemctl enable --now forge-ops-provision.path >/dev/null 2>&1

# ---------------------------------------------------------------- portal credential intake → root installs into /etc/forge
cat > /usr/local/sbin/forge-exec-cred-provision <<'X'
#!/usr/bin/env python3
"""Consume /srv/forge/var/run/cred_provision.json (owner pasted it on the logged-in portal via a one-time link) →
/etc/forge/forge.env (UPPER_SNAKE) or /etc/forge/<name>.pem (root:forge 0640) → restart FORGE. Never echoes values."""
import json, os, re, shutil, subprocess, sys, time
P = "/srv/forge/var/run/cred_provision.json"
if not os.path.exists(P):
    sys.exit(0)
try:
    d = json.load(open(P))
finally:
    os.remove(P)
name, kind, val = str(d.get("name", "")), str(d.get("kind", "")), str(d.get("value", ""))
if kind == "pem" and re.fullmatch(r"[a-z][a-z0-9_]{2,40}", name) and "BEGIN" in val:
    path = f"/etc/forge/{name}.pem"
    with open(path + ".tmp", "w") as fh:
        fh.write(val.strip() + "\n")
    os.chmod(path + ".tmp", 0o640); shutil.chown(path + ".tmp", "root", "forge"); os.replace(path + ".tmp", path)
elif kind == "env" and re.fullmatch(r"[A-Z][A-Z0-9_]{2,63}", name) and "\n" not in val:
    env = "/etc/forge/forge.env"
    shutil.copy2(env, f"/etc/forge/backup/forge.env.{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}")
    lines = [l for l in open(env).read().splitlines() if not l.startswith(name + "=")] + [f"{name}={val}"]
    open(env, "w").write("\n".join(lines) + "\n")
else:
    sys.exit("invalid credential payload")
subprocess.run(["systemctl", "restart", "forge"], check=False)
print("installed credential", name, "(value not shown); FORGE restarted")
X
chmod 700 /usr/local/sbin/forge-exec-cred-provision
mkdir -p /etc/forge/backup
cat > /etc/systemd/system/forge-cred-provision.path <<'X'
[Unit]
Description=Install a FORGE credential submitted via a one-time portal link
[Path]
PathExists=/srv/forge/var/run/cred_provision.json
[Install]
WantedBy=multi-user.target
X
cat > /etc/systemd/system/forge-cred-provision.service <<'X'
[Unit]
Description=Install FORGE credential (root, one-shot)
[Service]
Type=oneshot
ExecStart=/usr/local/sbin/forge-exec-cred-provision
X
systemctl daemon-reload; systemctl enable --now forge-cred-provision.path >/dev/null 2>&1

# ---------------------------------------------------------------- emergency revocation
cat > /usr/local/sbin/forge-exec-revoke <<'X'
#!/usr/bin/env bash
# EMERGENCY: cut remote control now. Stops the agent + transports, wipes messaging credentials, rotates the OPS API token.
set -uo pipefail
systemctl disable --now forge-ops forge-signal 2>/dev/null
/usr/local/sbin/forge-exec-env-set TELEGRAM_BOT_TOKEN=__DELETE__ TELEGRAM_ALLOWED_USERS=__DELETE__ TELEGRAM_ALLOWED_CHATS=__DELETE__ \
  SIGNAL_ACCOUNT=__DELETE__ SIGNAL_ALLOWED_USERS=__DELETE__ SIGNAL_HTTP_URL=__DELETE__
python3 -c "import secrets; open('/srv/forge/var/run/ops_token','w').write(secrets.token_urlsafe(32))"
sudo -u forge env PYTHONPATH=/srv/forge/src /srv/forge/.venv/bin/python -c "
from forge.persistence.db import Database; Database('/srv/forge/var/state/forge.sqlite').kv_set('ops.telegram', None)"
chown forge:forge /srv/forge/var/run/ops_token; chmod 600 /srv/forge/var/run/ops_token
systemctl restart forge
echo "REVOKED: forge-ops stopped+disabled, messaging credentials removed, OPS API token rotated. Trading engine unaffected."
echo "Also revoke the bot itself: Telegram → @BotFather /revoke ; Signal → unregister/remove the bot number."
X
chmod 700 /usr/local/sbin/forge-exec-revoke

systemctl daemon-reload
systemctl enable forge-ops >/dev/null 2>&1
SIG=$(cat $OH/SOUL.md $OH/config.yaml $OH/.env /etc/systemd/system/forge-ops.service /etc/systemd/system/forge-ops.service.d/*.conf \
      $(find $OH/plugins -type f -name "*.py" -o -type f -name "*.yaml" | sort) 2>/dev/null | sha256sum | cut -c1-16)
if [ "$(cat $OH/.setup_sig 2>/dev/null)" != "$SIG" ] || ! systemctl is-active -q forge-ops; then
  systemctl restart forge-ops; echo "$SIG" > $OH/.setup_sig; chown forge-ops:forge-ops $OH/.setup_sig; sleep 6
  echo "forge-ops: restarted (changed) → $(systemctl is-active forge-ops)"
else
  echo "forge-ops: unchanged — not restarted (no Telegram interruption)"
fi
