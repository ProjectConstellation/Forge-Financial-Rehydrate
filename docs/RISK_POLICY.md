# Risk policy (deterministic; enforced in `forge.risk.governor` — protected core)
Entry orders require ALL: trading state RUNNING · no blocking breakers · fresh treasury snapshot (≤120s) · reconciliation OK ·
fresh market data · valid book · spread ≤ strategy limit · fee/slippage estimate present · positive expected net edge after
costs and opportunity cost · daily loss > −15% · venue rules known/tradable · concurrency < regime cap · size ≤ deployable
cash − reserve − exit buffer, ≤ regime max position fraction, ≤ family concentration cap · ≥ venue minimum · order-rate limit.
Exits: may only sell held quantity (no shorting). No leverage. No transfers.
Reserve: SURVIVAL (<$100) 5–20% (default 10%); ≥$100 sticky $25 floor + growing fraction (OP-008 surface).
Strategy thresholds (OP-004): promotion needs P(net edge>0) ≥ 0.90 + alpha-vs-drift P ≥ 0.60 + robustness + DSR; incumbents
demoted on posterior collapse (P<0.35 with n≥10), 5-loss streak, or −20% strategy drawdown → shadow + postmortem.
Circuit breakers: exchange rejects, WS integrity, balance mismatch, slippage anomaly, auth errors, duplicate orders, order
frequency, P&L recon mismatch, inference/modal spend anomalies, rapid drawdown, clock drift.
