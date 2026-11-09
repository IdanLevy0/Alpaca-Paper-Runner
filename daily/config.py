"""Multi-strategy daily runner settings. PAPER ONLY.

Each sleeve is one frozen card variant with its own slice of the account. Slice = BUDGET[stage] x VOL_SCALE, where
stage comes from the research gates (daily/PROTOCOL.md) and VOL_SCALE = min(1, 10% / the variant's backtest volatility).
Orders are tagged "d-<card>-..." so each sleeve's results stay separate. Orders only when DAILY_ENABLED=true.
"""
BUDGET = {"holdout_pass": 0.25, "valid_pass": 0.15, "learning": 0.05}
VOL_TARGET = 0.10
MIN_ORDER_USD = 5.0          # skip dust trades smaller than this
REBALANCE_AFTER_ET = (9, 35)  # stock sleeves trade once a day, on the first pass after 09:35 ET
ORDER_PREFIX = "d-"

# card, variant name, stage, backtest annual volatility (train, after costs). Filled in from research results.
SLEEVES = []
