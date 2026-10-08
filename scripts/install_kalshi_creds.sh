#!/usr/bin/env bash
# Install Kalshi API credentials into /etc/forge (secure). Never commit keys.
# Usage (on forge host as forgeadmin with sudo):
#   sudo bash /srv/forge/scripts/install_kalshi_creds.sh <API_KEY_ID> /path/to/kalshi_private_key.pem
# Or pipe PEM:
#   sudo bash /srv/forge/scripts/install_kalshi_creds.sh <API_KEY_ID> -
set -euo pipefail
KEY_ID="${1:-}"
PEM_SRC="${2:-}"
if [[ -z "$KEY_ID" || -z "$PEM_SRC" ]]; then
  echo "usage: $0 <KALSHI_API_KEY_ID> <pem_file|->"; exit 1
fi
DEST=/etc/forge/kalshi_private_key.pem
ENV=/etc/forge/forge.env
install -d -m 0750 -o root -g forge /etc/forge
if [[ "$PEM_SRC" == "-" ]]; then
  sudo tee "$DEST" > /dev/null
else
  sudo cp "$PEM_SRC" "$DEST"
fi
sudo chown root:forge "$DEST"
sudo chmod 0640 "$DEST"
# Upsert env vars (do not print secrets)
sudo cp -a "$ENV" "/etc/forge/backup/forge.env.$(date -u +%Y%m%dT%H%M%SZ)"
sudo grep -q '^KALSHI_API_KEY_ID=' "$ENV" 2>/dev/null \
  && sudo sed -i "s|^KALSHI_API_KEY_ID=.*|KALSHI_API_KEY_ID=${KEY_ID}|" "$ENV" \
  || echo "KALSHI_API_KEY_ID=${KEY_ID}" | sudo tee -a "$ENV" > /dev/null
sudo grep -q '^KALSHI_PRIVATE_KEY_PATH=' "$ENV" 2>/dev/null \
  && sudo sed -i "s|^KALSHI_PRIVATE_KEY_PATH=.*|KALSHI_PRIVATE_KEY_PATH=${DEST}|" "$ENV" \
  || echo "KALSHI_PRIVATE_KEY_PATH=${DEST}" | sudo tee -a "$ENV" > /dev/null
# PAPER-first: keep LIVE off until founder authorizes
sudo grep -q '^KALSHI_LIVE=' "$ENV" 2>/dev/null \
  && sudo sed -i 's|^KALSHI_LIVE=.*|KALSHI_LIVE=off|' "$ENV" \
  || echo "KALSHI_LIVE=off" | sudo tee -a "$ENV" > /dev/null
sudo systemctl restart forge.service
sleep 3
systemctl is-active forge.service
# Prove configured without leaking key material
sudo -u forge /srv/forge/.venv/bin/python - <<'PY'
import os
from pathlib import Path
kid=os.environ.get("KALSHI_API_KEY_ID","")
path=os.environ.get("KALSHI_PRIVATE_KEY_PATH","/etc/forge/kalshi_private_key.pem")
print("key_id_set", bool(kid), "len", len(kid))
print("pem_exists", Path(path).exists(), "mode", oct(Path(path).stat().st_mode & 0o777) if Path(path).exists() else None)
# systemd may need EnvironmentFile reload - check via forge kv after restart
PY
echo "Installed. Fund Kalshi account (~\$25), keep KALSHI_LIVE=off until PAPER shadow proves, then founder sets LIVE."
