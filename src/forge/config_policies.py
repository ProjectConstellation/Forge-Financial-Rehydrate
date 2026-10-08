"""Operator/founder policy constants (not secrets)."""
SPOT_MODE = "PAPER_REAL_MARKET_SIM_MONEY"  # directional Coinbase spot stays paper until fee-aware forward +EV
PRIMARY_TRUE_NET_USD_PER_H = 1.0
DIAGNOSTIC_PROGRESS_USD_PER_H = 0.50
# Kalshi eventual LIVE micro-pilot caps (PAPER until founder LIVE auth)
KALSHI_LIVE_MAX_OPEN_COST_PER_MARKET_USD = 3.0
KALSHI_LIVE_MAX_AGGREGATE_OPEN_COST_USD = 5.0
# Inference
INFERENCE_DEFAULT_EFFORT = "medium"
INFERENCE_HIGH_ROLES = frozenset({
    "ops", "luke", "governor", "cyrus", "alpha_inventor", "quinn", "adversary", "vale",
    "critic", "ada", "rail_hunter", "sloane", "architect", "mira", "eng", "rowan",
})
