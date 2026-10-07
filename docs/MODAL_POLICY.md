# Modal policy
App `forge-research` in environment `forge`; Volume `forge-market`. `search` (2 CPU, 3 GiB, 900s timeout, ≤16 containers,
scale-to-zero after 60s), `ping`. No permanent warm worker (not yet measured worth it). Budget $30/month: GREEN <60% → bursts
every cycle while FORGE has no validated edge (SURVIVAL escalation), YELLOW every 4th, ORANGE every 8th, RED none (local only).
Cost per job = container-seconds × (2 × $0.0000131 + 3 × $0.00000222) → compute_jobs + ledger OPEX:COMPUTE (true net P&L).
Measured: 2 workers × ~65s ≈ 6,740 genomes ≈ $0.004.
