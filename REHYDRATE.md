# Forge Financial - Rehydration Backup

## Overview
This repository contains a backup of the **Northstar Forge** autonomous financial income engine,
formerly hosted on a Linode server (`104.237.131.109`, Linode ID: `107667705`).

## What's Included
- **Full git history** (all commits up to 2026-10-16) — see `git log` for complete history
- **Source code** in `src/forge/` (178 Python modules)
- **Configuration** in `config/`, `pyproject.toml`, `uv.lock`
- **Documentation** (AGENTS.md, ARCHITECTURE.md, README.md, SECURITY.md)
- **Database migration scripts** in `src/forge/persistence/migrations/`
- **Runtime configuration** in `runtime/` (Hermes agent platform)
- **Tests** in `tests/`

## Additional Assets (uploaded separately as release attachments)
1. **Git bundle** (`forge-git-history.bundle`) — Complete git bundle with all objects, refs, packs
   - Available at: https://github.com/ProjectConstellation/Forge-Financial-Rehydrate/releases/tag/full-git-history

## Missing (requires Linode server access)
The following items exist on the original Linode server but are NOT in this git repo:
- `var/state/forge.sqlite` — Live trading database (1.3GB)
- `.engineering/` — Pre-migration backups with .bak files and DB snapshots (3.5GB)
- `runtime/eng/repo/.git` — Separate git repo for engineering tools
- `runtime/hermes/app/src/.git` — Separate git repo for Hermes platform

## Restore Instructions
See `RESTORE.md` for step-by-step restoration guide.

## Status
- Git history: RESTORED ✓
- Source code: RESTORED ✓  
- Database: PENDING (requires Linode recovery)
- Engineering backups: PENDING (requires Linode recovery)
