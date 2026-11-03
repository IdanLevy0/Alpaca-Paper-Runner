"""Backtest every strategy on Alpaca BTC/USD 4h bars, year by year, and apply the pass gate.

Run from the project folder:  py -3.12 -m backtest.run_backtest   (or python -m backtest.run_backtest)
Writes BACKTEST_RESULT.md and caches bars in backtest/bars_4h.json.
"""
import json
import os
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from runner.alpaca import fetch_crypto_bars           # noqa: E402
from runner.strategies import STRATEGIES               # noqa: E402
from backtest.engine import run, summarize, FEE        # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SYMBOLS = ["BTC/USD", "ETH/USD"]
YEARS = [2021, 2022, 2023, 2024, 2025, 2026]

# Pass gate, fixed before looking at results
GATE_MIN_YEARS_PROFITABLE = 4
GATE_MIN_PF = 1.2
GATE_MIN_TRADES_PER_YEAR = 25


def load_bars(symbol, refresh=False):
    cache = os.path.join(HERE, "bars_4h_" + symbol.replace("/", "") + ".json")
    if os.path.exists(cache) and not refresh:
        with open(cache) as f:
            return json.load(f)
    bars = fetch_crypto_bars(symbol, "4Hour", "2020-06-01T00:00:00Z",
                             key=os.environ.get("ALPACA_API_KEY"), secret=os.environ.get("ALPACA_SECRET_KEY"))
    now = datetime.now(timezone.utc).timestamp()
    bars = [b for b in bars if datetime.fromisoformat(b["t"].replace("Z", "+00:00")).timestamp() + 4 * 3600 <= now]
    with open(cache, "w") as f:
        json.dump(bars, f)
    return bars


def evaluate(bars):
    out = {}
    for name, fn in STRATEGIES.items():
        trades = run(bars, fn)
        per_year = {y: summarize([t for t in trades if t["entry_time"].startswith(str(y))]) for y in YEARS}
        allr = summarize([t for t in trades if t["entry_time"][:4] >= str(YEARS[0])])
        yrs_up = sum(1 for y in YEARS if per_year[y]["return_pct"] > 0)
        avg_trades = allr["trades"] / len(YEARS)
        passed = yrs_up >= GATE_MIN_YEARS_PROFITABLE and allr["pf"] >= GATE_MIN_PF and avg_trades >= GATE_MIN_TRADES_PER_YEAR
        out[name] = {"per_year": per_year, "all": allr, "years_up": yrs_up, "avg_trades": avg_trades, "pass": passed}
    return out


def buy_hold(bars):
    res = {}
    for y in YEARS:
        yb = [b for b in bars if b["t"].startswith(str(y))]
        if yb:
            res[y] = (yb[-1]["c"] / yb[0]["o"] - 1) * 100
    return res


def report(symbol, bars, res):
    bh = buy_hold(bars)
    L = [f"## {symbol} 4h, long only, Alpaca data", "",
         f"Bars: {bars[0]['t']} to {bars[-1]['t']} ({len(bars)} bars).", "",
         "| Strategy | " + " | ".join(str(y) for y in YEARS) + " | All PF | Trades/yr | Max DD | Gate |",
         "|---|" + "---|" * len(YEARS) + "---|---|---|---|"]
    for name, r in res.items():
        cells = [f"{r['per_year'][y]['return_pct']:+.1f}% ({r['per_year'][y]['trades']})" for y in YEARS]
        L.append(f"| {name} | " + " | ".join(cells) +
                 f" | {r['all']['pf']:.2f} | {r['avg_trades']:.0f} | {r['all']['max_dd_pct']:.1f}% | {'PASS' if r['pass'] else 'fail'} |")
    L.append("| buy and hold | " + " | ".join(f"{bh.get(y, 0):+.1f}%" for y in YEARS) + " | | | | |")
    L += ["", "Cells: return for trades entered that year (trade count)."]
    return "\n".join(L)


if __name__ == "__main__":
    parts = ["# Backtest result", "",
             f"Fee {FEE*100:.2f}% per side + 0.05% slippage. Gate: profitable in >= {GATE_MIN_YEARS_PROFITABLE} of "
             f"{len(YEARS)} years, PF >= {GATE_MIN_PF}, >= {GATE_MIN_TRADES_PER_YEAR} trades per year on average.", ""]
    for sym in SYMBOLS:
        bars = load_bars(sym, refresh="--refresh" in sys.argv)
        parts += [report(sym, bars, evaluate(bars)), ""]
    text = "\n".join(parts)
    print(text)
    with open(os.path.join(os.path.dirname(HERE), "BACKTEST_RESULT.md"), "w") as f:
        f.write(text + "\n")
