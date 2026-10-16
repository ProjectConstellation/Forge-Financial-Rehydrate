#!/usr/bin/env bash
# Install Alpaca PAPER API credentials into /etc/forge. Never commit keys.
# Usage: sudo bash /srv/forge/scripts/install_alpaca_paper_creds.sh <KEY_ID> <SECRET>
set -euo pipefail
KEY_ID="${1:-}"; SECRET="${2:-}"
[[ -n "$KEY_ID" && -n "$SECRET" ]] || { echo "usage: $0 <APCA_API_KEY_ID> <APCA_API_SECRET_KEY>"; exit 1; }
ENV=/etc/forge/forge.env
install -d -m 0750 -o root -g forge /etc/forge
cp -a "$ENV" "/etc/forge/backup/forge.env.$(date -u +%Y%m%dT%H%M%SZ)"
upsert(){ local k="$1" v="$2"; grep -q "^${k}=" "$ENV" 2>/dev/null && sed -i "s|^${k}=.*|${k}=${v}|" "$ENV" || echo "${k}=${v}" >>"$ENV"; }
upsert APCA_API_KEY_ID "$KEY_ID"
upsert APCA_API_SECRET_KEY "$SECRET"
upsert APCA_API_BASE_URL "https://paper-api.alpaca.markets"
upsert ALPACA_PAPER "true"
upsert ALPACA_LIVE "off"
systemctl restart forge.service
sleep 2
systemctl is-active forge.service
echo "Alpaca PAPER creds installed. ALPACA_LIVE=off."
