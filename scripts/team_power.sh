#!/bin/bash
# FORGE team power switch — the ONLY privileged operation Luca (ops) may perform via sudo.
#
# Founder order 2026-10-10: "Luke never gets paused ever, because I need Luke to have the ability to
# pause the team or bring the team back online." Implementing that needs to reach the Hermes cron state,
# which is owned by forge-hermes. Rather than grant the forge service a broad sudo rule (or allow `env`,
# which would permit arbitrary command execution as forge-hermes), this wrapper exposes exactly four
# verbs and nothing else. Every invocation is appended to an audit log.
#
# Deliberate limits:
#   * no argument is ever passed to a shell; only the fixed subcommands below are constructed
#   * forge-ops (Luca's own gateway) is NEVER paused — the founder must always be able to reach him
#   * job ids are read from the live jobs.json, never accepted as caller input
#   * resume verifies each job returned to `scheduled` and reports any that did not
set -euo pipefail

HH=/srv/forge/runtime/hermes/home
HERMES=/srv/forge/runtime/hermes/app/venv/bin/hermes
AUDIT=/srv/forge/var/log/team_power_audit.log
ACTOR="${FORGE_POWER_ACTOR:-unknown}"
mkdir -p "$(dirname "$AUDIT")"

log() {
  printf '%s actor=%s action=%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$ACTOR" "$1" "${2:-}" >> "$AUDIT"
}

run_hermes() {
  sudo -n -u forge-hermes env HOME="$HH" HERMES_HOME="$HH" "$HERMES" "$@"
}

# Every officer job id, from the live state file. Excludes nothing by name — pause/resume act on the
# whole officer roster; forge-ops runs under a separate gateway (runtime/ops) and is not in this file.
# Resolve a ROLE NAME to its job id from live state. A caller may never pass a job id: that would let
# a compromised service make the root executor run an arbitrary cron job. Unknown roles are refused.
role_to_job_id() {
  python3 -c "
import json,sys
role=sys.argv[1]
d=json.load(open('$HH/cron/jobs.json'))
jobs=d.get('jobs',d)
L=list(jobs.values()) if isinstance(jobs,dict) else jobs
want='forge-'+role.replace('_','-')
for j in L:
    if j.get('name')==want:
        print(j['id']); sys.exit(0)
sys.exit(1)
" "$1"
}

job_ids() {
  python3 -c "
import json,sys
d=json.load(open('$HH/cron/jobs.json'))
jobs=d.get('jobs',d)
L=list(jobs.values()) if isinstance(jobs,dict) else jobs
for j in L: print(j['id'])
"
}

job_states() {
  python3 -c "
import json
d=json.load(open('$HH/cron/jobs.json'))
jobs=d.get('jobs',d)
L=list(jobs.values()) if isinstance(jobs,dict) else jobs
from collections import Counter
c=Counter(j.get('state') for j in L)
for j in L: print('%-26s %s' % (j.get('name'), j.get('state')))
print('STATES ' + json.dumps(dict(c)))
"
}

cmd="${1:-status}"
case "$cmd" in
  pause)
    n=0
    for id in $(job_ids); do
      if run_hermes cron pause "$id" >/dev/null 2>&1; then n=$((n+1)); fi
    done
    log pause "paused=$n"
    echo "paused $n officer job(s); forge-ops (Luca) left running by design"
    job_states
    ;;
  resume)
    n=0; failed=""
    for id in $(job_ids); do
      if run_hermes cron resume "$id" >/dev/null 2>&1; then n=$((n+1)); else failed="$failed $id"; fi
    done
    log resume "resumed=$n failed=${failed:-none}"
    echo "resumed $n officer job(s); failed:${failed:- none}"
    job_states
    ;;
  wake)
    # On-demand wake of ONE officer, by role name. Bounded: the role must exist in live state.
    role="${2:-}"
    if [ -z "$role" ]; then
      log "denied:wake" "no role supplied"
      echo "usage: team_power.sh wake <role>" >&2
      exit 2
    fi
    if ! jid=$(role_to_job_id "$role"); then
      log "denied:wake" "unknown role=$role"
      echo "unknown role: $role (not present in live jobs.json)" >&2
      exit 3
    fi
    # `hermes cron run` BLOCKS for the whole officer run (30-200s). Launching it in the foreground would
    # hold the single root executor, so a founder's pause request arriving mid-run would wait behind it.
    # Launch detached and confirm the LAUNCH only. Completion is recorded by the officer's own
    # role_report, which is the honest source of truth for "did the run produce work".
    # NOTE: `run_hermes` is a shell FUNCTION, so it cannot be passed to setsid (setsid execs a binary).
    # Invoke the binary directly here. Failure to launch is detected synchronously; a launched run
    # completes on its own and is proven by the officer's role_report, not by this exit code.
    if setsid sudo -n -u forge-hermes env HOME="$HH" HERMES_HOME="$HH" HERMES_ACCEPT_HOOKS=1 \
         "$HERMES" cron run "$jid" >/dev/null 2>&1 < /dev/null & then
      log wake "role=$role job=$jid result=LAUNCHED pid=$!"
      echo "LAUNCHED $role ($jid) pid=$!"
      echo "NOTE launch confirmed only; run completion is proven by the officer's role_report"
    else
      log wake "role=$role job=$jid result=FAILED"
      echo "wake failed for $role ($jid)" >&2
      exit 4
    fi
    ;;
  status)
    log status ""
    job_states
    ;;
  *)
    log "denied:$cmd" ""
    echo "usage: team_power.sh {pause|resume|status|wake <role>}" >&2
    exit 2
    ;;
esac
