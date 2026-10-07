#!/usr/bin/env bash
# Deploy CODE ONLY from the command server's working copy to the FORGE host (post-cutover).
# Never touches state (var/), Hermes home/runtime, secrets (/etc/forge) or units. Runs the full test suite on the
# FORGE host BEFORE restarting; refuses to restart on failure.  Usage:  scripts/deploy-code.sh [--restart] [--hermes]
set -euo pipefail
NEW=${FORGE_HOST:-forgeadmin@104.237.131.109}
KEY=${FORGE_KEY:-$HOME/.ssh/forge_migrate_ed25519}
SSH="ssh -i $KEY -o BatchMode=yes"
cd "$(dirname "$0")/.."
git diff --quiet HEAD -- src tests scripts hermes modal_apps config pyproject.toml uv.lock || {
  echo "uncommitted code changes — commit first (deploys are traceable to a commit)"; exit 1; }
# production may contain commits shipped by the FORGE Engineer → never overwrite them
GIT_SSH_COMMAND="$SSH" git fetch -q "$NEW:/srv/forge" HEAD
git merge-base --is-ancestor FETCH_HEAD HEAD || {
  echo "production has commits you don't have (FORGE Engineer deploys) — run:"
  echo "  GIT_SSH_COMMAND=\"$SSH\" git pull --rebase $NEW:/srv/forge HEAD"; exit 1; }
rsync -rlt --delete --no-owner --no-group -e "$SSH" --rsync-path="sudo rsync" \
  --include=/src/*** --include=/tests/*** --include=/scripts/*** --include=/hermes/*** --include=/modal_apps/*** \
  --include=/config/*** --include=/docs/*** --include=/.git/*** --include=/pyproject.toml --include=/uv.lock \
  --include=/README.md --include=/ARCHITECTURE.md --include=/AGENTS.md --include=/SECURITY.md --exclude='*' \
  ./ "$NEW:/srv/forge/"
$SSH "$NEW" 'set -e; sudo chown forgeadmin:forge /srv/forge; sudo chmod 750 /srv/forge; sudo chown -R forgeadmin:forgeadmin /srv/forge/src /srv/forge/tests /srv/forge/scripts /srv/forge/hermes \
  /srv/forge/modal_apps /srv/forge/config /srv/forge/docs /srv/forge/.git /srv/forge/pyproject.toml /srv/forge/uv.lock; sudo chmod -R g+rX /srv/forge/src /srv/forge/hermes \
  /srv/forge/scripts; cd /srv/forge && UV_PYTHON_DOWNLOADS=never .tools/uv sync --frozen --quiet; \
  timeout 1200 .venv/bin/pytest -q -p no:warnings -p no:cacheprovider > /tmp/forge-deploy-tests.log 2>&1; rc=$?; \
  tail -3 /tmp/forge-deploy-tests.log; exit $rc' || { echo "TESTS FAILED ON HOST — not restarting (old process keeps running)"; exit 1; }
echo "deployed $(git rev-parse --short HEAD) to $NEW"
if [ "${1:-}" = "--restart" ] || [ "${2:-}" = "--restart" ]; then
  $SSH "$NEW" 'sudo systemctl restart forge; for i in $(seq 1 30); do sleep 4; curl -fsS -m 3 http://127.0.0.1:8470/health >/dev/null && { echo "forge healthy"; break; }; done'
fi
if [ "${1:-}" = "--hermes" ] || [ "${2:-}" = "--hermes" ]; then $SSH "$NEW" 'sudo systemctl restart forge-hermes && echo hermes restarted'; fi
