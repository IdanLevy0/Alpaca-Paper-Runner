"""Run one pre-registered multi-day card on train + validation (holdout sealed). Writes research/results/<card>.md.

py -m daily.research --card E001 [--random 200]
"""
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from daily.data import load                                                       # noqa: E402
from daily.engine import STOCK_PERIODS, decide, simulate, shifted, stats, boot_p, by_year  # noqa: E402
from daily.strategies import CARDS, BENCHMARKS                                   # noqa: E402

COSTS = {"stock": (0.0, 0.0003, 0.0005), "crypto": (0.0, 0.0025, 0.0040)}
BASE = {"stock": 0.0003, "crypto": 0.0025}
CRYPTO_PERIODS = {"train": ("2016-01-01", "2022-12-31"), "valid": ("2023-01-01", "2023-12-31"),
                  "holdout": ("2024-01-01", "2099-01-01")}
PPY = {"stock": 252, "crypto": 365}


def kind_of(card):
    return "crypto" if card.startswith("B") else "stock"


def run_card(card, n_random=200, panel=None, seed=11):
    kind = kind_of(card)
    periods = STOCK_PERIODS if kind == "stock" else CRYPTO_PERIODS
    ppy = PPY[kind]
    panel = panel if panel is not None else load(kind)
    (tr0, tr1), (va0, va1) = periods["train"], periods["valid"]
    hold = periods["holdout"][0]
    t_end = int(np.searchsorted(panel.dates, va1, side="right")) - 1     # decisions never look past validation
    base = BASE[kind]
    res = {}
    for st in CARDS[card]():
        W, R = decide(panel, st, 0, t_end)
        row = {"strategy": st, "W": W, "R": R}
        for c in COSTS[kind]:
            row[("train", c)] = simulate(panel, W, R, tr0, tr1, c, hold, periods_per_year=ppy)
        row[("valid", base)] = simulate(panel, W, R, va0, va1, base, hold, periods_per_year=ppy)
        res[st.name] = row
    bm = BENCHMARKS[card]()
    bW, bR = decide(panel, bm, 0, t_end)
    bench = {p: simulate(panel, bW, bR, a, b, base, hold, periods_per_year=ppy) for p, (a, b) in (("train", (tr0, tr1)), ("valid", (va0, va1)))}
    best = max(res, key=lambda k: stats(res[k][("train", base)][1], ppy)["sharpe"])
    row = res[best]
    row["best"] = True
    real = stats(row[("train", base)][1], ppy)["sharpe"]
    row["p"] = boot_p(row[("train", base)][1])
    rng, sh = np.random.default_rng(seed), []
    a, b = panel.day(tr0), int(np.searchsorted(panel.dates, tr1, side="right")) - 1
    st = row["strategy"]
    for _ in range(n_random):
        if st.kind == "timing":
            W2, R2 = shifted(row["W"], row["R"], a, b, int(rng.integers(21, max(22, b - a - 21))))
        else:
            class Rand:
                def weights(self, h, _st=st):
                    return _st.random_weights(h, rng)
            W2, R2 = decide(panel, Rand(), 0, b)
        sh.append(stats(simulate(panel, W2, R2, tr0, tr1, base, hold, periods_per_year=ppy)[1], ppy)["sharpe"])
    row["random_pct"] = float(np.mean([real > s for s in sh]) * 100)
    row["random_median_sharpe"] = float(np.median(sh))
    return res, bench, bm.name, periods


def gate(row, bench, base, ppy=252):
    tr, va = stats(row[("train", base)][1], ppy), stats(row[("valid", base)][1], ppy)
    btr, bva = stats(bench["train"][1], ppy), stats(bench["valid"][1], ppy)
    g1 = tr["mean_bp"] > 0 and row["p"] < 0.05 and tr["sharpe"] >= btr["sharpe"] and row["random_pct"] >= 90
    g2 = g1 and va["mean_bp"] > 0 and va["sharpe"] >= bva["sharpe"] - 0.25
    return g1, g2, tr, va, btr, bva


