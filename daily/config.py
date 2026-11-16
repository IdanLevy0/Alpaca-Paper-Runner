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
from daily.strategies import FABER5
from stockbot.config import SYMBOLS as STOCKS_100

SLEEVES = [
    # 2026-11-16 Idan: use the whole paper account. Fixed slices ("pct"), no volatility cap. With H001 at 20%
    # (stockbot/config.py BUDGET_PCT) the four add up to 100%. None of these passed every research gate.
    {"card": "E001", "variant": "trend_sma200_month", "stage": "learning", "vol": 0.062, "pct": 0.30, "universe": FABER5},
    {"card": "E002", "variant": "lowvol_n10_l60", "stage": "learning", "vol": 0.134, "pct": 0.40,
     "universe": list(STOCKS_100)},
    {"card": "B003", "variant": "btc_tom_m4_p2", "stage": "learning", "vol": 0.278, "pct": 0.10, "universe": ["BTC/USD"]},
]
