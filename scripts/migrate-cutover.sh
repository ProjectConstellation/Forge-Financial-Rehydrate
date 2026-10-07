#!/usr/bin/env bash
# FORGE cutover: old command server → dedicated Linode. Run on the OLD server:  sudo scripts/migrate-cutover.sh
# Guarantees a single running FORGE: old units are stopped AND disabled before the final sync; files stay intact
# (rollback: sudo scripts/migrate-cutover.sh rollback).
set -euo pipefail
NEW=${FORGE_NEW_HOST:-forgeadmin@104.237.131.109}
KEY=/home/NorthStarImagine/.ssh/forge_migrate_ed25519
SSH="ssh -i $KEY -o UserKnownHostsFile=/home/NorthStarImagine/.ssh/known_hosts -o BatchMode=yes $NEW"
UNITS="forge-tunnel forge-hermes forge"
cd "$(dirname "$0")/.."

if [ "${1:-}" = "rollback" ]; then
  $SSH "sudo systemctl disable --now $UNITS" || true
  systemctl enable --now forge forge-hermes forge-tunnel
  echo "rolled back: FORGE running on the old server"; exit 0
fi

echo "== preflight on new host (read-only)"
$SSH "sudo -u forge bash -c 'set -a; . /etc/forge/forge.env; set +a; export HOME=/srv/forge/var/modal-home MODAL_ENVIRONMENT=forge; cd /srv/forge; timeout 150 .venv/bin/python scripts/preflight.py'" \
  || { echo "preflight failed on new host — aborting before any downtime"; exit 1; }

echo "== stop + disable old FORGE ($(date -u +%T))"
systemctl disable --now $UNITS
echo "== final sync"
scripts/migrate-sync.sh final
echo "== new host: ownership/ACL refresh + start"
$SSH "sudo bash /srv/forge/scripts/migrate-setup.sh >/dev/null && sudo systemctl enable --now forge && sleep 20 && sudo systemctl enable --now forge-hermes forge-tunnel"

echo "== verify"
for i in $(seq 1 30); do
  if $SSH "curl -fsS -m 5 http://127.0.0.1:8470/health >/dev/null"; then echo "new API healthy"; break; fi; sleep 10
done
$SSH "systemctl is-active $UNITS; free -h | sed -n 2p"
curl -s -o /dev/null -m 15 -w "portal https://forge.northstarimagine.com → HTTP %{http_code}\n" https://forge.northstarimagine.com/
echo "cutover complete ($(date -u +%T)). Rollback: sudo scripts/migrate-cutover.sh rollback"
