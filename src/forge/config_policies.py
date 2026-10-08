"""Operator/founder policy constants (not secrets)."""
SPOT_MODE = "PAPER_REAL_MARKET_SIM_MONEY"  # directional Coinbase spot stays PAPER until fee-aware forward +EV
PRIMARY_TRUE_NET_USD_PER_H = 1.0
DIAGNOSTIC_PROGRESS_USD_PER_H = 0.50
# Kalshi eventual LIVE micro-pilot caps (PAPER until founder LIVE auth)
KALSHI_LIVE_MAX_OPEN_COST_PER_MARKET_USD = 3.0
KALSHI_LIVE_MAX_AGGREGATE_OPEN_COST_USD = 5.0

# Inference — spend wisely, not capped. DeepSeek Thinking: medium | high | max
# "extra_high" / "xhigh" are aliases for DeepSeek max (highest spend we use).
INFERENCE_DEFAULT_EFFORT = "medium"
INFERENCE_EFFORTS = frozenset({"medium", "high", "extra_high", "xhigh", "max"})
# Roles whose *scheduled hard jobs* default to HIGH (not everyday chat)
INFERENCE_HIGH_ROLES = frozenset({
    "governor", "cyrus", "alpha_inventor", "quinn", "adversary", "vale",
    "critic", "ada", "rail_hunter", "sloane", "architect", "mira", "eng", "rowan",
})
# Luke/ops everyday = MEDIUM; escalate by trigger/complexity, not by role alone
INFERENCE_CHAT_ROLES = frozenset({"ops", "luke"})

RED_ZONE_NAV_USD = 50.0
TRIAL_8H_HOURS = 8.0
MODE_LABEL_PAPER = "PAPER — REAL MARKET / SIMULATED MONEY"
MODE_LABEL_LIVE = "LIVE — REAL MARKET / REAL MONEY"
