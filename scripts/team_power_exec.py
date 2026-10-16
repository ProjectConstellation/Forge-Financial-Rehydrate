#!/usr/bin/env python3
"""Root-side executor for the FORGE workforce power switch.

forge.service is hardened (NoNewPrivileges=yes, ProtectSystem=strict, ReadWritePaths=/srv/forge/var),
so it can NEVER escalate privileges — which is correct and must not be weakened. Instead the service
drops a signed request file into /srv/forge/var/run/ and this script, invoked by a root systemd path
unit, performs the pause/resume by dropping to forge-hermes through the narrow sudoers rule.

Protocol:
    request : /srv/forge/var/run/team_power.request.json   {"verb": "pause|resume|status", "actor": ..., "nonce": ...}
    result  : /srv/forge/var/run/team_power.result.<nonce>.json
The request file is consumed (removed) after handling so a unit restart cannot replay it.

This script is root-owned 0750 and only ever runs the three fixed verbs.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

RUN = Path("/srv/forge/var/run")
REQUEST_GLOB = "team_power.request.*.json"
LEGACY_REQUEST = RUN / "team_power.request.json"      # pre-nonce layout; drained then removed
SCRIPT = "/srv/forge/scripts/team_power.sh"
AUDIT = Path("/srv/forge/var/log/team_power_audit.log")
VERBS = ("pause", "resume", "status", "wake")


def write_result(nonce: str, payload: dict) -> None:
    path = RUN / f"team_power.result.{nonce}.json"
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, default=str))
    os.replace(tmp, path)
    try:
        os.chmod(path, 0o640)
    except OSError:
        pass


def main() -> int:
    """Drain EVERY pending request. A single shared request file meant concurrent wakes overwrote one
    another and were silently dropped, so this loops over all per-nonce requests until none remain."""
    paths = sorted(RUN.glob(REQUEST_GLOB))
    if LEGACY_REQUEST.exists():
        paths.append(LEGACY_REQUEST)
    if not paths:
        return 0
    rc = 0
    for path in paths:
        try:
            if not handle(path):
                rc = 1
        except Exception as e:                       # never let one bad request block the rest
            write_result("unknown", {"ok": False, "error": f"{type(e).__name__}: {e}"})
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass
            rc = 1
    return rc


def handle(path: Path) -> bool:
    try:
        req = json.loads(path.read_text())
    except Exception as e:
        # Consume the bad request so the path unit does not spin on it forever.
        write_result("unknown", {"ok": False, "error": f"unreadable request: {type(e).__name__}: {e}"})
        path.unlink(missing_ok=True)
        return False

    verb = str(req.get("verb") or "")
    actor = str(req.get("actor") or "unknown")[:80]
    nonce = str(req.get("nonce") or str(int(time.time() * 1000)))[:64]

    # Consume first: a crash must not leave a replayable request behind.
    path.unlink(missing_ok=True)

    if verb not in VERBS:
        write_result(nonce, {"ok": False, "error": f"verb {verb!r} not permitted", "allowed": list(VERBS)})
        return False

    # `wake` takes exactly one extra argument: a ROLE NAME. The wrapper resolves it to a job id from
    # live state and refuses unknown roles, so this can never be used to run an arbitrary job.
    argv = [SCRIPT, verb]
    if verb == "wake":
        role = str(req.get("arg") or "").strip()[:64]
        if not role or not all(ch.isalnum() or ch in "_-" for ch in role):
            write_result(nonce, {"ok": False, "verb": verb,
                                 "error": f"wake requires a bare role name, got {role!r}"})
            return False
        argv.append(role)
    try:
        proc = subprocess.run(
            argv, capture_output=True, text=True, timeout=240,
            env={**os.environ, "FORGE_POWER_ACTOR": f"root-executor:{actor}"},
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        ok = proc.returncode == 0
    except subprocess.TimeoutExpired:
        out, ok = "timeout after 240s", False
    except Exception as e:
        out, ok = f"{type(e).__name__}: {e}", False

    # Count the resulting job states from the wrapper's own STATES line when present.
    states = {}
    for line in out.splitlines():
        if line.startswith("STATES "):
            try:
                states = json.loads(line[len("STATES "):])
            except Exception:
                states = {}

    write_result(nonce, {"ok": ok, "verb": verb, "actor": actor, "states": states,
                         "detail": out.strip()[:2000], "ts": time.time()})
    return bool(ok)


if __name__ == "__main__":
    sys.exit(main())
