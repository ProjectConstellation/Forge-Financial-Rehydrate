# CURRENT REQUIREMENT MATRIX — Institutional Workforce Overhaul
**Date:** 2026-10-08T21:10Z · Host: `/srv/forge` · Blueprint: Workforce Realtime Overhaul

| Requirement | Existing component | State | Evidence | Gap | Action | Test | Proof |
|---|---|---|---|---|---|---|---|
| No fake DONE | `officer_dispatch.py` | BROKEN | high→`acked_cooldown` DONE still | Critical OK; high still faked | Never DONE except role_report | T2 critical+high | Zero acked_cooldown DONE after deploy |
| 30m RED SLA | heartbeat 12h STALE | WEAK | ages ~20h STALE | SLA too long | EmploymentAccountability 30m RED | T1/T4 | age_h≤0.5 or valid IDLE_BY_DESIGN |
| Wake gate | forge_gate meaningful∨quiet | WEAK | cron ok + skip STALE | No directive/SLA/event | New predicate in forge_gate + digest | T2 | OPEN critical wakes despite quiet |
| Workflow engine | ops_directives only | MISSING | no stage/handoff tables | No Quinn→Ada chain | agent_workflows + handoffs | T3 | handoff persists restart |
| Results contract | role_reports freeform | PARTIAL | reports exist | No ACTION/DECISION/NO_ACTION | Schema + genome enforce | prompt eval | report has result_type |
| Nolan/Reid/Ellis/Mira | briefs only | WEAK | brief_*.md | No process/heartbeat | First-class cron+gates+boots | roster | heartbeat includes 4 roles |
| Tess economic | forge_scout URL hash | BROKEN | prompt≠inputs | Doc scout only | forge_scout_econ + edge_decay KV | T edge | wake on decay WEAKENING |
| Employment supervisor | stale_nudge 6h | PARTIAL | normal nudge | No force-wake/Casey | employment_accountability.py | T4 | force wake + Casey page |
| Capital realloc | reallocator KV | PARTIAL | directives only | Weak actuation | Bridge stables + measure Δ$/h | capital cycle | stables capital-hours ↑ |
| Edge decay actuated | edge_decay.py | PARTIAL | KV+actions | Not always cutting | Vigil+realloc integration | decay replay | REDUCE→release |
| Modal research | econ_orchestrator | PARTIAL | request YELLOW | Often not launched | Force RED ZONE burst | modal jobs | job completed + attribution |
| Luke SOUL | SOUL.md + ops_* | WORKING | Telegram ops | Missing workforce SLA tools | ops_workforce + charter | NL Q | Luke answers who is stale |
| PWA workforce | f_agents chips | PARTIAL | STALE chips | No state/SLA/handoff | Workforce panel + API | UI | shows WORKING/STALE/IDLE |
| PreLIVE proof | prelive_proof.py | PARTIAL | NO_GO | Officers stale blocks | Clear STALE + stables PAPER | prelive | gates flip when ready |
| 8h trial | paper_trial | PARTIAL | running under target | Workforce not participating | Restart after overhaul | scorecard | workforce metrics in trial |

## Root cause of ~20h STALE
1. Gate skip when digest not “meaningful” and quiet_h not elapsed  
2. Sparse cron (Ada daily, Quinn 3h, Vale 6h)  
3. high-priority fake DONE hid silence  
4. Specialists never wake (briefs only)  
5. Tess not wired to economic telemetry  

## Preserve
PAPER-before-LIVE, $1/h target, Treasury Truth, Position Vigil, Escalator, deterministic risk, ops_* Luke tools, Evidence Board, Modal client.
