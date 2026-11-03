"""Bar-by-bar backtest that calls the same signal functions the live runner uses.

Rules (written down so live behaviour can be compared):
- Signal judged at the close of bar i on bars[i-LOOKBACK+1 .. i]. Entry at the OPEN of bar i+1, plus slippage.
- Stop and target are fixed at entry from the signal's distances.
- From the entry bar on: if a bar's low <= stop, exit at the stop (if the bar opened below it, at the open).
  Else if high >= target, exit at the target. If both happen in one bar, the stop is assumed first.
- Time exit at the close of the bar that completes max_bars.
- Fee on each side; one position at a time; no new entry on the exit bar.
"""
from runner.strategies import LOOKBACK

FEE = 0.0025       # Alpaca crypto taker, tier 1 (0.25% per side)
SLIPPAGE = 0.0005  # 0.05% assumed on market entries and stop/time exits


def run(bars, signal_fn, fee=FEE, slippage=SLIPPAGE):
    trades, i, n = [], 0, len(bars)
    while i < n - 1:
        sig = signal_fn(bars[max(0, i - LOOKBACK + 1):i + 1])
        if not sig:
            i += 1
            continue
        e = i + 1
        entry = bars[e]["o"] * (1 + slippage)
        stop, target = entry - sig["stop_dist"], entry + sig["target_dist"]
        exit_px, reason, j = None, None, e
        last = min(n - 1, e + sig["max_bars"] - 1)
        for j in range(e, last + 1):
            b = bars[j]
            if b["l"] <= stop:
                exit_px, reason = min(stop, b["o"]) * (1 - slippage), "stop"
                break
            if b["h"] >= target:
                exit_px, reason = target, "target"
                break
        if exit_px is None:
            if last < e + sig["max_bars"] - 1:   # ran out of data: trade still open, skip it
                break
            exit_px, reason, j = bars[last]["c"] * (1 - slippage), "time", last
        ret = (exit_px * (1 - fee)) / (entry * (1 + fee)) - 1
        trades.append({"entry_time": bars[e]["t"], "exit_time": bars[j]["t"], "entry": entry,
                       "exit": exit_px, "reason": reason, "ret": ret})
        i = j + 1
    return trades


def summarize(trades):
    if not trades:
        return {"trades": 0, "return_pct": 0.0, "pf": 0.0, "win_rate": 0.0, "max_dd_pct": 0.0}
    eq, peak, mdd, gp, gl, wins = 1.0, 1.0, 0.0, 0.0, 0.0, 0
    for t in trades:
        eq *= 1 + t["ret"]
        peak = max(peak, eq)
        mdd = max(mdd, 1 - eq / peak)
        if t["ret"] > 0:
            gp += t["ret"]; wins += 1
        else:
            gl -= t["ret"]
    return {"trades": len(trades), "return_pct": (eq - 1) * 100, "pf": gp / gl if gl else float("inf"),
            "win_rate": wins / len(trades) * 100, "max_dd_pct": mdd * 100}
