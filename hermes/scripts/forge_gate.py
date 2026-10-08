"""Wake gate — blueprint §10.

WAKE if OPEN critical/high directive OR pending handoff OR SLA near/breach OR
owned econ event OR material metric deterioration OR prelive blocker OR Luke ask OR
deep-review due OR recovery lever available.

SKIP only if no actionable work AND within SLA AND valid IDLE/WAITING state.
Quiet hours never suppress urgent work.
"""
import json
import sys
import time
import urllib.request

from forge_common import call, gate, now, save, skip, state, wake

role, est, quiet_h = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
key = sys.argv[4] if len(sys.argv) > 4 else role
st = state()
last = float(st.get(key, 0))
a = gate(role, est)
if a is None:
    skip()
    sys.exit(0)

# Pull digest + workforce urgency
d = call(f"/api/agent/digest?since={last or now() - 3600}&role={role}")
# Extra signals from digest (server-enriched) or direct allow context
urgent = bool(d.get("urgent") or d.get("open_critical") or d.get("pending_handoff") or d.get("sla_breach"))
due = now() - last >= quiet_h * 3600 or a.get("mode") == "credit"
meaningful = bool(d.get("meaningful"))

if not urgent and not meaningful and not due:
    # Final check: recovery under floor with actionable lever for this role
    if not d.get("recovery_lever"):
        skip()
        sys.exit(0)

st[key] = now()
save(st)
wake({
    "budget": {k: a.get(k) for k in ("headroom", "budget_24h", "spent_24h", "hermes_value_per_usd")},
    "changes": d,
    "wake_reason": "urgent" if urgent else ("meaningful" if meaningful else ("due" if due else "recovery_lever")),
})
