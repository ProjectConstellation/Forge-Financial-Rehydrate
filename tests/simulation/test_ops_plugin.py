"""OPS plugin: confirmation codes never reach the model; secrets are redacted from logs/outputs; units are whitelisted."""
import importlib.util
import json
from pathlib import Path

PLUGIN = Path(__file__).resolve().parents[2] / "hermes" / "plugin" / "hermes-forge-ops" / "__init__.py"


def _load():
    spec = importlib.util.spec_from_file_location("forge_ops_plugin", PLUGIN)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class Ctx:
    def __init__(self):
        self.tools, self.hooks = {}, {}

    def register_tool(self, name, toolset, schema, handler):
        assert toolset == "forge_ops"
        self.tools[name] = handler

    def register_hook(self, name, fn):
        self.hooks[name] = fn


def test_code_is_stripped_and_sent_out_of_band(monkeypatch):
    m = _load()
    sent = []

    def fake_call(method, path, body=None, actor="ops", timeout=30.0):
        if path == "/api/ops/tools":
            return {"tools": [], "actions": {"resume_trading": {"class": "CONFIRM", "description": "resume"}}, "roles": ["all"]}
        if path == "/api/ops/action":
            return {"status": "CONFIRMATION_REQUIRED", "pending_id": "ab12cd34", "owner_code": "493817", "description": "resume"}
        return {}
    monkeypatch.setattr(m, "_call", fake_call)
    monkeypatch.setattr(m, "_send_owner", lambda text: sent.append(text) or True)
    ctx = Ctx()
    m.register(ctx)
    out = ctx.tools["ops_action"]({"action": "resume_trading"}, session_id="s1")
    assert "493817" not in out and json.loads(out)["owner_notified_out_of_band"] is True
    assert "493817" in sent[0] and "ab12cd34" in sent[0]
    for name in ("ops_status", "ops_assign", "ops_directives", "ops_confirm", "ops_restart", "ops_logs", "ops_host", "ops_audit"):
        assert name in ctx.tools
    assert "error" in json.loads(ctx.tools["ops_restart"]({"unit": "sshd"}))          # only FORGE units


def test_redaction():
    m = _load()
    s = ("token=abc123 Authorization: Bearer xyz sk-ABCDEFGHIJKLMNOPQRSTUV 123456789:AAHdqTcvCH1vGWJxfSeofSAs0K5PALDsaw "
         "-----BEGIN EC PRIVATE KEY-----\nMHcCAQEE\n-----END EC PRIVATE KEY----- KXBTCD-26OCT0712-T82799.99 stg_1m4afwb06dkfweesfq2dtt")
    r = m.redact(s)
    for secret in ("abc123", "xyz", "sk-ABCDEF", "AAHdqTcv", "MHcCAQEE"):
        assert secret not in r
    assert "KXBTCD-26OCT0712-T82799.99" in r and "stg_1m4afwb06dkfweesfq2dtt" in r       # operational ids survive
