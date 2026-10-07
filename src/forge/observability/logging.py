"""Structured JSON logging (DOSSIER §33). Secrets never logged (SecretStr + scrubbing)."""

from __future__ import annotations

import json
import logging
import re
import sys
from datetime import UTC, datetime
from logging.handlers import RotatingFileHandler

_SECRET = re.compile(r"(sk-[A-Za-z0-9]{8,}|as-[A-Za-z0-9]{8,}|-----BEGIN [A-Z ]*PRIVATE KEY-----[^-]*)")


class JsonFormatter(logging.Formatter):
    def format(self, r: logging.LogRecord) -> str:
        msg = _SECRET.sub("[REDACTED]", r.getMessage())
        d = {"ts": datetime.fromtimestamp(r.created, UTC).isoformat(timespec="milliseconds"), "level": r.levelname,
             "logger": r.name, "msg": msg}
        if r.exc_info:
            d["exc"] = _SECRET.sub("[REDACTED]", self.formatException(r.exc_info))[-4000:]
        return json.dumps(d, ensure_ascii=False)


def setup_logging(settings) -> None:
    settings.ensure_dirs()
    root = logging.getLogger()
    root.setLevel(settings.log_level)
    for h in list(root.handlers):
        root.removeHandler(h)
    fh = RotatingFileHandler(settings.log_dir / "forge.jsonl", maxBytes=20_000_000, backupCount=10)
    fh.setFormatter(JsonFormatter())
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(JsonFormatter())
    root.addHandler(fh)
    root.addHandler(sh)
    for noisy in ("httpx", "websockets", "uvicorn.access", "hpack"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
