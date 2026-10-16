# FORGE — Alpaca PAPER Rail (Staged Micro → Scale Training)

## Doctrine
Practice on the capital we actually have (or are about to deploy) — then raise the training ceiling **only as real treasury earnings grow**.

| Stage | Training NAV | When |
|-------|--------------|------|
| **SEED** | **$25** | Tiny / first-slice learning |
| **BOOTSTRAP** | **$50** | Default RED ZONE / early ops |
| **REGULAR** | **$200** | Treasury ≥ ~$50 |
| **SCALE** | **$2000** | Treasury ≥ ~$1000 (ramps from $200→$2000 between $200–$1000 treasury) |

Broker paper equity ($100k) is **ignored**. Paper PnL vanity does **not** unlock higher stages — **earned treasury** does.

## Risk fractions (auto)
- SEED: max order 40% / max open 60% / ≤3 positions  
- BOOTSTRAP: 30% / 50% / ≤4  
- REGULAR: 20% / 40% / ≤5  
- SCALE: 15% / 35% / ≤8  

## Ops
- Auto stage: `ALPACA_TRAIN_STAGE=auto`  
- Force: `seed|bootstrap|regular|scale`  
- Status: `/srv/forge/var/alpaca_paper_status.json` → `training_nav_usd`, `bankroll_policy.stage`
