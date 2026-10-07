"""Generic gate: wake the role only if (a) FORGE grants budget and (b) something meaningful changed since the role's last
run OR the role's max quiet interval elapsed. Usage: forge_gate.py <role> <est_usd> <max_quiet_hours>"""
import sys

from forge_common import call, gate, now, save, skip, state, wake

role, est, quiet_h = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
st = state()
last = float(st.get(role, 0))
a = gate(role, est)
if a is None:
    skip()
    sys.exit(0)
d = call(f"/api/agent/digest?since={last or now() - 3600}")
due = now() - last >= quiet_h * 3600
if not d.get("meaningful") and not due:
    skip()
    sys.exit(0)
st[role] = now()
save(st)
wake({"budget": {k: a.get(k) for k in ("headroom", "budget_24h", "spent_24h", "hermes_value_per_usd")}, "changes": d})
