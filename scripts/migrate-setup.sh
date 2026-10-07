#!/usr/bin/env bash
# FORGE new-host setup (dedicated Linode, x86_64, 4 vCPU / 8 GB). Run on the NEW server as root after migrate-sync.sh.
# Idempotent. Rebuilds every architecture-specific artefact from lockfiles / pinned sources; never prints secrets.
# Does NOT start or enable FORGE (two FORGE instances must never run at once) — cutover does that.
set -euo pipefail
UV_VERSION=0.12.23
CLOUDFLARED_VERSION=2026.9.3
HERMES_PY=3.13.16
F=/srv/forge; H=$F/runtime/hermes
ADMIN=${FORGE_ADMIN:-forgeadmin}

echo "== ownership + ACLs"
find $F -maxdepth 1 -mindepth 1 ! -name var ! -name runtime -exec chown -R "$ADMIN:$ADMIN" {} +
chown "$ADMIN:forge" $F; chmod 750 $F
chown forge:forge $F/var/.gitkeep 2>/dev/null || true
chown -R forge:forge $F/var
chown root:root $F/runtime $H; chmod 755 $F/runtime $H
chown -R forge-hermes:forge-hermes $H/app $H/home $H/work
setfacl -m u:forge-hermes:--x $F; setfacl -m u:forge-hermes:--x $F/runtime
mkdir -p $F/.devvar
chmod -R g+rX $F/src $F/hermes $F/scripts $F/config $F/modal_apps $F/pyproject.toml $F/uv.lock 2>/dev/null || true

echo "== uv $UV_VERSION (official astral release)"
mkdir -p $F/.tools
if ! $F/.tools/uv --version 2>/dev/null | grep -q "$UV_VERSION"; then
  T=$(mktemp -d)
  curl -fsSL -o $T/uv.tgz "https://github.com/astral-sh/uv/releases/download/$UV_VERSION/uv-x86_64-unknown-linux-gnu.tar.gz"
  curl -fsSL -o $T/uv.sha "https://github.com/astral-sh/uv/releases/download/$UV_VERSION/uv-x86_64-unknown-linux-gnu.tar.gz.sha256"
  (cd $T && echo "$(cut -d' ' -f1 uv.sha)  uv.tgz" | sha256sum -c -)
  tar -xzf $T/uv.tgz -C $T; install -m 755 $T/uv-x86_64-unknown-linux-gnu/uv $T/uv-x86_64-unknown-linux-gnu/uvx $F/.tools/
  rm -rf $T
fi
chown -R "$ADMIN:$ADMIN" $F/.tools

echo "== FORGE venv (Python 3.14, uv.lock --frozen)"
sudo -u "$ADMIN" env UV_CACHE_DIR=$F/.cache/uv UV_PYTHON=/usr/bin/python3.14 UV_PYTHON_DOWNLOADS=never \
  bash -c "cd $F && .tools/uv sync --frozen --quiet"
$F/.venv/bin/python -c "import forge, numpy, pyarrow, duckdb, fastapi, httpx, cryptography, modal; print('forge venv ok', numpy.__version__, modal.__version__)"

echo "== Hermes v0.21.5 venv (uv-managed Python $HERMES_PY, editable pinned source, frozen package set)"
cd $H/work
HU="env UV_NO_CONFIG=1 UV_CACHE_DIR=$H/app/uvcache UV_PYTHON_INSTALL_DIR=$H/app/python HOME=$H/home"
if [ ! -x $H/app/venv/bin/hermes ]; then
  sudo -u forge-hermes $HU $F/.tools/uv python install "$HERMES_PY" --quiet
  sudo -u forge-hermes $HU $F/.tools/uv venv $H/app/venv --python "$HERMES_PY" --prompt hermes-agent --quiet
  sudo -u forge-hermes $HU $F/.tools/uv pip install --python $H/app/venv/bin/python --quiet -r $F/scripts/hermes-freeze.txt
fi
PYBIN=$(ls -d $H/app/python/cpython-3.13*-linux-x86_64-gnu/bin | head -1)
sudo -u forge-hermes mkdir -p $H/home/.local/bin
ln -sfn "$PYBIN/python3.13" $H/home/.local/bin/python3.13; chown -h forge-hermes:forge-hermes $H/home/.local/bin/python3.13
sudo -u forge-hermes $H/app/venv/bin/hermes --version | head -1

echo "== cloudflared $CLOUDFLARED_VERSION (official .deb)"
if ! cloudflared --version 2>/dev/null | grep -q "$CLOUDFLARED_VERSION"; then
  T=$(mktemp -d)
  curl -fsSL -o $T/cf.deb "https://github.com/cloudflare/cloudflared/releases/download/$CLOUDFLARED_VERSION/cloudflared-linux-amd64.deb"
  dpkg -i $T/cf.deb >/dev/null; rm -rf $T
fi
ln -sfn /usr/bin/cloudflared /usr/local/bin/cloudflared
ln -sfn $F/scripts/hermes-mode.sh /usr/local/bin/forge-hermes-mode

echo "== resource envelope for the dedicated 4 vCPU / 8 GB host (D-028)"
cat > /etc/systemd/system/forge.slice <<'X'
[Unit]
Description=FORGE resource envelope (FORGE + Hermes): dedicated host 4 vCPU / 8 GB, ~1 GB reserved for the OS (D-028)

[Slice]
CPUQuota=400%
MemoryMax=7G
MemoryHigh=6600M
X
cat > /etc/systemd/system/forge.service.d/memory.conf <<'X'
[Service]
MemoryMax=5600M
MemoryHigh=5200M
X
mkdir -p /etc/systemd/system/forge-hermes.service.d
cat > /etc/systemd/system/forge-hermes.service.d/memory.conf <<'X'
[Service]
MemoryMax=1200M
X
# Hermes sandbox: other-project paths only exist on the old host → optional (-); FORGE secrets/DB stay hidden
cat > /etc/systemd/system/forge-hermes.service.d/paths.conf <<'X'
[Service]
InaccessiblePaths=
InaccessiblePaths=/etc/forge /srv/forge/var -/srv/forge/.devvar -/srv/northstar -/opt/northstar
X
# IPv4-only egress: the Coinbase CDP key allows exactly one IPv4 address (104.237.131.109); IPv6 egress → HTTP 401
printf "net.ipv6.conf.all.disable_ipv6=1\nnet.ipv6.conf.default.disable_ipv6=1\nnet.ipv6.conf.lo.disable_ipv6=0\n" \
  > /etc/sysctl.d/91-forge-ipv4.conf
sysctl -q -p /etc/sysctl.d/91-forge-ipv4.conf
systemctl daemon-reload
echo "setup complete (units installed, NOT enabled/started)"
