"""Settings for the paper runner. Change STRATEGY after a strategy passes the backtest gate."""
STRATEGY = "trend_pullback"     # one of runner.strategies.STRATEGIES
SYMBOL = "BTC/USD"
TIMEFRAME = "4Hour"
BAR_SECONDS = 4 * 3600
POSITION_PCT = 0.25             # share of paper equity per trade
MAX_NOTIONAL = 25_000.0         # hard cap per trade in USD
MAX_ENTRIES_PER_DAY = 3         # safety cap, far above what the strategies normally do
