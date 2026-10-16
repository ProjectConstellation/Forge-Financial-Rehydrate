# Rehydrate Imagine Forge

## Outcome

A replacement agent should know where production is, what is running, what money is real, what changed, what is unfinished and exactly what to do next. Rehydration is read-only unless the founder separately authorizes implementation.

## 1. Locate and authenticate

From the command center, use the already provisioned key:

```bash
ssh -i /home/NorthStarImagine/.ssh/forge_migrate_ed25519 \
  -o BatchMode=yes -o StrictHostKeyChecking=yes \
  forgeadmin@104.237.131.109
```

Production lives at `/srv/forge`. The command-center `forge-dev` and `forge-overhaul` trees are historical working material; they are not current production. Never execute migration sync or rollback merely to establish a workspace. Do not print credentials.

## 2. Read before making assumptions

Read AGENTS.md, this directory’s README, FOUNDER_INTENT, CURRENT_STATE, WORK_QUEUE, KNOWN_ISSUES, SYSTEM_MAP, LUKE_CONTRACT, latest sessions and linked evidence. Read original CURRENT_STATE/BUILD_STATUS as historical claims, then compare against running truth. Before money/secrets/live-path changes, read the relevant governing section verbatim.

## 3. Establish the code baseline

```bash
sudo git -C /srv/forge status --short
sudo git -C /srv/forge log -10 --format='%h %ad %s' --date=iso
sudo git -C /srv/forge diff --stat
```

Read applicable nested AGENTS.md instructions in any directory you will edit. Identify existing modified and untracked files. Do not reset, clean, discard, broadly stage or overwrite them. State who owns a change as UNKNOWN if no evidence identifies the author. Use a unique session filename before implementation.

## 4. Establish host and service truth

```bash
hostname
nproc
free -h
sudo systemctl list-units 'forge*' --all --no-pager
sudo systemctl show forge.service forge-hermes.service forge-ops.service forge.slice \
  -p Id -p ActiveState -p SubState -p MemoryCurrent -p MemoryMax -p NRestarts
```

A timer-backed one-shot being inactive between runs is expected. A running process is not proof of useful economic work. Inspect Forge-only failed units and sanitized logs only when needed; never dump environment files, command environments or private runtime configuration.

## 5. Read authenticated telemetry without exposing the token

The operator token is at `/srv/forge/var/run/operator_token`. Read it inside the remote process and use it as an HTTP Authorization header; never print it or include it in a prompt or artifact. Use only audited/read-only GET paths for this stage.

| Endpoint | What to assess |
|---|---|
| /health, /ready | Process and market liveness; not permission for LIVE |
| /api/overview | Mode, trading state, account, fees, population, costs, feed, loops |
| /api/v1/treasury | Reported capital; corroborate wallet and separate paper equity |
| /api/v1/performance?window=24h | Reported LIVE/PAPER/cost partitions and coverage |
| /api/velocity | Expected frontier vs realized; independently inspect cost scope |
| /api/v1/workforce | Report age, SLA, open work, handoffs and economic claims |
| /api/v1/econ/tournament | Pre-live proof, experiments, attribution and trial |
| /api/v1/research | Actual research, compute spend/budget and rail status |
| /api/v1/systems | Loop restarts, silent intervals, guardian and model policy |
| /api/v1/risk | Known HTTP 500 at initial takeover; record response, do not mutate |

Read Alpaca’s existing `/srv/forge/var/alpaca_paper_status.json`; it is PAPER, and broker $100k is not Forge wealth. Sanitize free text and credential-link/token fields before exporting. Timestamp each observation; the engine continues running during inspection, so captures are not one atomic snapshot.

## 6. Cross-check financial claims

Separate real wallets, paper capital, shadow per-contract outcomes, hypothetical frontier estimates, verified operating spend and owner transfers. Reconcile deposits/withdrawals/internal moves. Treat inconsistent money reports as unresolved. Look for complete fee legs, currency conversion, fill probability, settlement delays and shared-capital constraints. Read Known Issues before trusting “proven” flags or EARNER grades.

Do not initialize Forge runtime objects to inspect the database: constructors run migrations and create state. If direct SQL is required, use SQLite URI `mode=ro` and `PRAGMA query_only=ON`, bounded SELECT queries and consistent read transactions. Never write into an actively running DB as part of rehydration.

## 7. Produce a takeover acknowledgment

Report host/root, Git head and pre-existing modifications, mode/live flags/trading state, verified treasury and unsettled questions, service health, spend/runway, active trial, top blockers, next owner/action and scope authorized. Mention missing evidence rather than inventing completion. Read the latest assessment but reconsider it against newer measurements.

## 8. Maintain continuity during work

Copy templates/SESSION.md to sessions/<UTC>-<agent>-<task>.md. Declare file scope, intended behavior, tests/verification planned and rollback. Add checkpoints after changes, deploys, unexpected results and before context loss. Preserve raw evidence. Fill before/after change receipts. End with an exact next action and any running process/job IDs. Refresh shared summaries without deleting others’ work.

Tests, deploys, service changes, experiments and money actions need the relevant authorized implementation scope; the read-only takeover checklist itself does not authorize them.

## Latest forensic passover — 2026-10-09

Read [the completed forensic report](reports/2026-10-09-FORGE-FORENSIC-PASSOVER.md) and [session journal](sessions/20261009T160250Z-codex-forensic-passover.md). It records the PAPER_ONLY observation `20261009T150017Z` (15:00:17–16:00:17 UTC; 13 samples), its evidence limits, current team/role findings and prioritized queue. The target final artifact is under `/srv/forge/var/research/paper_trial_1h/20261009T150017Z/`. The observation ended successfully. Refresh all runtime and financial facts before acting.
