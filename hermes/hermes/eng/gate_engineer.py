"""Pre-run gate for the FORGE Engineer: wake only when a ticket needs work (no LLM cost when idle)."""
import json
import os
import urllib.request
from pathlib import Path

HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
try:
    tok = (HOME / "forge" / "eng_token").read_text().strip()
    req = urllib.request.Request("http://127.0.0.1:8470/api/ops/eng/next", headers={"Authorization": f"Bearer {tok}"})
    t = json.loads(urllib.request.urlopen(req, timeout=20).read().decode()).get("ticket")
except Exception as e:
    print(json.dumps({"wakeAgent": False, "note": f"FORGE unreachable {e}"}))
    raise SystemExit(0)
print(json.dumps({"wakeAgent": bool(t), "context": {"ticket": t}} if t else {"wakeAgent": False}, default=str)[:60000])
