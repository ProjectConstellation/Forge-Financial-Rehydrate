"""Founder portal authentication (public via forge.northstarimagine.com).

- Credentials from /etc/forge/forge.env: FORGE_PORTAL_USER + FORGE_PORTAL_PASSWORD_HASH (scrypt; never plaintext).
- Signed session cookie (HMAC-SHA256, HttpOnly, Secure behind HTTPS, SameSite=Strict, 30 days) + per-session CSRF token
  required on every state-changing request.
- Brute-force defense: 5 failed logins / 15 min per client IP → 15-min lockout; 30 failures / hour globally → lockout.
- Every login success/failure is written to the audit chain.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from collections import defaultdict, deque
from pathlib import Path


def hash_password(pw: str, salt: bytes | None = None) -> str:
    salt = salt or secrets.token_bytes(16)
    dk = hashlib.scrypt(pw.encode(), salt=salt, n=2 ** 14, r=8, p=1, dklen=32)
    return f"scrypt${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"


def verify_password(pw: str, stored: str) -> bool:
    try:
        _, salt_b64, dk_b64 = stored.split("$")
        salt = base64.b64decode(salt_b64)
        dk = hashlib.scrypt(pw.encode(), salt=salt, n=2 ** 14, r=8, p=1, dklen=32)
        return hmac.compare_digest(dk, base64.b64decode(dk_b64))
    except Exception:
        return False


class PortalAuth:
    COOKIE = "forge_session"

    def __init__(self, home: Path) -> None:
        self.user = os.environ.get("FORGE_PORTAL_USER", "").strip()
        self.pw_hash = os.environ.get("FORGE_PORTAL_PASSWORD_HASH", "").strip()
        p = home / "run" / "session_secret"
        if not p.exists():
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(secrets.token_hex(32))
            p.chmod(0o600)
        self.secret = p.read_text().strip().encode()
        self.fail_ip: dict[str, deque[float]] = defaultdict(deque)
        self.fail_all: deque[float] = deque()
        self.locked_until: dict[str, float] = {}

    @property
    def configured(self) -> bool:
        return bool(self.user and self.pw_hash)

    # ---- sessions -------------------------------------------------------------------------------------
    def issue(self, user: str) -> tuple[str, str]:
        csrf = secrets.token_urlsafe(24)
        body = base64.urlsafe_b64encode(json.dumps({"u": user, "exp": int(time.time()) + 30 * 86400,
                                                    "csrf": csrf}).encode()).decode()
        sig = hmac.new(self.secret, body.encode(), hashlib.sha256).hexdigest()
        return f"{body}.{sig}", csrf

    def session(self, cookie: str | None) -> dict | None:
        if not cookie or "." not in cookie:
            return None
        body, sig = cookie.rsplit(".", 1)
        if not hmac.compare_digest(sig, hmac.new(self.secret, body.encode(), hashlib.sha256).hexdigest()):
            return None
        try:
            data = json.loads(base64.urlsafe_b64decode(body.encode()))
        except Exception:
            return None
        return data if data.get("exp", 0) > time.time() else None

    # ---- login with brute-force defense -----------------------------------------------------------------
    def _prune(self, q: deque[float], window: float) -> None:
        now = time.time()
        while q and now - q[0] > window:
            q.popleft()

    def locked(self, ip: str) -> float:
        now = time.time()
        until = max(self.locked_until.get(ip, 0), self.locked_until.get("*", 0))
        return max(0.0, until - now)

    def attempt(self, ip: str, user: str, pw: str) -> bool:
        if self.locked(ip) > 0 or not self.configured:
            return False
        ok = hmac.compare_digest(user.strip().lower(), self.user.lower()) & verify_password(pw, self.pw_hash)
        if ok:
            self.fail_ip.pop(ip, None)
            return True
        now = time.time()
        q = self.fail_ip[ip]
        q.append(now)
        self._prune(q, 900)
        self.fail_all.append(now)
        self._prune(self.fail_all, 3600)
        if len(q) >= 5:
            self.locked_until[ip] = now + 900
        if len(self.fail_all) >= 30:
            self.locked_until["*"] = now + 900
        return False
