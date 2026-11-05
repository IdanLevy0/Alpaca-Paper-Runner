"""Research report for the breakout-trend family.

Answers four questions per coin: is it robust (settings grid), is it luck (bootstrap + random entries),
does it beat simple (buy-and-hold, 200-day average filter), does it generalize (in-sample vs later years, other coins).

Run:  python -m research.run_research [--refresh]
Writes RESEARCH_REPORT.md and research/out/replay.html (open it in a browser).
"""
import itertools
import json
import os
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from backtest.engine import FEE, SLIPPAGE                       # noqa: E402
from research.fast import breakout_trades                      # noqa: E402
from research.stats import equity_stats, bootstrap_pvalue, random_entry_percentile  # noqa: E402

SYMBOLS = ["BTC/USD", "ETH/USD", "SOL/USD"]
START = "2021-01-01"            # results counted from here; earlier candles only warm up indicators
SPLIT = "2024-01-01"            # in-sample before, out-of-sample from here
BASE = {"lookback": 20, "trend_len": 200, "stop_atr": 2.0, "trail_atr": 3.0, "exit_ema": 50}
GRID = {"lookback": [10, 20, 30, 55], "stop_atr": [1.5, 2.0, 3.0], "trail_atr": [2.0, 3.0, 4.0, 5.0],
        "exit_ema": [20, 50, 100]}
SMA_FILTER_LEN = 1200           # 200 days of 4h candles
MIN_TRADES_IS = 30


def years_between(a, b):
    f = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))
    return (f(b) - f(a)).days / 365.25


def after(trades, start, end=None):
    return [t for t in trades if t["entry_time"] >= start and (end is None or t["entry_time"] < end)]


def benchmarks(bars, i0):
    """Buy-and-hold, and 'hold only while the close is above its 200-day average'.
    The filter decides at each candle close and trades at the next open, paying fee + slippage on every switch.
    Both equity series line up with bars[i0:]."""
    c, o, n = [b["c"] for b in bars], [b["o"] for b in bars], len(bars)
    bh_eq = [c[k] / o[i0] for k in range(i0, n)]
    sma, s = [None] * n, 0.0
    for k in range(n):
        s += c[k]
        if k >= SMA_FILTER_LEN:
            s -= c[k - SMA_FILTER_LEN]
        if k >= SMA_FILTER_LEN - 1:
            sma[k] = s / SMA_FILTER_LEN
    eq, pos, switches, f_eq = 1.0, False, 0, []
    for k in range(i0, n - 1):
        want = sma[k - 1] is not None and c[k - 1] > sma[k - 1]
        if want != pos:
            eq *= (1 - FEE) * (1 - SLIPPAGE)
            pos, switches = want, switches + 1
        if pos:
            eq *= o[k + 1] / o[k]
        f_eq.append(eq)
    f_eq.append(eq)
    return bh_eq, f_eq, switches


def dd(series):
    peak, m = series[0], 0.0
    for v in series:
        peak = max(peak, v)
        m = max(m, 1 - v / peak)
    return m * 100


def yearly(trades, bars, i0):
    out = {}
    for y in sorted({b["t"][:4] for b in bars[i0:]}):
        ty = [t for t in trades if t["entry_time"].startswith(y)]
        r = 1.0
        for t in ty:
            r *= 1 + t["ret"]
        yb = [b for b in bars if b["t"].startswith(y)]
        out[y] = {"ret": (r - 1) * 100, "n": len(ty), "bh": (yb[-1]["c"] / yb[0]["o"] - 1) * 100}
    return out


