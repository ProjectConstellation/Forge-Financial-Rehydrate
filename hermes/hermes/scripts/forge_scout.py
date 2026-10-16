"""Scout pre-check: URL diffs OR economic telemetry urgency → wake LLM."""
import hashlib
import html
import json
import re
import sys
import urllib.request

from forge_common import HOME, call, gate, skip, wake

WATCH = {
    "coinbase_advanced_fees": "https://help.coinbase.com/en/coinbase/trading-and-funding/advanced-trade/advanced-trade-fees",
    "coinbase_one": "https://www.coinbase.com/one",
    "coinbase_usdc": "https://www.coinbase.com/usdc",
    "coinbase_new_listings": "https://help.coinbase.com/en/coinbase/trading-and-funding/advanced-trade/new-asset-listings",
    "coinbase_prediction_intro": "https://help.coinbase.com/en/coinbase/trading-and-funding/prediction-markets/intro",
    "kalshi_fees_help": "https://help.kalshi.com/en/articles/13823805-fees",
    "kalshi_crypto_markets": "https://help.kalshi.com/en/articles/13823838-crypto-markets",
    "kalshi_docs_index": "https://docs.kalshi.com/llms.txt",
    "kalshi_maintenance": "https://docs.kalshi.com/getting_started/maintenance_and_pauses.md",
    "cdp_docs_index": "https://docs.cdp.coinbase.com/llms.txt",
        "alpaca_trading_api": "https://alpaca.markets/trading-api",
    "alpaca_mcp_server": "https://docs.alpaca.markets/us/docs/alpaca-mcp-server",
    "alpaca_cli": "https://docs.alpaca.markets/us/docs/alpacas-cli",
    "alpaca_paper": "https://docs.alpaca.markets/us/docs/paper-trading",
    "alpaca_docs": "https://docs.alpaca.markets/docs/getting-started",
    "kalshi_series_fee_changes": "https://api.elections.kalshi.com/trade-api/v2/series/fee_changes",
}
SNAP = HOME / "forge" / "scout"
SNAP.mkdir(parents=True, exist_ok=True)


def text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 FORGE-scout"})
    raw = urllib.request.urlopen(req, timeout=25).read().decode("utf-8", "replace")
    raw = re.sub(r"<script.*?</script>|<style.*?</style>", " ", raw, flags=re.S)
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", " ", raw))).strip()[:200000]


def econ_wake():
    try:
        d = call("/api/agent/digest?since=0&role=scout")
    except Exception as e:
        return {"error": str(e)[:200]}
    if d.get("urgent") or d.get("recovery_lever") or d.get("open_critical") or d.get("pending_handoff") or d.get("sla_breach") or d.get("prelive_block"):
        return d
    try:
        if d.get("meaningful") and float((d.get("treasury") or {}).get("equity_usd") or 0) < 50:
            return d
    except Exception:
        pass
    return None


changes = {}
for key, url in WATCH.items():
    try:
        t = text(url)
    except Exception:
        continue
    h = hashlib.sha256(t.encode()).hexdigest()
    f = SNAP / f"{key}.json"
    old = json.loads(f.read_text()) if f.exists() else None
    f.write_text(json.dumps({"hash": h, "text": t[:100000]}))
    if old and old["hash"] != h:
        a, b = set(re.split(r"(?<=[.!?])\s+", old["text"])), re.split(r"(?<=[.!?])\s+", t)
        new_sent = [s for s in b if s not in a][:25]
        changes[key] = {"url": url, "new_or_changed_sentences": new_sent}

ew = econ_wake()
if not changes and not ew:
    skip()
    sys.exit(0)
if gate("scout", 0.01) is None:
    skip()
    sys.exit(0)
ctx = {"changed_sources": changes}
if ew:
    ctx["economic"] = {k: ew.get(k) for k in (
        "urgent", "recovery_lever", "open_critical", "pending_handoff", "sla_breach",
        "prelive_block", "ops_directives", "warnings", "treasury", "meaningful",
    ) if k in ew}
    ctx["wake_reason"] = "url_diff+economic" if changes else "economic_telemetry"
wake(ctx)
