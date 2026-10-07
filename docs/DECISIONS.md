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
