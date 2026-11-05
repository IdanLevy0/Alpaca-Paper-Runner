"""Statistics for judging a backtest. Pure Python so the GitHub runner needs no extra packages."""
import math
import random


def equity_stats(trades, years):
    """Compounded return, max drawdown, profit factor, trades per year, from a list of trades with 'ret'."""
    eq, peak, mdd, gp, gl, wins = 1.0, 1.0, 0.0, 0.0, 0.0, 0
    for t in trades:
        eq *= 1 + t["ret"]
        peak = max(peak, eq)
        mdd = max(mdd, 1 - eq / peak)
        if t["ret"] > 0:
            gp += t["ret"]; wins += 1
        else:
            gl -= t["ret"]
    n = len(trades)
    return {"trades": n, "return_pct": (eq - 1) * 100,
            "cagr_pct": (eq ** (1 / years) - 1) * 100 if years > 0 and eq > 0 else 0.0,
            "max_dd_pct": mdd * 100, "pf": gp / gl if gl else (float("inf") if gp else 0.0),
            "win_rate": wins / n * 100 if n else 0.0, "per_year": n / years if years else 0.0}


def bootstrap_pvalue(rets, n_boot=5000, seed=7):
    """One-sided p-value for 'average trade return > 0'. Shift returns to mean 0 (the null), resample,
    and count how often chance alone gives an average at least as good as the real one.
    Also returns a 90% interval for the average trade return (in %)."""
    if len(rets) < 5:
        return {"p": None, "lo": None, "hi": None}
    rnd, m = random.Random(seed), sum(rets) / len(rets)
    centered = [r - m for r in rets]
    n, hits, means = len(rets), 0, []
    for _ in range(n_boot):
        if sum(rnd.choice(centered) for _ in range(n)) / n >= m:
            hits += 1
        means.append(sum(rnd.choice(rets) for _ in range(n)) / n)
    means.sort()
    return {"p": hits / n_boot, "lo": means[int(0.05 * n_boot)] * 100, "hi": means[int(0.95 * n_boot)] * 100}


def random_entry_percentile(bars, trades, fee, slippage, n_sims=500, seed=11):
    """Is the entry rule better than luck? Re-run the same number of trades with the same holding times,
    entered at random candles. Returns the percentile of the real total return among the random ones."""
    if not trades:
        return None
    rnd, n = random.Random(seed), len(bars)
    holds = [t["bars"] for t in trades]
    real = sum(math.log(1 + t["ret"]) for t in trades)
    beats = 0
    for _ in range(n_sims):
        tot = 0.0
        for h in holds:
            k = rnd.randrange(250, max(251, n - h - 1))
            ent = bars[k]["o"] * (1 + slippage)
            ex = bars[min(n - 1, k + h - 1)]["c"] * (1 - slippage)
            tot += math.log((ex * (1 - fee)) / (ent * (1 + fee)))
        beats += real > tot
    return beats / n_sims * 100
