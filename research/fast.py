"""Fast simulator for the breakout-trend family. Same rules as backtest/engine.py + runner/strategies.py,
but indicators are computed once over the whole series instead of on a 600-bar window every candle.
tests/test_research.py checks it makes the same trades as the slow engine.
"""
from backtest.engine import FEE, SLIPPAGE
from runner import indicators as ind
from runner.strategies import WARMUP


def _sma(values, n):
    out, s = [None] * len(values), 0.0
    for i, v in enumerate(values):
        s += v
        if i >= n:
            s -= values[i - n]
        if i >= n - 1:
            out[i] = s / n
    return out


def breakout_trades(bars, lookback=20, trend_len=200, stop_atr=2.0, trail_atr=3.0, exit_ema=50,
                    fee=FEE, slippage=SLIPPAGE, trace=False):
    c = [b["c"] for b in bars]
    a = ind.atr(bars, 14)
    e = ind.ema(c, exit_ema)
    sma = _sma(c, trend_len)
    hh = ind.highest([b["h"] for b in bars], lookback)
    warm = max(WARMUP, trend_len + 5)
    trades, i, n = [], 0, len(bars)
    while i < n - 1:
        if i + 1 < warm or hh[i] is None or a[i] is None or not (c[i] > hh[i] and c[i] > sma[i]):
            i += 1
            continue
        k = i + 1
        entry = bars[k]["o"] * (1 + slippage)
        stop, peak = entry - stop_atr * a[i], entry
        stops, exit_px, reason, j = [], None, None, k
        while j < n:
            b = bars[j]
            if trace:
                stops.append((b["t"], stop))
            if b["l"] <= stop:
                exit_px, reason = min(stop, b["o"]) * (1 - slippage), "stop"
                break
            peak = max(peak, c[j])
            if e[j] is not None and c[j] < e[j]:
                exit_px, reason = c[j] * (1 - slippage), "signal"
                break
            stop = max(stop, peak - trail_atr * a[j])
            j += 1
        if exit_px is None:
            break
        t = {"entry_time": bars[k]["t"], "exit_time": bars[j]["t"], "entry": entry, "exit": exit_px,
             "reason": reason, "ret": (exit_px * (1 - fee)) / (entry * (1 + fee)) - 1, "bars": j - k + 1}
        if trace:
            t.update(stops=stops, why_in={"close": c[i], "high_n": hh[i], "sma": sma[i], "atr": a[i]},
                     why_out={"close": c[j], "ema": e[j], "stop": stops[-1][1] if stops else stop})
        trades.append(t)
        i = j + 1
    return trades
