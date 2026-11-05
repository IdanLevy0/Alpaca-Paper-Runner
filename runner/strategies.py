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


def breakout_trend(bars):
    """Rebuilt from the Trader.dev S38/S62 family (R2-09): Donchian-20 breakout in an uptrend, let winners run.
    Entry: close > highest high of the prior 20 candles AND close > SMA200.
    Initial stop 2 ATR below entry. No fixed target or time limit: exits come from manage_breakout_trend."""
    if len(bars) < WARMUP:
        return None
    closes, a = _prep(bars)
    sma200 = sum(closes[-200:]) / 200
    hh = ind.highest([b["h"] for b in bars], 20)[-1]
    if None in (hh, a[-1]):
        return None
    if closes[-1] > hh and closes[-1] > sma200:
        return {"stop_dist": 2.0 * a[-1], "target_dist": None, "max_bars": None}
    return None


def manage_breakout_trend(bars, trade):
    """Called at each candle close while in the trade. Stop trails 3 ATR below the highest close since entry
    (never moves down). Exit at the close if it falls below EMA50."""
    closes, a = _prep(bars)
    e50 = ind.ema(closes, 50)[-1]
    trade["peak_close"] = max(trade.get("peak_close", trade["entry"]), closes[-1])
    new_stop = max(trade["stop"], trade["peak_close"] - 3.0 * a[-1])
    return {"stop": new_stop, "exit": e50 is not None and closes[-1] < e50}


def explain_breakout_trend(bars):
    """One line for the run log: how close the last closed candle is to a breakout_trend entry."""
    if len(bars) < WARMUP:
        return f"only {len(bars)} bars, need {WARMUP}"
    closes = [b["c"] for b in bars]
    c, sma200 = closes[-1], sum(closes[-200:]) / 200
    hh = ind.highest([b["h"] for b in bars], 20)[-1]
    gap = (hh / c - 1) * 100
    trend = "yes" if c > sma200 else f"no, {(sma200 / c - 1) * 100:.1f}% below"
    brk = "yes" if c > hh else f"needs +{gap:.1f}%"
    return f"close {c:,.0f} | 20-bar high {hh:,.0f} ({brk}) | above SMA200 {sma200:,.0f}: {trend}"


EXPLAIN = {"breakout_trend": explain_breakout_trend}

# Strategies with candle-close exit management. Others use fixed stop/target/time only.
MANAGERS = {"breakout_trend": manage_breakout_trend}

STRATEGIES = {
    "breakout_trend": breakout_trend,
    "trend_pullback": trend_pullback,
    "donchian_breakout": donchian_breakout,
    "thrust_long": thrust_long,
}
