# Forge Financial - Restore Instructions

## Prerequisites
- A Linux server (Ubuntu 24.04 LTS recommended)
- Python 3.14
- Git
- At least 20GB free disk space (for full restore with runtime)

## Step 1: Clone the Repository
```bash
git clone https://github.com/ProjectConstellation/Forge-Financial-Rehydrate.git /srv/forge
cd /srv/forge
```

## Step 2: Restore Git History (if needed)
The git bundle is available as a release asset:
```bash
# Download from: https://github.com/ProjectConstellation/Forge-Financial-Rehydrate/releases/tag/full-git-history
git clone forge-git-history.bundle forge-git-full
cd forge-git-full
git branch -a
git checkout main
```

## Step 3: Set Up Python Environment
```bash
python3.14 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r uv.lock  # or: uv sync
```

## Step 4: Restore Database
The database files were on the original Linode server (`/srv/forge/var/state/forge.sqlite`).
If a database backup is available, restore it:
```bash
cp forge.sqlite var/state/forge.sqlite
```

## Step 5: Restore Configuration
```bash
# Environment variables (from .engineering backup .env files)
cp .engineering/20261009T213224Z-qwen-migration/eng.env.bak .env
# etc.
```

## Step 6: Start Services
```bash
# Forge services
sudo cp systemd/forge.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now forge forge-hermes forge-ops forge-eng
```

## Runtime Architecture
- **forge** (main daemon)
- **forge-hermes** (agent orchestrator)
- **forge-ops** (operations)
- **forge-eng** (engineering)
- **forge-overnight.timer** (nightly maintenance)
