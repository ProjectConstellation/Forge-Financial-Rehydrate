# Hermes in FORGE — runbook (swap models with zero recoding)

Hermes Agent v0.21.5 (pinned) runs as `forge-hermes.service` (user `forge-hermes`, HERMES_HOME=/srv/forge/runtime/hermes/home,
slice `forge.slice` = FORGE's 4 vCPU / 4 GB envelope). It has NO exchange keys and can only use FORGE's agent API
(127.0.0.1:8470/api/agent/*, agent token, loopback only).

## What is model-independent (preserved across every swap)
- Role genomes (prompts): FORGE DB `prompt_genomes` — served by `forge_get_role_brief`; versioned, evolved by the Architect.
- Constitution (immutable): `src/forge/agents/constitution.py`.
- Tools: FORGE `ToolRouter` (`src/forge/brain/tools.py`) via the `hermes-forge` plugin.
- Jobs: thin bootstraps in `hermes/prompts/boot_*.md`; gates in `hermes/scripts/`.
- Evidence, attribution, calibration, panels: FORGE DB (prompt_runs, role_reports, agent_predictions, agent_panels).

## Swap (one command each)
```bash
forge-hermes-mode opus 180 72        # Claude Opus 5.5 (Azure, operator credit $180 over 72 h, high reasoning, fast cadence)
forge-hermes-mode deepseek           # DeepSeek V4.1 Flash (deepseek-flash), ROI-measured budget, lean cadence
forge-hermes-mode status             # current model + jobs

# Any other OpenAI- or Anthropic-compatible endpoint: endpoint + model + key, nothing else
echo "$API_KEY" | forge-hermes-mode add-provider my-llm https://host/v1 chat_completions my-model 0.5 2.0   # $/M in, out
forge-hermes-mode use my-llm my-model            # ROI-budget mode
forge-hermes-mode use my-llm my-model 100 48     # prepaid/free credit pool: $100 over 48 h
```
Keys live only in `/srv/forge/runtime/hermes/home/.env` (0600, forge-hermes). Both Opus (`azure-opus`) and DeepSeek
(`deepseek`) providers stay configured permanently; swapping only changes the active provider/model + cadence.

## Verify after a swap
```bash
sudo systemctl status forge-hermes --no-pager | head -5
sudo -u forge-hermes env HOME=/srv/forge/runtime/hermes/home HERMES_HOME=/srv/forge/runtime/hermes/home \
  /srv/forge/runtime/hermes/app/venv/bin/hermes cron status
curl -s localhost:8470/api/surface -H "Authorization: Bearer $(sudo cat /srv/forge/var/run/operator_token)" | head -c 300
```
Role output: FORGE `role_reports`; prompt performance: tool `get_prompt_performance` (or table `prompt_genomes`/`prompt_runs`).

## Roles (genomes v1, see `src/forge/agents/roles.py`)
governor (CIO) · alpha_inventor (Scientist A) · adversary (Scientist B) · critic (red team) · doctor (SRE) ·
rail_hunter (+ change-triggered scout) · architect (prompt evolution). Pipeline: invent → falsify (blind, calibrated) →
critique → FORGE validation/Modal → governor → deterministic Risk Governor → execution → doctor → outcomes → memory.
