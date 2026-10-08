"""Seed strategy families (DOSSIER §28, DIRECTIVE §21) — starting DNA, not sacred strategies.

Designed for the measured cost reality (Intro tier: maker 0.50%, taker 0.90%): multi-hour horizons,
maker-first entries, take-profit floors ≥ 1.5% so the round-trip fee hurdle (~1.0–1.4%) is cleared.
Evolution, DeepSeek, and Modal tournaments will mutate, specialize, cross and replace these.
"""

from __future__ import annotations

from forge.strategies.genome import Condition as C
from forge.strategies.genome import EntryLogic, Execution, ExitLogic, Genome, Sizing


def seed_genomes() -> list[Genome]:
    return [
        Genome(
            id="seed_momentum_ignition", family="momentum",
            hypothesis="Return acceleration confirmed by abnormal volume and efficient trend tends to continue for hours.",
            regimes_allow=["TREND_UP", "BREAKOUT_EXPANSION", "EUPHORIA_BUYING"], min_regime_prob=0.35,
            entry=EntryLogic(all=[C(f="ret_12", op="gt", v=0.012), C(f="rvol_12", op="gt", v=1.8),
                                  C(f="ema_gap", op="gt", v=0.0), C(f="er_24", op="gt", v=0.45)]),
            exit=ExitLogic(tp_atr=3.0, sl_atr=1.6, tp_min_pct=0.018, time_stop_bars=48, trail_atr=2.0),
            execution=Execution(entry="maker", maker_offset_bps=8, maker_ttl_bars=2),
            known_failure_modes=["late entry after exhaustion", "false breakouts in thin books"]),
        Genome(
            id="seed_squeeze_breakout", family="breakout",
            hypothesis="Volatility compression followed by a range break with volume expansion starts a directional leg.",
            regimes_allow=["BREAKOUT_EXPANSION", "TREND_UP", "RANGE_LOW_VOL"], min_regime_prob=0.3,
            entry=EntryLogic(all=[C(f="brk_hi_48", op="gt", v=0.0), C(f="vol_ratio", op="gt", v=1.3),
                                  C(f="rvol_12", op="gt", v=1.5)],
                             any=[C(f="vol_pct", op="lt", v=0.55), C(f="bb_width_pct", op="lt", v=0.35)]),
            exit=ExitLogic(tp_atr=3.5, sl_atr=1.5, tp_min_pct=0.02, time_stop_bars=72),
            execution=Execution(entry="maker", maker_offset_bps=5, maker_ttl_bars=2),
            known_failure_modes=["breakout failure / bull trap"]),
        Genome(
            id="seed_trend_pullback", family="trend_pullback",
            hypothesis="In established uptrends, short-term oversold pullbacks revert toward trend (buy the dip, with the trend).",
            regimes_allow=["TREND_UP"], min_regime_prob=0.3,
            entry=EntryLogic(all=[C(f="ema_gap_slow", op="gt", v=0.003), C(f="slope_96", op="gt", v=0.8),
                                  C(f="z_20", op="lt", v=-1.0), C(f="rsi_14", op="lt", v=0.42)]),
            exit=ExitLogic(tp_atr=2.5, sl_atr=2.0, tp_min_pct=0.016, time_stop_bars=96),
            execution=Execution(entry="maker", maker_offset_bps=12, maker_ttl_bars=4),
            known_failure_modes=["trend reversal disguised as pullback"]),
        Genome(
            id="seed_range_reversion", family="mean_reversion",
            hypothesis="In non-trending regimes, extreme deviations below the local mean revert (regime-vetoed).",
            regimes_allow=["RANGE_LOW_VOL", "RANGE_HIGH_VOL"], regimes_deny=["TREND_DOWN", "PANIC_SELLING"],
            min_regime_prob=0.35,
            entry=EntryLogic(all=[C(f="z_50", op="lt", v=-2.0), C(f="range_pos_48", op="lt", v=0.15),
                                  C(f="er_24", op="lt", v=0.3)]),
            exit=ExitLogic(tp_atr=2.0, sl_atr=2.5, tp_min_pct=0.015, time_stop_bars=72),
            execution=Execution(entry="maker", maker_offset_bps=15, maker_ttl_bars=4),
            known_failure_modes=["mean moving (regime transition)", "trend start"]),
        Genome(
            id="seed_panic_wick_catch", family="liquidity_provision",
            hypothesis="During liquidation cascades, deep resting bids get filled at dislocated prices that rebound (paid as maker).",
            regimes_allow=["PANIC_SELLING", "RANGE_HIGH_VOL"], min_regime_prob=0.25,
            entry=EntryLogic(all=[C(f="ret_12", op="lt", v=-0.035), C(f="rvol_12", op="gt", v=2.2),
                                  C(f="dd_288", op="lt", v=-0.05)]),
            exit=ExitLogic(tp_atr=3.0, sl_atr=3.0, tp_min_pct=0.025, sl_max_pct=0.08, time_stop_bars=96),
            execution=Execution(entry="maker", maker_offset_bps=80, maker_ttl_bars=6),
            sizing=Sizing(kelly_mult=0.25, max_fraction=0.35),
            known_failure_modes=["catching a falling knife in a genuine crash"]),
        Genome(
            id="seed_relative_strength", family="rotation",
            hypothesis="Assets with persistent beta-adjusted outperformance vs BTC keep outperforming over a day (cross-sectional momentum).",
            regimes_deny=["PANIC_SELLING", "TREND_DOWN"],
            entry=EntryLogic(all=[C(f="rs_btc_48", op="gt", v=0.03), C(f="ret_288", op="gt", v=0.02),
                                  C(f="ema_gap_slow", op="gt", v=0.0)]),
            exit=ExitLogic(tp_atr=5.0, sl_atr=2.5, tp_min_pct=0.03, time_stop_bars=288),
            execution=Execution(entry="maker", maker_offset_bps=10, maker_ttl_bars=6),
            cooldown_bars=48, known_failure_modes=["sector rotation reversal"]),
        Genome(
            id="seed_vwap_reclaim", family="momentum",
            hypothesis="Price reclaiming the daily VWAP with positive short-term momentum attracts continuation flow.",
            regimes_allow=["TREND_UP", "RANGE_LOW_VOL", "BREAKOUT_EXPANSION"], min_regime_prob=0.3,
            entry=EntryLogic(all=[C(f="vwap_dist_288", op="between", v=0.0, v2=0.006),
                                  C(f="vwap_dist_288", op="rising", v=0.002, lookback=6),
                                  C(f="ret_3", op="gt", v=0.002), C(f="ema_gap", op="gt", v=0.0)]),
            exit=ExitLogic(tp_atr=2.5, sl_atr=1.5, tp_min_pct=0.015, time_stop_bars=48),
            known_failure_modes=["chop around VWAP"]),
        Genome(
            id="seed_vol_expansion", family="volatility",
            hypothesis="A volatility regime shift upward with a new daily high marks the start of an impulsive move.",
            regimes_allow=["BREAKOUT_EXPANSION", "EUPHORIA_BUYING", "TREND_UP"], min_regime_prob=0.3,
            entry=EntryLogic(all=[C(f="vol_ratio", op="gt", v=1.6), C(f="ret_6", op="gt", v=0.008),
                                  C(f="brk_hi_288", op="gt", v=0.0)]),
            exit=ExitLogic(tp_atr=3.0, sl_atr=1.8, tp_min_pct=0.02, time_stop_bars=36, trail_atr=1.8),
            execution=Execution(entry="taker"),
            known_failure_modes=["blow-off top"]),
        Genome(
            id="seed_oversold_uptrend", family="mean_reversion",
            hypothesis="Deeply oversold RSI inside a slow uptrend marks temporary capitulation that reverts.",
            regimes_deny=["PANIC_SELLING", "TREND_DOWN"],
            entry=EntryLogic(all=[C(f="rsi_14", op="lt", v=0.3), C(f="ema_gap_slow", op="gt", v=0.0),
                                  C(f="dd_288", op="gt", v=-0.08)]),
            exit=ExitLogic(tp_atr=2.2, sl_atr=2.2, tp_min_pct=0.015, time_stop_bars=72),
            execution=Execution(entry="maker", maker_offset_bps=10, maker_ttl_bars=3),
            known_failure_modes=["trend break"]),
        Genome(
            id="seed_acceleration", family="momentum",
            hypothesis="Second-derivative (acceleration) of price with intraday trend support precedes multi-hour continuation.",
            regimes_allow=["TREND_UP", "BREAKOUT_EXPANSION"], min_regime_prob=0.3,
            entry=EntryLogic(all=[C(f="accel_6", op="gt", v=0.01), C(f="ret_24", op="gt", v=0.0),
                                  C(f="slope_24", op="gt", v=1.0)]),
            exit=ExitLogic(tp_atr=2.8, sl_atr=1.6, tp_min_pct=0.018, time_stop_bars=48),
            known_failure_modes=["news-driven spikes that fade"]),
    
        Genome(
            id="seed_maker_micro_edge", family="microstructure",
            hypothesis="Tight maker offset on liquid majors harvests micro-edge when spread wide vs fee (fee-aware).",
            regimes_allow=["RANGE_LOW_VOL", "RANGE_HIGH_VOL"], min_regime_prob=0.25,
            entry=EntryLogic(all=[C(f="bb_width_pct", op="gt", v=0.15), C(f="rvol_12", op="lt", v=2.0),
                                  C(f="er_24", op="lt", v=0.45)]),
            exit=ExitLogic(tp_atr=1.2, sl_atr=1.2, tp_min_pct=0.012, time_stop_bars=24),
            execution=Execution(entry="maker", maker_offset_bps=6, maker_ttl_bars=2),
            known_failure_modes=["adverse selection when informed flow arrives"]),
        Genome(
            id="seed_inventory_skew", family="inventory",
            hypothesis="Lean inventory with the short-term imbalance; exit when imbalance flips (execution alpha).",
            regimes_deny=["PANIC_SELLING"],
            entry=EntryLogic(all=[C(f="ret_3", op="gt", v=0.0015), C(f="rvol_12", op="gt", v=1.2),
                                  C(f="ema_gap", op="gt", v=0.0)]),
            exit=ExitLogic(tp_atr=1.8, sl_atr=1.4, tp_min_pct=0.012, time_stop_bars=18),
            execution=Execution(entry="maker", maker_offset_bps=10, maker_ttl_bars=2),
            known_failure_modes=["toxic flow"]),
        Genome(
            id="seed_slow_compounder", family="carry_proxy",
            hypothesis="Low-turnover maker entries on gentle uptrends; prioritize fee survival over excitement.",
            regimes_allow=["TREND_UP", "RANGE_LOW_VOL"], min_regime_prob=0.3,
            entry=EntryLogic(all=[C(f="slope_96", op="gt", v=0.5), C(f="vol_pct", op="lt", v=0.5),
                                  C(f="rsi_14", op="between", v=0.4, v2=0.6)]),
            exit=ExitLogic(tp_atr=4.0, sl_atr=2.0, tp_min_pct=0.02, time_stop_bars=144),
            execution=Execution(entry="maker", maker_offset_bps=12, maker_ttl_bars=6),
            known_failure_modes=["slow bleed in chop"]),
        Genome(
            id="seed_cross_section_lag", family="cross_asset",
            hypothesis="Lagged leaders vs BTC: buy laggards after leader impulse when beta-adjusted residual positive.",
            regimes_allow=["TREND_UP", "BREAKOUT_EXPANSION"], min_regime_prob=0.25,
            entry=EntryLogic(all=[C(f="rs_btc_48", op="lt", v=-0.01), C(f="ret_12", op="gt", v=0.0),
                                  C(f="rvol_12", op="gt", v=1.3)]),
            exit=ExitLogic(tp_atr=2.5, sl_atr=1.8, tp_min_pct=0.015, time_stop_bars=48),
            execution=Execution(entry="maker", maker_offset_bps=8, maker_ttl_bars=3),
            known_failure_modes=["leader already reversing"]),
        Genome(
            id="seed_event_gap_fade", family="event_driven",
            hypothesis="Fade overextended gaps when volume spikes but efficiency ratio stays low (exhaustion).",
            regimes_allow=["RANGE_HIGH_VOL", "EUPHORIA_BUYING"], min_regime_prob=0.2,
            entry=EntryLogic(all=[C(f="ret_6", op="gt", v=0.025), C(f="er_24", op="lt", v=0.35),
                                  C(f="rvol_12", op="gt", v=2.0)]),
            exit=ExitLogic(tp_atr=2.0, sl_atr=2.5, tp_min_pct=0.015, time_stop_bars=36),
            execution=Execution(entry="maker", maker_offset_bps=15, maker_ttl_bars=2),
            known_failure_modes=["news trend continuation"]),

    ]
