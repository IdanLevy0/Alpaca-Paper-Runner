"""Run the pre-registered intraday hypotheses on train and validation; write STOCK_RESEARCH_REPORT.md.

python -m stocks.research            (train + validation; the holdout stays sealed)
"""
import json
import os
import sys
import time

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from stocks import features as F                          # noqa: E402
from stocks.data import Universe, PERIODS                  # noqa: E402
from stocks.engine import run, random_picker, COST         # noqa: E402
from stocks.strategies import variants                     # noqa: E402

OUT = os.path.join(ROOT, "stocks", "out")


def stats(daily, trades):
    r = np.array([x[1] for x in daily]) if daily else np.zeros(1)
    eq = np.cumprod(1 + r)
    dd = float(np.max(1 - eq / np.maximum.accumulate(eq))) if len(eq) else 0.0
    tr = np.array([t["ret"] for t in trades]) if trades else np.zeros(0)
    return {"days": len(r), "mean_bp": float(r.mean() * 1e4), "ann_pct": float(((1 + r.mean()) ** 252 - 1) * 100),
            "sharpe": float(r.mean() / r.std() * np.sqrt(252)) if r.std() > 0 else 0.0,
            "max_dd_pct": dd * 100, "trades": len(tr), "trades_per_day": len(tr) / max(1, len(r)),
            "win_pct": float((tr > 0).mean() * 100) if len(tr) else 0.0,
            "avg_trade_bp": float(tr.mean() * 1e4) if len(tr) else 0.0,
            "days_traded_pct": float(np.mean([x[2] > 0 for x in daily]) * 100) if daily else 0.0}


def boot_p(daily, n=5000, seed=3):
    r = np.array([x[1] for x in daily])
    if len(r) < 20:
        return None
    rng, m = np.random.default_rng(seed), r.mean()
    c = r - m
    means = c[rng.integers(0, len(c), size=(n, len(c)))].mean(axis=1)
    return float((means >= m).mean())


def by_year(daily):
    out = {}
    for d, r, _ in daily:
        out.setdefault(d[:4], []).append(r)
    return {y: float((np.prod(1 + np.array(v)) - 1) * 100) for y, v in out.items()}


def family(name):
    return name.split("_")[0]


def main(n_random=100, card=None):
    t0 = time.time()
    u = Universe()
    feats = {"prev_close": F.prev_close(u), "sigma60": F.sigma60(u)}
    print(f"loaded + features {time.time() - t0:.0f}s", flush=True)
    tr0, tr1 = PERIODS["train"]
    va0, va1 = PERIODS["valid"]
    res = {}
    for st in variants(card):
        row = {}
        for c in (0.0, COST, 0.0005):
            daily, trades = run(u, feats, st, tr0, tr1, cost=c)
            row[c] = (daily, trades)
        res[st.name] = {"strategy": st, "train": row}
        s = stats(*row[COST])
        print(f"{st.name}: train mean {s['mean_bp']:+.2f}bp/day, {s['trades_per_day']:.1f} trades/day "
              f"({time.time() - t0:.0f}s)", flush=True)
    for fam in sorted({family(k) for k in res}):
        names = [k for k in res if family(k) == fam]
        best = max(names, key=lambda k: np.mean([x[1] for x in res[k]["train"][COST][0]]))
        res[best]["best_of_family"] = True
        st = res[best]["strategy"]
        res[best]["p"] = boot_p(res[best]["train"][COST][0])
        real = np.mean([x[1] for x in res[best]["train"][COST][0]])
        rng, beats = np.random.default_rng(17), 0
        for _ in range(n_random):
            d, _t = run(u, feats, st, tr0, tr1, picker=random_picker(st, rng))
            beats += real > np.mean([x[1] for x in d])
        res[best]["random_pct"] = beats / n_random * 100
        res[best]["valid"] = run(u, feats, st, va0, va1)
        print(f"{best}: random done ({time.time() - t0:.0f}s)", flush=True)
    dates, on, intra = F.market_split(u, feats["prev_close"])
    split = {}
    for d, a, b in zip(dates, on, intra):
        if d >= PERIODS["holdout"][0] or not (np.isfinite(a) and np.isfinite(b)):
            continue
        y = split.setdefault(d[:4], [1.0, 1.0])
        y[0] *= 1 + a
        y[1] *= 1 + b
    return res, split


