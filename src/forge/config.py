"""Typed FORGE configuration.

Layering (later wins): built-in defaults → config/base.yaml → config/<env>.yaml → FORGE_* env vars.
Secrets come only from the environment (prod: /etc/forge/forge.env via systemd EnvironmentFile;
dev: .env) and are held as SecretStr so they never render in logs/reprs.
"""

from __future__ import annotations

import os
from decimal import Decimal
from enum import StrEnum
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, SecretStr, field_validator, model_validator

REPO_ROOT = Path(__file__).resolve().parents[2]


class Mode(StrEnum):
    MOCK = "MOCK"        # fixture data, fake venue, deterministic
    REPLAY = "REPLAY"    # historical data, simulated execution
    SHADOW = "SHADOW"    # live data, would-be orders only
    PAPER = "PAPER"      # live data, persistent simulated account
    LIVE = "LIVE"        # real orders (requires FORGE_LIVE_TRADING=true + readiness gate)


class ReserveBelow100(BaseModel):
    normal_fraction: Decimal = Decimal("0.15")
    min_fraction: Decimal = Decimal("0.05")   # stricter rule of DIRECTIVE §6 wins: never 0
    max_fraction: Decimal = Decimal("0.20")


class ReserveAtOrAbove100(BaseModel):
    threshold_usd: Decimal = Decimal("100")
    hard_floor_usd: Decimal = Decimal("25")
    sticky: bool = True                       # once activated, the floor persists (RESOLUTIONS #4)
    extra_fraction_per_decade: Decimal = Decimal("0.02")  # reserve gets stricter as treasury grows


class TreasuryConfig(BaseModel):
    # OP-001: treasury = full balance of the configured portfolio (USD + held assets).
    # "fixed_cap" restores the original DOSSIER/DIRECTIVE $20 cap if the operator ever wants it.
    capital_mode: str = "full_account"          # full_account | fixed_cap
    capital_cap_usd: Decimal | None = None      # only used when capital_mode == fixed_cap
    initial_capital_usd: Decimal = Decimal("28.27")  # paper/mock seed = live balance at adoption
    external_injection_limit_usd: Decimal | None = None
    quote_currency: str = "USD"
    profit_reinvest: bool = True
    reserve_below_100: ReserveBelow100 = ReserveBelow100()
    reserve_at_or_above_100: ReserveAtOrAbove100 = ReserveAtOrAbove100()
    ops_profit_share_default: Decimal = Decimal("0.10")
    ops_profit_share_min: Decimal = Decimal("0.05")
    ops_profit_share_max: Decimal = Decimal("0.15")
    exit_fee_buffer_fraction: Decimal = Decimal("0.012")  # always kept to pay exits


class RiskConfig(BaseModel):
    leverage_enabled: bool = False
    stale_market_ms: int = 5_000
    max_open_positions: int = 3
    max_orders_per_minute: int = 6
    concentration_checklist_fraction: Decimal = Decimal("0.50")
    concentration_critic_fraction: Decimal = Decimal("0.80")
    kelly_fraction_min: Decimal = Decimal("0.10")
    kelly_fraction_max: Decimal = Decimal("0.50")
    daily_drawdown_breaker_fraction: Decimal = Decimal("0.15")
    max_slippage_bps_default: Decimal = Decimal("25")
    reject_breaker_count: int = 5
    allow_transfers: bool = False             # Stage-2 cash-out only; needs key can_transfer + allowlist
    transfer_allowlist: list[str] = Field(default_factory=list)


class ModalConfig(BaseModel):
    enabled: bool = True
    environment: str = "forge"
    monthly_budget_usd: Decimal = Decimal("30")
    warm_policy: str = "auto"                 # auto | off | on — auto = only if measured worth it
    cpu_core_second_usd: Decimal = Decimal("0.0000131")
    memory_gib_second_usd: Decimal = Decimal("0.00000222")
    job_timeout_s: int = 900
    max_parallel: int = 16


class ComputeConfig(BaseModel):
    local_target_vcpu: int = 2
    local_max_vcpu: int = 3
    process_workers: int = 2
    modal: ModalConfig = ModalConfig()


class ModelPrice(BaseModel):
    """USD per 1M tokens at PEAK; off-peak is 50% (verified 2026-10-06, OP-004)."""
    input_cache_hit: Decimal
    input_cache_miss: Decimal
    output: Decimal


class DeepSeekConfig(BaseModel):
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-flash"            # fast brain: high-frequency tool loops
    deep_model: str = "deepseek-flash"        # cheapest frontier; depth via effort=max, not Pro (cost discipline)
    deep_effort: str = "max"
    starting_budget_usd: Decimal = Decimal("5")
    prices: dict[str, ModelPrice] = Field(default_factory=lambda: {
        "deepseek-flash": ModelPrice(input_cache_hit=Decimal("0.006"), input_cache_miss=Decimal("0.30"),
                                     output=Decimal("1.20")),
        "deepseek-v4-pro": ModelPrice(input_cache_hit=Decimal("0.044"), input_cache_miss=Decimal("1.32"),
                                      output=Decimal("3.96")),
    })
    # Peak windows (UTC, Mon–Fri): 01–04 and 06–10. Everything else is off-peak (50% price).
    peak_windows_utc: list[tuple[int, int]] = Field(default_factory=lambda: [(1, 4), (6, 10)])
    timeout_s: float = 300.0
    max_concurrency: int = 8
    min_balance_reserve_usd: Decimal = Decimal("0.10")   # tiny floor: a session that dies mid-way wastes its spend (OP-014)
    spend_runway_days: float = 3.0                        # OP-014: pace ALL available credit over this runway (use it, don't hoard)


