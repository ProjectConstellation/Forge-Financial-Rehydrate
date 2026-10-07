"""Strategy Genome + DSL (DOSSIER §12, DIRECTIVE §14) — FORGE's core proprietary IP.

A strategy is declarative DNA built from whitelisted primitives. It can be mutated, crossed,
hashed, versioned, and audited; it is compiled into vectorized signal arrays by `compile_entries`.
No LLM-written code ever executes live: DeepSeek proposes genomes, the validator + backtester judge.
"""

from __future__ import annotations

import hashlib
import json
from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from forge.features.engine import FEATURE_DOCS, MICRO_FEATURES
from forge.regime.engine import REGIMES

Op = Literal["gt", "lt", "between", "outside", "rising", "falling"]
ALLOWED_FEATURES = set(FEATURE_DOCS) - set(MICRO_FEATURES)   # bar features (backtestable)
LIVE_ONLY = set(MICRO_FEATURES)


class Condition(BaseModel):
    model_config = ConfigDict(frozen=True)
    f: str                                  # feature name
    op: Op
    v: float = 0.0
    v2: float | None = None                 # upper bound for between/outside
    lookback: int = 1                       # for rising/falling: compare with value `lookback` bars ago

    @field_validator("f")
    @classmethod
    def _known(cls, v: str) -> str:
        if v not in ALLOWED_FEATURES and v not in LIVE_ONLY:
            raise ValueError(f"unknown feature {v!r}")
        return v

    @model_validator(mode="after")
    def _bounds(self) -> Condition:
        if self.op in ("between", "outside") and (self.v2 is None or self.v2 <= self.v):
            raise ValueError("between/outside require v2 > v")
        if not 1 <= self.lookback <= 96:
            raise ValueError("lookback must be in [1, 96]")
        return self


class EntryLogic(BaseModel):
    all: list[Condition] = Field(default_factory=list)
    any: list[Condition] = Field(default_factory=list)
    min_any: int = 1

    @model_validator(mode="after")
    def _non_empty(self) -> EntryLogic:
        if not self.all and not self.any:
            raise ValueError("entry needs at least one condition")
        if len(self.all) + len(self.any) > 12:
            raise ValueError("entry too complex (max 12 conditions) — complexity penalty")
        return self


class ExitLogic(BaseModel):
    tp_atr: float = Field(2.0, ge=0.3, le=20)        # take-profit distance in ATR(14) units
    sl_atr: float = Field(1.5, ge=0.3, le=15)        # stop distance in ATR units
    tp_min_pct: float = Field(0.015, ge=0.0, le=0.5)  # never target less than this (fee hurdle)
    sl_max_pct: float = Field(0.06, ge=0.003, le=0.3)  # cap on stop distance
    time_stop_bars: int = Field(48, ge=2, le=2016)
    trail_atr: float | None = Field(None, ge=0.3, le=15)
    exit_all: list[Condition] = Field(default_factory=list)   # signal-decay exit (all true → exit)
    # Profit Lock Intelligence (operator directive): once a trade has covered its round-trip costs, the stop jumps to
    # breakeven-plus-fees (a winner can never become a loss) and then ratchets to lock a fraction of peak profit.
    be_trigger_pct: float = Field(0.022, ge=0.004, le=0.08)   # MANDATORY (operator rule): tunable, never removable
    be_buffer_pct: float = Field(0.015, ge=0.012, le=0.1)     # stop level above entry once armed (≥ round-trip fees)
    lock_frac: float = Field(0.5, ge=0.25, le=0.95)           # keep at least this share of the max favorable excursion

    @field_validator("be_trigger_pct", "lock_frac", mode="before")
    @classmethod
    def _lock_mandatory(cls, v: object, info: object) -> object:
        if v is None:                                          # legacy/evolved genomes that disabled the lock
            return 0.022 if getattr(info, "field_name", "") == "be_trigger_pct" else 0.5
        return v


class Execution(BaseModel):
    entry: Literal["maker", "taker"] = "maker"
    maker_offset_bps: float = Field(5.0, ge=0.0, le=300.0)   # limit below last close
    maker_ttl_bars: int = Field(3, ge=1, le=48)
    exit_tp: Literal["maker", "taker"] = "maker"
    max_spread_bps: float = Field(30.0, ge=0.5, le=500.0)


class Sizing(BaseModel):
    model: Literal["kelly", "fixed"] = "kelly"
    kelly_mult: float = Field(0.35, ge=0.05, le=1.0)
    max_fraction: float = Field(0.5, ge=0.01, le=1.0)
    fixed_fraction: float = Field(0.2, ge=0.01, le=1.0)


