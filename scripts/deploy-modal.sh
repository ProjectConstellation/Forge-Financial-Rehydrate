#!/usr/bin/env bash
# Deploy FORGE's Modal app into the isolated `forge` environment.
# NOTE: Modal's change detection can skip deploys when only mounted local source changed
# ("Deployment skipped: no changes detected") → always stop + deploy, then verify the source hash.
set -euo pipefail
cd "$(dirname "$0")/.."
sudo -u forge bash -c 'set -a; . /etc/forge/forge.env; set +a; export HOME=/srv/forge/var/modal-home MODAL_ENVIRONMENT=forge
  mkdir -p "$HOME"; cd /srv/forge
  /srv/forge/.venv/bin/modal app stop forge-research --env forge -y >/dev/null 2>&1 || true
  PYTHONPATH=/srv/forge/src /srv/forge/.venv/bin/modal deploy modal_apps/forge_research.py --env forge
  /srv/forge/.venv/bin/python -c "import modal; print(\"remote:\", modal.Function.from_name(\"forge-research\",\"ping\",environment_name=\"forge\").remote())"'
python3 -c "import hashlib,pathlib; s=pathlib.Path('src/forge'); print('local forge_src_hash:', hashlib.sha256(b''.join(p.read_bytes() for p in sorted(s.rglob('*.py')))).hexdigest()[:12])"
