#!/usr/bin/env python3
"""FORGE root deployer — the ONLY path by which AI-written code reaches production (Engineering Cell, OP-025).

Not an AI. Runs as root from a systemd timer; one change at a time (flock). For each QUEUED / APPROVED ticket:
  1. stage   fresh clone of production HEAD; fetch the engineer's commit; it must descend from production HEAD
  2. policy  PROTECTED paths (risk, live execution, venues, money movement, auth/ops/security, deps, deploy tooling)
             → AWAITING_OWNER until the owner approves via EXECUTIVE OPS (2FA / out-of-band code);
             forbidden content in added lines (secrets, credential files, shells, eval) → REJECTED
  3. test    ruff on changed files + the FULL test suite, as the unprivileged engineer user, no network, no secrets
  4. deploy  fast-forward production, restart affected services
  5. watch   10 min: API health, no new stale loops, no new Tracebacks → else automatic rollback + restart
  6. report  ticket status/log via the OPS API + a Telegram note to the owner
"""

from __future__ import annotations

import fcntl
import json
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

PROD = Path("/srv/forge")
ENG_REPO = Path("/srv/forge/runtime/eng/repo")
STAGE = Path("/srv/forge/runtime/deploy/stage")
API = "http://127.0.0.1:8470"
WATCH_S = 600
PROTECTED = (
    r"^src/forge/risk/", r"^src/forge/execution/", r"^src/forge/venues/", r"^src/forge/ledger/", r"^src/forge/ops/",
    r"^src/forge/api/(ops_api|auth|agent_api|server)\.py$", r"^src/forge/core/state\.py$", r"^src/forge/treasury/regime\.py$",
    r"^src/forge/opportunities/kalshi_live\.py$", r"^src/forge/treasury/idle_yield\.py$", r"^src/forge/config\.py$",
    r"^src/forge/audit/", r"^src/forge/persistence/db\.py$", r"^scripts/", r"^hermes/", r"^deploy/", r"^pyproject\.toml$",
    r"^uv\.lock$", r"^\.", r"^config/", r"^modal_apps/",
)
FORBIDDEN = (
    (r"/etc/forge|forge\.env|kalshi_private_key|ops_token|ops_totp|eng_token|agent_token|operator_token|session_secret",
     "touches credential files"),
    (r"COINBASE_CDP_API_KEY|DEEPSEEK_API_KEY|MODAL_TOKEN|TELEGRAM_BOT_TOKEN|AZURE_ANTHROPIC|KALSHI_API_KEY|OPENROUTER",
     "reads secret environment variables"),
    (r"\bos\.system\(|subprocess\.(?:run|Popen|call|check_output)\(.*shell\s*=\s*True|\beval\(|\bexec\(|__import__\(",
     "shell / dynamic code execution"),
    (r"move_funds|withdraw|/v2/accounts/[^\"']*/(?:transactions|withdrawals)|portfolios/move", "money movement"),
    (r"systemctl|sudo\b|/root/|\.ssh/", "host administration"),
)


def sh(cmd: list[str], cwd: Path | None = None, timeout: int = 1800, check: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=check)


def api(method: str, path: str, body: dict | None = None) -> dict:
    tok = (PROD / "var/run/ops_token").read_text().strip()
    req = urllib.request.Request(API + path, method=method, data=json.dumps(body).encode() if body else None,
                                 headers={"Authorization": f"Bearer {tok}", "Content-Type": "application/json",
                                          "X-Ops-Actor": "deployer"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode() or "{}")


def notify(text: str) -> None:
    try:
        env = dict(line.split("=", 1) for line in Path("/srv/forge/runtime/ops/home/.env").read_text().splitlines() if "=" in line)
        tok, chat = env.get("TELEGRAM_BOT_TOKEN"), (env.get("TELEGRAM_ALLOWED_USERS") or "").split(",")[0]
        if tok and chat:
            data = urllib.parse.urlencode({"chat_id": chat, "text": text[:3500]}).encode()
            urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/sendMessage", data=data, timeout=15)
    except Exception:
        pass


def report(tid: int, status: str, log: str, cls: str | None = None, title: str = "") -> None:
    api("POST", "/api/ops/eng/deploy_result", {"id": tid, "deploy_status": status, "deploy_class": cls, "log": log[-7000:]})
    icon = {"DEPLOYED": "✅", "AWAITING_OWNER": "⏸️", "ROLLED_BACK": "↩️"}.get(status, "⚠️")
    notify(f"{icon} FORGE engineering — ticket #{tid} {title[:80]}: {status}\n{log[-700:]}")


def health() -> dict:
    try:
        tok = (PROD / "var/run/ops_token").read_text().strip()
        req = urllib.request.Request(API + "/api/ops/status", headers={"Authorization": f"Bearer {tok}"})
        with urllib.request.urlopen(req, timeout=15) as r:
            st = json.loads(r.read().decode())
        return {"ok": True, "stale": set(st["health"]["stale_loops"])}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200], "stale": set()}


