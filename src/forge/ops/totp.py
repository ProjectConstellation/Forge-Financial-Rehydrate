"""RFC 6238 TOTP second factor for consequential OPS commands (transfers, resume, live enablement, unlock).

The secret lives in var/run/ops_totp (0600, forge user), created by the root-only `forge-exec-2fa` command and shown once
as an otpauth:// QR for the owner's authenticator app. The model never sees it, so neither the model nor injected text can
produce a valid code. Replay protection: each accepted time-step is recorded; a code is accepted once.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import struct
import time
from pathlib import Path
from typing import Any

STEP = 30
WINDOW = 1          # accept ±1 step (clock skew)


def _code(secret_b32: str, counter: int) -> str:
    key = base64.b32decode(secret_b32.upper() + "=" * (-len(secret_b32) % 8))
    h = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    o = h[-1] & 0x0F
    return f"{(struct.unpack('>I', h[o:o + 4])[0] & 0x7FFFFFFF) % 1_000_000:06d}"


def secret_path(home: Path) -> Path:
    return Path(home) / "run" / "ops_totp"


def configured(home: Path) -> bool:
    p = secret_path(home)
    return p.exists() and p.stat().st_size >= 16


def verify(home: Path, db: Any, code: str, now: float | None = None) -> tuple[bool, str]:
    if not configured(home):
        return False, "2FA not configured"
    code = "".join(ch for ch in str(code) if ch.isdigit())
    if len(code) != 6:
        return False, "authenticator code must be 6 digits"
    secret = secret_path(home).read_text().strip()
    t = int((now if now is not None else time.time()) // STEP)
    last = int(db.kv_get("ops.totp.last_step") or 0)
    for c in range(t - WINDOW, t + WINDOW + 1):
        if hmac.compare_digest(_code(secret, c), code):
            if c <= last:
                return False, "code already used (replay) — wait for the next code"
            db.kv_set("ops.totp.last_step", c)
            return True, "ok"
    return False, "wrong authenticator code"
