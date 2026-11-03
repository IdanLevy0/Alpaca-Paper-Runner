"""Long-only BTC/USD strategies on 4h bars. Shared by the backtest and the live runner.

Each strategy's signal(bars) returns None or a dict:
  stop_dist, target_dist : price distances from the ENTRY price, fixed when the trade opens
  max_bars               : time exit after this many 4h bars
The signal is judged on the LAST bar in `bars`, which must be a completed bar.
"""
from runner import indicators as ind

WARMUP = 220     # bars needed before any signal
LOOKBACK = 600   # backtest and live both judge a signal on exactly the last 600 bars


def _prep(bars):
    closes = [b["c"] for b in bars]
    return closes, ind.atr(bars, 14)


def trend_pullback(bars):
    """Uptrend (close > EMA200) + short-term oversold (RSI2 < 10). Stop 2 ATR, target 3 ATR, 30 bars (5 days)."""
    if len(bars) < WARMUP:
        return None
    closes, a = _prep(bars)
    e200, r2 = ind.ema(closes, 200)[-1], ind.rsi(closes, 2)[-1]
    if None in (e200, r2, a[-1]):
        return None
    if closes[-1] > e200 and r2 < 10:
        return {"stop_dist": 2.0 * a[-1], "target_dist": 3.0 * a[-1], "max_bars": 30}
    return None


def donchian_breakout(bars):
    """Close breaks the prior 20-bar high while above EMA200. Stop 2 ATR, target 4 ATR, 60 bars (10 days)."""
    if len(bars) < WARMUP:
        return None
    closes, a = _prep(bars)
    e200, hh = ind.ema(closes, 200)[-1], ind.highest([b["h"] for b in bars], 20)[-1]
    if None in (e200, hh, a[-1]):
        return None
    if closes[-1] > hh and closes[-1] > e200:
        return {"stop_dist": 2.0 * a[-1], "target_dist": 4.0 * a[-1], "max_bars": 60}
    return None


def thrust_long(bars):
    """Range-expansion thrust (long side of log #30): bar range >= 1.8 ATR, close in top 25% of the bar,
    close > EMA100. Stop at the bar's low, target 2R, 24 bars (4 days)."""
    if len(bars) < WARMUP:
        return None
    closes, a = _prep(bars)
    e100, b = ind.ema(closes, 100)[-1], bars[-1]
    if None in (e100, a[-2]):
        return None
    rng = b["h"] - b["l"]
    if rng >= 1.8 * a[-2] and (b["c"] - b["l"]) >= 0.75 * rng and b["c"] > e100:
        risk = b["c"] - b["l"]
        return {"stop_dist": risk, "target_dist": 2.0 * risk, "max_bars": 24}
    return None


STRATEGIES = {
    "trend_pullback": trend_pullback,
    "donchian_breakout": donchian_breakout,
    "thrust_long": thrust_long,
}