class Universe(BaseModel):
    symbols: list[str] | Literal["dynamic"] = "dynamic"
    min_volume_usd: float = 2_000_000.0
    max_spread_bps: float = 25.0


class Genome(BaseModel):
    id: str
    family: str
    generation: int = 0
    parents: list[str] = Field(default_factory=list)
    hypothesis: str
    interval_s: int = 300
    universe: Universe = Universe()
    regimes_allow: list[str] = Field(default_factory=list)   # empty = any
    regimes_deny: list[str] = Field(default_factory=list)
    min_regime_prob: float = Field(0.0, ge=0.0, le=1.0)
    entry: EntryLogic
    exit: ExitLogic = ExitLogic()
    execution: Execution = Execution()
    sizing: Sizing = Sizing()
    cooldown_bars: int = Field(6, ge=0, le=2016)
    meta_min_prob: float = Field(0.0, ge=0.0, le=0.99)       # calibrated P(win) gate when a meta-model exists
    expected_behavior: str = ""
    known_failure_modes: list[str] = Field(default_factory=list)
    origin: str = "seed"                                      # seed | mutation | crossover | llm | resurrection

    @field_validator("regimes_allow", "regimes_deny")
    @classmethod
    def _regimes(cls, v: list[str]) -> list[str]:
        bad = [r for r in v if r not in REGIMES]
        if bad:
            raise ValueError(f"unknown regimes {bad}")
        return v

    def dna(self) -> dict:
        """Trading-relevant content only (identity/narrative excluded) — defines behavior."""
        return self.model_dump(mode="json", exclude={"id", "generation", "parents", "hypothesis",
                                                     "expected_behavior", "known_failure_modes", "origin"})

    def dna_hash(self) -> str:
        return hashlib.sha256(json.dumps(self.dna(), sort_keys=True).encode()).hexdigest()[:16]

    def features_used(self) -> set[str]:
        conds = [*self.entry.all, *self.entry.any, *self.exit.exit_all]
        return {c.f for c in conds} | {"atr_14"}

    def live_only(self) -> bool:
        return bool(self.features_used() & LIVE_ONLY)

    def complexity(self) -> int:
        return len(self.entry.all) + len(self.entry.any) + len(self.exit.exit_all) + \
            len(self.regimes_allow) + len(self.regimes_deny) + (1 if self.exit.trail_atr else 0)


# ---- compiler -------------------------------------------------------------------------------------
def _cond(c: Condition, f: dict[str, np.ndarray]) -> np.ndarray:
    x = f.get(c.f)
    if x is None:
        raise KeyError(c.f)
    with np.errstate(invalid="ignore"):
        if c.op == "gt":
            m = x > c.v
        elif c.op == "lt":
            m = x < c.v
        elif c.op == "between":
            m = (x >= c.v) & (x <= c.v2)
        elif c.op == "outside":
            m = (x < c.v) | (x > c.v2)
        else:
            prev = np.full(len(x), np.nan)
            prev[c.lookback:] = x[:-c.lookback]
            m = (x > prev + c.v) if c.op == "rising" else (x < prev - c.v)
    return m & np.isfinite(x)


def compile_entries(g: Genome, f: dict[str, np.ndarray], probs: dict[str, np.ndarray] | None) -> np.ndarray:
    n = len(next(iter(f.values())))
    m = np.ones(n, dtype=bool)
    for c in g.entry.all:
        m &= _cond(c, f)
    if g.entry.any:
        cnt = np.zeros(n, dtype=int)
        for c in g.entry.any:
            cnt += _cond(c, f)
        m &= cnt >= g.entry.min_any
    if probs is not None:
        if g.regimes_allow:
            pa = np.sum([probs[r] for r in g.regimes_allow], axis=0)
            m &= pa >= max(g.min_regime_prob, 1e-9)
        if g.regimes_deny:
            pd = np.sum([probs[r] for r in g.regimes_deny], axis=0)
            m &= pd < 0.5
    atr = f["atr_14"]
    m &= np.isfinite(atr)
    return m


def compile_exit_signal(g: Genome, f: dict[str, np.ndarray]) -> np.ndarray | None:
    if not g.exit.exit_all:
        return None
    n = len(next(iter(f.values())))
    m = np.ones(n, dtype=bool)
    for c in g.exit.exit_all:
        m &= _cond(c, f)
    return m


def barrier_pcts(g: Genome, atr_frac: float) -> tuple[float, float]:
    """Take-profit / stop distances (fractions) for a given ATR/close, applying floors and caps."""
    tp = max(g.exit.tp_atr * atr_frac, g.exit.tp_min_pct)
    sl = min(max(g.exit.sl_atr * atr_frac, 0.002), g.exit.sl_max_pct)
    return tp, sl
