"""CDP API key JWT signing (ES256) for Coinbase Advanced Trade on a personal account.

Verified against docs.cdp.coinbase.com (2026-10-06): CDP Secret API Key, ECDSA/ES256 only,
one JWT per request, 2-minute expiry, REST `uri` claim = "METHOD host/path" (no query string),
WebSocket JWT has no `uri` claim.
"""

from __future__ import annotations

import secrets
import time

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from pydantic import SecretStr


class CdpSigner:
    def __init__(self, key_name: SecretStr, key_secret: SecretStr, host: str = "api.coinbase.com") -> None:
        pem = key_secret.get_secret_value().replace("\\n", "\n").strip() + "\n"
        key = serialization.load_pem_private_key(pem.encode(), password=None)
        if not isinstance(key, ec.EllipticCurvePrivateKey):
            raise ValueError("Coinbase Advanced Trade requires an ECDSA (ES256) CDP key")
        self._key = key
        self._name = key_name.get_secret_value()
        self.host = host

    def _encode(self, payload: dict[str, object]) -> str:
        return jwt.encode(payload, self._key, algorithm="ES256",
                          headers={"kid": self._name, "nonce": secrets.token_hex()})

    def rest_jwt(self, method: str, path: str) -> str:
        now = int(time.time())
        path = path.split("?", 1)[0]
        return self._encode({"sub": self._name, "iss": "cdp", "nbf": now, "exp": now + 120,
                             "uri": f"{method.upper()} {self.host}{path}"})

    def ws_jwt(self) -> str:
        now = int(time.time())
        return self._encode({"sub": self._name, "iss": "cdp", "nbf": now, "exp": now + 120})

    def __repr__(self) -> str:  # never leak key material
        return "CdpSigner(<redacted>)"