def tracebacks(since: float) -> int:
    out = sh(["journalctl", "-u", "forge", "--since", f"@{int(since)}", "--no-pager", "-o", "cat"]).stdout
    return out.count("Traceback (most recent call last)")


def classify(changed: list[str], added: str) -> tuple[str, list[str]]:
    problems = [why for pat, why in FORBIDDEN if re.search(pat, added)]
    if problems:
        return "REJECTED", problems
    hits = [f for f in changed if any(re.search(p, f) for p in PROTECTED)]
    return ("PROTECTED", hits) if hits else ("STANDARD", [])


def run_tests(stage: Path) -> tuple[bool, str]:
    """Tests execute AI-written code → unprivileged engineer user, no network, secrets/state invisible."""
    sh(["chown", "-R", "forge-eng:forge-eng", str(stage)])
    cmd = ["systemd-run", "--wait", "--pipe", "--quiet", "--collect", "-p", "User=forge-eng", "-p", "Group=forge-eng",
           "-p", "PrivateNetwork=yes", "-p", "ProtectSystem=strict", "-p", "ProtectHome=yes", "-p", "PrivateTmp=yes",
           "-p", "NoNewPrivileges=yes", "-p", f"ReadWritePaths={stage}", "-p", "MemoryMax=2G", "-p", "CPUQuota=200%",
           "-p", "InaccessiblePaths=/etc/forge /srv/forge/var /srv/forge/runtime/hermes/home /srv/forge/runtime/ops "
                 "-/srv/forge/runtime/signal /srv/forge-archive", "-p", f"WorkingDirectory={stage}",
           "-E", f"PYTHONPATH={stage}/src", "-E", "HOME=/tmp",
           "/srv/forge/runtime/eng/repo/.venv/bin/python", "-m", "pytest", "-q", "-p", "no:cacheprovider", "-x", "tests"]
    r = sh(cmd, timeout=1800)
    return r.returncode == 0, (r.stdout + r.stderr)[-3000:]


def lint(stage: Path, changed: list[str]) -> tuple[bool, str]:
    py = [f for f in changed if f.endswith(".py") and (stage / f).exists()]
    if not py:
        return True, ""
    r = sh(["/srv/forge/.venv/bin/ruff", "check", "--output-format", "concise", *py], cwd=stage)
    return r.returncode == 0, (r.stdout + r.stderr)[-1500:]