def analyze(symbol, bars):
    i0 = next(k for k, b in enumerate(bars) if b["t"] >= START)
    yrs = years_between(bars[i0]["t"], bars[-1]["t"])
    base_tr = after(breakout_trades(bars, **BASE, trace=True), START)
    st = equity_stats(base_tr, yrs)
    st["exposure_pct"] = sum(t["bars"] for t in base_tr) / (len(bars) - i0) * 100
    yr = yearly(base_tr, bars, i0)
    st["years_up"] = sum(1 for v in yr.values() if v["ret"] > 0)
    boot = bootstrap_pvalue([t["ret"] for t in base_tr])
    rnd = random_entry_percentile(bars, base_tr, FEE, SLIPPAGE)
    bh_eq, f_eq, switches = benchmarks(bars, i0)
    bh = {"return_pct": (bh_eq[-1] - 1) * 100, "cagr_pct": (bh_eq[-1] ** (1 / yrs) - 1) * 100, "max_dd_pct": dd(bh_eq)}
    fl = {"return_pct": (f_eq[-1] - 1) * 100, "cagr_pct": (max(f_eq[-1], 1e-9) ** (1 / yrs) - 1) * 100,
          "max_dd_pct": dd(f_eq), "switches_per_year": switches / yrs}

    yrs_is, yrs_oos = years_between(bars[i0]["t"], SPLIT + "T00:00:00Z"), years_between(SPLIT + "T00:00:00Z", bars[-1]["t"])
    grid = []
    keys = list(GRID)
    for combo in itertools.product(*GRID.values()):
        p = dict(BASE, **dict(zip(keys, combo)))
        tr = after(breakout_trades(bars, **p), START)
        g = equity_stats(tr, yrs)
        g["is"] = equity_stats(after(tr, START, SPLIT), yrs_is)
        g["oos"] = equity_stats(after(tr, SPLIT), yrs_oos)
        grid.append((p, g))
    eligible = [x for x in grid if x[1]["is"]["trades"] >= MIN_TRADES_IS] or grid
    best = max(eligible, key=lambda x: x[1]["is"]["pf"])
    base_g = next(g for p, g in grid if all(p[k] == BASE[k] for k in BASE))
    oos_pfs = sorted(g["oos"]["pf"] for _, g in grid)
    return {"symbol": symbol, "years": yrs, "start": bars[i0]["t"], "end": bars[-1]["t"], "base": st,
            "yearly": yr, "boot": boot, "random_pct": rnd, "bh": bh, "filter": fl, "grid": grid,
            "best": best, "base_g": base_g, "oos_median_pf": oos_pfs[len(oos_pfs) // 2],
            "trades": base_tr, "bars": bars[i0:], "bh_eq": bh_eq, "f_eq": f_eq}


def fmt_pf(x):
    return "inf" if x == float("inf") else f"{x:.2f}"


def verdict(r):
    b, out = r["base"], []
    p = r["boot"]["p"]
    if p is None:
        out.append("Too few trades to test for luck.")
    elif p < 0.05 and (r["random_pct"] or 0) >= 90:
        out.append(f"Evidence of a real edge: a result this good happens by chance about {p*100:.0f}% of the time.")
    elif p < 0.2:
        out.append(f"Weak evidence: chance alone gives a result this good {p*100:.0f}% of the time.")
    else:
        out.append(f"No evidence it beats luck: chance gives a result this good {p*100:.0f}% of the time.")
    beat_bh, beat_f = b["cagr_pct"] > r["bh"]["cagr_pct"], b["cagr_pct"] > r["filter"]["cagr_pct"]
    out.append(("Beats" if beat_bh else "Loses to") + " buy-and-hold on yearly return, and "
               + ("beats" if beat_f else "loses to") + " the simple 200-day-average filter.")
    if b["max_dd_pct"] < r["bh"]["max_dd_pct"]:
        out.append(f"Smaller worst drop than buy-and-hold ({b['max_dd_pct']:.0f}% vs {r['bh']['max_dd_pct']:.0f}%), "
                   f"while in the market {b['exposure_pct']:.0f}% of the time.")
    share = sum(1 for _, g in r["grid"] if g["pf"] >= 1.2) / len(r["grid"]) * 100
    out.append(f"{share:.0f}% of the {len(r['grid'])} nearby settings reach PF 1.2 "
               + ("(robust)." if share >= 50 else "(fragile: results depend on the exact settings)." if share < 20 else "(mixed)."))
    bp, bg = r["best"]
    out.append(f"Best settings picked on 2021-2023 (PF {fmt_pf(bg['is']['pf'])}) scored PF {fmt_pf(bg['oos']['pf'])} on 2024 onward; "
               f"the default scored {fmt_pf(r['base_g']['oos']['pf'])}. "
               + ("Picking the best past settings did not help." if bg["oos"]["pf"] <= r["base_g"]["oos"]["pf"] else "Picking the best past settings held up."))
    return out


def heat(r, rows, cols, fixed):
    pf = {}
    for p, g in r["grid"]:
        if all(p[k] == v for k, v in fixed.items()):
            pf[(p[rows], p[cols])] = g["pf"]
    L = [f"| {rows} \\ {cols} | " + " | ".join(str(c) for c in GRID[cols]) + " |",
         "|---|" + "---|" * len(GRID[cols])]
    for rv in GRID[rows]:
        L.append(f"| {rv} | " + " | ".join(fmt_pf(pf.get((rv, cv), 0)) for cv in GRID[cols]) + " |")
    return "\n".join(L)


def report(results):
    L = ["# Research report: breakout_trend", "",
         f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}. Long only, 4h candles, Alpaca data, "
         f"{FEE*100:.2f}% fee per side + {SLIPPAGE*100:.2f}% slippage. Results from {START}. "
         f"Default settings: 20-candle breakout above SMA200, 2 ATR stop, trail 3 ATR, exit below EMA50.", ""]
    L += ["## Summary", "", "| Coin | Strategy CAGR | Buy-hold CAGR | 200-day filter CAGR | Strategy max DD | Buy-hold max DD | PF | Trades/yr | Luck p-value | Beats random entries |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        b = r["base"]
        p = "n/a" if r["boot"]["p"] is None else f"{r['boot']['p']:.2f}"
        L.append(f"| {r['symbol']} | {b['cagr_pct']:+.1f}% | {r['bh']['cagr_pct']:+.1f}% | {r['filter']['cagr_pct']:+.1f}% | "
                 f"{b['max_dd_pct']:.0f}% | {r['bh']['max_dd_pct']:.0f}% | {fmt_pf(b['pf'])} | {b['per_year']:.0f} | {p} | "
                 f"{(r['random_pct'] or 0):.0f}% of random runs |")
    L += ["", "How to read: luck p-value under 0.05 is good evidence, over 0.2 means it could easily be chance. "
          "'Beats random entries' should be 90%+ for the entry rule to be adding anything.", ""]
    for r in results:
        L += [f"## {r['symbol']}", "", *[f"- {v}" for v in verdict(r)], "",
              "| Year | " + " | ".join(r["yearly"]) + " |", "|---|" + "---|" * len(r["yearly"]),
              "| Strategy | " + " | ".join(f"{v['ret']:+.1f}% ({v['n']})" for v in r["yearly"].values()) + " |",
              "| Buy-hold | " + " | ".join(f"{v['bh']:+.1f}%" for v in r["yearly"].values()) + " |", "",
              f"Average trade {r['boot']['lo'] or 0:+.2f}% to {r['boot']['hi'] or 0:+.2f}% (90% range). "
              f"Win rate {r['base']['win_rate']:.0f}%, in the market {r['base']['exposure_pct']:.0f}% of the time.", "",
              "Profit factor by breakout length and trail (stop 2 ATR, exit EMA50):", "",
              heat(r, "lookback", "trail_atr", {"stop_atr": 2.0, "exit_ema": 50}), "",
              "Profit factor by exit EMA and initial stop (breakout 20, trail 3 ATR):", "",
              heat(r, "exit_ema", "stop_atr", {"lookback": 20, "trail_atr": 3.0}), ""]
    return "\n".join(L)


def replay_payload(results):
    def secs(t):
        return int(datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp())
    out = {"fee": FEE, "params": BASE, "coins": {}}
    for r in results:
        bars = r["bars"]
        eq, curve = 1.0, [[secs(bars[0]["t"]), 1.0]]
        for t in r["trades"]:
            eq *= 1 + t["ret"]
            curve.append([secs(t["exit_time"]), round(eq, 5)])
        step = 6
        out["coins"][r["symbol"]] = {
            "candles": [[secs(b["t"]), round(b["o"], 2), round(b["h"], 2), round(b["l"], 2), round(b["c"], 2)] for b in bars],
            "trades": [{"in": secs(t["entry_time"]), "out": secs(t["exit_time"]), "entry": round(t["entry"], 2),
                        "exit": round(t["exit"], 2), "reason": t["reason"], "ret": round(t["ret"] * 100, 2), "bars": t["bars"],
                        "stops": [[secs(a), round(b, 2)] for a, b in t["stops"]],
                        "why_in": {k: round(v, 2) for k, v in t["why_in"].items()},
                        "why_out": {k: (round(v, 2) if v is not None else None) for k, v in t["why_out"].items()}}
                       for t in r["trades"]],
            "equity": curve,
            "bh": [[secs(bars[k]["t"]), round(r["bh_eq"][k], 5)] for k in range(0, len(bars), step)],
            "filter": [[secs(bars[k]["t"]), round(r["f_eq"][k], 5)] for k in range(0, len(bars), step)],
            "summary": {"cagr": round(r["base"]["cagr_pct"], 1), "bh_cagr": round(r["bh"]["cagr_pct"], 1),
                        "dd": round(r["base"]["max_dd_pct"], 1), "pf": round(min(r["base"]["pf"], 99), 2),
                        "trades": r["base"]["trades"], "win": round(r["base"]["win_rate"], 0),
                        "p": r["boot"]["p"], "verdict": verdict(r)},
        }
    return out


def write_replay(results, path):
    with open(os.path.join(ROOT, "research", "replay_template.html")) as f:
        html = f.read()
    data = json.dumps(replay_payload(results), separators=(",", ":"))
    with open(path, "w") as f:
        f.write(html.replace("/*__DATA__*/null", data))


def main(load):
    results = []
    for sym in SYMBOLS:
        try:
            bars = load(sym)
        except Exception as e:  # e.g. a coin with no data
            print(f"skipping {sym}: {type(e).__name__}")
            continue
        if len(bars) < 1500:
            print(f"skipping {sym}: only {len(bars)} candles")
            continue
        results.append(analyze(sym, bars))
    text = report(results)
    with open(os.path.join(ROOT, "RESEARCH_REPORT.md"), "w") as f:
        f.write(text + "\n")
    os.makedirs(os.path.join(ROOT, "research", "out"), exist_ok=True)
    write_replay(results, os.path.join(ROOT, "research", "out", "replay.html"))
    print(text)


if __name__ == "__main__":
    from backtest.run_backtest import load_bars
    main(lambda s: load_bars(s, refresh="--refresh" in sys.argv))