def gate(r):
    tr = stats(*r["train"][COST])
    passed1 = tr["mean_bp"] > 0 and (r.get("p") or 1) < 0.05 and (r.get("random_pct") or 0) >= 90
    va = stats(*r["valid"]) if "valid" in r else None
    passed2 = passed1 and va is not None and va["mean_bp"] > 0
    return passed1, passed2, tr, va


def report(res, split):
    L = ["# Stock intraday research: train + validation", "",
         "Rules: stocks/PROTOCOL.md (committed before any result). 100 stocks, 5-minute bars, long only, flat by 15:55. "
         f"Base cost {COST*100:.2f}% per side. Train 2016-04 to 2021-12, validation 2022-2023. Holdout (2024 on) sealed.", "",
         "## All variants on train", "",
         "| Variant | Mean/day (0% cost) | Mean/day (0.03%) | Mean/day (0.05%) | Per year (0.03%) | Sharpe | Max DD | Trades/day | Avg trade | Win |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for k, r in res.items():
        s0, s, s5 = (stats(*r["train"][c]) for c in (0.0, COST, 0.0005))
        L.append(f"| {k}{' (best)' if r.get('best_of_family') else ''} | {s0['mean_bp']:+.2f}bp | {s['mean_bp']:+.2f}bp | "
                 f"{s5['mean_bp']:+.2f}bp | {s['ann_pct']:+.1f}% | {s['sharpe']:.2f} | {s['max_dd_pct']:.0f}% | "
                 f"{s['trades_per_day']:.1f} | {s['avg_trade_bp']:+.1f}bp | {s['win_pct']:.0f}% |")
    L += ["", "bp = basis points (1bp = 0.01%). Mean/day is the whole portfolio's average daily return.", ""]
    for k, r in res.items():
        if not r.get("best_of_family"):
            continue
        p1, p2, tr, va = gate(r)
        L += [f"## Gate check: {k}", "",
              f"- Train after costs: {tr['mean_bp']:+.2f}bp/day ({tr['ann_pct']:+.1f}%/yr), luck p-value "
              f"{r['p']:.3f}, beats {r['random_pct']:.0f}% of random-stock runs.",
              f"- Gate 1 (train): {'PASS' if p1 else 'FAIL'}.",
              f"- Validation 2022-2023: {va['mean_bp']:+.2f}bp/day ({va['ann_pct']:+.1f}%/yr), {va['trades_per_day']:.1f} trades/day.",
              f"- Gate 2 (validation): {'PASS' if p2 else 'FAIL' if p1 else 'not reached'}.", "",
              "| Year | " + " | ".join(by_year(r['train'][COST][0])) + " | " + " | ".join(by_year(r['valid'][0])) + " |",
              "|---|" + "---|" * (len(by_year(r['train'][COST][0])) + len(by_year(r['valid'][0]))),
              "| Return | " + " | ".join(f"{v:+.1f}%" for v in by_year(r['train'][COST][0]).values()) + " | "
              + " | ".join(f"{v:+.1f}%" for v in by_year(r['valid'][0]).values()) + " |", ""]
    L += ["## H3: where the market's return happens (equal-weight 100 stocks, 2016-2023)", "",
          "| Year | Overnight (close to open) | Intraday (open to close) |", "|---|---|---|"]
    for y, (a, b) in split.items():
        L.append(f"| {y} | {(a - 1) * 100:+.1f}% | {(b - 1) * 100:+.1f}% |")
    L += ["", "A flat-by-close strategy can only ever earn from the intraday column."]
    return "\n".join(L)


if __name__ == "__main__":
    # python -m stocks.research                 -> H001 + H002, writes STOCK_RESEARCH_REPORT.md
    # python -m stocks.research --card H003     -> that card only, writes research/results/H003.md
    args = sys.argv[1:]
    card = args[args.index("--card") + 1] if "--card" in args else None
    n = int(args[args.index("--random") + 1]) if "--random" in args else 100
    res, split = main(n, card)
    text = report(res, split)
    if card:
        os.makedirs(os.path.join(ROOT, "research", "results"), exist_ok=True)
        path = os.path.join(ROOT, "research", "results", card + ".md")
        text = text.replace("# Stock intraday research: train + validation", f"# {card} results: train + validation")
    else:
        path = os.path.join(ROOT, "STOCK_RESEARCH_REPORT.md")
    with open(path, "w") as f:
        f.write(text + "\n")
    print(text)
