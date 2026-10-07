# Decisions (what · why · benefit · risk · rollback)
| ID | Decision | Why / benefit | Risk | Rollback |
|---|---|---|---|---|
| D-001 | Root `/srv/forge`, service user `forge`, secrets `/etc/forge/forge.env` | Operator-approved isolation (DIR §0) | none | n/a |
| D-002 | SQLite WAL + Parquet (no Postgres yet) | No Postgres server on host; installing one = host change (RESOLUTIONS #3) | write concurrency at scale | Postgres adapter behind `Database` |
| D-003 | `modal/` → `modal_apps/` | A top-level `modal` dir shadows the Modal SDK | none | rename |
| D-004 | Modal environment `forge` | Workspace may be shared; isolate apps/volumes | none | n/a |
| D-005 | Slippage/spread are attribution, not extra ledger debits | Already inside fill prices → avoid double counting | none | n/a |
| D-006 | Treasury = full account (OP-001) | Operator policy | larger capital at risk | `treasury.capital_mode: fixed_cap` |
| D-007 | Bars from REST at interval boundaries; WS for BBO/book/flow | Guaranteed-complete bars; WS for microstructure/execution | REST lag ~8s | n/a |
| D-008 | Market-trades `side` = maker side (flip for aggressor) | Measured live 84–90% agreement with book | Coinbase semantics change | flip mapping |
| D-009 | Alpha-vs-drift gate (P(alpha>0) ≥ 0.60) added to 90% rule | 5m "winner" was market beta (RESEARCH_LOG) | may reject pure-trend sleeves | separate labeled beta sleeve |
| D-010 | LLM never trades; it ships validated genomes/lessons/focus | Fast path deterministic; OP-009 §6 | slower LLM-to-capital path | n/a |
| D-011 | Pro deep sessions: high (scheduled) / max (critical), 32k output, finalize step | Max effort exhausted 8k budget on thinking (observed) | higher per-session cost | config |
| D-012 | Modal deploy = stop + deploy + hash verify | Modal skipped deploy on mounted-source change (observed) | brief app downtime | n/a |
| D-013 | Paper book seeded from live USD balance | Paper results comparable to live capital (OP-001) | none | n/a |
| D-014 | Capital velocity as hurdle-rate pricing, not holding caps (OP-008) | Never reject exceptional long trades by rule | hurdle mis-estimation | learned hurdle + regime multiplier |
| D-015 | TypeSafe Jev = optional SEMANTIC triage router (SHADOW→GATE by measured agreement), NOT the numeric trade reflex | Jev docs: weak at numeric precision; FORGE fast path is deterministic ms + own-data calibrated 2nd opinion; Jev ≈ $0.0001/triage vs Flash ≈ $0.0015 and sub-second vs ~3 s → frequent triage, fewer wasted escalations; Kalshi contract/news parsing later | vendor dependency (circuit + optional) | unset TYPESAFE_API_KEY |
| D-016 | Convex Trend Exit uses hour-equivalent ATR (×√(3600/interval)); stays an evolvable gene, default OFF | raw 5m ATR made the catastrophe stop < round-trip fee (−92% in Time Machine); even fixed it lost to evolved time-stop exits on both windows | may under-use convexity on 1h genomes | gene default/evolution |
| D-017 | Risk-at-stop as a CAP (5%/position, 10% aggregate), Kelly-elite remains the sizer | A/B: identical results (cap non-binding with tight 5m stops at $28) | none measurable | `risk_at_stop_cap` params |
| D-018 | ECR/haircut/drawdown gates enforced on LIVE; PAPER logs verdicts and keeps a probe size | otherwise forward evidence could never earn back the H=0.25 haircut | paper P&L includes trades live would skip (labelled `paper_exploration`) | n/a |
| D-019 | Sealed exam window 15% (selection 65 / validation 20); one exam per genome, ever; sealed metrics never reach search or the LLM | P0.4 holdout contamination | fewer promotions | `SEALED_FRAC=0` |
| D-020 | WS level2 sharded ≤25 products/session | measured: Coinbase rejects >30 L2 products per session | more connections | `L2_SHARD` |
| D-021 | Opportunity Surface Registry replaces the static rail list (writes venue_catalog) | OP-013: discovery, re-probing, product_type enum sweep, docs diff | probe rate limits (paced, 429 = unknown) | disable `surface` loop |
| D-022 | Kalshi rail = read-only public API + SHADOW evidence only; no Kalshi orders exist in code | no credentials, no authorized funding rail (Coinbase key can_transfer=false); evidence first | opportunity cost while shadowing | n/a |
| D-023 | Equities: official Advanced Trade API exposes 17.9k EQUITY products (CCM) incl. GLD/IAU/SGOV/BIL; NOT executed yet | eligibility + commission unverified; no validated equity strategy | delays T-bill idle yield | operator confirms eligibility → $1 calibration order |
| D-024 | Futures (CFM: gold, silver, oil, US500, crypto perps) = DATA rail | no CFM account; contract notional ≫ treasury; leverage forbidden by policy | none | OP to allow unlevered futures |
| D-025 | Event-contract probability = stacked (model, market) Bayesian logistic with market-centred prior; trade on the lower bound | a model without proof must not override a liquid market; weight is earned from settled outcomes | slower to act on genuine edge | prior SDs |
| D-026 | Path-dependent (MAX/MIN/one-touch) Kalshi series excluded from the terminal-price model | terminal model misprices barriers ~2× | missed barrier opportunities | add reflection-principle barrier model |