class CoinbaseConfig(BaseModel):
    enabled: bool = True
    rest_base: str = "https://api.coinbase.com"
    ws_url: str = "wss://advanced-trade-ws.coinbase.com"
    quote_currencies: list[str] = Field(default_factory=lambda: ["USD", "USDC"])
    universe_max: int = 60
    ws_symbols_max: int = 60
    default_maker_fee: Decimal = Decimal("0.005")   # verified Intro tier 2026-10-06
    default_taker_fee: Decimal = Decimal("0.009")


class VenuesConfig(BaseModel):
    coinbase: CoinbaseConfig = CoinbaseConfig()


class Secrets(BaseModel):
    deepseek_api_key: SecretStr | None = None
    modal_token_id: SecretStr | None = None
    modal_token_secret: SecretStr | None = None
    coinbase_key_name: SecretStr | None = None
    coinbase_key_secret: SecretStr | None = None

    def available(self) -> dict[str, bool]:
        return {
            "deepseek": self.deepseek_api_key is not None,
            "modal": self.modal_token_id is not None and self.modal_token_secret is not None,
            "coinbase": self.coinbase_key_name is not None and self.coinbase_key_secret is not None,
        }


class Settings(BaseModel):
    env: str = "development"
    mode: Mode = Mode.PAPER
    live_trading: bool = False
    home: Path = REPO_ROOT / ".devvar"
    api_host: str = "127.0.0.1"
    api_port: int = 8470
    log_level: str = "INFO"
    treasury: TreasuryConfig = TreasuryConfig()
    risk: RiskConfig = RiskConfig()
    compute: ComputeConfig = ComputeConfig()
    deepseek: DeepSeekConfig = DeepSeekConfig()
    venues: VenuesConfig = VenuesConfig()
    secrets: Secrets = Field(default_factory=Secrets, exclude=True)

    @field_validator("api_host")
    @classmethod
    def _localhost_only(cls, v: str) -> str:
        # DIRECTIVE §28 / DOSSIER §34.4: private during build. Public exposure is an operator action.
        if v not in ("127.0.0.1", "localhost", "::1"):
            raise ValueError("FORGE API must bind to localhost; public exposure requires operator action")
        return v

    @model_validator(mode="after")
    def _live_requires_flag(self) -> Settings:
        if self.mode == Mode.LIVE and not self.live_trading:
            raise ValueError("Mode LIVE requires FORGE_LIVE_TRADING=true")
        if self.risk.leverage_enabled:
            raise ValueError("Leverage is disabled in Phase 1 (DOSSIER §22.3)")
        if self.compute.local_max_vcpu > 3:
            raise ValueError("Local vCPU ceiling is 3")
        return self

    # ---- paths -------------------------------------------------------------------------------
    @property
    def state_dir(self) -> Path:
        return self.home / "state"

    @property
    def db_path(self) -> Path:
        return self.state_dir / "forge.sqlite"

    @property
    def audit_dir(self) -> Path:
        return self.home / "audit"

    @property
    def market_dir(self) -> Path:
        return self.home / "market"

    @property
    def research_dir(self) -> Path:
        return self.home / "research"

    @property
    def log_dir(self) -> Path:
        return self.home / "logs"

    @property
    def run_dir(self) -> Path:
        return self.home / "run"

    @property
    def backup_dir(self) -> Path:
        return self.home / "backups"

    def ensure_dirs(self) -> None:
        for p in (self.state_dir, self.audit_dir, self.market_dir, self.research_dir, self.log_dir,
                  self.run_dir, self.backup_dir):
            p.mkdir(parents=True, exist_ok=True)

    def redacted(self) -> dict[str, Any]:
        d = self.model_dump(mode="json")
        d["secrets_present"] = self.secrets.available()
        return d


def _deep_merge(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any]:
    out = dict(a)
    for k, v in b.items():
        out[k] = _deep_merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    data = yaml.safe_load(path.read_text()) or {}
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a mapping")
    return data


def _load_dotenv(path: Path) -> None:
    """Minimal .env loader for development (does not override existing env)."""
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        os.environ.setdefault(k.strip(), v)


def _secret(name: str) -> SecretStr | None:
    v = os.environ.get(name, "").strip()
    return SecretStr(v) if v else None


def _truthy(v: str | None) -> bool:
    return (v or "").strip().lower() in ("1", "true", "yes", "on")


def load_settings(config_dir: Path | None = None, **overrides: Any) -> Settings:
    config_dir = config_dir or REPO_ROOT / "config"
    _load_dotenv(REPO_ROOT / ".env")
    env = os.environ.get("FORGE_ENV", overrides.get("env", "development"))
    data = _deep_merge(_read_yaml(config_dir / "base.yaml"), _read_yaml(config_dir / f"{env}.yaml"))
    data["env"] = env
    if "FORGE_MODE" in os.environ:
        data["mode"] = os.environ["FORGE_MODE"]
    if "FORGE_HOME" in os.environ:
        data["home"] = os.environ["FORGE_HOME"]
    if "FORGE_API_PORT" in os.environ:
        data["api_port"] = int(os.environ["FORGE_API_PORT"])
    data["live_trading"] = _truthy(os.environ.get("FORGE_LIVE_TRADING"))
    data = _deep_merge(data, overrides)
    s = Settings.model_validate(data)
    s.secrets = Secrets(
        deepseek_api_key=_secret("DEEPSEEK_API_KEY"),
        modal_token_id=_secret("MODAL_TOKEN_ID"),
        modal_token_secret=_secret("MODAL_TOKEN_SECRET"),
        coinbase_key_name=_secret("COINBASE_CDP_API_KEY_NAME"),
        coinbase_key_secret=_secret("COINBASE_CDP_API_KEY_SECRET"),
    )
    return s