def deploy_one(t: dict) -> None:
    tid, sha, title = int(t["id"]), str(t["commit_sha"]), str(t.get("title") or "")
    log: list[str] = [f"ticket #{tid} commit {sha[:10]}"]
    sh(["rm", "-rf", str(STAGE)])
    STAGE.parent.mkdir(parents=True, exist_ok=True)
    sh(["git", "clone", "-q", "--no-hardlinks", str(PROD), str(STAGE)], check=True)
    prod_head = sh(["git", "rev-parse", "HEAD"], cwd=STAGE).stdout.strip()
    f = sh(["git", "fetch", "-q", str(ENG_REPO), sha], cwd=STAGE)
    if f.returncode != 0:
        return report(tid, "REJECTED", "\n".join(log + ["commit not found in engineer repo", f.stderr[-400:]]), title=title)
    if sh(["git", "merge-base", "--is-ancestor", prod_head, sha], cwd=STAGE).returncode != 0:
        return report(tid, "REBASE_REQUIRED", "\n".join(log + [f"commit is not based on production HEAD {prod_head[:10]} — "
                                                                "rebase onto prod and resubmit"]), title=title)
    changed = [x for x in sh(["git", "diff", "--name-only", prod_head, sha], cwd=STAGE).stdout.split() if x]
    added = "\n".join(line[1:] for line in sh(["git", "diff", "-U0", prod_head, sha, "--", "*.py"], cwd=STAGE).stdout.splitlines()
                      if line.startswith("+") and not line.startswith("+++"))     # code only (docs may say "withdraw")
    cls, why = classify(changed, added)
    log.append(f"changed: {', '.join(changed[:30])}")
    if cls == "REJECTED":
        return report(tid, "REJECTED", "\n".join(log + [f"policy: {w}" for w in why]), "REJECTED", title)
    if cls == "PROTECTED" and t.get("deploy_status") != "APPROVED":
        return report(tid, "AWAITING_OWNER", "\n".join(log + ["protected areas: " + ", ".join(why[:10]),
                                                              "reply to FORGE: 'approve deploy " + str(tid) + "'"]), cls, title)
    sh(["git", "checkout", "-q", sha], cwd=STAGE, check=True)
    ok, out = lint(STAGE, changed)
    if not ok:
        return report(tid, "TESTS_FAILED", "\n".join(log + ["ruff:", out]), cls, title)
    ok, out = run_tests(STAGE)
    log.append("tests: " + (out.strip().splitlines() or ["?"])[-1])
    if not ok:
        return report(tid, "TESTS_FAILED", "\n".join(log + [out]), cls, title)
    # ---- deploy (fast-forward production) ----
    api("POST", "/api/ops/eng/deploy_result", {"id": tid, "deploy_status": "DEPLOYING", "deploy_class": cls, "log": "\n".join(log)})
    before = health()
    t0 = time.time()
    as_admin = ["sudo", "-u", "forgeadmin", "git", "-C", str(PROD)]
    sh([*as_admin, "fetch", "-q", str(ENG_REPO), sha], check=True)
    m = sh([*as_admin, "merge", "--ff-only", "-q", sha])
    if m.returncode != 0:
        return report(tid, "REBASE_REQUIRED", "\n".join(log + ["production moved; ff failed", m.stderr[-300:]]), cls, title)
    units = ["forge"] + (["forge-hermes"] if any(x.startswith("hermes/") for x in changed) else [])
    sh(["systemctl", "restart", *units])
    healthy, reason = False, "no health within 180 s"
    for _ in range(45):
        time.sleep(4)
        h = health()
        if h["ok"]:
            healthy, reason = True, ""
            break
    end = time.time() + WATCH_S
    while healthy and time.time() < end:
        time.sleep(30)
        h = health()
        new_stale = h["stale"] - before["stale"]
        tb = tracebacks(t0)
        if not h["ok"] or new_stale or tb > 3:
            healthy, reason = False, f"health={h['ok']} new_stale={sorted(new_stale)} tracebacks={tb}"
    if not healthy:
        sh([*as_admin, "reset", "-q", "--hard", prod_head])
        sh(["systemctl", "restart", *units])
        return report(tid, "ROLLED_BACK", "\n".join(log + [f"post-deploy watch failed: {reason}",
                                                           f"production restored to {prod_head[:10]}"]), cls, title)
    report(tid, "DEPLOYED", "\n".join(log + [f"deployed {sha[:10]} ({cls}); healthy for {WATCH_S // 60} min"]), cls, title)


def main() -> int:
    lock = open("/run/forge-deployer.lock", "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return 0
    try:
        queue = api("GET", "/api/ops/eng/queue")
    except Exception as e:
        print("FORGE API unreachable:", e)
        return 0
    for t in queue[:1]:                                   # one change per run
        try:
            deploy_one(t)
        except Exception as e:  # noqa: BLE001
            report(int(t["id"]), "REJECTED", f"deployer error: {type(e).__name__}: {str(e)[:400]}", title=str(t.get("title")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
