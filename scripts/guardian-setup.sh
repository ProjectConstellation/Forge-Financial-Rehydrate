#!/usr/bin/env bash
# FORGE always-on hardening + GUARDIAN watchdog. Run on the FORGE host as root (idempotent; restarts nothing that runs).
set -euo pipefail
install -m 700 /srv/forge/scripts/forge_guardian.py /usr/local/sbin/forge-guardian
install -m 755 /srv/forge/scripts/guardian-snooze.sh /usr/local/sbin/forge-guardian-snooze
mkdir -p /var/lib/forge-guardian
# never stop retrying: unlimited restarts for every FORGE service
for u in forge forge-hermes forge-tunnel forge-ops forge-eng; do
  mkdir -p /etc/systemd/system/$u.service.d
  printf "[Unit]\nStartLimitIntervalSec=0\n[Service]\nRestart=always\nRestartSec=5\n" > /etc/systemd/system/$u.service.d/10-always.conf
done
# EXECUTIVE OPS = owner's real-time interface → highest priority, more headroom
printf "[Service]\nCPUQuota=100%%\nCPUWeight=400\nNice=-2\nMemoryMax=1200M\nIOWeight=400\n" > /etc/systemd/system/forge-ops.service.d/20-priority.conf
cat > /etc/systemd/system/forge-guardian.service <<'X'
[Unit]
Description=FORGE GUARDIAN watchdog (verify every service is working; repair; alert owner once per incident)
After=network-online.target
[Service]
Type=oneshot
ExecStart=/usr/local/sbin/forge-guardian
TimeoutStartSec=300
X
cat > /etc/systemd/system/forge-guardian.timer <<'X'
[Unit]
Description=FORGE GUARDIAN every 60 s
[Timer]
OnBootSec=90s
OnUnitInactiveSec=60s
AccuracySec=5s
[Install]
WantedBy=timers.target
X
systemctl daemon-reload
for u in forge forge-hermes forge-tunnel forge-ops forge-eng forge-guardian.timer forge-deployer.timer forge-ops-provision.path; do
  systemctl enable "$u" >/dev/null 2>&1 || true
done
systemctl start forge-guardian.timer
echo "guardian: $(systemctl is-active forge-guardian.timer)"
