#!/usr/bin/env bash
# FORGE migration sync: old (command server, aarch64) → new dedicated Linode (x86_64). Run on the OLD server as root.
# Secrets travel only inside this SSH stream (never printed). Architecture-specific trees (venvs, uv pythons, binaries)
# are excluded and rebuilt on the new host. Usage:  sudo scripts/migrate-sync.sh [final]
set -euo pipefail
NEW=${FORGE_NEW_HOST:-forgeadmin@104.237.131.109}
KEY=/home/NorthStarImagine/.ssh/forge_migrate_ed25519
SSH="ssh -i $KEY -o UserKnownHostsFile=/home/NorthStarImagine/.ssh/known_hosts -o BatchMode=yes"
R=(rsync -aHAX --delete --info=stats1 -e "$SSH" --rsync-path="sudo rsync")

if [ "${1:-}" = "final" ] && systemctl is-active -q forge.service; then
  echo "refusing final sync while forge.service is running here (stop it first)"; exit 1
fi

$SSH "${NEW}" "sudo mkdir -p /srv/forge/runtime/hermes/app /srv/forge/runtime/hermes/home /srv/forge/runtime/hermes/work /etc/forge"
# 1. repository (code, docs, migrations, Hermes plugin/prompts, lockfile, .git)
"${R[@]}" --exclude=/.venv --exclude=/.cache --exclude=/.tools --exclude=/.hypothesis --exclude=/.pytest_cache \
  --exclude=/.ruff_cache --exclude=/.devvar --exclude=/var --exclude=/runtime /srv/forge/ "$NEW:/srv/forge/"
# 2. state: DB, market data, audit journal, run tokens, modal home
"${R[@]}" /srv/forge/var/ "$NEW:/srv/forge/var/"
# 3. Hermes: pinned source + home (config, .env, cron, skills, memory, plugin) + work; arch-specific bits excluded
"${R[@]}" --exclude=/venv --exclude=/python --exclude=/uvcache --exclude=/uvenv /srv/forge/runtime/hermes/app/ "$NEW:/srv/forge/runtime/hermes/app/"
"${R[@]}" --exclude=/bin/tirith --exclude=/.local/bin --exclude=/.cache --exclude=/gateway.sock --exclude=/gateway.pid \
  --exclude=/gateway.lock /srv/forge/runtime/hermes/home/ "$NEW:/srv/forge/runtime/hermes/home/"
"${R[@]}" /srv/forge/runtime/hermes/work/ "$NEW:/srv/forge/runtime/hermes/work/"
# 4. secrets + tunnel credentials
"${R[@]}" /etc/forge/ "$NEW:/etc/forge/"
# 5. systemd units (resource envelope re-tuned on the new host by migrate-setup)
for u in forge.service forge.slice forge-hermes.service forge-tunnel.service; do
  "${R[@]}" "/etc/systemd/system/$u" "$NEW:/etc/systemd/system/$u"; done
"${R[@]}" /etc/systemd/system/forge.service.d/ "$NEW:/etc/systemd/system/forge.service.d/"
echo "sync complete ($(date -u +%FT%TZ))"
