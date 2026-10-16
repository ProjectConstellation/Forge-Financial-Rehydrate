# Imagine Forge continuity system

Start here when the founder says: **“Go rehydrate on the continuity system.”**

This is the engineering handoff and operational knowledge system for Imagine Forge on its dedicated production server. It records what agents built, exactly what they touched, progress, evidence, decisions, unresolved defects, and the next concrete work. It supplements the original governing documents and operational database; it does not replace either.

## Read order

1. `/srv/forge/AGENTS.md` and `FOUNDER_INTENT.md`.
2. `REHYDRATE.md` — step-by-step takeover protocol.
3. `CURRENT_STATE.md` — dated working summary; refresh runtime facts.
4. `WORK_QUEUE.md` — prioritized backlog, owners, acceptance evidence.
5. `KNOWN_ISSUES.md` — confirmed findings separated from hypotheses.
6. `SYSTEM_MAP.md` and `LUKE_CONTRACT.md` — architecture and founder interface.
7. `CHANGELOG.md` and the latest files in `sessions/`.
8. Referenced `evidence/` and `reports/` artifacts; then the governing section before consequential work.

## File map

| Location | Purpose | Update rule |
|---|---|---|
| FOUNDER_INTENT.md | Latest instructions, boundaries, target meaning | Quote/paraphrase faithfully; identify session/date; never invent authorization |
| CURRENT_STATE.md | Fast resumption summary | Include UTC timestamp, source and uncertainty |
| WORK_QUEUE.md | Priorities, blockers, next action, proof required | Update after a meaningful checkpoint |
| KNOWN_ISSUES.md | Reproducible defects and unresolved questions | Never turn an untested theory into a fact |
| SYSTEM_MAP.md | Components, paths, services and data ownership | Update whenever architecture changes |
| LUKE_CONTRACT.md | Telegram delegation, financial truth, transfers | Preserve owner authorization and actual capabilities |
| CHANGELOG.md | Append-only session index | Link session and evidence; distinguish planned/deployed/observed |
| sessions/ | Detailed per-agent work journals | Unique filename per session; preserve prior entries |
| evidence/ | Timestamped sanitized observations | Immutable after capture; correct with a new capture |
| reports/ | Assessment and implementation proposals | Timestamp and distinguish opinion from established fact |
| templates/ | Session, change receipt, incident and experiment formats | Copy templates; fill all applicable fields |

## How agents leave notes

Engineering agents with authorized shell/file access create a unique session file before changing production. Checkpoint it after each meaningful change and before context loss, agent replacement, or ending work. Use `templates/SESSION.md`. At handoff, append CHANGELOG and refresh CURRENT_STATE/WORK_QUEUE if facts changed.

Hermes officers continue to use their existing typed FORGE tools and persistent `role_reports`, `agent_results`, `agent_handoffs`, workflows, lessons and opportunity memory. Their sandbox is not widened by this documentation. A coding/operator agent can reference or export those records into evidence. **Automatic Hermes-to-Markdown journal export is not implemented by this change.**

## Evidence and completion

A written note proves only that a note exists. A commit proves only that code was recorded. Tests prove the tested behavior. A deploy receipt proves delivery. Runtime observation proves observed behavior in a stated window. Settled venue/account reconciliation proves financial outcomes. Do not collapse these into “DONE.”

States: PLANNED → IN_PROGRESS → IMPLEMENTED → VERIFIED → DEPLOYED → OBSERVED. BLOCKED and ROLLED_BACK are explicit. Financial claims additionally require SETTLED_RECONCILED, with LIVE/PAPER/SHADOW and costs stated.

Do not store keys, bearer tokens, confirmation codes, private keys, credential setup links, full environments, or unredacted logs here. Record locations and access procedures only.

## Concurrent work

Give each agent a separate journal and a declared file scope. Read Git status before editing. Existing uncommitted changes belong to their original work and must be preserved. Do not overwrite another journal or stage the whole repository. Shared summaries are coordination points; re-read them immediately before writing and preserve others’ additions. This system is a documented protocol, not an enforced lock manager.

## Joint financial-team mandate
Read [TEAM_ECONOMICS.md](TEAM_ECONOMICS.md) for the latest founder clarification: integrated Hermes collaboration, outcome-linked inference spending, and $1/hour aggregate primary target. This is a recorded contract; runtime enforcement remains implementation work.

## Latest dated takeover report — 2026-10-09

Use [the forensic passover](reports/2026-10-09-FORGE-FORENSIC-PASSOVER.md) for the completed one-hour PAPER observation, runtime/service activation, Hermes role analysis, earnings truth, recommended next actions and uncertainty. Read [the latest checkpoint](CURRENT_STATE.md), then revalidate current facts on the live target.
