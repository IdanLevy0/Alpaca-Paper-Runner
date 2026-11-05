"""Bar-by-bar backtest that calls the same signal and manage functions the live runner uses.

Rules (written down so live behaviour can be compared):
- Signal judged at the close of bar i on bars[i-LOOKBACK+1 .. i]. Entry at the OPEN of bar i+1, plus slippage.
- Stop (and target, if any) set at entry from the signal's distances.
- Each bar from entry on: if low <= stop, exit at the stop (at the open if it opened below). Else if a target
  exists and high >= target, exit at the target. Stop is assumed first if both happen in one bar.
- At each bar's close: strategies with a manager may raise the stop (applies from the next bar) or exit at the
  close. Strategies with max_bars exit at the close of the bar that completes max_bars.
- Fee on each side; one position at a time; no new entry on the exit bar.
"""
from runner.strategies import LOOKBACK, MANAGERS

FEE = 0.0025       # Alpaca crypto taker, tier 1 (0.25% per side)
SLIPPAGE = 0.0005  # 0.05% assumed on market entries and stop/close exits


def run(bars, signal_fn, fee=FEE, slippage=SLIPPAGE, manager=None, trace=False):
    """trace=True adds per-trade 'stops' [(bar time, stop in force that bar)] and 'target' for the replay viewer."""
    if manager is None:
        manager = next((m for k, m in MANAGERS.items() if getattr(signal_fn, "__name__", "") == k), None)
    trades, i, n = [], 0, len(bars)
    while i < n - 1:
        sig = signal_fn(bars[max(0, i - LOOKBACK + 1):i + 1])
        if not sig:
            i += 1
            continue
        e = i + 1
        entry = bars[e]["o"] * (1 + slippage)
        trade = {"entry": entry, "stop": entry - sig["stop_dist"]}
        target = entry + sig["target_dist"] if sig.get("target_dist") else None
        max_bars = sig.get("max_bars")
        exit_px = reason = None
        stops = []
        j = e
        while j < n:
            b = bars[j]
            if trace:
                stops.append((b["t"], trade["stop"]))
            if b["l"] <= trade["stop"]:
                exit_px, reason = min(trade["stop"], b["o"]) * (1 - slippage), "stop"
                break
            if target is not None and b["h"] >= target:
                exit_px, reason = target, "target"
                break
            if manager:
                m = manager(bars[max(0, j - LOOKBACK + 1):j + 1], trade)
                if m["exit"]:
                    exit_px, reason = b["c"] * (1 - slippage), "signal"
                    break
                trade["stop"] = m["stop"]
            if max_bars and j - e + 1 >= max_bars:
                exit_px, reason = b["c"] * (1 - slippage), "time"
                break
            j += 1
        if exit_px is None:      # ran out of data with the trade still open: skip it
            break
        ret = (exit_px * (1 - fee)) / (entry * (1 + fee)) - 1
        t = {"entry_time": bars[e]["t"], "exit_time": bars[j]["t"], "entry": entry,
             "exit": exit_px, "reason": reason, "ret": ret}
        if trace:
            t.update(stops=stops, target=target, initial_stop=stops[0][1] if stops else trade["stop"])
        trades.append(t)
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