def report(card, res, bench, bname, periods=STOCK_PERIODS):
    kind = kind_of(card)
    ppy = PPY[kind]
    base = BASE[kind]
    c0, c1, c2 = COSTS[kind]
    L = [f"# {card} results: train + validation", "",
         f"Rules: daily/PROTOCOL.md and the card (committed before any result). Fills at the next open. "
         f"Base cost {base * 100:.2f}% per side. Train {periods['train'][0]} to {periods['train'][1]} (or first data), "
         f"validation {periods['valid'][0][:4]}-{periods['valid'][1][:4]}. Holdout (2024 on) sealed. Cash earns 0%.", "",
         "## All variants on train", "",
         f"| Variant | Per year ({c0 * 100:g}% cost) | Per year ({c1 * 100:g}%) | Per year ({c2 * 100:g}%) | Sharpe | Volatility | Max drawdown | Turnover/yr |",
         "|---|---|---|---|---|---|---|---|"]
    for k, r in res.items():
        s0, s1, s2 = (stats(r[("train", c)][1], ppy) for c in (c0, c1, c2))
        L.append(f"| {k}{' (best)' if r.get('best') else ''} | {s0['cagr_pct']:+.1f}% | {s1['cagr_pct']:+.1f}% | "
                 f"{s2['cagr_pct']:+.1f}% | {s1['sharpe']:.2f} | {s1['vol_pct']:.1f}% | {s1['max_dd_pct']:.1f}% | "
                 f"{r[('train', c1)][2]:.1f}x |")
    bt = stats(bench["train"][1], ppy)
    L += [f"| {bname} | | {bt['cagr_pct']:+.1f}% | | {bt['sharpe']:.2f} | {bt['vol_pct']:.1f}% | {bt['max_dd_pct']:.1f}% | "
          f"{bench['train'][2]:.1f}x |", "",
          "Per year = compound annual return. Sharpe = return per unit of risk (higher is better). Turnover/yr = how many "
          "times a year the whole portfolio is traded.", ""]
    k = [k for k in res if res[k].get("best")][0]
    row = res[k]
    g1, g2, tr, va, btr, bva = gate(row, bench, base, ppy)
    yt, yv = by_year(*row[("train", base)][:2]), by_year(*row[("valid", base)][:2])
    bt_y = by_year(*bench["train"][:2])
    bv_y = by_year(*bench["valid"][:2])
    L += [f"## Gate check: {k}", "",
          f"- Train after costs: {tr['cagr_pct']:+.1f}%/yr, Sharpe {tr['sharpe']:.2f} vs benchmark {btr['sharpe']:.2f}, "
          f"luck p-value {row['p']:.3f}, beats {row['random_pct']:.0f}% of random runs (their median Sharpe "
          f"{row['random_median_sharpe']:.2f}).",
          f"- Gate 1 (train): {'PASS' if g1 else 'FAIL'}.",
          f"- Validation {periods['valid'][0][:4]}-{periods['valid'][1][:4]}: {va['cagr_pct']:+.1f}%/yr, Sharpe {va['sharpe']:.2f} vs benchmark {bva['sharpe']:.2f}, "
          f"max drawdown {va['max_dd_pct']:.1f}% vs {bva['max_dd_pct']:.1f}%.",
          f"- Gate 2 (validation): {'PASS' if g2 else 'FAIL' if g1 else 'not reached (shown for information)'}.", "",
          "| Year | " + " | ".join(list(yt) + list(yv)) + " |", "|---|" + "---|" * (len(yt) + len(yv)),
          "| Strategy | " + " | ".join(f"{v:+.1f}%" for v in list(yt.values()) + list(yv.values())) + " |",
          "| Benchmark | " + " | ".join(f"{bt_y.get(y, 0):+.1f}%" for y in yt) + " | "
          + " | ".join(f"{bv_y.get(y, 0):+.1f}%" for y in yv) + " |"]
    return "\n".join(L) + "\n", g1, g2


if __name__ == "__main__":
    args = sys.argv[1:]
    card = args[args.index("--card") + 1]
    n = int(args[args.index("--random") + 1]) if "--random" in args else 200
    res, bench, bname, periods = run_card(card, n)
    text, g1, g2 = report(card, res, bench, bname, periods)
    os.makedirs(os.path.join(ROOT, "research", "results"), exist_ok=True)
    open(os.path.join(ROOT, "research", "results", card + ".md"), "w").write(text)
    print(text)
